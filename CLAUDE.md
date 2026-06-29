# ThreatRAG — Claude Code Project Guide

## Project Overview
ThreatRAG is a cybersecurity RAG (Retrieval-Augmented Generation) pipeline that ingests
MITRE ATT&CK, OWASP Top 10, and CVE data into a vector store, then answers analyst
questions with cited sources and an agentic investigation workflow.

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
| Backend | Python 3.11 + FastAPI + Pydantic v2 |
| RAG | LangChain 0.3 + LCEL |
| Agents | LangGraph 0.2 (Phase 3) |
| LLM | Kimchi kimi-k2.6 (OpenAI-compatible) |
| Embeddings | Ollama nomic-embed-text (local) |
| Vector DB | Qdrant |
| Relational DB | PostgreSQL + pgvector (Phase 3) |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Streaming | SSE (FastAPI StreamingResponse) |

## LLM Configuration (Kimchi)
- Provider: Kimchi Inference (OpenAI-compatible endpoint)
- Model: `kimi-k2-5` / `kimi-k2.6`
- Base URL: `https://api.kimchiinference.com/v1` (check env)
- Key env var: `KIMCHI_API_KEY`
- Use `langchain_openai.ChatOpenAI` with `openai_api_base` pointing to Kimchi endpoint

## Development Phases
- **Phase 1** — RAG Core: ingest MITRE ATT&CK + OWASP, basic Q&A with citations
- **Phase 2** — Agentic Loop: ReAct agent, NVD CVE tool, web search, SSE chat
- **Phase 3** — Multi-Agent: LangGraph Researcher→Critic→Reporter, RAGAs eval, pgvector

## Code Conventions
- Each file ≤ 150 lines — split at logical boundaries
- One responsibility per file (store.py, embedder.py, chain.py, etc.)
- All async/await — no sync IO on the hot path
- Pydantic models for all API contracts
- No business logic in route handlers — delegate to service layer
- Errors: raise typed exceptions, let FastAPI exception handlers format them

## Environment Variables (backend/.env)
```
KIMCHI_API_KEY=<your-key>
KIMCHI_BASE_URL=https://api.kimchiinference.com/v1
LLM_MODEL=kimi-k2-5
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=threat_intel
OLLAMA_URL=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
DATABASE_URL=postgresql://threatrag:threatrag@localhost:5432/threatrag
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
- Kimchi is the primary LLM (not Anthropic) — use `langchain_openai.ChatOpenAI` + custom base_url
- Embeddings are local via Ollama (free) — `nomic-embed-text` at 768 dims
- All streaming via SSE — WebSocket only in Phase 3 for agent progress
- Security hardening per OWASP LLM Top 10 is built-in, not bolted on
