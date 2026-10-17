import json
import uuid
from pathlib import Path

import httpx
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client.models import PointStruct

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.embedder import BaseEmbedder
from app.rag.store import QdrantStore

log = get_logger(__name__)
MITRE_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
OWASP_LLM_URL = "https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-2023-v1_1.pdf"
BATCH_SIZE = 100


def _point_id(key: str) -> str:
    """Deterministic ID so re-ingesting the same chunk overwrites instead of duplicating."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def _splitter() -> RecursiveCharacterTextSplitter:
    s = get_settings()
    return RecursiveCharacterTextSplitter(
        chunk_size=s.chunk_size,
        chunk_overlap=s.chunk_overlap,
        separators=["\n\n", "\n", ". ", " "],
    )


async def _upsert_in_batches(
    points: list[PointStruct], store: QdrantStore
) -> None:
    for i in range(0, len(points), BATCH_SIZE):
        await store.upsert(points[i : i + BATCH_SIZE])
        log.info("batch_upserted", count=min(i + BATCH_SIZE, len(points)), total=len(points))


async def ingest_pdf(
    path: str, doc_type: str, store: QdrantStore, embedder: BaseEmbedder
) -> int:
    loader = PyPDFLoader(path)
    pages = loader.load()
    chunks = _splitter().split_documents(pages)
    points: list[PointStruct] = []

    vectors = await embedder.embed_batch([c.page_content for c in chunks])
    for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
        points.append(
            PointStruct(
                id=_point_id(f"{Path(path).name}:{doc_type}:{idx}"),
                vector=vector,
                payload={
                    "text": chunk.page_content,
                    "source": Path(path).name,
                    "doc_type": doc_type,
                    "page": chunk.metadata.get("page", 0),
                    "chunk_index": idx,
                },
            )
        )
        if idx % 50 == 0:
            log.info("ingestion_progress", doc_type=doc_type, chunk=idx, total=len(chunks))

    await _upsert_in_batches(points, store)
    log.info("ingestion_complete", doc_type=doc_type, total_chunks=len(points))
    return len(points)


async def ingest_mitre_attack(
    path: str, store: QdrantStore, embedder: BaseEmbedder
) -> int:
    source = Path(path)
    if not source.exists():
        log.info("downloading_mitre", url=MITRE_URL)
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(MITRE_URL)
            r.raise_for_status()
            source.write_bytes(r.content)

    stix = json.loads(source.read_text())
    techniques = [o for o in stix.get("objects", []) if o.get("type") == "attack-pattern"]
    points: list[PointStruct] = []

    for obj in techniques:
        ext_refs = obj.get("external_references", [])
        ext_id = next((r["external_id"] for r in ext_refs if r.get("source_name") == "mitre-attack"), "")
        tactic = ", ".join(p.get("phase_name", "") for p in obj.get("kill_chain_phases", []))
        platforms = ", ".join(obj.get("x_mitre_platforms", []))
        desc = (obj.get("description") or "")[:1000]

        text = (
            f"Technique: {obj.get('name', '')}\n"
            f"ID: {ext_id}\n"
            f"Tactic: {tactic}\n"
            f"Platforms: {platforms}\n"
            f"Description: {desc}"
        )
        points.append(
            PointStruct(
                id=_point_id(f"mitre:{obj.get('id', ext_id)}"),
                vector=[],
                payload={
                    "text": text,
                    "source": source.name,
                    "doc_type": "mitre_attack",
                    "technique_id": ext_id,
                    "name": obj.get("name", ""),
                    "tactic": tactic,
                    "platforms": platforms,
                    "chunk_index": len(points),
                },
            )
        )

    vectors = await embedder.embed_batch([str((p.payload or {})["text"]) for p in points])
    for point, vector in zip(points, vectors):
        point.vector = vector
    await _upsert_in_batches(points, store)
    log.info("mitre_ingested", total=len(points))
    return len(points)


async def ingest_owasp_llm(store: QdrantStore, embedder: BaseEmbedder) -> int:
    dest = Path("data/sources/owasp_llm_top10.pdf")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        log.info("downloading_owasp", url=OWASP_LLM_URL)
        # Stream to disk to handle large PDF (>90MB) within timeout
        timeout = httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            async with client.stream("GET", OWASP_LLM_URL) as r:
                r.raise_for_status()
                with dest.open("wb") as f:
                    async for chunk in r.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
    return await ingest_pdf(str(dest), "owasp_llm", store, embedder)
