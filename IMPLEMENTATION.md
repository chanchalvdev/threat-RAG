# ThreatRAG — Implementation Guide
Step-by-step record of what was built and how to run it.

---

## Step 1 — Harness Engineering

Before any code, the development harness was set up to enforce quality gates automatically.

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Project guide: tech stack, conventions, Kimchi LLM config, env vars |
| `.claude/settings.json` | Hook config: runs `ruff check` on every Python edit |
| `.claude/hooks/post-edit.sh` | PostToolUse hook: lint gate |
| `.claude/hooks/on-stop.sh` | Stop hook: prints session file summary |
| `.claude/agents/planner.md` | Planner agent prompt |
| `.claude/agents/reviewer.md` | Security code reviewer prompt |
| `.claude/agents/validator.md` | QA validator prompt |
| `.claude/skills/validate.md` | `/validate` skill: lint → typecheck → test → health |

---

## Step 2 — Specifications (spec-first)

All specs were written **before** any implementation code.

| File | Contents |
|------|---------|
| `spec/SPEC.md` | Master spec: problem, personas, phases, non-functional requirements |
| `spec/phase1.md` | 16 acceptance criteria for RAG core (F1.1–F1.16) |
| `spec/phase2.md` | 12 acceptance criteria for agentic loop (F2.1–F2.12) |
| `spec/phase3.md` | 13 acceptance criteria for multi-agent + eval (F3.1–F3.13) |
| `spec/api-schema.md` | Full API contract with JSON request/response examples |
| `spec/validation-plan.md` | 4 validation levels + curl smoke tests |

---

## Step 3 — Infrastructure

```
threatrag/infra/
  docker-compose.yml   # Qdrant, PostgreSQL+pgvector, Ollama, backend, frontend
  nginx.conf           # Reverse proxy + SSE stream support (no buffering)

threatrag/
  Makefile             # All developer commands (setup, dev, test, ingest, docker-up…)
```

**Services started by `make docker-up`:**
| Service | Port | Purpose |
|---------|------|---------|
| Qdrant | 6333 | Vector store for embeddings |
| PostgreSQL 17 + pgvector | 5432 | Report storage + vector search |
| Ollama | 11434 | Local `nomic-embed-text` embeddings (768-dim) |
| Backend (FastAPI) | 8000 | API server |
| Frontend (nginx) | 3000 | React SPA |

---

## Step 4 — Backend (Phase 1: RAG Core)

```
backend/app/
  core/
    config.py          # Settings (BaseSettings) — reads from .env
    logging.py         # structlog JSON logger + request middleware
  models/
    schemas.py         # Pydantic models: QueryRequest, RAGResponse, IngestJob, HealthCheck
  rag/
    store.py           # QdrantStore: create collection, upsert, cosine search
    embedder.py        # OllamaEmbedder + NomicEmbedder; batch with asyncio.Semaphore
    ingestion.py       # PDF ingest (PyPDFLoader), MITRE STIX JSON ingest
    prompts.py         # RAG_PROMPT (security analyst system prompt)
    sanitiser.py       # OWASP LLM Top 10: injection detection + output redaction
    chain.py           # ThreatRAGChain: LCEL pipeline, stream() + query()
  api/
    deps.py            # FastAPI Depends() factories (cached store + chain)
    routes/
      query.py         # POST /query  POST /query/stream (SSE)
      ingest.py        # POST /ingest/pdf|mitre|owasp  GET /ingest/status|stats
  main.py              # FastAPI app, lifespan, CORS, router mount, /health
```

**Flow:**  
`POST /api/v1/query` → injection check → embed question → Qdrant search → RAG prompt + LLM (Kimchi) → sanitise output → return sources + answer

**LLM config (Kimchi):**
```python
ChatOpenAI(
    model="kimi-k2-5",
    openai_api_key=settings.kimchi_api_key,
    openai_api_base="https://api.kimchiinference.com/v1",
    streaming=True,
)
```

---

## Step 5 — Backend (Phase 2: Agentic Loop)

```
backend/app/
  models/
    agent_schemas.py   # AgentThought, AgentChunk, AgentDone, AgentError; to_sse()
  agent/
    tools.py           # ThreatRAGSearchTool, NVDCVETool, TavilySearchTool
    react_agent.py     # ThreatIntelAgent using langgraph.prebuilt.create_react_agent
    session.py         # SessionManager: 30-min TTL, max 100 sessions, background eviction
  api/routes/
    chat.py            # POST /chat/stream (SSE)  GET/DELETE /chat/history/{id}
```

**Why `langgraph.prebuilt.create_react_agent`?**  
LangChain 1.3.x removed `AgentExecutor`. The prebuilt LangGraph function is the correct API in 2025.

**Streaming:**  
`astream_events(version="v2")` → `on_tool_start` / `on_tool_end` / `on_chat_model_stream` events → SSE chunks to browser

---

## Step 6 — Backend (Phase 3: Multi-Agent + Evaluation)

```
backend/app/
  agent/
    graph.py           # InvestigationState, researcher_node → critic_node → reporter_node
  db/
    connection.py      # psycopg async pool; lifespan hook connects on startup
    reports.py         # save_report(), get_reports() with pgvector similarity search
  evaluation/
    ragas_eval.py      # RAGAs scores (lazy import; returns zeros if ragas not installed)
  api/routes/
    investigate.py     # POST /investigate/stream (SSE, multi-agent graph)
    evaluate.py        # POST /evaluate → RAGAs faithfulness / relevancy / precision / recall
```

**Multi-agent flow:**
```
researcher_node  →  critic_node  →  reporter_node
    (gather)          (validate)       (write report)
        ↑__________________|
        (iterates if critique found issues)
```

---

## Step 7 — Frontend

```
web/src/
  lib/api.ts            # All typed API functions; SSE stream parser; session_id from headers
  components/
    Layout.tsx           # Collapsible sidebar + HealthDot
    SourceCard.tsx       # Source document card (collapsed/expanded)
    ChatMessage.tsx      # User/assistant messages with ReactMarkdown + copy button
    ToolCallTimeline.tsx # ReAct tool call cards with status animation
    ReportViewer.tsx     # Streaming markdown report + RAGAs score bars
  pages/
    Chat.tsx             # Chat interface with session management
    KnowledgeBase.tsx    # PDF drag-drop + MITRE/OWASP ingest + stats chart
    Investigate.tsx      # IOC input → multi-agent stream → report
    Analytics.tsx        # RAGAs eval form + score history charts
```

**Tech stack:** React 18 + TypeScript + Vite + Tailwind CSS + @tanstack/react-query + recharts + react-markdown

---

## Step 8 — Tests (39/39 passing)

```
tests/unit/
  test_sanitiser.py   10 tests — injection patterns, HTML escape, secret redaction
  test_ingestion.py    5 tests — MITRE STIX filter, batch size, PDF payload
  test_chain.py        5 tests — RAGResponse structure, source fields, doc_type filter
  test_tools.py        9 tests — NVD parsing, CVE validation, RAG search, Tavily fallback
  test_ragas.py        4 tests — exception handling, missing ragas package, score model
  test_routes.py       6 tests — health, query, short question 422, injection 400, SSE, ingest 202
```

**Test isolation:** FastAPI `dependency_overrides` + `AsyncMock` — no real LLM calls in unit tests.

---

## Step 9 — Deployment Files

```
backend/Dockerfile      # multi-stage: builder installs deps → runtime as non-root user
web/Dockerfile          # multi-stage: node builds → nginx serves static files
web/postcss.config.js   # Tailwind CSS PostCSS config
infra/nginx.conf        # SPA routing + /api proxy with SSE buffering disabled
infra/docker-compose.yml # all 5 services with health checks and depends_on
```

---

## Validation Results

| Check | Result |
|-------|--------|
| `ruff check app/` | All checks passed |
| `tsc --noEmit` (frontend) | No errors |
| `npm run build` (frontend) | ✓ built in ~2s |
| `pytest tests/unit/ -q` | 39 passed, 0 failed |

---

## How to Run (Quick Start)

```bash
# 1 — Copy .env and add your Kimchi API key
cp backend/.env.example backend/.env
# Edit backend/.env: set KIMCHI_API_KEY=your_key_here

# 2 — Start infrastructure (Qdrant, Postgres, Ollama)
make docker-up

# 3 — Pull embedding model
make pull-models    # pulls nomic-embed-text into Ollama

# 4 — Run database migration
make migrate

# 5 — Start backend (dev mode, auto-reload)
make dev            # http://localhost:8000

# 6 — Start frontend (dev mode, hot-reload)
make dev-web        # http://localhost:5173

# 7 — Ingest threat intel
curl -X POST http://localhost:8000/api/v1/ingest/mitre
curl -X POST http://localhost:8000/api/v1/ingest/owasp

# 8 — Smoke test
curl http://localhost:8000/health/ready
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is prompt injection in LLM applications?"}'
```

---

## Environment Variables (backend/.env)

```
KIMCHI_API_KEY=your_key_here
KIMCHI_BASE_URL=https://api.kimchiinference.com/v1
LLM_MODEL=kimi-k2-5

QDRANT_URL=http://localhost:6333
OLLAMA_URL=http://localhost:11434

POSTGRES_DSN=postgresql://threatrag:threatrag@localhost:5432/threatrag

TAVILY_API_KEY=           # optional — enables web search tool
LANGFUSE_SECRET_KEY=      # optional — enables LLM observability
```
