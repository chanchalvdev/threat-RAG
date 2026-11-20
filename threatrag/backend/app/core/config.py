from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Cloud Run mounts every key as one Secret Manager file (one secret = free tier); a missing
        # file is skipped, and the later file wins.
        env_file=(".env", "/secrets/threatrag.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM providers, tried in LLM_ORDER; one without a key is skipped (app/core/llm_providers.py)
    llm_order: str = "groq,openrouter,gemini,cerebras,kimchi"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "nvidia/nemotron-3.5-lightning:free"
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "qwen/qwen3.8-27b"
    cerebras_api_key: str = ""
    cerebras_base_url: str = "https://api.cerebras.ai/v1"
    cerebras_model: str = "gpt-oss-120b"
    # Kimchi (OpenAI-compatible); LLM_MODEL is its model
    kimchi_api_key: str = ""
    kimchi_base_url: str = "https://llm.kimchi.dev/openai/v1"
    llm_provider: Literal["kimchi", "openai"] = "kimchi"
    llm_model: str = "kimi-k2.6"
    llm_timeout_s: float = 120.0
    llm_max_tokens: int = 4096  # hard cap on completion length (guards against runaway generation)

    # Google Gemini via its OpenAI-compatible endpoint
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    gemini_model: str = "gemini-3.5-flash-lite"

    # Evaluation judge: a different model from the generator, so it does not grade its own work.
    # JUDGE_PROVIDER names a provider in LLM_ORDER to take its key and URL; else JUDGE_API_KEY /
    # JUDGE_BASE_URL; else the primary provider's.
    judge_model: str = ""
    judge_provider: str = ""
    judge_api_key: str = ""
    judge_base_url: str = ""

    # API surface
    cors_origins: list[str] = [
        "http://localhost:5173", "http://localhost:5174", "http://localhost:3000",
    ]
    api_key: str = ""  # when set, /api/v1/* requires header X-API-Key
    # Prompt-injection guard: heuristic scoring; "llm" adds a judge-model second opinion on borderline input
    guard_mode: Literal["off", "heuristic", "llm"] = "heuristic"
    max_upload_mb: int = 25
    jwt_secret: str = ""               # when set, /api/v1/* requires an HS256 bearer token; sessions are per subject
    rate_limit_per_minute: int = 120   # per identity (or per client address when anonymous); 0 disables
    llm_daily_request_cap: int = 0     # all callers together, per UTC day, on routes that call a model; 0 disables
    redis_url: str = ""                # empty = in-process state (single worker, lost on restart)

    # Vector Store
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "threat_intel_v2"  # v2 = named dense + sparse vectors (hybrid search)

    # Embeddings
    embedding_provider: Literal["ollama", "gemini"] = "ollama"
    ollama_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 768

    # Database (Phase 3)
    database_url: str = "postgresql://threatrag:threatrag@localhost:5432/threatrag"

    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retrieval_k: int = 6

    # Retrieval (Phase 7). Thresholds are cosine similarities calibrated on eval/golden.jsonl.
    retrieval_mode: Literal["dense", "hybrid"] = "hybrid"
    exact_match: bool = True              # look up T####(.###) / LLM## identifiers directly
    reranker: Literal["none", "cross_encoder"] = "none"
    reranker_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    rerank_candidates: int = 20
    max_chunks_per_ref: int = 2           # chunks of one technique allowed in the final context
    abstain_below: float = 0.57           # best match weaker than this: answer "not in the knowledge base"
    confident_above: float = 0.68

    # Observability
    debug: bool = False
    log_format: str = "console"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    # USD per million tokens for the primary model; 0 = cost is reported as unknown
    llm_price_in_per_mtok: float = 0.0
    llm_price_out_per_mtok: float = 0.0

    # External APIs
    tavily_api_key: str = ""
    abuseipdb_api_key: str = ""
    otx_api_key: str = ""
    abusech_auth_key: str = ""  # shared by MalwareBazaar, URLhaus and ThreatFox
    nvd_api_key: str = ""       # raises NVD's limit from 5 to 50 requests per 30 s
    virustotal_api_key: str = ""
    greynoise_api_key: str = ""

    # Report notifications (Phase 12). URLs come from configuration only, never from a request.
    slack_webhook_url: str = ""
    teams_webhook_url: str = ""
    public_base_url: str = ""   # links in notifications point here

    # Feeds (Phase 11): a TAXII 2.1 collection URL (.../collections/<id>/); auth optional
    taxii_url: str = ""
    taxii_user: str = ""
    taxii_password: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
