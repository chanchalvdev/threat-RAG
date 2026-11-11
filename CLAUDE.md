# ThreatRAG — Claude Code Project Guide

## Project Overview
ThreatRAG is a cybersecurity RAG (Retrieval-Augmented Generation) pipeline that ingests
MITRE ATT&CK and the OWASP LLM Top 10 into a vector store (CVE data is looked up live
from NVD, not ingested), then answers analyst questions with cited sources and an agentic
investigation workflow.

## Repository Layout
```
threat-RAG/
├── .claude/              # Claude Code harness (hooks, agents, skills)
│   ├── settings.json     # permissions + hook config
│   ├── hooks/            # shell scripts triggered by Claude events
│   ├── agents/           # subagent prompt files
│   └── skills/           # skill definitions
├── spec/                 # Specification files (source of truth)
│   ├── SPEC.md           # master specification
│   ├── phase1.md         # Phase 1 detailed spec
│   ├── phase2.md         # Phase 2 detailed spec
│   ├── phase3.md         # Phase 3 detailed spec
│   ├── phase4.md         # Phase 4: Phase-3 completion + hardening
│   ├── phase5-9-plan.md  # Phases 5–9 plan and status
│   ├── api-schema.md     # API contract
│   └── validation-plan.md # test & validation checklist
└── threatrag/            # Application code
    ├── backend/          # FastAPI Python backend
    │   ├── app/          # Application source
    │   ├── tests/        # Unit + integration tests
    │   ├── migrations/   # SQL migrations
    │   └── data/         # Data files (gitignored)
    ├── web/              # React 18 + TypeScript frontend
    └── infra/            # Docker + deployment configs
```

## Tech Stack
| Layer | Technology |
|---|---|
| Backend | Python 3.13 + FastAPI + Pydantic v2 |
| RAG | LangChain 1.3 |
| Agents | LangGraph 1.2 |
| LLM | Gemini primary, Kimchi fallback (both OpenAI-compatible) |
| Embeddings | Ollama nomic-embed-text (local) |
| Vector DB | Qdrant |
| Relational DB | PostgreSQL + pgvector (Phase 3) |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Streaming | SSE (FastAPI StreamingResponse) |

## LLM Configuration
- Primary: Gemini via its OpenAI-compatible endpoint — `GEMINI_API_KEY`, `GEMINI_MODEL`
- Fallback: Kimchi — `KIMCHI_API_KEY`, `KIMCHI_BASE_URL`, `LLM_MODEL`
- Always build models with `app/core/llm.py:get_llm`; never construct `ChatOpenAI` elsewhere
- Providers retire model IDs: if a call returns 404, list `/models` and update the env var

## Development Phases
- **Phase 1** — RAG Core: ingest MITRE ATT&CK + OWASP, basic Q&A with citations
- **Phase 2** — Agentic Loop: ReAct agent, NVD CVE tool, web search, SSE chat
- **Phase 3** — Multi-Agent: LangGraph Researcher→Critic→Reporter, LLM-judge eval, pgvector
- **Phase 4** — Phase-3 completion and hardening (`spec/phase4.md`)
- **Phases 5–9** — packaging, eval harness, hybrid retrieval, guardrails, production shape (`spec/phase5-9-plan.md`)

## Code Conventions
- Each file ≤ 150 lines — split at logical boundaries
- One responsibility per file (store.py, embedder.py, chain.py, etc.)
- All async/await — no sync IO on the hot path
- Pydantic models for all API contracts
- No business logic in route handlers — delegate to service layer
- Errors: raise typed exceptions, let FastAPI exception handlers format them

## Environment Variables (backend/.env)
```
GEMINI_API_KEY=<your-key>
GEMINI_MODEL=gemini-3.5-flash-lite
KIMCHI_API_KEY=<optional fallback key>
KIMCHI_BASE_URL=https://llm.kimchi.dev/openai/v1
LLM_MODEL=kimi-k2.7
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=threat_intel
OLLAMA_URL=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
DATABASE_URL=postgresql://threatrag:threatrag@localhost:5435/threatrag
DEBUG=true
```

## Running Locally
```bash
# Start infrastructure
docker compose -f threatrag/infra/docker-compose.yml up -d

# Backend
cd threatrag/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd threatrag/web
npm install && npm run dev

# Tests
cd threatrag/backend
pytest tests/unit -v
pytest tests/integration -v -m integration
```

## Validation Checklist (per feature)
1. Unit tests pass (`pytest tests/unit -v`)
2. Type check passes (`mypy app/`)
3. Linting clean (`ruff check app/`)
4. Integration test passes if applicable
5. Manual smoke test via `/health/ready`

## Key Decisions
- Gemini is the primary LLM and Kimchi the fallback (not Anthropic) — use `app/core/llm.py:get_llm`, which builds `langchain_openai.ChatOpenAI` with a custom base_url
- Embeddings are local via Ollama (free) — `nomic-embed-text` at 768 dims
- All streaming via SSE — WebSocket only in Phase 3 for agent progress
- Security hardening per OWASP LLM Top 10 is built-in, not bolted on
