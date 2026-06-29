# ThreatRAG — Complete Development Playbook

RAG pipeline over MITRE ATT&CK, CVEs, and threat intel with a
multi-tool agentic layer. Every prompt below is copy-paste ready.

---

## Stack Reference

| Layer | Technology | Notes |
|---|---|---|
| Backend | Python 3.11 + FastAPI | async, Pydantic v2 |
| RAG Orchestration | LangChain 0.3 | Phase 1–2 |
| Multi-Agent | LangGraph 0.2 | Phase 3 |
| LLM | Claude API (Anthropic) or Kimchi kimi-k2.6 | OpenAI-compatible |
| Embeddings | Ollama + nomic-embed-text (local, free) | 768 dim |
| Vector DB | Qdrant (Docker local / Qdrant Cloud free) | |
| Relational DB | PostgreSQL + pgvector (Neon free tier) | Phase 3 |
| Evaluation | RAGAs | Phase 3 |
| Frontend | React 18 + TypeScript + Vite + Tailwind | |
| Streaming | SSE (FastAPI StreamingResponse) | Phase 2+ |
| Realtime | WebSocket (Phase 3 agent progress) | |

---

## Project Structure

```
threatrag/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point
│   │   ├── api/
│   │   │   ├── deps.py              # shared dependency injection
│   │   │   └── routes/
│   │   │       ├── ingest.py        # document ingestion endpoints
│   │   │       ├── query.py         # RAG query endpoints
│   │   │       ├── chat.py          # agentic chat endpoints (Phase 2)
│   │   │       └── investigate.py   # multi-agent endpoints (Phase 3)
│   │   ├── core/
│   │   │   ├── config.py            # Pydantic Settings
│   │   │   └── logging.py           # structlog setup
│   │   ├── rag/
│   │   │   ├── ingestion.py         # loaders, chunkers, embedders
│   │   │   ├── retrieval.py         # retriever + reranker
│   │   │   └── chain.py             # LangChain RAG chain
│   │   ├── agent/
│   │   │   ├── tools.py             # LangChain tools (Phase 2)
│   │   │   └── graph.py             # LangGraph multi-agent (Phase 3)
│   │   └── models/
│   │       └── schemas.py           # Pydantic request/response models
│   ├── data/
│   │   ├── sources/                 # raw data files (PDFs, JSON)
│   │   └── processed/               # chunked data cache
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile
│   └── .env.example
├── web/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── lib/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml
├── Makefile
└── README.md
```

---

## Environment Setup

**Prompt — Environment bootstrap**
> Create a complete setup for the ThreatRAG Python project.
> Write `backend/requirements.txt` with pinned versions of:
> `fastapi[standard]==0.115.*`, `uvicorn[standard]==0.32.*`, `langchain==0.3.*`,
> `langchain-community==0.3.*`, `langchain-anthropic==0.3.*`, `langchain-openai==0.3.*`,
> `langgraph==0.2.*`, `qdrant-client==1.13.*`, `pydantic-settings==2.6.*`,
> `python-multipart==0.0.*`, `structlog==24.*`, `httpx==0.28.*`, `ragas==0.2.*`,
> `psycopg[binary]==3.2.*`, `pgvector==0.3.*`, `pypdf==5.*`, `tiktoken==0.8.*`.
> Write `requirements-dev.txt` with: `pytest==8.*`, `pytest-asyncio==0.24.*`,
> `pytest-httpx==0.35.*`, `httpx==0.28.*`, `ruff==0.8.*`, `mypy==1.13.*`.
> Write a `Makefile` with targets: `setup` (creates venv, pip install both),
> `dev` (uvicorn with --reload), `test` (pytest -v), `lint` (ruff check + mypy),
> `ingest` (runs the ingestion script), `docker-up` / `docker-down`.

**Prompt — docker-compose for local development**
> Write `docker-compose.yml` for the ThreatRAG project with these services:
> `qdrant`: image `qdrant/qdrant:v1.13.0`, ports 6333:6333 and 6334:6334,
> volume `qdrant_storage:/qdrant/storage`, healthcheck on `GET /`.
> `postgres`: image `pgvector/pgvector:pg17`, env POSTGRES_DB=threatrag,
> port 5432:5432, volume `pg_data`, healthcheck `pg_isready`.
> `ollama`: image `ollama/ollama:latest`, port 11434:11434, volume `ollama_data`,
> with a `depends_on` post-start command that runs `ollama pull nomic-embed-text`.
> `backend`: build from `./backend`, env_file `.env`, depends on all three services,
> ports 8000:8000, volumes `./backend:/app` for hot reload.
> `web`: build from `./web`, depends on backend, port 5173:5173.

---

---

# PHASE 1 — RAG Core

**Goal:** Ingest OWASP Top 10 PDF + MITRE ATT&CK STIX JSON into Qdrant.
Build a Q&A chain that retrieves relevant chunks and answers with source citations.

---

## 1-A · Backend

---

### Feature: FastAPI app setup + config

**Prompt**
> Create `backend/app/core/config.py` using `pydantic-settings`.
> Define a `Settings` class with fields:
> `anthropic_api_key: str`, `kimchi_api_key: str = ""`, `llm_provider: Literal["anthropic","kimchi"] = "anthropic"`,
> `llm_model: str = "claude-sonnet-4-6"`, `qdrant_url: str = "http://localhost:6333"`,
> `qdrant_collection: str = "threat_intel"`, `ollama_url: str = "http://localhost:11434"`,
> `embedding_model: str = "nomic-embed-text"`, `embedding_dim: int = 768`,
> `database_url: str = "postgresql://..."`, `chunk_size: int = 1000`, `chunk_overlap: int = 200`,
> `retrieval_k: int = 6`, `debug: bool = False`.
> Use `model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")`.
> Create `backend/app/main.py` with a FastAPI app, lifespan context manager that initialises
> the Qdrant collection on startup, CORS for `http://localhost:5173`,
> and routers mounted at `/api/v1/`.

---

### Feature: Structured logging

**Prompt**
> Create `backend/app/core/logging.py` using `structlog`.
> Configure JSON output in production (`LOG_FORMAT=json` env var) and
> colourised console output in development.
> Add a FastAPI middleware that logs every request with:
> `method`, `path`, `status_code`, `duration_ms`, `request_id` (UUID from `X-Request-ID` header).
> Export a `get_logger(name: str)` function used throughout the app.
> Bind the `request_id` to all log lines within a request using `structlog.contextvars`.

---

### Feature: Qdrant collection setup

**Prompt**
> Create `backend/app/rag/store.py` in the ThreatRAG project.
> Implement an async `QdrantStore` class using `qdrant_client.AsyncQdrantClient`.
> In `__init__`, accept `url`, `collection_name`, and `vector_size` (default 768).
> Implement `async def ensure_collection(self)` that creates the collection with
> cosine distance if it does not exist, adds payload indexes on `source`, `doc_type`,
> and `chunk_index` fields for efficient filtering.
> Implement `async def upsert(self, points: list[PointStruct])` and
> `async def search(self, vector: list[float], k: int, filter: Filter | None) -> list[ScoredPoint]`.
> Use `qdrant_client.models` types throughout.

---

### Feature: PDF ingestion with chunking

**Prompt**
> Create `backend/app/rag/ingestion.py` in the ThreatRAG project.
> Implement `async def ingest_pdf(path: str, doc_type: str, store: QdrantStore, embedder: Embedder) -> int`.
> Use `langchain_community.document_loaders.PyPDFLoader` to load the PDF.
> Split with `RecursiveCharacterTextSplitter(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap, separators=["\n\n", "\n", ". ", " "])`.
> For each chunk: generate an embedding with the embedder, build a `PointStruct` with a UUID,
> the vector, and payload `{text, source, doc_type, page, chunk_index}`.
> Batch upsert in groups of 100. Return the total chunk count.
> Log progress every 50 chunks.

---

### Feature: MITRE ATT&CK JSON ingestion

**Prompt**
> Add `async def ingest_mitre_attack(path: str, store: QdrantStore, embedder: Embedder) -> int`
> to `backend/app/rag/ingestion.py` in the ThreatRAG project.
> Load the MITRE ATT&CK STIX JSON from
> `https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json`
> (download and cache locally in `data/sources/mitre_attack.json` if not present).
> Filter STIX objects with `type == "attack-pattern"`. For each technique, build a text chunk:
> `"Technique: {name}\nID: {external_id}\nTactic: {tactic}\nPlatforms: {platforms}\nDescription: {description[:1000]}"`.
> Store with payload `{technique_id, name, tactic, platforms, doc_type: "mitre_attack"}`.
> Also add `async def ingest_owasp_llm(store, embedder) -> int` that fetches the OWASP LLM Top 10
> PDF from the official URL and ingests it the same way with `doc_type: "owasp_llm"`.

---

### Feature: Embedder abstraction

**Prompt**
> Create `backend/app/rag/embedder.py` in the ThreatRAG project.
> Define an abstract base class `BaseEmbedder` with:
> `async def embed(self, text: str) -> list[float]`
> `async def embed_batch(self, texts: list[str]) -> list[list[float]]`.
> Implement `OllamaEmbedder(BaseEmbedder)` that POSTs to `{ollama_url}/api/embeddings`
> with `{"model": model_name, "prompt": text}` and returns the `embedding` field.
> Implement `embed_batch` with `asyncio.gather` limited to 5 concurrent calls using a semaphore.
> Implement `OpenAIEmbedder(BaseEmbedder)` as a fallback using `langchain_openai.OpenAIEmbeddings`
> wrapped in async. Add `get_embedder(settings: Settings) -> BaseEmbedder` factory function.

---

### Feature: RAG retrieval chain

**Prompt**
> Create `backend/app/rag/chain.py` in the ThreatRAG project.
> Build a `ThreatRAGChain` class that wraps a complete RAG pipeline using LangChain Expression Language (LCEL).
> Constructor accepts `store: QdrantStore`, `embedder: BaseEmbedder`, `llm: BaseChatModel`.
> Implement `async def query(self, question: str, doc_types: list[str] | None = None) -> RAGResponse`.
> The chain: embed the question → search Qdrant (k=6, optional doc_type filter) → format context
> with source citations → call the LLM with a security analyst system prompt.
> `RAGResponse` is a Pydantic model with `answer: str`, `sources: list[SourceDoc]`, `tokens_used: int`.
> `SourceDoc` has `text: str`, `source: str`, `doc_type: str`, `score: float`.
> Use `langchain_anthropic.ChatAnthropic` or `langchain_openai.ChatOpenAI` based on `settings.llm_provider`.

---

### Feature: System prompt for security RAG

**Prompt**
> Create `backend/app/rag/prompts.py` in the ThreatRAG project.
> Define the RAG system prompt as a `ChatPromptTemplate` with:
> system: `"You are a senior cybersecurity analyst and threat intelligence expert. Answer questions
> using ONLY the provided context from security knowledge bases (MITRE ATT&CK, OWASP, CVE feeds).
> Always cite your sources using [Source: X] notation. If the context does not contain enough
> information to answer confidently, say so rather than guessing.
> Format technical content (technique IDs, CVE numbers, code) in backticks."`.
> human: `"Context:\n{context}\n\nQuestion: {question}"`.
> Add a separate `INVESTIGATOR_PROMPT` used in Phase 3 for the multi-agent setup.

---

### Feature: /ingest endpoint

**Prompt**
> Create `backend/app/api/routes/ingest.py` in the ThreatRAG project.
> `POST /api/v1/ingest/pdf` — accepts `multipart/form-data` with a PDF file and a `doc_type` field.
> Save the file to `data/sources/`, run `ingest_pdf` in a background task, return immediately with
> `{"status": "accepted", "job_id": "<uuid>", "filename": "..."}`.
> `POST /api/v1/ingest/mitre` — no body needed, runs `ingest_mitre_attack` in background.
> `POST /api/v1/ingest/owasp` — runs `ingest_owasp_llm` in background.
> `GET /api/v1/ingest/status/{job_id}` — check job status from an in-memory dict
> `{job_id: {status, chunks_processed, total_chunks, error}}`.
> `GET /api/v1/ingest/stats` — returns `{collection, total_vectors, doc_type_counts}` from Qdrant.

---

### Feature: /query endpoint with citations

**Prompt**
> Create `backend/app/api/routes/query.py` in the ThreatRAG project.
> `POST /api/v1/query` accepts:
> `{"question": str, "doc_types": list[str] | None, "k": int = 6}`.
> Validate that `question` is 10–2000 chars and `k` is 1–20.
> Call `chain.query(question, doc_types)` and return the full `RAGResponse` as JSON.
> Add `POST /api/v1/query/stream` that uses `StreamingResponse` with `text/event-stream`.
> For the streaming version: emit `data: {"type":"source","data":{...SourceDoc}}\n\n`
> for each retrieved source, then emit `data: {"type":"chunk","data":"..."}\n\n` for
> each LLM token using `chain.astream`, then `data: {"type":"done"}\n\n` at the end.

---

### Feature: Health and readiness checks

**Prompt**
> Add health check endpoints to `backend/app/main.py` in the ThreatRAG project.
> `GET /health` returns `{"status":"ok"}` with 200 — always fast.
> `GET /health/ready` checks:
> (1) Qdrant: calls `client.get_collection(collection_name)`, expects no error,
> (2) Ollama: GETs `{ollama_url}/api/tags`, checks that `nomic-embed-text` is in the list,
> (3) LLM: sends a 1-token completion `{"messages":[{"role":"user","content":"hi"}],"max_tokens":1}`.
> Returns `{"status":"ready","checks":{"qdrant":"ok","ollama":"ok","llm":"ok"}}` or 503 with
> `{"status":"degraded","checks":{...}}` if any check fails. Cache for 30 seconds.

---

## 1-B · Frontend Setup

---

### Feature: React + TypeScript + Vite scaffold

**Prompt**
> Create the `web/` directory in the ThreatRAG project and scaffold a React 18 + TypeScript + Vite app.
> Install: `tailwindcss`, `@tailwindcss/typography`, `@tanstack/react-query@5`,
> `axios`, `react-router-dom@6`, `lucide-react`, `recharts`, `react-markdown`,
> `remark-gfm`, `highlight.js`, `clsx`, `tailwind-merge`.
> Configure Tailwind with a custom theme: dark mode via `class`, font families
> `"Geist Sans"` (sans) and `"Geist Mono"` (mono) from Google Fonts.
> In `vite.config.ts`, proxy `/api` to `http://localhost:8000` in dev.
> Create `src/lib/api.ts` with an axios instance and typed interfaces mirroring all backend Pydantic schemas.

---

### Feature: Typed API client

**Prompt**
> Create `web/src/lib/api.ts` in the ThreatRAG frontend with full TypeScript types.
> Mirror these backend schemas: `SourceDoc`, `RAGResponse`, `IngestStatus`, `IngestStats`.
> Export functions:
> `queryRAG(question: string, docTypes?: string[], k?: number): Promise<RAGResponse>`,
> `ingestPDF(file: File, docType: string): Promise<{job_id: string}>`,
> `ingestMITRE(): Promise<{job_id: string}>`,
> `getIngestStatus(jobId: string): Promise<IngestStatus>`,
> `getIngestStats(): Promise<IngestStats>`,
> `getHealth(): Promise<{status: string}>`.
> For streaming, export `streamQuery(question: string, onSource: (s: SourceDoc) => void, onChunk: (t: string) => void): Promise<void>`
> that uses the native `fetch` API and parses the SSE stream line by line.

---

## 1-C · UI/UX Components

---

### Feature: Design system and layout

**Prompt**
> Create `web/src/components/Layout.tsx` in the ThreatRAG frontend.
> The app layout is dark-first: `bg-gray-950` background, `bg-gray-900` sidebar, `bg-gray-800` cards.
> Left sidebar (64px wide collapsed, 240px expanded) with:
> app logo (shield icon + "ThreatRAG"), nav items (Chat, Knowledge Base, Investigate, Analytics),
> collapse toggle button at the bottom.
> Main area: full height, scrollable.
> Header bar (48px): breadcrumb, model selector dropdown (Claude claude-sonnet-4-6, kimi-k2.6), health status dot.
> Create a `ThemeProvider` context and `useTheme` hook for dark/light toggle.
> Export CSS custom properties for the 5 severity colours matching the SIEMAgent palette.

---

### Feature: SourceCard component

**Prompt**
> Create `web/src/components/SourceCard.tsx` in the ThreatRAG frontend.
> Props: `source: SourceDoc`, `index: number`, `expanded?: boolean`.
> Collapsed state: shows `[{index}]` badge, doc_type chip (MITRE/OWASP/CVE coloured differently),
> source filename truncated, relevance score as a small bar (0–1 mapped to 0–100%).
> Expanded state: shows full text with `prose-sm` Tailwind typography, monospace for
> technique IDs and CVE numbers, a "Copy text" button.
> Toggle between states on click with a smooth height transition.
> Add a `doc_type` colour map: MITRE=purple, OWASP=orange, CVE=red, custom=blue.

---

### Feature: Chat message component

**Prompt**
> Create `web/src/components/ChatMessage.tsx` in the ThreatRAG frontend.
> Props: `role: "user" | "assistant"`, `content: string`, `sources?: SourceDoc[]`, `isStreaming?: boolean`.
> User messages: right-aligned, blue background, plain text.
> Assistant messages: left-aligned, gray-800 background, content rendered with `react-markdown`
> and `remark-gfm` so ATT&CK technique IDs and code blocks are formatted.
> When `sources` is provided, show a collapsible "Sources (N)" section below the message
> listing `SourceCard` components.
> When `isStreaming` is true, show a blinking cursor at the end of the content.
> Add copy-to-clipboard button on hover.

---

### Feature: Knowledge base upload UI

**Prompt**
> Create `web/src/pages/KnowledgeBase.tsx` in the ThreatRAG frontend.
> Layout: two columns. Left: a dropzone component accepting PDF files,
> below it two buttons "Ingest MITRE ATT&CK" and "Ingest OWASP LLM Top 10".
> Right: ingestion stats panel showing `total_vectors` as a large number,
> a breakdown bar chart of `doc_type_counts` using recharts.
> When a file is dropped, show a progress card with job ID, polling `GET /api/v1/ingest/status/{id}`
> every 2s using `setInterval`, displaying a progress bar `chunks_processed / total_chunks`.
> Show a green checkmark when status is `"completed"` and a red badge if `"failed"`.
> Use `@tanstack/react-query` for the stats polling with a 5s refetch interval.

---

### Feature: Chat page with RAG

**Prompt**
> Create `web/src/pages/Chat.tsx` in the ThreatRAG frontend.
> This is the main page. Layout: chat history (scrollable, fills available height),
> sticky input bar at the bottom (textarea + submit button).
> Manage messages in a `useState` array of `{role, content, sources?, isStreaming?}`.
> On submit: add user message, add empty assistant message with `isStreaming: true`,
> call `streamQuery` which updates the assistant message content chunk by chunk.
> As sources arrive (before the LLM chunks), build up a `sources` array shown as
> a horizontal scrollable strip of mini source chips above the streaming response.
> After streaming ends, set `isStreaming: false` and render the full source cards.
> Add suggested starter questions: "What is T1110.001?", "Summarise OWASP LLM Top 10",
> "How does credential stuffing work?".

---

## 1-D · Testing

---

### Feature: Ingestion unit tests

**Prompt**
> Create `backend/tests/unit/test_ingestion.py` in the ThreatRAG project.
> Mock `QdrantStore` and `BaseEmbedder` using `unittest.mock.AsyncMock`.
> Test `ingest_pdf`: verify it calls `embedder.embed` once per chunk,
> verify `store.upsert` is called with batches of ≤100 points,
> verify each point payload has `text`, `source`, `doc_type`, `chunk_index` fields.
> Test `ingest_mitre_attack` with a small mock STIX bundle (3 attack-patterns):
> verify 3 chunks are created with correct `technique_id` and `tactic` payload fields.
> Use `pytest.mark.asyncio` and `pytest-asyncio` for all async tests.

---

### Feature: RAG chain unit tests

**Prompt**
> Create `backend/tests/unit/test_chain.py` in the ThreatRAG project.
> Mock `QdrantStore.search` to return 3 fake `ScoredPoint` objects with payloads.
> Mock the LLM with `langchain_core.language_models.fake.FakeStreamingListLLM`
> returning a fixed answer string.
> Test `ThreatRAGChain.query`: verify the returned `RAGResponse` has the correct answer,
> verify `sources` list has 3 entries with correct `doc_type` and `score`,
> verify the context passed to the LLM contains all 3 source texts.
> Test that when `doc_types=["mitre_attack"]` is passed, `store.search` is called with
> a filter that restricts to that doc_type.

---

### Feature: FastAPI endpoint tests

**Prompt**
> Create `backend/tests/integration/test_routes.py` in the ThreatRAG project.
> Use `httpx.AsyncClient` with `app` mounted via `ASGITransport`.
> In `conftest.py`, override `get_chain` and `get_store` FastAPI dependencies with mocks.
> Test `GET /health` → 200, `{"status":"ok"}`.
> Test `POST /api/v1/query` with valid body → 200, response has `answer` and `sources`.
> Test `POST /api/v1/query` with question too short → 422 validation error.
> Test `POST /api/v1/ingest/pdf` with a small real PDF → 202, `job_id` in response.
> Test `POST /api/v1/query/stream` → 200, `content-type: text/event-stream`,
> verify SSE events contain at least one `type: "source"` and one `type: "chunk"`.

---

### Feature: Retrieval quality test

**Prompt**
> Create `backend/tests/integration/test_retrieval_quality.py` in the ThreatRAG project
> with `pytest.mark.integration` marker.
> This test requires a running Qdrant with data ingested.
> Define a `QA_PAIRS` list of 5 question-answer pairs known to be in MITRE ATT&CK:
> e.g. `("What technique is T1110.001?", "Password Guessing")`.
> For each pair: run `chain.query(question)`, check the answer contains the expected keyword,
> check at least one source has `doc_type == "mitre_attack"`.
> Also test that asking about something completely unrelated (e.g. "What is the weather in Paris?")
> returns a response that says the context does not contain enough information.

---

---

# PHASE 2 — Agentic Loop

**Goal:** ReAct agent with 3 tools — RAG search, NVD CVE API, Tavily web search.
Conversation memory. FastAPI streaming chat endpoint.

---

## 2-A · Backend

---

### Feature: LangChain tool base + RAG search tool

**Prompt**
> Create `backend/app/agent/tools.py` in the ThreatRAG project.
> Implement a `ThreatRAGSearchTool` as a `langchain_core.tools.BaseTool` subclass.
> `name = "threat_rag_search"`, description = "Search the internal security knowledge base
> (MITRE ATT&CK, OWASP LLM Top 10, threat intel). Use this FIRST for any security question."
> `args_schema`: Pydantic model with `query: str`, `doc_types: list[str] | None = None`.
> `_arun`: embed the query with the `Embedder`, call `QdrantStore.search`, format results as
> `"[Source: {source}]\n{text}\n"` joined by `"---"`. Return the formatted string.
> Inject `store` and `embedder` via constructor; make tool async-only.

---

### Feature: NVD CVE API tool

**Prompt**
> Add `NVDCVETool` to `backend/app/agent/tools.py` in the ThreatRAG project.
> `name = "nvd_cve_lookup"`, description = "Look up CVE details from the NVD database.
> Use when a specific CVE ID (e.g. CVE-2024-1234) is mentioned."
> `args_schema`: `cve_id: str` validated with a regex `^CVE-\d{4}-\d{4,}$`.
> `_arun`: GET `https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}`.
> No API key required for basic access (rate limit: 5 req/30s without key, 50/30s with).
> Parse the response and return: `CVE ID, CVSS score, severity, description (first 500 chars), affected products (first 3)`.
> If the CVE is not found return a clear not-found message.
> Add exponential backoff with `asyncio.sleep` for 429 responses.

---

### Feature: Tavily web search tool

**Prompt**
> Add `TavilySearchTool` to `backend/app/agent/tools.py` in the ThreatRAG project.
> `name = "web_search"`, description = "Search the web for current threat intelligence,
> recent security news, or information not in the knowledge base. Use as a last resort."
> Use `langchain_community.tools.TavilySearchResults` with `max_results=5`.
> Wrap it in a custom tool class that prefixes the search query with "cybersecurity threat: "
> and post-processes results to include only `url`, `title`, and `content[:300]` per result.
> Get the Tavily API key from `settings.tavily_api_key` (free at tavily.com — 1000 searches/month).
> If the API key is not set, return a graceful error message instead of raising.

---

### Feature: ReAct agent setup

**Prompt**
> Create `backend/app/agent/react_agent.py` in the ThreatRAG project.
> Build a `ThreatIntelAgent` class using `langchain.agents.create_react_agent` (LangChain 0.3).
> Constructor: accepts `llm`, `tools: list[BaseTool]`, `memory: ConversationBufferMemory`.
> System prompt: `"You are a senior threat intelligence analyst. Use the available tools to
> answer security questions thoroughly. Always search the knowledge base first (threat_rag_search),
> then look up specific CVEs if mentioned (nvd_cve_lookup), and search the web only for
> very recent information (web_search). Provide your final answer in structured markdown
> with sections: Summary, Technical Details, MITRE ATT&CK Mapping, Recommendations."`.
> Implement `async def run(self, question: str) -> AgentResponse` and
> `async def stream(self, question: str) -> AsyncIterator[AgentStreamEvent]`.

---

### Feature: Conversation buffer memory

**Prompt**
> Add conversation memory management to `backend/app/agent/react_agent.py` in the ThreatRAG project.
> Use `langchain.memory.ConversationBufferWindowMemory(k=10)` to retain the last 10 turns.
> Create a `SessionManager` class in `backend/app/agent/session.py` that:
> stores `{session_id: (ThreatIntelAgent, last_accessed: datetime)}` in memory,
> creates a new agent+memory when a session_id is not found,
> evicts sessions not accessed in the last 30 minutes using a background `asyncio.Task`,
> limits to 100 concurrent sessions.
> Expose `get_or_create(session_id: str) -> ThreatIntelAgent`.

---

### Feature: Streaming SSE chat endpoint

**Prompt**
> Create `backend/app/api/routes/chat.py` in the ThreatRAG project.
> `POST /api/v1/chat/stream` accepts `{"question": str, "session_id": str | None}`.
> If `session_id` is None, generate a new UUID and return it as a response header `X-Session-ID`.
> Call `agent.stream(question)` and yield SSE events:
> `data: {"type":"thought","data":"Searching knowledge base..."}\n\n` for agent thoughts,
> `data: {"type":"tool_call","data":{"name":"...","input":"..."}}\n\n` when a tool is called,
> `data: {"type":"tool_result","data":"..."}\n\n` when a tool returns,
> `data: {"type":"chunk","data":"..."}\n\n` for each LLM output token,
> `data: {"type":"done","session_id":"..."}\n\n` at the end.
> `GET /api/v1/chat/history/{session_id}` returns the conversation history as a list of `{role, content}`.

---

### Feature: Agent stream event types

**Prompt**
> Create `backend/app/models/agent_schemas.py` in the ThreatRAG project.
> Define Pydantic models for all agent stream events:
> `AgentThought(type: Literal["thought"], data: str)`,
> `AgentToolCall(type: Literal["tool_call"], data: ToolCallData)` where
> `ToolCallData` has `name: str, input: str, tool_use_id: str`,
> `AgentToolResult(type: Literal["tool_result"], data: str, tool_use_id: str)`,
> `AgentChunk(type: Literal["chunk"], data: str)`,
> `AgentDone(type: Literal["done"], session_id: str, total_tokens: int)`,
> `AgentError(type: Literal["error"], data: str)`.
> Create a `AgentStreamEvent = Union[...]` discriminated union.
> Add a serialiser helper `to_sse(event: AgentStreamEvent) -> str` that produces the SSE line.

---

## 2-B · Frontend

---

### Feature: Streaming chat with SSE and tool display

**Prompt**
> Upgrade `web/src/pages/Chat.tsx` in the ThreatRAG frontend to use the new agentic endpoint.
> Update `streamQuery` to parse the new SSE event types: `thought`, `tool_call`, `tool_result`, `chunk`, `done`.
> Each assistant message now tracks: `content`, `thoughts: string[]`, `toolCalls: ToolCall[]`, `sources`.
> Show thoughts as small italic lines in gray-500 above the response while streaming.
> Store `session_id` in `sessionStorage` so conversations persist across page refreshes.
> Add a "New conversation" button that clears the session_id and message history.
> Show a `X-Session-ID` indicator in the header when a session is active.

---

### Feature: Tool call visualisation panel

**Prompt**
> Create `web/src/components/ToolCallTimeline.tsx` in the ThreatRAG frontend.
> Renders the sequence of tool calls for a single agent response.
> Each tool call is a card with: tool icon (database for RAG, shield for CVE, globe for web),
> tool name as a badge, input query truncated to 80 chars, and the result truncated to 150 chars.
> Clicking a card expands to show the full input and output.
> While a tool is in-flight (call received but no result yet), show a spinner.
> Animate cards sliding in from the left as they arrive during streaming.
> Show total tool calls and estimated tokens used at the bottom.

---

### Feature: Conversation history sidebar

**Prompt**
> Create `web/src/components/ConversationSidebar.tsx` in the ThreatRAG frontend.
> Fetch `GET /api/v1/chat/history/{session_id}` using react-query.
> Render the history as a collapsible side panel (slides in from right on mobile).
> Each entry shows role icon, first 60 chars of content, and timestamp.
> Add a "Clear history" button that calls `DELETE /api/v1/chat/history/{session_id}`
> (implement this endpoint in the backend too).
> Add a "Export conversation" button that downloads the full history as a Markdown file.

---

### Feature: Threat search suggestions

**Prompt**
> Create `web/src/components/SearchSuggestions.tsx` in the ThreatRAG frontend.
> Renders below the chat input when the input is empty.
> Show 6 suggestion chips in 2 rows:
> "Explain T1055 Process Injection", "What CVEs affect Log4j?",
> "OWASP LLM01: Prompt Injection", "How does ransomware spread laterally?",
> "Compare T1078 and T1133", "Latest supply chain attack techniques".
> Clicking a chip fills the input and auto-submits.
> After the first message, hide suggestions and show a "Suggested follow-ups" row
> of 3 chips generated by calling `POST /api/v1/chat/suggestions` (implement this endpoint
> to call the LLM with a prompt to generate 3 follow-up questions based on the last exchange).

---

## 2-C · Testing

---

### Feature: Tool unit tests with mock HTTP

**Prompt**
> Create `backend/tests/unit/test_tools.py` in the ThreatRAG project using `pytest-httpx`.
> Test `NVDCVETool._arun("CVE-2021-44228")` with a mock NVD API response:
> assert the return string contains "Log4Shell", "CVSS: 10.0", "Critical".
> Test with a 404 response: assert "not found" message returned, no exception raised.
> Test with a 429 response: assert the tool retries after backoff (mock `asyncio.sleep`).
> Test `ThreatRAGSearchTool._arun` with a mocked `QdrantStore.search`:
> assert the returned string contains the mocked source text and source filename.
> Test `TavilySearchTool._arun` with `settings.tavily_api_key = ""`:
> assert a graceful "API key not configured" string is returned.

---

### Feature: Agent integration test

**Prompt**
> Create `backend/tests/integration/test_agent.py` in the ThreatRAG project.
> Use `langchain_core.language_models.fake.FakeStreamingListLLM` to avoid real LLM calls.
> Configure the fake LLM to return a ReAct-formatted response:
> `"Thought: I should search the knowledge base\nAction: threat_rag_search\nAction Input: T1110\nObservation: ...\nFinal Answer: T1110 is..."`.
> Test that `agent.run("What is T1110?")` returns an `AgentResponse` with non-empty `answer`.
> Test that the `RAGSearch` tool was called with `"T1110"` as the query.
> Test `SessionManager`: create 2 sessions, assert they have different `agent` instances,
> access session 1, simulate time passing (mock datetime), assert session 2 is evicted.

---

---

# PHASE 3 — Multi-Agent + Evaluation

**Goal:** LangGraph graph with Researcher → Critic → Reporter agents.
RAGAs evaluation pipeline. pgvector report persistence.

---

## 3-A · Backend

---

### Feature: LangGraph state definition

**Prompt**
> Create `backend/app/agent/graph.py` in the ThreatRAG project.
> Define the LangGraph state using `typing_extensions.TypedDict`:
> `class InvestigationState(TypedDict):
>   ioc: str                         # IOC being investigated (IP/hash/domain/CVE)
>   ioc_type: Literal["ip","hash","domain","cve","technique"]
>   researcher_output: str           # raw gathered intelligence
>   critic_feedback: str             # validation and gaps identified
>   final_report: str                # structured markdown report
>   sources: list[SourceDoc]         # all sources used
>   tool_calls: list[dict]           # audit trail of every tool call
>   iteration: int                   # critic→researcher loop counter
>   status: Literal["researching","critiquing","reporting","done","error"]`.
> Also define `InvestigationRequest(BaseModel)` with `ioc`, `ioc_type`, `session_id`.
> And `InvestigationReport(BaseModel)` with all final fields plus `ragas_scores`.

---

### Feature: Researcher agent node

**Prompt**
> Add the `researcher_node` to `backend/app/agent/graph.py` in the ThreatRAG project.
> This is an async function `async def researcher_node(state: InvestigationState) -> InvestigationState`.
> It uses the full tool suite from Phase 2: `ThreatRAGSearchTool`, `NVDCVETool`, `TavilySearchTool`.
> System prompt: `"You are a threat intelligence researcher. Given an IOC ({ioc_type}: {ioc}),
> gather comprehensive intelligence. Search the knowledge base first, then look up CVEs if relevant,
> then search the web for recent reporting. Compile ALL findings into a detailed research document
> with sections: IOC Overview, Technical Analysis, MITRE ATT&CK Mapping, Related Threats, Raw Evidence."`.
> Run the LLM with tools until `finish_reason == "stop"`. Update state with the output and tool_calls.

---

### Feature: Critic agent node

**Prompt**
> Add the `critic_node` to `backend/app/agent/graph.py` in the ThreatRAG project.
> This is an async function `async def critic_node(state: InvestigationState) -> InvestigationState`.
> It does NOT use any tools — it only reviews the `researcher_output`.
> System prompt: `"You are a critical security reviewer. Review the researcher's report and identify:
> 1. Factual gaps or unsupported claims, 2. Missing MITRE technique coverage,
> 3. Outdated information that needs web verification, 4. Unclear or ambiguous statements.
> If the report is thorough and accurate, respond with APPROVED.
> Otherwise, respond with NEEDS_REVISION: <specific gap 1> | <gap 2> | ..."`.
> Parse the LLM response: if it starts with `"APPROVED"`, route to reporter.
> If `"NEEDS_REVISION"` and `state.iteration < 2`, route back to researcher. Else force to reporter.

---

### Feature: Reporter agent node

**Prompt**
> Add the `reporter_node` to `backend/app/agent/graph.py` in the ThreatRAG project.
> This is an async function `async def reporter_node(state: InvestigationState) -> InvestigationState`.
> System prompt: `"You are a senior threat intelligence report writer. Transform the research
> findings into a professional incident report. Format:
> # Threat Intelligence Report: {ioc}
> ## Executive Summary (3 sentences for a non-technical audience)
> ## Technical Analysis (detailed, with code blocks for hashes/IPs)
> ## MITRE ATT&CK Coverage (table: Tactic | Technique | Evidence)
> ## Indicators of Compromise (formatted table)
> ## Recommended Actions (numbered, prioritised)
> ## References (all sources cited)"`.
> The reporter has no tools and no retry logic. Its output is the final report.
> Set `state.status = "done"` and `state.final_report` to the LLM output.

---

### Feature: LangGraph assembly + routing

**Prompt**
> Complete `backend/app/agent/graph.py` in the ThreatRAG project by assembling the LangGraph.
> Import `StateGraph, END` from `langgraph.graph`.
> Create `graph = StateGraph(InvestigationState)`.
> Add nodes: `graph.add_node("researcher", researcher_node)`, `"critic"`, `"reporter"`.
> Set `graph.set_entry_point("researcher")`.
> Add edge researcher → critic.
> Add conditional edge from critic: if `state.status == "needs_revision"` → researcher,
> else → reporter.
> Add edge reporter → END.
> Compile: `app = graph.compile()`.
> Create `async def run_investigation(request: InvestigationRequest) -> InvestigationReport`
> that calls `await app.ainvoke(initial_state)` and wraps the result.

---

### Feature: Streaming graph execution

**Prompt**
> Add streaming support to the LangGraph execution in `backend/app/agent/graph.py`.
> Use `app.astream_events(initial_state, version="v2")` to get node-level events.
> For each event, yield an SSE-compatible `GraphEvent` Pydantic model:
> `{"type":"node_start","node":"researcher","iteration":1}` when a node begins,
> `{"type":"node_chunk","node":"researcher","data":"..."}` for LLM tokens within a node,
> `{"type":"node_done","node":"researcher","summary":"Gathered 12 sources"}` when a node ends,
> `{"type":"routing","from":"critic","to":"researcher","reason":"Missing CVE coverage"}`,
> `{"type":"report_chunk","data":"..."}` during the final reporter node streaming.
> Create `POST /api/v1/investigate/stream` in `backend/app/api/routes/investigate.py`
> that accepts `InvestigationRequest` and streams these events.

---

### Feature: RAGAs evaluation pipeline

**Prompt**
> Create `backend/app/evaluation/ragas_eval.py` in the ThreatRAG project.
> Implement `async def evaluate_response(question: str, answer: str, contexts: list[str], ground_truth: str | None) -> RagasScores`.
> Use `ragas.metrics`: `faithfulness`, `answer_relevancy`, `context_precision`, `context_recall`.
> `RagasScores` is a Pydantic model with `faithfulness: float`, `answer_relevancy: float`,
> `context_precision: float`, `context_recall: float | None`, `overall: float` (weighted average).
> Wrap the `ragas.evaluate` call to handle cases where `ground_truth` is None (skip recall metric).
> Create `POST /api/v1/evaluate` that accepts `{question, answer, contexts, ground_truth?}`
> and returns `RagasScores`. This enables the frontend to show quality scores per response.

---

### Feature: PostgreSQL + pgvector report storage

**Prompt**
> Create `backend/app/db/reports.py` in the ThreatRAG project.
> Use `psycopg[binary]` async client + `pgvector` extension.
> Define a `reports` table with columns:
> `id UUID PRIMARY KEY`, `ioc TEXT`, `ioc_type TEXT`, `final_report TEXT`,
> `sources JSONB`, `ragas_scores JSONB`, `embedding VECTOR(768)`,
> `created_at TIMESTAMPTZ DEFAULT NOW()`, `session_id TEXT`.
> Implement `async def save_report(report: InvestigationReport, embedding: list[float]) -> str`.
> Implement `async def find_similar_reports(embedding: list[float], k: int = 5) -> list[ReportSummary]`
> using `<=>` cosine operator. Implement `async def get_report(report_id: str) -> InvestigationReport | None`.
> Write the migration SQL as `backend/migrations/001_create_reports.sql`.

---

## 3-B · Frontend

---

### Feature: Investigate page with agent visualisation

**Prompt**
> Create `web/src/pages/Investigate.tsx` in the ThreatRAG frontend.
> Layout: top section with an IOC input (text field) and IOC type selector (IP/Hash/Domain/CVE/Technique).
> Below that: a real-time agent collaboration visualiser.
> Connect to `POST /api/v1/investigate/stream` using the SSE parser.
> Show three agent cards side by side: Researcher, Critic, Reporter.
> Each card has a status indicator: idle (gray), active (pulsing blue), done (green), skipped.
> When `node_start` arrives for a node, animate it to active state.
> Display `node_chunk` events as streaming text inside the active card (last 300 chars shown).
> When `routing` events arrive, draw an animated arrow between cards.

---

### Feature: Streaming report viewer

**Prompt**
> Create `web/src/components/ReportViewer.tsx` in the ThreatRAG frontend.
> Props: `reportChunks: string[]` (accumulates as `report_chunk` SSE events arrive), `isStreaming: boolean`.
> Render the accumulated text as Markdown using `react-markdown` + `remark-gfm`.
> The MITRE ATT&CK table in the report should render as a proper HTML table with severity colouring.
> Add a sticky action bar at the top-right: "Copy Markdown", "Export PDF" (using browser print API),
> "Save Report" (calls `POST /api/v1/investigate/save`).
> When `isStreaming` is true, auto-scroll to the bottom as new chunks arrive.
> After streaming, show `RagasScores` as coloured progress bars below the report
> (green > 0.8, yellow 0.5–0.8, red < 0.5).

---

### Feature: RAGAs metrics dashboard

**Prompt**
> Create `web/src/pages/Analytics.tsx` in the ThreatRAG frontend.
> Fetch `GET /api/v1/analytics/ragas` (implement this endpoint to return historical scores from PostgreSQL).
> Show four `recharts LineChart` components for the 4 RAGAs metrics over time (last 20 evaluations).
> Each chart has a reference line at 0.8 (good threshold) and 0.5 (minimum acceptable).
> Below the charts, show a table of recent queries with columns: IOC, model, scores, timestamp.
> Add a "Run evaluation" button that lets you paste a question + answer + context and
> shows the RAGAs scores in a modal using `POST /api/v1/evaluate`.

---

### Feature: Similar reports panel

**Prompt**
> Add a `SimilarReports` section to `web/src/pages/Investigate.tsx` in the ThreatRAG frontend.
> After an investigation completes, call `GET /api/v1/investigate/similar?ioc={ioc}`.
> Implement this backend endpoint to embed the ioc string, query pgvector, and return
> the top 5 most similar past reports.
> In the frontend, show a "Past investigations" row of compact cards below the report:
> each card shows the IOC, ioc_type, a truncated executive summary, the date,
> and colour-coded RAGAs score badge.
> Clicking a card loads the full past report in the ReportViewer.

---

## 3-C · Testing

---

### Feature: LangGraph node unit tests

**Prompt**
> Create `backend/tests/unit/test_graph.py` in the ThreatRAG project.
> Test `researcher_node` with a mocked LLM and mocked tools:
> assert the returned state has `researcher_output` non-empty and `status == "researching"` → "done".
> Test `critic_node` with researcher output that says "APPROVED":
> assert `critic_feedback == "APPROVED"` and the routing function returns "reporter".
> Test `critic_node` with output starting "NEEDS_REVISION":
> assert `iteration` increments and routing returns "researcher" when `iteration < 2`.
> Test that when `iteration == 2` and critic says NEEDS_REVISION, routing still goes to reporter.
> Test `reporter_node` with mocked LLM: assert `final_report` contains the expected markdown headers.

---

### Feature: RAGAs evaluation test

**Prompt**
> Create `backend/tests/unit/test_ragas.py` in the ThreatRAG project.
> Mock `ragas.evaluate` to return fixed metric scores.
> Test `evaluate_response` with a question, answer, contexts, and ground_truth:
> assert the returned `RagasScores` has correct individual fields and a reasonable `overall` score.
> Test with `ground_truth=None`: assert `context_recall` is `None` and no error is raised.
> Test the `POST /api/v1/evaluate` endpoint using `httpx.AsyncClient`:
> assert valid payload → 200 with all 4 score fields present.
> Assert invalid payload (missing `question`) → 422.

---

### Feature: E2E test with Playwright

**Prompt**
> Create `web/e2e/threatrag.spec.ts` in the ThreatRAG frontend using Playwright.
> Configure `playwright.config.ts` with `baseURL: "http://localhost:5173"` and
> a `webServer` config that starts the FastAPI backend and Vite dev server.
> Test 1 (Chat): Navigate to Chat, type "What is T1110.001?", submit,
> wait for streaming to complete, assert the response contains "Password Guessing",
> assert at least one SourceCard appears with doc_type "mitre_attack".
> Test 2 (Knowledge Base): Navigate to Knowledge Base, click "Ingest MITRE ATT&CK",
> assert the progress card appears, poll until status shows "completed".
> Test 3 (Investigate): Navigate to Investigate, type "CVE-2021-44228", select "CVE",
> click Investigate, wait for all 3 agent cards to turn green, assert report contains "Log4Shell".

---

---

# DEPLOYMENT — Free Options

---

## Free Deployment Stack (Recommended Combination)

| Service | Provider | Free Tier |
|---|---|---|
| Frontend | **Vercel** | Unlimited, 100GB bandwidth/month |
| Backend API | **Render** | 512MB RAM, 0.1 CPU (spins down) |
| Vector DB | **Qdrant Cloud** | 1 cluster, 1GB storage, 1M vectors |
| PostgreSQL | **Neon** | 0.5GB storage, pgvector built-in |
| LLM | **Kimchi Inference** | Pay-per-token (~$3–5 total for learning) |
| Embeddings | Ollama on Render (limited) **or** Nomic Embed API | Nomic: 10K free/month |
| Monitoring | **Langfuse Cloud** | 50K traces/month free |

---

### Feature: Production Dockerfile — Backend

**Prompt**
> Write a multi-stage `backend/Dockerfile` for the ThreatRAG FastAPI backend.
> Stage 1 (`builder`): use `python:3.11-slim`, install `build-essential`,
> copy `requirements.txt`, run `pip install --no-cache-dir -r requirements.txt` into `/app/deps`.
> Stage 2 (`runtime`): use `python:3.11-slim` (no build tools),
> copy deps from builder with `COPY --from=builder /app/deps /usr/local/lib/python3.11/site-packages`,
> copy app source. Set `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]`.
> Add `HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1`.
> Final image should be under 400MB. Use non-root user `appuser`.

---

### Feature: Production Dockerfile — Frontend

**Prompt**
> Write a multi-stage `web/Dockerfile` for the ThreatRAG React frontend.
> Stage 1 (`build`): use `node:22-alpine`, run `npm ci`, run `npm run build`.
> In `vite.config.ts`, ensure the build sets `VITE_API_URL` from env to point to the
> production backend URL (Render URL) instead of localhost.
> Stage 2 (`runtime`): use `nginx:1.27-alpine`, copy `web/dist` to `/usr/share/nginx/html`,
> copy a custom `nginx.conf` that handles React Router (try_files $uri /index.html),
> compresses with gzip, and proxies `/api` to the backend URL.
> The final image should be under 50MB.

---

### Feature: Render deployment (backend)

**Prompt**
> Create `render.yaml` in the ThreatRAG project root for Render Blueprint deployment.
> Define a `web` service with:
> `type: web`, `name: threatrag-api`, `runtime: docker`, `dockerfilePath: ./backend/Dockerfile`,
> `plan: free`, `healthCheckPath: /health`.
> Environment variables: `ANTHROPIC_API_KEY` (from Render secret), `KIMCHI_API_KEY`,
> `QDRANT_URL` (from Qdrant Cloud), `QDRANT_API_KEY`, `DATABASE_URL` (from Neon),
> `OLLAMA_URL: https://api.nomic.ai/v1` (use Nomic Embed API instead of local Ollama),
> `EMBEDDING_MODEL: nomic-embed-text-v1.5`, `TAVILY_API_KEY`.
> Add a `preDeployCommand: python -m app.scripts.migrate` for DB migrations.
> Write `backend/app/scripts/migrate.py` that runs the SQL migration file on startup.

---

### Feature: Vercel deployment (frontend)

**Prompt**
> Create `vercel.json` in the `web/` directory for Vercel deployment.
> Set `framework: "vite"`, `buildCommand: "npm run build"`, `outputDirectory: "dist"`.
> Add a rewrite rule: `{"source": "/api/:path*", "destination": "https://your-render-app.onrender.com/api/:path*"}`
> so the frontend proxies API calls to the Render backend in production.
> Create `web/.env.production` with `VITE_API_URL=https://your-render-app.onrender.com`.
> Create `web/.env.development` with `VITE_API_URL=http://localhost:8000`.
> Update `web/src/lib/api.ts` to use `import.meta.env.VITE_API_URL` as the axios `baseURL`.
> Document the deployment steps: `vercel login`, `vercel --prod` from the `web/` directory.

---

### Feature: Neon PostgreSQL + pgvector setup

**Prompt**
> Write the complete database setup for the ThreatRAG project using Neon free tier.
> Create `backend/migrations/001_init.sql`:
> `CREATE EXTENSION IF NOT EXISTS vector;`
> Create the `reports` table with all columns from the storage feature above.
> Create indexes: `CREATE INDEX ON reports USING hnsw (embedding vector_cosine_ops);`
> and `CREATE INDEX ON reports (ioc, ioc_type);`.
> Create `backend/app/db/connection.py` that reads `DATABASE_URL` from settings,
> creates an async `psycopg` connection pool (`min_size=2, max_size=10`),
> and exposes it as a FastAPI dependency `get_db_conn`.
> Write `backend/app/scripts/migrate.py` that checks if the schema exists and runs missing migrations.

---

### Feature: Qdrant Cloud + Nomic Embed API setup

**Prompt**
> Update `backend/app/rag/embedder.py` to add `NomicEmbedder(BaseEmbedder)`.
> Nomic Embed API is OpenAI-compatible at `https://api-atlas.nomic.ai/v1/embedding/text`.
> POST with header `Authorization: Bearer {NOMIC_API_KEY}` and body
> `{"model":"nomic-embed-text-v1.5","texts":["..."],"task_type":"search_document"}`.
> Note: task_type should be `"search_query"` for queries and `"search_document"` for ingestion.
> Update `get_embedder(settings)` to return `NomicEmbedder` when `settings.embedding_provider == "nomic"`.
> Update `QdrantStore` to accept a Qdrant Cloud URL + API key
> (`qdrant_client.AsyncQdrantClient(url=url, api_key=api_key)`).
> Document in README: how to get free Qdrant Cloud cluster URL and API key at cloud.qdrant.io.

---

### Feature: Fly.io alternative deployment

**Prompt**
> Create `fly.toml` in the ThreatRAG project root for Fly.io deployment (alternative to Render).
> Configure: `app = "threatrag-api"`, `primary_region = "sin"` (Singapore — closest to UAE),
> `[build] dockerfile = "./backend/Dockerfile"`.
> Services: `internal_port = 8000`, `auto_stop_machines = "stop"`, `auto_start_machines = true`,
> `min_machines_running = 0` (scale to zero when unused — free tier).
> Set `[vm] memory = "512mb" cpu_kind = "shared" cpus = 1`.
> Write a `scripts/fly-deploy.sh` that: runs `fly auth login`, `fly apps create threatrag-api`,
> `fly secrets set ANTHROPIC_API_KEY=... QDRANT_URL=... DATABASE_URL=...`, then `fly deploy`.
> Note: Fly free tier includes 3 shared VMs × 256MB or 1 VM × 512MB — use the 512MB option.

---

---

# CROSS-CUTTING CONCERNS

---

## OWASP LLM Top 10 Security Hardening

**Prompt**
> Harden the ThreatRAG FastAPI backend against the OWASP LLM Top 10.
> LLM01 (Prompt Injection): In `backend/app/rag/chain.py`, add an input sanitisation step
> before the RAG query that checks for injection patterns
> (system prompt override attempts, role-play instructions, `ignore previous instructions`).
> Reject requests with `HTTP 400` and log the attempt.
> LLM02 (Insecure Output Handling): In the `/query` response, run the LLM answer through
> a sanitiser that strips HTML tags and control characters before returning it.
> LLM06 (Sensitive Information Disclosure): Add a post-processor that redacts patterns
> matching API keys, passwords, and PII (emails, phone numbers) from LLM outputs using regex.
> LLM09 (Misinformation): Add a confidence score field to `RAGResponse` that is `low`
> when fewer than 2 sources were retrieved (k < 2) and warn in the response.

---

## Prompt injection defence for agent tools

**Prompt**
> Implement prompt injection defence in `backend/app/agent/tools.py` for the ThreatRAG project.
> Create a `sanitise_tool_input(text: str) -> str` function that:
> (1) Truncates input to 500 characters,
> (2) Strips any text after known injection markers: `\nSystem:`, `\nHuman:`, `\nAI:`,
> `ignore previous`, `disregard`, `new instruction`,
> (3) Escapes curly braces to prevent f-string injection in prompt templates.
> Apply `sanitise_tool_input` to all tool inputs before they are used.
> Add a `max_tool_calls: int = 10` guard in the ReAct agent loop that raises
> `MaxToolCallsExceeded` if an agent makes more than 10 tool calls in one turn
> (prevents runaway loops from adversarial prompts).

---

## Langfuse observability

**Prompt**
> Add Langfuse observability to the ThreatRAG backend for tracing LLM calls.
> Install `langfuse` and `langfuse.decorators`.
> In `backend/app/core/config.py` add `langfuse_public_key: str = ""` and `langfuse_secret_key: str = ""`.
> In `backend/app/main.py`, initialise the Langfuse client in the lifespan if keys are set.
> In `ThreatRAGChain.query`, wrap the LLM call with `@observe(name="rag_query")` decorator.
> In the agent tools, wrap each `_arun` with `@observe(name="tool_{name}")`.
> In the LangGraph nodes, add `langfuse_handler = CallbackHandler()` to the LangGraph
> `config` dict so all node LLM calls are traced automatically.
> Langfuse Cloud free tier: 50K traces/month — sufficient for a learning project.

---

## GitHub Actions CI/CD

**Prompt**
> Write `.github/workflows/ci.yml` for the ThreatRAG project.
> Trigger on `push` to all branches and `pull_request` to `main`.
> Job `lint-backend`: checkout, setup python 3.11, install dev requirements,
> run `ruff check backend/` and `mypy backend/app`.
> Job `test-backend`: setup python, install requirements, run `pytest backend/tests/unit -v --cov=app --cov-report=xml`, upload coverage to Codecov.
> Job `test-integration` (only on `main` push): use `services` to spin up Qdrant and PostgreSQL,
> pull Ollama model, run `pytest backend/tests/integration -v -m integration`.
> Job `lint-frontend`: setup node 22, `npm ci` in `web/`, run `npm run lint` and `npm run typecheck`.
> Job `test-frontend`: run `npm run test -- --run --coverage`.
> Job `e2e` (only on PRs to main): build both Docker images, start with docker-compose, run Playwright.
> Job `deploy` (only on `main` push, after all tests pass): run `fly deploy` or trigger Render deploy hook.
