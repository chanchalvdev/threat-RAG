# Phase 3 — Multi-Agent + Evaluation Specification

## Goal
LangGraph Researcher→Critic→Reporter pipeline. RAGAs eval. pgvector report persistence.

---

## Backend Features

### F3.1 — Investigation State (backend/app/agent/graph.py)
- `InvestigationState(TypedDict)`: ioc, ioc_type, researcher_output,
  critic_feedback, final_report, sources, tool_calls, iteration, status
- `InvestigationRequest(BaseModel)`: ioc, ioc_type, session_id
- `InvestigationReport(BaseModel)`: all final fields + ragas_scores

### F3.2 — Researcher Node
- Uses all 3 tools from Phase 2
- Compiles: IOC Overview, Technical Analysis, MITRE Mapping, Related Threats, Raw Evidence

### F3.3 — Critic Node
- No tools — reviews researcher output only
- Returns "APPROVED" or "NEEDS_REVISION: gap1 | gap2 | ..."
- Routes to reporter if approved OR if iteration >= 2

### F3.4 — Reporter Node
- Produces structured markdown report with Executive Summary,
  Technical Analysis, MITRE Coverage table, IOC table, Recommendations, References

### F3.5 — Graph Assembly
- `StateGraph(InvestigationState)`
- researcher → critic → (conditional) → reporter | researcher
- `app = graph.compile()`
- `run_investigation(request)` wrapper

### F3.6 — Streaming Graph (backend/app/agent/graph.py)
- `app.astream_events(state, version="v2")`
- Emits: `node_start`, `node_chunk`, `node_done`, `routing`, `report_chunk`
- `POST /api/v1/investigate/stream` route

### F3.7 — RAGAs Evaluation (backend/app/evaluation/ragas_eval.py)
- `evaluate_response(question, answer, contexts, ground_truth)` → `RagasScores`
- Metrics: faithfulness, answer_relevancy, context_precision, context_recall
- Skips recall when ground_truth is None
- `POST /api/v1/evaluate` route

### F3.8 — DB Connection (backend/app/db/connection.py)
- `psycopg` async pool (min=2, max=10)
- `get_db_conn` FastAPI dependency

### F3.9 — Report Storage (backend/app/db/reports.py)
- `save_report(report, embedding)` → report_id
- `find_similar_reports(embedding, k=5)` → list of ReportSummary
- `get_report(report_id)` → InvestigationReport | None

### F3.10 — SQL Migration (backend/migrations/001_init.sql)
- `CREATE EXTENSION IF NOT EXISTS vector`
- `reports` table with HNSW index on embedding

---

## Frontend Features

### F3.11 — Investigate Page (web/src/pages/Investigate.tsx)
- IOC input + type selector
- Three agent cards (Researcher, Critic, Reporter) with status
- Animated arrow on routing events
- Similar past reports row at bottom

### F3.12 — ReportViewer (web/src/components/ReportViewer.tsx)
- Streaming markdown render
- MITRE table with severity colouring
- Copy Markdown + Export PDF + Save Report actions
- RAGAs score bars below report

### F3.13 — Analytics Page (web/src/pages/Analytics.tsx)
- 4 recharts LineCharts for RAGAs metrics over time
- Recent queries table
- "Run evaluation" modal

---

## Acceptance Criteria (Phase 3 Done When:)
- [ ] CVE-2021-44228 investigation produces report with "Log4Shell" + MITRE table
- [ ] Critic routes back to researcher at least once for a gap-filled query
- [ ] RAGAs scores returned for a test evaluation call
- [ ] Report saved to PostgreSQL and retrieved via similar report search
- [ ] Investigate UI shows all 3 agent cards transitioning state
