"""One-shot script to ingest all default data sources."""
import asyncio
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.rag.embedder import get_embedder
from app.rag.ingestion import ingest_mitre_attack, ingest_owasp_llm
from app.rag.store import QdrantStore

log = get_logger(__name__)


async def main() -> None:
    configure_logging()
    s = get_settings()
    store = QdrantStore(url=s.qdrant_url, collection=s.qdrant_collection, vector_size=s.embedding_dim)
    await store.ensure_collection()
    embedder = get_embedder(s)

    log.info("ingesting_mitre")
    mitre_path = str(Path("data/sources/mitre_attack.json"))
    count = await ingest_mitre_attack(mitre_path, store, embedder)
    log.info("mitre_done", chunks=count)

    log.info("ingesting_owasp")
    count = await ingest_owasp_llm(store, embedder)
    log.info("owasp_done", chunks=count)


if __name__ == "__main__":
    asyncio.run(main())
