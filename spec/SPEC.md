# ThreatRAG — Master Specification

**Version:** 1.0  
**Date:** 2026-06-28  
**Author:** Spec-Driven Development  

---

## 1. Problem Statement

Security analysts spend hours manually searching MITRE ATT&CK, NVD, and OWASP
documentation to respond to threats. ThreatRAG automates this by:
- Ingesting authoritative security knowledge bases into a vector store
- Answering analyst questions with cited sources
- Running autonomous multi-agent investigations on IOCs (IPs, hashes, CVE IDs)

## 2. Users

| Persona | Need |
|---|---|
| SOC Analyst (L1) | Quick answers to "what is this technique?" with citations |
| Threat Hunter | Investigate an IOC end-to-end with structured report |
| Security Engineer | Ingest custom threat intel PDFs into the knowledge base |

## 3. Phases

### Phase 1 — RAG Core (MVP)
- Ingest MITRE ATT&CK STIX JSON + OWASP PDFs into Qdrant
- Basic Q&A with source citations via `/api/v1/query`
- Streaming responses via SSE
- Simple chat UI

### Phase 2 — Agentic Loop
- ReAct agent with 3 tools: RAG search, NVD CVE API, web search
- Conversation memory (10-turn window)
- Streaming agent thoughts + tool calls via SSE

### Phase 3 — Multi-Agent Investigation
- LangGraph: Researcher → Critic → Reporter pipeline
- RAGAs quality evaluation
- PostgreSQL + pgvector report persistence
- Full investigation UI with agent visualisation

## 4. Non-Functional Requirements

| Requirement | Target |
|---|---|
| P50 RAG query latency | < 2 s (TTFT) |
| Ingestion throughput | ≥ 100 chunks/min |
| Concurrent users | ≥ 10 (free tier infra) |
| Security | OWASP LLM Top 10 hardened |
| Code quality | Ruff clean, Mypy strict, ≥80% unit test coverage |

## 5. Data Sources

| Source | Format | Size | Update Frequency |
|---|---|---|---|
| MITRE ATT&CK Enterprise | STIX JSON | ~3MB | Quarterly |
| OWASP LLM Top 10 | PDF | ~2MB | Annual |
| NVD CVE Database | REST API | N/A | Real-time via tool |
| Custom threat intel | PDF upload | Variable | On-demand |

## 6. Architecture Overview

```
User
  │
  ▼
React 18 Frontend (Vite + Tailwind)
  │  SSE / REST
  ▼
FastAPI Backend
  ├── /api/v1/query        → ThreatRAGChain (Phase 1)
  ├── /api/v1/chat         → ThreatIntelAgent (Phase 2)
  ├── /api/v1/investigate  → LangGraph Pipeline (Phase 3)
  └── /api/v1/ingest       → Ingestion workers
         │
         ├── Qdrant (vector store)
         ├── Ollama (embeddings, local)
         ├── Kimchi kimi-k2.6 (LLM)
         └── PostgreSQL + pgvector (Phase 3, reports)
```

## 7. File Size Budget
Each source file must stay under 150 lines.
Split logic at natural seams:
- `config.py` — settings only
- `store.py` — Qdrant client wrapper only
- `embedder.py` — embedding abstraction only
- `chain.py` — RAG chain assembly only
- `ingestion.py` — document loading + chunking only
- `prompts.py` — prompt templates only

## 8. LLM Provider: Kimchi
- Model: `kimi-k2-5`
- API: OpenAI-compatible (`/v1/chat/completions`)
- Auth: `Authorization: Bearer $KIMCHI_API_KEY`
- Use `langchain_openai.ChatOpenAI` with `openai_api_base` pointing to Kimchi URL
- Env var: `KIMCHI_API_KEY`, `KIMCHI_BASE_URL`

## 9. References
- Phase 1 detail: [spec/phase1.md](phase1.md)
- Phase 2 detail: [spec/phase2.md](phase2.md)
- Phase 3 detail: [spec/phase3.md](phase3.md)
- API contract: [spec/api-schema.md](api-schema.md)
- Validation plan: [spec/validation-plan.md](validation-plan.md)
