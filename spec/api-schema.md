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
  "checks": { "qdrant": "ok", "ollama": "ok", "llm": "ok" }
}
```
Response 503 (any check fails):
```json
{
  "status": "degraded",
  "checks": { "qdrant": "ok", "ollama": "error: connection refused", "llm": "ok" }
}
```

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
