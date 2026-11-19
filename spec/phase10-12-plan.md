# Phases 10–13 — Analyst loop, fresh knowledge, wider enrichment, deployment

**Date:** 2026-11-19
**Source:** the unbuilt rows of `spec/phase4.md` Part C, plus the findings still open in
`spec/phase5-9-plan.md` (G31, G43).
**Branches:** one per phase, each merged only when its gate is green.

| Phase | Branch | Theme | Status |
|---|---|---|---|
| 10 | `feat/phase10-analyst-feedback` | Feedback on answers and reports; analyst sends a report back | in progress |
| 11 | `feat/phase11-fresh-knowledge` | Scheduled ATT&CK / KEV / TAXII refresh, guarded by the eval | planned |
| 12 | `feat/phase12-enrichment-exports` | RDAP, VirusTotal, GreyNoise; PDF export; Slack / Teams | planned |
| 13 | `feat/phase13-deploy` | Public deployment, live Langfuse trace, live-model CI test | needs accounts |

Gate for every phase: `ruff check app/` clean · `mypy app/` clean · `pytest tests/unit` green with
coverage ≥ 80% · web `lint`, `typecheck`, `test`, `build`, `e2e` green · `e2e:stack` green on the
compose stack · files ≤ 150 lines. Every new key is optional: with it empty the feature is off and
nothing else changes. Keys and how to get them: `docs/environment.md`.

Still out of scope: SIEM webhooks, case management, RBAC, multi-tenancy, Helm, OIDC (G35).

---

## Phase 10 — Analyst feedback

- F10.1 Migration `003_feedback.sql`: `feedback` (subject, target `answer` | `report`, target ID,
  rating ±1, note, question, answer excerpt), one row per subject and target, so a second vote
  replaces the first. `reports` gains `parent_id` and `analyst_gaps`.
- F10.2 `POST /feedback` (keyed by `identity.sub`), `GET /feedback/summary` (counts per target and
  the latest down-votes), `GET /feedback/candidates` (down-voted answers as JSONL in the golden-set
  shape, for a human to complete and add to `eval/golden.jsonl`; never added automatically).
- F10.3 Send back: `InvestigationRequest` accepts `analyst_gaps` and `parent_id`. The gaps pass
  `ensure_safe`, open the run as the Critic's revision request, and the new report links to its
  parent. The `done` event carries the Critic's last feedback so the UI can prefill the gaps.
- F10.4 UI: thumbs and an optional note on chat answers and reports; "Send back to Researcher" on a
  finished report; a feedback panel and candidate download on Analytics.

Acceptance: a vote persists per identity and a re-vote replaces it; a send-back produces a new
report whose parent is the first and whose research addresses the stated gaps; an injection in
`analyst_gaps` is rejected with 400; Analytics shows the counts.

## Phase 11 — Fresh knowledge

- F11.1 ATT&CK release check: a conditional GET (ETag) on the STIX bundle. Unchanged: nothing
  happens. Changed: re-index, then delete points that the new release no longer produces
  (revoked or deprecated techniques), so the index never empties mid-refresh.
- F11.2 CISA KEV moves from a per-process dict into shared state (`get_state`), refreshed by the
  job and fetched on a miss.
- F11.3 TAXII 2.1 pull (`TAXII_URL`, optional `TAXII_USER` / `TAXII_PASSWORD`): reports,
  indicators, malware and intrusion sets since the stored `added_after` cursor, indexed as
  `doc_type=taxii`.
- F11.4 `NVD_API_KEY`, sent as `apiKey` (50 instead of 5 requests per 30 s).
- F11.5 `python -m app.scripts.refresh_feeds [--every 24h]`: lock in shared state, run F11.1–F11.3,
  and after an ATT&CK re-index run the retrieval eval; a hit@6 drop over 0.03 against the last run
  is logged as an error and exits non-zero. Last run is visible at `GET /ingest/feeds`.
- F11.6 Compose `scheduler` service (profile `feeds`) runs the loop with the backend image.

Acceptance: an unchanged ETag re-indexes nothing; a changed bundle removes stale techniques; two
API workers share one KEV copy; the TAXII cursor advances; the NVD key is sent when set.

## Phase 12 — Enrichment and exports

- F12.1 RDAP (no key) for domains and IPs: registrar, registration date (domain age), status,
  network name and country.
- F12.2 VirusTotal v3 (`VIRUSTOTAL_API_KEY`) for hashes, IPs and domains: engine verdict counts,
  reputation, popular threat label.
- F12.3 GreyNoise Community (`GREYNOISE_API_KEY`) for IPs: internet-scanner noise, benign
  business service (RIOT), classification.
- F12.4 `GET /investigate/reports/{id}/pdf`: the report as a PDF (IOCs printed verbatim).
- F12.5 `POST /investigate/reports/{id}/notify` with `channel` `slack` | `teams`: posts IOC, type
  and summary to `SLACK_WEBHOOK_URL` / `TEAMS_WEBHOOK_URL`. URLs come from configuration only,
  never from the request. `GET /investigate/exports` says which channels are configured.
- F12.6 UI: PDF download and channel buttons next to STIX export, shown only when configured.

Acceptance: each new source appears in tool evidence when keyed and as "not checked" when not; a
PDF opens and contains the report; a notify call posts once to the configured URL and returns 409
when the channel is not configured.

## Phase 13 — Deploy and verify (needs the owner's accounts)

- The web image's API target comes from `BACKEND_URL` (nginx template), so the two images can be
  hosted separately.
- Hosted Qdrant, Postgres (pgvector) and Redis; Gemini embeddings in a new collection, re-ingested.
- G31: one live Langfuse trace. G43: public URL with `LLM_DAILY_REQUEST_CAP` and `JWT_SECRET` or
  `API_KEY`. CI runs `STACK_LLM=1` with a repository secret.
