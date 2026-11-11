# ThreatRAG

Retrieval-augmented threat intelligence for SOC analysts: cited answers over MITRE ATT&CK and
the OWASP LLM Top 10, a tool-using chat agent, and a Researcher → Critic → Reporter
investigation pipeline that turns an indicator (CVE, IP, domain, hash) into a structured report.

![ThreatRAG architecture](docs/diagrams/threatrag-architecture.gif)

## What it does

| Capability | How |
|---|---|
| Cited Q&A | Retrieval over MITRE ATT&CK + OWASP LLM Top 10 in Qdrant, streamed over SSE |
| Agentic chat | LangGraph ReAct agent, 10-turn memory, capped tool calls, live tool timeline |
| IOC investigation | LangGraph Researcher → Critic → Reporter with a revision loop and streamed report |
| Enrichment tools | NVD, CISA KEV, FIRST EPSS, Shodan InternetDB, AbuseIPDB, OTX, abuse.ch, web search |
| Report memory | Reports stored in PostgreSQL + pgvector; similar past investigations surfaced |
| Evaluation | LLM-judge metrics (faithfulness, relevancy, context precision/recall) with history |
| Resilience | Provider fallback (Gemini → Kimchi) that never switches mid-stream |

## Quickstart

Requires Docker, Python 3.13 and Node 20.

```bash
# 1. Infrastructure: Qdrant, Postgres (pgvector), Ollama
docker compose -f threatrag/infra/docker-compose.yml up -d qdrant postgres ollama
docker compose -f threatrag/infra/docker-compose.yml exec ollama ollama pull nomic-embed-text

# 2. Backend
cd threatrag/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env            # set GEMINI_API_KEY (or KIMCHI_API_KEY)
uvicorn app.main:app --reload --port 8000

# 3. Load the knowledge base (downloads MITRE ATT&CK and the OWASP PDF on first run)
python -m app.scripts.ingest_all

# 4. Frontend
cd ../web && npm install && npm run dev      # http://localhost:5173
```

API docs with runnable examples: http://localhost:8000/docs.
`./start-services.sh` does steps 1–4 with health checks; see [docs/run-commands.md](docs/run-commands.md).

## Architecture

```
React 18 (Vite, Tailwind)  ──SSE/REST──▶  FastAPI
                                            ├─ /query        ThreatRAGChain (retrieve → prompt → stream)
                                            ├─ /chat         ReAct agent + session memory
                                            ├─ /investigate  LangGraph: Researcher → Critic → Reporter
                                            ├─ /ingest       MITRE STIX, OWASP PDF, custom PDF upload
                                            └─ /evaluate     LLM-judge metrics + history
                                                 │
        Qdrant (vectors) · Ollama nomic-embed-text (embeddings) · PostgreSQL + pgvector (reports)
        Gemini → Kimchi (LLM, OpenAI-compatible) · NVD / KEV / EPSS / Shodan / OTX / abuse.ch (tools)
```

A fuller map with the request flows is in [docs/architecture.html](docs/architecture.html).

## Design decisions

- **One LLM construction point.** `app/core/llm.py` builds every chat model. The fallback is a
  `ChatOpenAI` subclass rather than `.with_fallbacks()` so `bind_tools()` still works for the
  ReAct agent, and it refuses to switch providers once tokens have streamed.
- **Deterministic citations.** The Researcher's sources come from a direct retrieval, not from
  whatever the model chose to call, so every report carries evidence.
- **Technique validation.** Reports are checked against the ingested ATT&CK corpus; a wrong
  ID/name pairing is annotated rather than silently shipped.
- **Idempotent ingestion.** Point IDs are `uuid5` of the source key; re-ingesting overwrites.
  Points are tagged with their embedding model and mixing vector spaces is refused at startup.
- **Readiness that tells the truth.** `/health/ready` runs a one-token completion, because a
  provider can list models while refusing every request.
- **Small files.** Every source file is ≤ 150 lines with one responsibility.

## Quality gates

```bash
cd threatrag/backend
ruff check app/ && mypy app/ && pytest tests/unit --cov=app --cov-fail-under=80
cd ../web && npm run lint && npm run typecheck && npm run build
```

CI (`.github/workflows/ci.yml`) runs the same gates plus Docker builds and a Trivy scan.

## Known limits

Tracked with their fixes in [spec/phase5-9-plan.md](spec/phase5-9-plan.md):
retrieval is dense-only, the prompt-injection filter is a regex list, chat sessions and ingest
jobs live in process memory, and there is no published benchmark yet.

## Repository layout

```
spec/                 specifications (source of truth) and the phase plan
docs/                 architecture map, user guide, run commands, build log
threatrag/backend/    FastAPI app, tests, migrations
threatrag/web/        React frontend
threatrag/infra/      docker-compose and nginx
```

## Licence

MIT — see [LICENSE](LICENSE).
