import time
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent.session import session_manager
from app.api.deps import get_store
from app.api.routes import chat, evaluate, ingest, investigate, query
from app.api.security import require_api_key
from app.core.config import get_settings
from app.core.llm import fallback_enabled
from app.db.connection import close_pool, get_pool, is_db_ready, open_pool
from app.core.logging import configure_logging, get_logger, logging_middleware
from app.models.schemas import HealthCheck, ReadinessCheck

log = get_logger(__name__)
_ready_cache: dict[str, Any] = {"data": None, "expires": 0}


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    store = get_store()
    await store.ensure_collection()
    if await open_pool():
        from app.scripts.migrate import run_migrations
        await run_migrations()
    session_manager.start()
    log.info("startup_complete", collection=store.collection, db=is_db_ready())
    yield
    session_manager.stop()
    await close_pool()
    log.info("shutdown")


app = FastAPI(
    title="ThreatRAG API",
    version="1.0.0",
    description=(
        "Cybersecurity RAG + agentic investigation API over MITRE ATT&CK, OWASP LLM Top 10, "
        "and live CVE data. Every endpoint below has a sample request/response body — expand "
        "an operation and click **Try it out** to execute it against this server."
    ),
    lifespan=lifespan,
    openapi_tags=[
        {"name": "ingest", "description": "Load MITRE ATT&CK / OWASP / custom PDF sources into the vector store"},
        {"name": "query", "description": "Ask questions against the RAG knowledge base"},
        {"name": "chat", "description": "Conversational ReAct agent with tool use (RAG + NVD CVE + web search)"},
        {"name": "investigate", "description": "Multi-agent Researcher → Critic → Reporter IOC investigations"},
        {"name": "evaluate", "description": "RAGAs-based quality scoring of RAG answers"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
    expose_headers=["X-Session-ID"],
)
app.middleware("http")(logging_middleware)

for _router in (ingest.router, query.router, chat.router, investigate.router, evaluate.router):
    app.include_router(_router, prefix="/api/v1", dependencies=[Depends(require_api_key)])


@app.get("/health", response_model=HealthCheck, tags=["health"], summary="Liveness check")
async def health() -> HealthCheck:
    return HealthCheck(status="ok")


@app.get(
    "/health/ready",
    response_model=ReadinessCheck,
    tags=["health"],
    summary="Readiness check",
    description="Verifies Qdrant, Ollama, and the LLM are reachable. Cached for 30s.",
)
async def health_ready() -> ReadinessCheck:
    now = time.time()
    if _ready_cache["data"] and now < _ready_cache["expires"]:
        return _ready_cache["data"]

    s = get_settings()
    checks: dict[str, str] = {}

    async with httpx.AsyncClient(timeout=3) as client:
        try:
            await client.get(f"{s.qdrant_url}/collections/{s.qdrant_collection}")
            checks["qdrant"] = "ok"
        except Exception as e:
            checks["qdrant"] = f"error: {e}"

        try:
            r = await client.get(f"{s.ollama_url}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
            checks["ollama"] = "ok" if any(s.embedding_model in m for m in models) else "model_not_pulled"
        except Exception as e:
            checks["ollama"] = f"error: {e}"

        try:
            r = await client.get(
                f"{s.kimchi_base_url}/models", headers={"Authorization": f"Bearer {s.kimchi_api_key}"}
            )
            checks["llm"] = "ok" if r.status_code == 200 else f"http_{r.status_code}"
        except Exception as e:
            checks["llm"] = f"error: {e}"

        if fallback_enabled():
            try:
                r = await client.get(
                    f"{s.gemini_base_url}/models", headers={"Authorization": f"Bearer {s.gemini_api_key}"}
                )
                checks["llm_fallback"] = "ok" if r.status_code == 200 else f"http_{r.status_code}"
            except Exception as e:
                checks["llm_fallback"] = f"error: {e}"

    checks["postgres"] = "error: not connected"
    if is_db_ready():
        try:
            async with get_pool().connection() as conn:
                await conn.execute("SELECT 1")
            checks["postgres"] = "ok"
        except Exception as e:
            checks["postgres"] = f"error: {e}"

    status = "ready" if all(v == "ok" for v in checks.values()) else "degraded"
    result = ReadinessCheck(status=status, checks=checks)
    _ready_cache.update({"data": result, "expires": now + 30})
    return result
