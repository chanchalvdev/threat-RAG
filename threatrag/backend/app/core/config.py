from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM fallback — Kimchi (OpenAI-compatible), used when its key is set
    kimchi_api_key: str = ""
    kimchi_base_url: str = "https://llm.kimchi.dev/openai/v1"
    llm_provider: Literal["kimchi", "openai"] = "kimchi"
    llm_model: str = "kimi-k2.6"
    llm_timeout_s: float = 120.0
    llm_max_tokens: int = 4096  # hard cap on completion length (guards against runaway generation)

    # LLM primary — Google Gemini via its OpenAI-compatible endpoint
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    gemini_model: str = "gemini-3.5-flash-lite"

    # Evaluation judge: a different model from the generator, so it does not grade its own work.
    # Key and base URL default to the primary provider's.
    judge_model: str = ""
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
