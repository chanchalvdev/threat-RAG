# ThreatRAG API Schema

Base URL: `http://localhost:8000`

---

## Health

### GET /health
Response 200:
```json
{ "status": "ok" }
```

### GET /health/ready
Response 200:
```json
{
  "status": "ready",
  "checks": { "qdrant": "ok", "ollama": "ok", "llm": "ok", "llm_fallback": "http_402", "postgres": "ok", "redis": "ok" }
}
```
Always HTTP 200. `status` is `ready` when every core dependency is `ok` and at least one LLM
provider completes a one-token request; otherwise `degraded`. `redis` appears only when
`REDIS_URL` is set, `llm_fallback` only when two providers are configured. Cached for 60 s.

---

## Ingest

### POST /api/v1/ingest/pdf
Content-Type: multipart/form-data
Body: `file` (PDF), `doc_type` (string)
Response 202:
```json
{ "status": "accepted", "job_id": "uuid", "filename": "example.pdf" }
```

### POST /api/v1/ingest/mitre
Response 202:
```json
{ "status": "accepted", "job_id": "uuid" }
```

### GET /api/v1/ingest/status/{job_id}
Response 200:
```json
{
  "job_id": "uuid",
  "status": "processing|completed|failed",
  "chunks_processed": 150,
  "total_chunks": 300,
  "error": null
}
```

### GET /api/v1/ingest/stats
Response 200:
```json
{
  "collection": "threat_intel",
  "total_vectors": 1250,
  "doc_type_counts": { "mitre_attack": 800, "owasp_llm": 450 }
}
```

---

## Query

### POST /api/v1/query
Body:
```json
{ "question": "What is T1110.001?", "doc_types": ["mitre_attack"], "k": 6 }
```
Response 200:
```json
{
  "answer": "T1110.001 is Password Guessing...",
  "sources": [
    {
      "text": "Technique: Password Guessing...",
      "source": "mitre_attack.json",
      "doc_type": "mitre_attack",
      "score": 0.92
    }
  ],
  "tokens_used": 450
}
```

### POST /api/v1/query/stream
Body: same as /query
Response: text/event-stream
```
data: {"type":"source","data":{"text":"...","source":"...","doc_type":"mitre_attack","score":0.92}}

data: {"type":"chunk","data":"T1110.001 is "}

data: {"type":"chunk","data":"Password Guessing..."}

data: {"type":"done"}
```

---

## Chat (Phase 2)

### POST /api/v1/chat/stream
Body:
```json
{ "question": "Investigate CVE-2021-44228", "session_id": null }
```
Response: text/event-stream (header: X-Session-ID: uuid)
```
data: {"type":"thought","data":"Searching knowledge base..."}

data: {"type":"tool_call","data":{"name":"threat_rag_search","input":"CVE-2021-44228","tool_use_id":"t1"}}

data: {"type":"tool_result","data":"Log4Shell is...","tool_use_id":"t1"}

data: {"type":"chunk","data":"CVE-2021-44228, known as..."}

data: {"type":"done","session_id":"uuid","total_tokens":1200}
```

### GET /api/v1/chat/history/{session_id}
Response 200:
```json
[
  { "role": "user", "content": "What is Log4Shell?" },
  { "role": "assistant", "content": "Log4Shell (CVE-2021-44228)..." }
]
```

---

## Investigate (Phase 3)

### POST /api/v1/investigate/stream
Body:
```json
{ "ioc": "CVE-2021-44228", "ioc_type": "cve", "session_id": null }
```
Response: text/event-stream
```
data: {"type":"node_start","node":"researcher","iteration":1}

data: {"type":"node_chunk","node":"researcher","data":"Gathering intel..."}

data: {"type":"node_done","node":"researcher","summary":"Gathered 12 sources"}

data: {"type":"routing","from":"critic","to":"reporter","reason":"APPROVED"}

data: {"type":"report_chunk","data":"# Threat Intelligence Report..."}
```

---

## Evaluate (Phase 3)

### POST /api/v1/evaluate
Body:
```json
{
  "question": "What is T1110?",
  "answer": "T1110 is Brute Force...",
  "contexts": ["Technique: Brute Force..."],
  "ground_truth": "Brute Force"
}
```
Response 200:
```json
{
  "faithfulness": 0.92,
  "answer_relevancy": 0.88,
  "context_precision": 0.85,
  "context_recall": 0.90,
  "overall": 0.89
}
```

---

## Changes in Phases 6–9

These supersede the older examples above where they differ.

### Authentication and limits
- `X-API-Key: <key>` is required on `/api/v1/*` when `API_KEY` is set.
- `Authorization: Bearer <HS256 JWT>` is required on `/api/v1/*` when `JWT_SECRET` is set. The token
  needs `sub` and `exp`. Chat sessions belong to `sub`.
- Each identity (or client address when anonymous) gets `RATE_LIMIT_PER_MINUTE` requests per minute.
  Over the limit: `429` with a `Retry-After` header.

### POST /api/v1/query (response)
```json
{
  "answer": "…",
  "sources": [{ "text": "…", "source": "MITRE ATT&CK Enterprise", "doc_type": "mitre_attack", "score": 0.74, "ref_id": "T1110.003" }],
  "tokens_used": 1385,
  "confidence": "high",
  "abstained": false
}
```
`confidence` is `high`, `low` or `none`. When nothing relevant is retrieved the API does not call
the model: `abstained` is `true`, `confidence` is `none`, `sources` is empty and `answer` says so.
`score` is always cosine similarity to the question.

### POST /api/v1/chat/stream (events)
Adds `{"type": "source", "data": <SourceDoc>}` for each passage the knowledge-base tool retrieved.
`GET /api/v1/chat/history/{session_id}` returns `[]` for an unknown session and for a session that
belongs to another identity. `DELETE` clears only the caller's own session.

### POST /api/v1/ingest/owasp
Ingests the OWASP Top 10 for LLM Applications 2025 from the project's Markdown sources.
Job status is stored in shared state for 24 hours.

### GET /api/v1/investigate/reports/{report_id}/stix
Response 200, `application/stix+json;version=2.1`, as a download. A STIX 2.1 bundle with the report,
the investigated indicator (or `vulnerability` for a CVE), the ATT&CK techniques the report cites
that exist in the ingested corpus, and the relationships between them. 404 if the report is unknown.

### GET /api/v1/metrics
```json
{
  "routes": { "POST /api/v1/query": { "requests": 12, "errors_5xx": 0, "p50_ms": 2140.2, "p95_ms": 5310.9 } },
  "llm": { "calls": 31, "tokens_in": 48210, "tokens_out": 7904, "p50_ms": 3100.0, "p95_ms": 9200.4,
           "estimated_cost_usd": null, "by_model": { "gemini-3.5-flash-lite": { "calls": 31, "tokens_in": 48210, "tokens_out": 7904 } } },
  "counters": { "guard_blocked": 2, "guard_allowed": 40, "rag_abstained": 3 }
}
```
Per process, reset on restart. Latency covers the last 500 requests per route (time to first byte
for streams). `estimated_cost_usd` is `null` until `LLM_PRICE_IN_PER_MTOK` / `LLM_PRICE_OUT_PER_MTOK` are set.

---

## Error Responses

### 422 Validation Error
```json
{
  "detail": [
    { "loc": ["body", "question"], "msg": "value too short", "type": "string_too_short" }
  ]
}
```

### 400 Bad Request (prompt injection detected)
```json
{ "detail": "Request rejected: potential prompt injection detected" }
```

### 503 Service Unavailable
```json
{ "detail": "Qdrant not available" }
```
