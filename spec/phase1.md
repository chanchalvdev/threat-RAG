# Phase 1 — RAG Core Specification

## Goal
Ingest MITRE ATT&CK + OWASP into Qdrant. Answer security questions with citations.

---

## Backend Features

### F1.1 — Configuration (backend/app/core/config.py)
- `Settings` via pydantic-settings
- Fields: `kimchi_api_key`, `kimchi_base_url`, `llm_model`, `qdrant_url`,
  `qdrant_collection`, `ollama_url`, `embedding_model`, `embedding_dim=768`,
  `chunk_size=1000`, `chunk_overlap=200`, `retrieval_k=6`, `debug=False`
- Singleton via `lru_cache`

### F1.2 — Structured Logging (backend/app/core/logging.py)
- `structlog` with JSON in prod, coloured in dev
- Middleware: logs method, path, status_code, duration_ms, request_id
- `get_logger(name)` exported

### F1.3 — Qdrant Store (backend/app/rag/store.py)
- Async `QdrantStore` wrapping `AsyncQdrantClient`
- `ensure_collection()` — creates with cosine distance if missing
- `upsert(points)` — batch insert
- `search(vector, k, filter)` — returns `ScoredPoint` list

### F1.4 — Embedder (backend/app/rag/embedder.py)
- `BaseEmbedder` ABC: `embed(text)`, `embed_batch(texts)`
- `OllamaEmbedder` — POST to Ollama `/api/embeddings`
- `embed_batch` — max 5 concurrent via asyncio.Semaphore
- `get_embedder(settings)` factory

### F1.5 — Ingestion (backend/app/rag/ingestion.py)
- `ingest_pdf(path, doc_type, store, embedder)` — PyPDF + chunking
- `ingest_mitre_attack(path, store, embedder)` — STIX JSON parse
- `ingest_owasp_llm(store, embedder)` — downloads + ingests OWASP PDF
- Batch upsert in groups of 100; log every 50 chunks

### F1.6 — Prompts (backend/app/rag/prompts.py)
- `RAG_PROMPT` — ChatPromptTemplate with security analyst system prompt
- `INVESTIGATOR_PROMPT` — for Phase 3 multi-agent (placeholder in Phase 1)

### F1.7 — RAG Chain (backend/app/rag/chain.py)
- `ThreatRAGChain` class
- `query(question, doc_types)` → `RAGResponse`
- `astream(question, doc_types)` → `AsyncIterator[str]`
- Kimchi LLM via `ChatOpenAI(base_url=kimchi_base_url, api_key=kimchi_api_key)`

### F1.8 — Ingest Routes (backend/app/api/routes/ingest.py)
- `POST /api/v1/ingest/pdf` — multipart upload, background task
- `POST /api/v1/ingest/mitre` — background task
- `POST /api/v1/ingest/owasp` — background task
- `GET /api/v1/ingest/status/{job_id}` — in-memory job tracker
- `GET /api/v1/ingest/stats` — Qdrant collection stats

### F1.9 — Query Routes (backend/app/api/routes/query.py)
- `POST /api/v1/query` — sync RAG response with sources
- `POST /api/v1/query/stream` — SSE streaming response

### F1.10 — Health Checks (backend/app/main.py)
- `GET /health` — always 200
- `GET /health/ready` — checks Qdrant + Ollama + LLM, 30s cache

---

## Frontend Features

### F1.11 — API Client (web/src/lib/api.ts)
- Typed interfaces: `SourceDoc`, `RAGResponse`, `IngestStatus`, `IngestStats`
- `queryRAG`, `ingestPDF`, `ingestMITRE`, `getIngestStatus`, `getIngestStats`, `getHealth`
- `streamQuery` — native fetch + SSE parser

### F1.12 — Layout (web/src/components/Layout.tsx)
- Dark-first: `bg-gray-950` body
- Left sidebar (collapsed 64px / expanded 240px)
- Nav: Chat, Knowledge Base, Investigate, Analytics
- Header: breadcrumb, model selector, health dot

### F1.13 — SourceCard (web/src/components/SourceCard.tsx)
- Collapsed: badge, doc_type chip, source, relevance bar
- Expanded: full text, copy button
- Colour map: MITRE=purple, OWASP=orange, CVE=red, custom=blue

### F1.14 — ChatMessage (web/src/components/ChatMessage.tsx)
- User: right-aligned blue
- Assistant: react-markdown + remark-gfm
- Sources collapsible, blinking cursor when streaming

### F1.15 — KnowledgeBase Page (web/src/pages/KnowledgeBase.tsx)
- PDF dropzone + "Ingest MITRE" / "Ingest OWASP" buttons
- Progress cards with polling
- Stats panel with recharts bar chart

### F1.16 — Chat Page (web/src/pages/Chat.tsx)
- Streaming chat via SSE
- Suggested starter questions
- Source strip above streaming response

---

## Acceptance Criteria (Phase 1 Done When:)
- [ ] `POST /api/v1/ingest/mitre` ingests MITRE ATT&CK without error
- [ ] `POST /api/v1/query` returns answer + ≥1 source for "What is T1110.001?"
- [ ] `POST /api/v1/query/stream` streams tokens via SSE
- [ ] Frontend chat page streams and displays sources
- [ ] All unit tests pass
- [ ] Ruff + mypy clean
