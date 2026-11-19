# Phases 10–13 — Analyst loop, fresh knowledge, wider enrichment, deployment

**Date:** 2026-11-19
**Source:** the unbuilt rows of `spec/phase4.md` Part C, plus the findings still open in
`spec/phase5-9-plan.md` (G31, G43).
**Branches:** one per phase, each merged only when its gate is green.

| Phase | Branch | Theme | Status |
|---|---|---|---|
| 10 | `feat/phase10-analyst-feedback` | Feedback on answers and reports; analyst sends a report back | **done** 2026-11-19 |
| 11 | `feat/phase11-fresh-knowledge` | Scheduled ATT&CK / KEV / TAXII refresh, guarded by the eval | **done** 2026-11-20 |
| 12 | `feat/phase12-enrichment-exports` | RDAP, VirusTotal, GreyNoise; PDF export; Slack / Teams | **done** 2026-11-20 |
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

### Phase 10 result (verified 2026-11-19 on the compose stack, `gemini-3.5-flash-lite`)

- `CVE-2021-44228` filed, then sent back with "State the FIRST EPSS exploitation probability and
  whether CISA KEV lists it as actively exploited": the revision's first tool call was
  `cve_exploitation_lookup`, its summary states EPSS 100% and KEV with ransomware use, and it is
  stored with `parent_id` and `analyst_gaps`. (The parent already carried both figures, so this
  run proves the loop and the lineage, not an improvement in that report.)
- Unit 268 (coverage 90%), integration 11 (real Postgres: re-vote replaces, lineage), Playwright 6
  mocked + 5 full-stack (a vote stored in Postgres appears on Analytics).

Found during Phase 10:

| # | Finding | Status |
|---|---|---|
| G47 | A provider 429 (Gemini free tier: 15 requests/min; one investigation uses most of it) falls through to the fallback, and with Kimchi out of credits (402) the API answers a bare 500 | **fixed** 2026-11-20: when every provider fails on capacity (402/429/503), a typed `ModelUnavailable` carries the provider's retry hint; the API answers 503 with `Retry-After`, streams say when to try again. Other failures keep their own error |
| G48 | The backend image never contained `migrations/`: on a fresh database the migrator found no files, logged success and created no tables (found by the first CI full-stack run of `/feedback`; local Postgres already had tables) | **fixed**: image copies `migrations/`; the migrator raises when it finds none; verified on an empty database |

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

### Phase 11 result (verified 2026-11-20 on the compose stack)

- First run: the live ATT&CK bundle had changed since the corpus was built: 706 techniques,
  3,479 passages (was 3,428), 1 stale passage pruned, 96 s on CPU embeddings. A second run took
  3 s: ETag unchanged, nothing downloaded or indexed. KEV: 1,786 CVEs in shared state.
- The eval guard caught a real change: hit@6 fell from 0.946 to 0.929 because the new release
  adds T1698 Indirect and T1699 Direct Prompt Injection, which now outrank OWASP for `ow07`
  ("difference between direct and indirect prompt injection?"). The golden set was stale, not the
  retrieval: a golden item now accepts an expected technique or a matching passage of the
  expected type, and `ow07` lists T1698/T1699. On the new corpus: hit@6 0.946, hit@3 0.893 → 0.911,
  MRR 0.876 → 0.881 (`eval/results/v4-attack-refresh.json`).
- That first run also showed the guard had nothing to compare with, so a first re-index became
  the baseline unchecked. The job now scores the index before its first ATT&CK refresh; the
  forced re-run recorded baseline 0.946 → after 0.946.
- The bundle carries no release number; the release is named by its newest object change.
- TAXII: client verified read-only against MITRE's public TAXII 2.1 server (ICS collection: 1,190
  objects since 2025-01-01 → 64 passages, cursor from `X-TAXII-Date-Added-Last`); one request
  there returned a transient 502, which fails the step and leaves the cursor for the next run.
- Unit 281, Playwright 8 mocked + 5 full-stack.

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

### Phase 12 result (verified 2026-11-20)

- RDAP live, no key: `example.com` and `github.com` (registration date, age, registrar, status via
  rdap.org's redirect to Verisign), `8.8.8.8` (GOGL, Google LLC) and `185.220.101.1` (ARTIKEL10,
  DE). A domain registered under 30 days is marked NEWLY REGISTERED.
- VirusTotal and GreyNoise: parsing and auth headers unit-tested; not live-tested (no keys yet).
- PDF on the compose stack: the real `CVE-2021-44228` revision exports as a 2-page PDF with the
  IOC, the EPSS figures, the ATT&CK table, its sources and "revision of" its parent. Raw HTML in a
  report is printed as text, never rendered: an `<img src>` would otherwise be fetched by the
  server (SSRF from model output).
- Slack / Teams: payloads, https-only configured URLs, 409 when not configured and 502 when the
  webhook refuses are unit-tested; not posted to a real workspace (no webhook yet).
- Unit 290 (coverage 91%), Playwright 9 mocked + 6 full-stack.

## Phase 13 — Deploy and verify (needs the owner's accounts)

- The web image's API target comes from `BACKEND_URL` (nginx template), so the two images can be
  hosted separately.
- Hosted Qdrant, Postgres (pgvector) and Redis; Gemini embeddings in a new collection, re-ingested.
- G31: one live Langfuse trace. G43: public URL with `LLM_DAILY_REQUEST_CAP` and `JWT_SECRET` or
  `API_KEY`. CI runs `STACK_LLM=1` with a repository secret.
