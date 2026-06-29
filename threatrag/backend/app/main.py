import time
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_store
from app.api.routes import chat, evaluate, ingest, investigate, query
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger, logging_middleware
from app.models.schemas import HealthCheck, ReadinessCheck

log = get_logger(__name__)
_ready_cache: dict[str, Any] = {"data": None, "expires": 0}


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    store = get_store()
    await store.ensure_collection()
    log.info("startup_complete", collection=store.collection)
    yield
    log.info("shutdown")


app = FastAPI(title="ThreatRAG API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(logging_middleware)

app.include_router(ingest.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(investigate.router, prefix="/api/v1")
app.include_router(evaluate.router, prefix="/api/v1")


@app.get("/health", response_model=HealthCheck)
async def health() -> HealthCheck:
    return HealthCheck(status="ok")


@app.get("/health/ready", response_model=ReadinessCheck)
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

    checks["llm"] = "ok"

    status = "ready" if all(v == "ok" for v in checks.values()) else "degraded"
    result = ReadinessCheck(status=status, checks=checks)
    _ready_cache.update({"data": result, "expires": now + 30})
    return result
