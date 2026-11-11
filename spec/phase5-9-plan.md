# Phases 5–9 — From working demo to defensible system

**Date:** 2026-11-11
**Source:** end-to-end audit on 2026-11-11 (code, specs, lint/type/test gates, guardrail probes).
**Branches:** one stacked branch per phase, each merged only when its gate is green.

| Phase | Branch | Theme | Status |
|---|---|---|---|
| 5 | `feat/phase5-ship-and-show` | Repo packaging, docs, hygiene | **done** 2026-11-11 |
| 6 | `feat/phase6-eval-harness` | Golden set + offline evaluation | planned |
| 7 | `feat/phase7-hybrid-retrieval` | Hybrid search, rerank, abstention, richer corpus | planned |
| 8 | `feat/phase8-guardrails-observability` | Injection guard, IOC-safe sanitiser, telemetry | planned |
| 9 | `feat/phase9-production-shape` | Shared state, identity, integration/E2E tests, STIX export | planned |

Gate for every phase: `ruff check app/` clean · `mypy app/` clean · `pytest tests/unit` green with
coverage ≥ 80% · web `lint`, `typecheck`, `build` green · files ≤ 150 lines.

---

## Audit findings these phases close

| # | Finding | Phase |
|---|---|---|
| A1 | README is one line; no licence, results, demo or design notes | 5 |
| A2 | 139 MB of source data tracked in git despite `.gitignore` | 5 |
| A3 | Docs disagree with the code (LangChain 0.3 vs 1.3, Kimchi-primary, G25 open) | 5 |
| A4 | No golden dataset; quality is one manual run on a 3B model | 6 |
| A5 | Context precision uses the answer as its own reference (circular) | 6 |
| A6 | Judge is the same model as the generator | 6 |
| A7 | Dense-only retrieval; technique and CVE IDs retrieve poorly | 7 |
| A8 | `confidence` is "high" whenever ≥ 2 hits come back | 7 |
| A9 | MITRE descriptions cut at 1,000 chars; no mitigations, detections or groups | 7 |
| A10 | Regex injection filter blocks legitimate questions and misses paraphrases | 8 |
| A11 | Output sanitiser redacts IOCs (emails, digit runs) and HTML-escapes code | 8 |
| A12 | Tool and feed output reaches the LLM as plain text (indirect injection) | 8 |
| A13 | No tracing, token, cost or latency telemetry | 8 |
| A14 | Sessions and ingest jobs live in process memory; no rate limit | 9 |
| A15 | Any caller can read or clear any chat session (G26) | 9 |
| A16 | No integration, frontend or E2E tests | 9 |

---

## Phase 5 — Ship and show

- F5.1 README with pitch, architecture, quickstart, results table, design decisions, limits.
- F5.2 Stop tracking `backend/data/` and `web/dist/`; ingestion downloads sources on demand.
- F5.3 Move guides into `docs/`; fix every stale statement in `CLAUDE.md` and `spec/`.
- F5.4 Add `LICENSE` (MIT).
- F5.5 LLM model IDs come from config only; the default must be a model the provider serves.

Acceptance: a fresh clone is < 5 MB of tracked files; README quickstart matches the Makefile;
no doc names a version or provider order the code does not use.

## Phase 6 — Prove quality

- F6.1 `eval/golden.jsonl`: ≥ 60 questions with expected technique IDs / doc types, including
  ID lookups, paraphrases, OWASP LLM questions and unanswerable questions.
- F6.2 `app/evaluation/retrieval_metrics.py`: hit@k, MRR, exact-ID recall (pure functions).
- F6.3 `python -m app.scripts.run_eval`: retrieval metrics always; answer metrics
  (faithfulness, citation rate, abstention accuracy) when an LLM is reachable. Writes
  `eval/results/<label>.json` and a Markdown table.
- F6.4 Separate judge model (`JUDGE_MODEL` / `JUDGE_BASE_URL` / `JUDGE_API_KEY`).
- F6.5 Reference-free context precision when no ground truth is supplied (fixes A5).
- F6.6 Baseline numbers for the Phase 1 retriever recorded in `eval/results/`.

Acceptance: the golden set validates against the ingested corpus (every expected ID exists);
the runner reproduces the baseline table from a clean checkout plus a running stack.

## Phase 7 — Retrieval worth measuring

- F7.1 Sparse lexical vectors (`app/rag/sparse.py`) stored beside dense vectors; Qdrant IDF modifier.
- F7.2 Reciprocal-rank fusion of dense and sparse results (`app/rag/fusion.py`).
- F7.3 Exact-match path for `T####(.###)` and `CVE-YYYY-N` identifiers.
- F7.4 Optional cross-encoder reranker (`RERANKER=cross_encoder`), off the event loop.
- F7.5 Calibrated confidence and abstention: no LLM call when nothing relevant is retrieved.
- F7.6 MITRE ingestion keeps full descriptions (chunked), adds mitigations, detection notes and
  groups, and skips revoked/deprecated techniques. OWASP LLM Top 10 moves to the 2025 edition.
- F7.7 Ablation table (dense → hybrid → +exact → +rerank) produced by the Phase 6 runner.

Acceptance: exact-ID recall@6 ≥ 0.95 and hit@6 improves over the Phase 6 baseline; the
unanswerable questions abstain.

## Phase 8 — Guardrails and observability

- F8.1 `app/guard/`: scored injection detector that separates instructions from discussion,
  with an optional LLM second opinion for borderline input (`GUARD_MODE`).
- F8.2 `eval/injection_suite.jsonl` (attacks + benign security questions) and a runner that
  reports block rate and false-positive rate; thresholds enforced in unit tests.
- F8.3 Tool output is wrapped as untrusted data before it reaches the model (fixes A12).
- F8.4 Sanitiser keeps IOCs, redacts only credential-shaped strings, no HTML escaping,
  and works across stream chunk boundaries (fixes A11).
- F8.5 Telemetry: per-route latency p50/p95, LLM tokens and estimated cost, exposed at
  `GET /api/v1/metrics`; Langfuse tracing when keys are set.

Acceptance: block rate ≥ 90% and false-positive rate ≤ 5% on the suite; the four probes from
the audit behave correctly; `/metrics` reports real numbers after a query.

## Phase 9 — Production shape

- F9.1 `app/core/state.py`: key-value state with in-memory and Redis backends
  (`REDIS_URL`); chat history and ingest jobs move onto it (fixes A14).
- F9.2 Rate limiting per identity or IP (fixed window) → HTTP 429.
- F9.3 Identity: optional HS256 JWT (`JWT_SECRET`); chat sessions are owned by their subject
  (fixes A15 / G26).
- F9.4 Integration tests against real Qdrant, Postgres and Redis; CI job with service containers.
- F9.5 Frontend unit tests (Vitest) and one Playwright happy path.
- F9.6 STIX 2.1 bundle export for a saved report (`GET /investigate/reports/{id}/stix`).

Acceptance: restarting the API keeps chat history when Redis is configured; a second identity
gets 404 on another's session; the STIX bundle validates structurally.

---

## Out of scope (deliberately)

Helm/Kubernetes, multi-tenancy, RBAC roles, case management, SIEM webhooks. They cost weeks and
do not change the answer to "does this system work, and how do you know?".
