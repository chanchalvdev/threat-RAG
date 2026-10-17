# Phase 4 — Phase-3 Completion + Production Hardening

**Date:** 2026-10-16
**Status:** Part A implemented + live-validated 2026-10-16 · Part B/C planned

## Why this phase exists
A code audit on 2026-10-16 found Phases 1–3 *scaffolded* but several Phase 2/3
acceptance criteria not actually met at runtime:

| # | Gap | Where | Impact |
|---|---|---|---|
| G1 | Researcher binds tools but never executes them (one `ainvoke`, tool calls dropped) | `agent/graph.py` | Investigations contain no KB/NVD/web evidence |
| G2 | `/investigate/stream` runs the whole graph then fakes one `node_start` | `routes/investigate.py` | UI agent cards never transition; no live progress |
| G3 | Reports never persisted; `/investigate/save` saves nothing; DB pool + migrations never wired; `conn.fetchall` is not a psycopg API | `db/*`, `main.py` | No history, no similar-report search |
| G4 | Chat agent ignores session history (only the new question is sent) | `agent/react_agent.py` | Multi-turn memory broken (V2.2 fails) |
| G5 | `MAX_TOOL_CALLS` declared but never enforced | `agent/tools.py` | Unbounded agent loops |
| G6 | `ragas`/`datasets` not installed; RAGAs defaults to OpenAI LLM | `evaluation/ragas_eval.py` | `/evaluate` always returns 0.0 |
| G7 | Analytics page charts are `Math.random()` mock data | `web/src/pages/Analytics.tsx` | No real quality signal |
| G8 | PDF upload writes `file.filename` verbatim (path traversal), no type/size limit | `routes/ingest.py` | Arbitrary file write |
| G9 | Ingestion uses random `uuid4` IDs; sequential embedding | `rag/ingestion.py` | Re-ingest duplicates corpus; slow |
| G10 | `ChatOpenAI` built in 4 places with deprecated kwargs (mypy errors) | chain/agent/graph/chat | Drift, 14 mypy errors |
| G11 | `/health/ready` hard-codes `llm: ok`; no Postgres check | `main.py` | Readiness lies |
| G12 | `requirements.txt` pins LangChain 0.3 / LangGraph 0.2; venv runs 1.3 / 1.2 | `requirements.txt` | Docker image ≠ dev runtime |
| G13 | CORS origins hard-coded; no auth on any endpoint | `main.py` | Not deployable |
| G14 | `/ingest/stats` returns empty `doc_type_counts` | `routes/ingest.py` | KB page shows nothing per source |

---

## Part A — Phase 3 completion (this iteration)

### F4.1 LLM factory — `app/core/llm.py`
`get_llm(streaming=False, temperature=0.1) -> ChatOpenAI` using `model`, `api_key`,
`base_url`. All call sites use it. Fixes G10.

### F4.2 Investigation package (split `graph.py`, ≤150 LOC each)
- `agent/investigation_models.py` — State, Request (IOC validated per type), Report, events
- `agent/nodes.py` — researcher / critic / reporter
- `agent/graph.py` — graph assembly, `run_investigation`, `stream_investigation`

**Researcher** = `create_react_agent(llm, tools)` sub-agent, `recursion_limit = 2·MAX_TOOL_CALLS+1`.
Captures `tool_calls` (name, input, output[:300]) and runs a direct KB retrieval
for the IOC to populate `sources` (deterministic citations). Fixes G1, G5.

**Critic** returns `APPROVED` or `NEEDS_REVISION: …`; max 2 research iterations.

**Reporter** streams tokens (`report_chunk`).

### F4.3 Real streaming (fixes G2)
`stream_investigation()` maps `astream_events(v2)` → SSE:
`node_start{node,iteration}`, `tool_call{node,name,input}`, `node_done{node,summary}`,
`routing{from,to,reason}`, `report_chunk{data}`, `done{report_id,sources,similar}`, `error{data}`.

### F4.4 Persistence (fixes G3)
- Lifespan: run migrations + open pool; if Postgres is down, log and degrade (investigations still run, `report_id=null`).
- `db/reports.py` uses `cursor.fetchall()`, `%s::vector` literals.
- `services/investigation_service.py`: run → embed report → save → similar.
- Routes: `GET /investigate/reports`, `GET /investigate/reports/{id}`, `POST /investigate/save` (real save).

### F4.5 Chat memory (fixes G4, G5)
`ThreatIntelAgent` keeps LangChain messages (last 20 = 10 turns), passes them each turn,
appends the final answer after streaming; `recursion_limit` enforces MAX_TOOL_CALLS.
Injection check on chat + investigate inputs.

### F4.6 Evaluation (fixes G6, G7)
RAGAs wired to Kimchi (`LangchainLLMWrapper`) + Ollama embeddings. Scores persisted in
`evaluations` table (migration 002); `GET /evaluate/history`; Analytics charts read it.

### F4.7 Security & ops quick wins (fixes G8, G9, G11–G14)
- Upload: basename-only filename, `.pdf` + magic bytes, 25 MB cap.
- Deterministic `uuid5` point IDs + batched embedding.
- Readiness checks LLM (`GET /models`) and Postgres.
- `CORS_ORIGINS` + optional `API_KEY` (header `X-API-Key`) from settings.
- Per-doc-type counts via Qdrant `count` with filter.
- `requirements.txt` re-pinned to the tested runtime.

### Part A acceptance (validated live 2026-10-16)
Kimchi returned HTTP 402 "provider exhausted credits" for **every** model, so the live
runs used the same OpenAI-compatible client pointed at Ollama `qwen2.5:3b`
(`KIMCHI_BASE_URL=http://localhost:11434/v1`). Mechanics are proven; output *quality*
must be re-checked on Kimchi.
- [x] V3.1: CVE-2021-44228 → researcher→critic(NEEDS_REVISION)→researcher(nvd_cve_lookup)→critic→reporter; 715 report_chunk events; "Log4Shell", Executive Summary, MITRE section present
- [x] Report persisted; `GET /investigate/reports/{id}` returns it; CVE-2021-45046 run listed CVE-2021-44228 as similar (cosine 0.906)
- [x] V2.2: turn 2 "that technique" resolved to T1110.003 → credential-access (KB tool call)
- [x] `/evaluate` → faithfulness 0.67 / relevancy 0.81 / recall 1.0; row in `/evaluate/history`; Analytics charts it
- [x] Upload `../../../../tmp/pwned.pdf` → `data/sources/pwned.pdf`; non-PDF and bad magic → 400
- [x] ruff clean · mypy clean (was 14 errors) · 68 unit tests green (was 39) · web tsc + build clean
- [x] UI: agent cards transition live incl. "pass 2" badge and critic send-back; report + save footer render

### Found during live testing
| # | Finding | Status |
|---|---|---|
| G15 | `/health/ready` reports `llm: ok` via `/models` even when every model returns 402 | open (readiness now also reports `llm_fallback`) → probe a 1-token completion, cache 60 s |
| G16 | No completion cap → small model generated for 15+ min on one call | **fixed**: `LLM_MAX_TOKENS` (default 4096) |
| G17 | Judge returned bare `["true","false"]`; `bool("false")` is True | **fixed**: tolerant parser + `_truthy` |
| G18 | Reporter can emit mismatched technique ID/name (e.g. T1021.006 "Command and Scripting Interpreter") | open → validate IDs against ingested MITRE payloads before publish |
| G19 | No LLM fallback — a single provider outage stops everything | **fixed**: Gemini fallback (`app/core/llm.py`, set `GEMINI_API_KEY`); falls back on provider/connection errors, never after tokens streamed, never on 400/422 |
| G20 | `psycopg_pool` was never installed; `tavily-python` still not installed | pool **fixed**; Tavily path untested |
| G21 | Web ESLint config broken (ESLint 9 needs flat config) | open |
| G22 | Unit coverage 66% (< 80% target); DB/service paths only covered live | open → integration tests on compose stack |

---

## Part B — Production hardening (next)
| Area | Work |
|---|---|
| Identity | OIDC/JWT (Keycloak/Auth0), RBAC roles: analyst / engineer / admin; tenant_id on every row + Qdrant payload filter |
| State | Redis: chat sessions, ingest job status, rate-limit buckets (today all in-process memory → lost on restart, breaks with >1 worker) |
| Async work | Arq/Celery worker for ingestion + long investigations; API returns job id, UI subscribes via SSE |
| Rate limiting | Per-user + per-IP token buckets; LLM token budget per tenant |
| Observability | Langfuse tracing on every chain/agent run (keys already in env), OpenTelemetry → Prometheus/Grafana, structured audit log of who asked what |
| Guardrails | ML injection classifier (e.g. Llama-Guard / Prompt-Guard) instead of regex; output PII/secret scanning on agent + report text; tool allow-list per role |
| Reliability | Timeouts + circuit breakers on NVD/Tavily/LLM; LLM fallback model (`minimax-m3`); retry with jitter |
| Data | Alembic-style versioned migrations; Qdrant snapshots + PG backups; collection aliasing for zero-downtime re-index |
| CI/CD | GitHub Actions: ruff, mypy, pytest+cov ≥80%, web typecheck/build, Docker build, Trivy scan; Playwright E2E on compose stack |
| Deploy | Helm chart / ECS; Qdrant Cloud or HA; managed Postgres; secrets in Vault/SM; Ollama → GPU node or hosted embeddings |

## Part C — Feature roadmap
| Feature | Value |
|---|---|
| IOC enrichment tools: VirusTotal, AbuseIPDB, Shodan, AlienVault OTX, GreyNoise, WHOIS/passive DNS | `ip`/`hash`/`domain` investigations currently have no data source beyond web search |
| Scheduled feeds: MITRE quarterly, CISA KEV daily, NVD delta, STIX/TAXII | Keeps KB fresh without manual ingest |
| Hybrid retrieval: BM25 + dense, cross-encoder rerank, technique-ID exact match | IDs like T1059.001 retrieve poorly with dense-only |
| Report export: STIX 2.1 bundle, PDF, Jira/ServiceNow ticket, Slack/Teams | Fits SOC workflow |
| SIEM integration: Splunk/Sentinel/Elastic alert → auto-investigate webhook | Turns tool into automation |
| Golden-set eval regression in CI (RAGAs over 50 Q/A) | Catches prompt/model regressions |
| Human-in-the-loop: analyst approves/edits critic gaps, feedback 👍/👎 stored | Quality loop |
| Case management: link reports, chat, IOCs into a case timeline | Analyst UX |
