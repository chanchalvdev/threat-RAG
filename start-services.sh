#!/usr/bin/env bash
#
# ThreatRAG — manual, step-by-step service bring-up.
#
# Starts each dependency one at a time, waits for it to actually be healthy,
# and prints what it did before moving to the next one. Meant to be read
# top-to-bottom so you can see exactly what "running the app" involves.
#
# Usage:
#   ./start-services.sh          start everything
#   ./start-services.sh status   just print current status of each service
#   ./start-services.sh stop     stop backend + frontend (docker infra left running)
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/threatrag/backend"
WEB_DIR="$ROOT_DIR/threatrag/web"
LOG_DIR="$ROOT_DIR/.run"
mkdir -p "$LOG_DIR"

BACKEND_PORT=8000
FRONTEND_PORT=5174
POSTGRES_CONTAINER=infra-postgres-1

c_step()  { printf '\n\033[1;36m▶ %s\033[0m\n' "$1"; }
c_ok()    { printf '\033[1;32m  ✓ %s\033[0m\n' "$1"; }
c_warn()  { printf '\033[1;33m  ! %s\033[0m\n' "$1"; }
c_fail()  { printf '\033[1;31m  ✗ %s\033[0m\n' "$1"; }

wait_for() {
  # wait_for <name> <curl-url> <timeout-seconds>
  local name="$1" url="$2" timeout="${3:-30}" waited=0
  until curl -fsS -m 2 "$url" >/dev/null 2>&1; do
    waited=$((waited + 1))
    if [ "$waited" -ge "$timeout" ]; then
      c_fail "$name did not become ready within ${timeout}s (checked $url)"
      return 1
    fi
    sleep 1
  done
  c_ok "$name is ready ($url)"
}

pid_on_port() { lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null || true; }

# ---------------------------------------------------------------------------
status() {
  c_step "Postgres (docker: $POSTGRES_CONTAINER, port 5435)"
  docker ps --filter "name=$POSTGRES_CONTAINER" --format '  {{.Status}}' | grep -q . \
    && c_ok "container is running" || c_fail "container is not running"

  c_step "Qdrant (port 6333, shared container)"
  curl -fsS -m 2 http://localhost:6333/ >/dev/null 2>&1 && c_ok "reachable" || c_fail "not reachable"

  c_step "Ollama (port 11434, shared container)"
  curl -fsS -m 2 http://localhost:11434/ >/dev/null 2>&1 && c_ok "reachable" || c_fail "not reachable"

  c_step "Backend (FastAPI, port $BACKEND_PORT)"
  if [ -n "$(pid_on_port $BACKEND_PORT)" ]; then
    curl -fsS -m 2 http://localhost:$BACKEND_PORT/health >/dev/null 2>&1 \
      && c_ok "running, PID $(pid_on_port $BACKEND_PORT), /health ok" \
      || c_warn "port open (PID $(pid_on_port $BACKEND_PORT)) but /health failing"
  else
    c_fail "nothing listening on $BACKEND_PORT"
  fi

  c_step "Frontend (Vite, port $FRONTEND_PORT)"
  if [ -n "$(pid_on_port $FRONTEND_PORT)" ]; then
    c_ok "running, PID $(pid_on_port $FRONTEND_PORT)"
  else
    c_fail "nothing listening on $FRONTEND_PORT"
  fi
}

stop() {
  c_step "Stopping backend on port $BACKEND_PORT"
  pkill -f "uvicorn app.main" 2>/dev/null && c_ok "backend stopped" || c_warn "backend was not running"

  c_step "Stopping frontend on port $FRONTEND_PORT"
  local fe_pid; fe_pid="$(pid_on_port $FRONTEND_PORT)"
  [ -n "$fe_pid" ] && kill "$fe_pid" && c_ok "frontend stopped" || c_warn "frontend was not running"

  c_warn "Postgres/Qdrant/Ollama containers left running (shared infra) — stop manually if needed:"
  echo "    docker stop $POSTGRES_CONTAINER"
}

start() {
  # 1. Postgres — the app's own container (Qdrant/Ollama are assumed already
  #    running as shared containers used by other local projects too).
  c_step "1/4 Starting Postgres ($POSTGRES_CONTAINER on port 5435)"
  (cd "$ROOT_DIR/threatrag/infra" && docker compose up -d postgres)
  wait_for "Postgres" "http://localhost:5435" 20 2>/dev/null || true # curl can't speak pg wire proto, just give it a beat
  sleep 2
  docker exec "$POSTGRES_CONTAINER" pg_isready -U threatrag >/dev/null 2>&1 \
    && c_ok "Postgres accepting connections on 5435" \
    || c_fail "Postgres not ready — check: docker logs $POSTGRES_CONTAINER"

  # 2. Qdrant + Ollama — verify the shared containers are up (not started here,
  #    since other projects on this machine share them).
  c_step "2/4 Checking Qdrant (6333) and Ollama (11434)"
  wait_for "Qdrant" "http://localhost:6333/" 10 \
    || c_warn "Qdrant not reachable — start it, e.g.: docker start siemagent-qdrant-1"
  wait_for "Ollama" "http://localhost:11434/" 10 \
    || c_warn "Ollama not reachable — start it, e.g.: docker start siemagent-ollama-1"

  # 3. Backend — FastAPI via uvicorn, from the project's own venv.
  c_step "3/4 Starting backend (FastAPI on port $BACKEND_PORT)"
  if [ -n "$(pid_on_port $BACKEND_PORT)" ]; then
    c_warn "something is already listening on $BACKEND_PORT — killing it first"
    pkill -f "uvicorn app.main" 2>/dev/null || true
    sleep 1
  fi
  if [ ! -x "$BACKEND_DIR/.venv/bin/uvicorn" ]; then
    c_fail "no venv found at $BACKEND_DIR/.venv — set it up first:"
    echo "    cd $BACKEND_DIR && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
  fi
  (
    cd "$BACKEND_DIR"
    nohup .venv/bin/uvicorn app.main:app --port "$BACKEND_PORT" > "$LOG_DIR/backend.log" 2>&1 &
    echo $! > "$LOG_DIR/backend.pid"
  )
  wait_for "Backend" "http://localhost:$BACKEND_PORT/health" 30

  # 4. Frontend — Vite dev server.
  c_step "4/4 Starting frontend (Vite on port $FRONTEND_PORT)"
  if [ -n "$(pid_on_port $FRONTEND_PORT)" ]; then
    c_warn "something is already listening on $FRONTEND_PORT — killing it first"
    kill "$(pid_on_port $FRONTEND_PORT)" 2>/dev/null || true
    sleep 1
  fi
  (
    cd "$WEB_DIR"
    nohup npm run dev -- --port "$FRONTEND_PORT" > "$LOG_DIR/frontend.log" 2>&1 &
    echo $! > "$LOG_DIR/frontend.pid"
  )
  wait_for "Frontend" "http://localhost:$FRONTEND_PORT/" 30

  echo
  c_ok "All services up."
  echo "    Frontend  → http://localhost:$FRONTEND_PORT"
  echo "    Backend   → http://localhost:$BACKEND_PORT  (docs at /docs)"
  echo "    Postgres  → localhost:5435  (db=threatrag user=threatrag password=threatrag)"
  echo "    Qdrant UI → http://localhost:6333/dashboard"
  echo
  echo "    Logs: $LOG_DIR/backend.log  $LOG_DIR/frontend.log"
  echo "    Stop: ./start-services.sh stop"
}

case "${1:-start}" in
  start)  start ;;
  status) status ;;
  stop)   stop ;;
  *) echo "Usage: $0 [start|status|stop]"; exit 1 ;;
esac
