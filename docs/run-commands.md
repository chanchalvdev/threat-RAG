# ThreatRAG — Manual Run Commands

Individual commands to bring up every service by hand, in order. Run each in its own
terminal tab (backend and frontend must keep running in the foreground unless you background
them with `&`).

For the automated version of this, use `./start-services.sh` instead.

---

## 1. Postgres (docker)

```bash
cd threatrag/infra
docker compose up -d postgres
```

Check it's ready:
```bash
docker exec infra-postgres-1 pg_isready -U threatrag
```

## 2. Qdrant (vector store)

```bash
docker start siemagent-qdrant-1
```
(or, if that container doesn't exist on your machine, start it fresh with the project's own compose: `docker compose -f threatrag/infra/docker-compose.yml up -d qdrant`)

Check it's ready:
```bash
curl http://localhost:6333/
```

## 3. Ollama (local embeddings)

```bash
docker start siemagent-ollama-1
```
(or `docker compose -f threatrag/infra/docker-compose.yml up -d ollama`)

Check it's ready:
```bash
curl http://localhost:11434/
```

## 4. Backend (FastAPI)

```bash
cd threatrag/backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

First-time setup, if `.venv` doesn't exist yet:
```bash
cd threatrag/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Check it's ready:
```bash
curl http://localhost:8000/health
```

## 5. Frontend (Vite + React)

```bash
cd threatrag/web
npm run dev -- --port 5174
```

First-time setup, if `node_modules` doesn't exist yet:
```bash
cd threatrag/web
npm install
```

Then open:
```
http://localhost:5174
```

---

## Stopping everything

```bash
# Backend
pkill -f "uvicorn app.main"

# Frontend — find the PID on the port, then kill it
lsof -nP -iTCP:5174 -sTCP:LISTEN -t | xargs kill

# Postgres
docker stop infra-postgres-1

# Qdrant / Ollama (shared containers — only stop if nothing else needs them)
docker stop siemagent-qdrant-1 siemagent-ollama-1
```

---

## Database connection

```
Host:     localhost
Port:     5435
Database: threatrag
User:     threatrag
Password: threatrag

postgresql://threatrag:threatrag@localhost:5435/threatrag
```

```bash
docker exec -it infra-postgres-1 psql -U threatrag -d threatrag
```
