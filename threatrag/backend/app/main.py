from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_store
from app.api.routes import chat, evaluate, ingest, investigate, metrics, query
from app.api.identity import rate_limit
from app.api.security import require_api_key
from app.core.config import get_settings
from app.core.state import get_state
from app.db.connection import close_pool, is_db_ready, open_pool
from app.core.logging import configure_logging, get_logger, logging_middleware
from app.models.schemas import HealthCheck, ReadinessCheck
from app.rag.embedder import embedding_tag
from app.services.readiness import check_readiness

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    store = get_store()
    await store.ensure_collection()
    await store.assert_embedding(embedding_tag())
    if await open_pool():
        from app.scripts.migrate import run_migrations
        await run_migrations()
    log.info("startup_complete", collection=store.collection, db=is_db_ready())
    yield
    await get_state().close()
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
        {"name": "evaluate", "description": "LLM-judge quality scoring of RAG answers"},
        {"name": "metrics", "description": "Runtime latency, token and guard telemetry"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
    expose_headers=["X-Session-ID"],
)
app.middleware("http")(logging_middleware)

for _router in (ingest.router, query.router, chat.router, investigate.router, evaluate.router, metrics.router):
    app.include_router(_router, prefix="/api/v1", dependencies=[Depends(require_api_key), Depends(rate_limit)])


@app.get("/health", response_model=HealthCheck, tags=["health"], summary="Liveness check")
async def health() -> HealthCheck:
    return HealthCheck(status="ok")


@app.get(
    "/health/ready",
    response_model=ReadinessCheck,
    tags=["health"],
    summary="Readiness check",
    description="Verifies Qdrant, Ollama, and the LLM are reachable, and that the LLM can complete. Cached for 60s.",
)
async def health_ready() -> ReadinessCheck:
    return await check_readiness()
