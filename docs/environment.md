# Environment values — local and deployed

Every setting lives in `threatrag/backend/.env` locally (copy `.env.example`) and in the host's
secret/env settings when deployed. **Every external key is optional**: left empty, that feature
is off and the rest of the system works. Never commit `.env`; it is gitignored.

Generate a random secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## 1. Model and embeddings

| Variable | Local | Deployed | How to get it |
|---|---|---|---|
| `LLM_ORDER` | `groq,openrouter,gemini,cerebras` | same | Providers tried in order; one with an empty key is skipped, so the first keyed one is primary and the rest are its fallback chain. Known: `openrouter`, `groq`, `cerebras`, `gemini`, `kimchi`. |
| `OPENROUTER_API_KEY` | fallback | fallback | [openrouter.ai/keys](https://openrouter.ai/keys) → *Create Key* (`sk-or-v1-…`). Free models end in `:free`: 20 requests/min, **50/day** until the account has bought $10 of credits once, then 1,000/day. |
| `OPENROUTER_MODEL` | `nvidia/nemotron-3.5-lightning:free` | same | Must support tool calling. List free tool-capable models: `curl -s https://openrouter.ai/api/v1/models` and keep IDs ending `:free` whose `supported_parameters` include `tools`. |
| `GEMINI_API_KEY` | fallback | fallback | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) → *Create API key*. Free tier: 15 requests/min. Also used for the judge and for cloud embeddings. |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | same | Must be a model your key serves. On a 404, list models: `curl "https://generativelanguage.googleapis.com/v1beta/openai/models" -H "Authorization: Bearer $GEMINI_API_KEY"` |
| `GROQ_API_KEY`, `GROQ_MODEL` | primary (`qwen/qwen3.8-27b`) | primary | [console.groq.com/keys](https://console.groq.com/keys). Free, no card, the lowest latency of the free options. Free tier: 1,000 requests/day, 8,000 tokens/min per model, so a long investigation spills over to the next provider. Model list: `GET https://api.groq.com/openai/v1/models`. |
| `CEREBRAS_API_KEY`, `CEREBRAS_MODEL` | optional | optional | [cloud.cerebras.ai](https://cloud.cerebras.ai) → *API Keys*. Free, no card, very fast; generous daily token allowance. |
| `JUDGE_MODEL`, `JUDGE_PROVIDER` | `gemini-3.1-flash-lite`, `gemini` | same | A different model from the generator, so evaluation does not grade its own work. `JUDGE_PROVIDER` names whose key and URL it uses. |
| `KIMCHI_API_KEY`, `LLM_MODEL` | not used | not used | Only when `kimchi` is in `LLM_ORDER`. |
| `EMBEDDING_PROVIDER` | `ollama` | `gemini` | Most hosts cannot run Ollama. Gemini embeddings reuse `GEMINI_API_KEY`. |
| `OLLAMA_URL` | `http://localhost:11434` | — | `brew install ollama && ollama pull nomic-embed-text` |
| `QDRANT_COLLECTION` | `threat_intel_v2` | e.g. `threat_intel_gemini` | **A new embedder needs a new collection name and a re-ingest**: the API refuses to start on a collection built with another embedder. |

## 2. Data stores

| Variable | Local | Deployed | How to get it |
|---|---|---|---|
| `QDRANT_URL` | `http://localhost:6333` | cluster URL | [cloud.qdrant.io](https://cloud.qdrant.io) → free 1 GB cluster → copy the URL (`https://…:6333`). |
| `QDRANT_API_KEY` | empty | cluster key | Same console → *API Keys* → create. |
| `DATABASE_URL` | `postgresql://threatrag:threatrag@localhost:5435/threatrag` | `postgresql://…?sslmode=require` | [neon.tech](https://neon.tech) or [supabase.com](https://supabase.com) (both support pgvector) → create project → connection string. Migrations run at API start-up and enable `vector` themselves. |
| `REDIS_URL` | `redis://localhost:6380/0` | `rediss://default:…@…:6379` | [upstash.com](https://upstash.com) → create Redis database → copy the `rediss://` URL. Empty = state lives in one process and is lost on restart. |

Local stores come from `docker compose -f threatrag/infra/docker-compose.yml up -d qdrant postgres redis`.

## 3. Web search and threat-intel enrichment

All free tiers. Each source shows as "not checked (no API key configured)" in tool evidence until set.

| Variable | Used by | How to get it |
|---|---|---|
| `TAVILY_API_KEY` | chat agent's `web_search` | [app.tavily.com](https://app.tavily.com) → sign up → the key is on the dashboard (`tvly-…`). |
| `ABUSEIPDB_API_KEY` | IP lookups | [abuseipdb.com/register](https://www.abuseipdb.com/register) → *Account* → *API* → *Create Key*. |
| `OTX_API_KEY` | IP, domain, hash lookups | [otx.alienvault.com](https://otx.alienvault.com) → sign up → *Settings* → *OTX Key*. |
| `ABUSECH_AUTH_KEY` | MalwareBazaar, URLhaus, ThreatFox | [auth.abuse.ch](https://auth.abuse.ch) → sign in (GitHub/Google/X) → *Optional* → *Generate Auth-Key*. One key covers all three. |
| `NVD_API_KEY` *(Phase 11)* | CVE lookups | [nvd.nist.gov/developers/request-an-api-key](https://nvd.nist.gov/developers/request-an-api-key) → the key arrives by email; activate it from the link. |
| `VIRUSTOTAL_API_KEY` *(Phase 12)* | hash, IP, domain lookups | [virustotal.com](https://www.virustotal.com/gui/join-us) → sign up → profile menu → *API key*. Free: 4 requests/min, 500/day. |
| `GREYNOISE_API_KEY` *(Phase 12)* | IP lookups | [viz.greynoise.io/signup](https://viz.greynoise.io/signup) → *Account* → *API Key* (Community). |

No key needed: Shodan InternetDB, CISA KEV, FIRST EPSS, RDAP *(Phase 12)*.

## 4. Feeds and notifications

| Variable | Phase | How to get it |
|---|---|---|
| `TAXII_URL` | 11 | A TAXII 2.1 **collection** URL from your TIP (OpenCTI, MISP, a vendor feed). To try it: MITRE's public server `https://attack-taxii.mitre.org/api/v21/collections/<id>/` (list IDs at `…/api/v21/collections/`). |
| `TAXII_USER`, `TAXII_PASSWORD` | 11 | From the feed provider; empty for public servers. |
| `SLACK_WEBHOOK_URL` | 12 | [api.slack.com/apps](https://api.slack.com/apps) → *Create New App* → *Incoming Webhooks* → on → *Add New Webhook to Workspace* → pick a channel → copy `https://hooks.slack.com/services/…`. |
| `TEAMS_WEBHOOK_URL` | 12 | Teams channel → *Workflows* → template *"Post to a channel when a webhook request is received"* → copy the URL it shows. |
| `PUBLIC_BASE_URL` | 12 | The site's public address, so notifications link to the report. |

## 5. Observability

| Variable | How to get it |
|---|---|
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` | [cloud.langfuse.com](https://cloud.langfuse.com) → create organisation and project → *Settings* → *API Keys* → *Create* (`pk-lf-…`, `sk-lf-…`). |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` (EU) or `https://us.cloud.langfuse.com` (US), matching the region you signed up in. |
| `LLM_PRICE_IN_PER_MTOK`, `LLM_PRICE_OUT_PER_MTOK` | USD per million tokens from the provider's pricing page. 0 = cost shown as "not priced". |

## 6. Access control (deployed)

| Variable | Local | Deployed |
|---|---|---|
| `JWT_SECRET` | empty (everyone is `anonymous`) | random secret (above). Mint tokens with `python -m app.scripts.mint_token --sub alice`. |
| `API_KEY` | empty | Alternative to JWT for a single client: random secret, sent as `X-API-Key`. |
| `LLM_DAILY_REQUEST_CAP` | `0` (off) | e.g. `300`: all model-calling requests per UTC day, across every visitor. |
| `RATE_LIMIT_PER_MINUTE` | `120` | `30`–`60` for a public demo. |
| `FORWARDED_ALLOW_IPS` | — | The proxy's address(es) the API trusts for `X-Forwarded-For`, so rate limits see visitors, not the proxy. `*` only if the API is not reachable except through that proxy. |
| `CORS_ORIGINS` | defaults cover Vite | `["https://your-site.example"]` when the browser calls the API from another origin. |
| `DEBUG` | `true` | `false` |
| `LOG_FORMAT` | `console` | `json` |

## 7. Web image

| Variable | Compose | Hosted apart |
|---|---|---|
| `BACKEND_URL` | `http://backend:8000` (default) | The API's URL, e.g. `https://threatrag-api.onrender.com`. nginx proxies `/api` and `/health` to it, so the browser stays same-origin and `CORS_ORIGINS` can stay narrow. |

---

## Checklists

**Local, full features:** `OPENROUTER_API_KEY` and/or `GROQ_API_KEY`, `GEMINI_API_KEY`, `JUDGE_MODEL`, `REDIS_URL=redis://localhost:6380/0`,
`TAVILY_API_KEY`, `ABUSEIPDB_API_KEY`, `OTX_API_KEY`, `ABUSECH_AUTH_KEY`, then (as their phases
land) `NVD_API_KEY`, `VIRUSTOTAL_API_KEY`, `GREYNOISE_API_KEY`, `SLACK_WEBHOOK_URL`.
Restart the API after editing `.env`; `GET /health/ready` shows what is connected.

**Deployed:** everything above except Ollama, plus `EMBEDDING_PROVIDER=gemini` with a new
`QDRANT_COLLECTION`, hosted `QDRANT_URL`/`QDRANT_API_KEY`, `DATABASE_URL`, `REDIS_URL`,
`JWT_SECRET` or `API_KEY`, `LLM_DAILY_REQUEST_CAP`, `FORWARDED_ALLOW_IPS`, `DEBUG=false`,
`LOG_FORMAT=json`, and `BACKEND_URL` on the web service. After the first deploy, ingest once:
`POST /api/v1/ingest/mitre` and `POST /api/v1/ingest/owasp` (with your token or key).
