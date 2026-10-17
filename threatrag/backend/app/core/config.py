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

    # LLM — Kimchi (OpenAI-compatible)
    kimchi_api_key: str = ""
    kimchi_base_url: str = "https://llm.kimchi.dev/openai/v1"
    llm_provider: Literal["kimchi", "openai"] = "kimchi"
    llm_model: str = "kimi-k2.6"
    llm_timeout_s: float = 120.0
    llm_max_tokens: int = 4096  # hard cap on completion length (guards against runaway generation)

    # API surface
    cors_origins: list[str] = [
        "http://localhost:5173", "http://localhost:5174", "http://localhost:3000",
    ]
    api_key: str = ""  # when set, /api/v1/* requires header X-API-Key
    max_upload_mb: int = 25

    # Vector Store
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "threat_intel"

    # Embeddings
    ollama_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 768

    # Database (Phase 3)
    database_url: str = "postgresql://threatrag:threatrag@localhost:5432/threatrag"

    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retrieval_k: int = 6

    # Observability
    debug: bool = False
    log_format: str = "console"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    # External APIs
    tavily_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
