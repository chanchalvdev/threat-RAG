"""Shared indexing path (embed, build points, upsert) and custom PDF ingestion."""
import uuid
from pathlib import Path
from typing import Any

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel
from qdrant_client.models import PointStruct

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.embedder import BaseEmbedder, embedding_tag
from app.rag.sparse import encode_document
from app.rag.store import DENSE, SPARSE, QdrantStore

log = get_logger(__name__)
BATCH_SIZE = 100


class Chunk(BaseModel):
    key: str                 # stable identity: the same key always overwrites the same point
    text: str
    payload: dict[str, Any]  # source, doc_type and any source-specific fields


def point_id(key: str) -> str:
    """Deterministic ID so re-ingesting the same chunk overwrites instead of duplicating."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def splitter() -> RecursiveCharacterTextSplitter:
    s = get_settings()
    return RecursiveCharacterTextSplitter(
        chunk_size=s.chunk_size, chunk_overlap=s.chunk_overlap, separators=["\n\n", "\n", ". ", " "],
    )


async def index_chunks(chunks: list[Chunk], store: QdrantStore, embedder: BaseEmbedder) -> int:
    """Embed and upsert in batches: one dense and one lexical vector per chunk."""
    await store.assert_embedding(embedding_tag())
    tag = embedding_tag()
    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start : start + BATCH_SIZE]
        vectors = await embedder.embed_batch([c.text for c in batch])
        points = [
            PointStruct(
                id=point_id(c.key),
                vector={DENSE: vector, SPARSE: encode_document(c.text)},
                payload={**c.payload, "text": c.text, "embedding_model": tag, "chunk_index": start + offset},
            )
            for offset, (c, vector) in enumerate(zip(batch, vectors))
        ]
        await store.upsert(points)
        log.info("batch_upserted", count=start + len(batch), total=len(chunks))
    return len(chunks)


async def ingest_pdf(path: str, doc_type: str, store: QdrantStore, embedder: BaseEmbedder) -> int:
    name = Path(path).name
    pieces = splitter().split_documents(PyPDFLoader(path).load())
    chunks = [
        Chunk(
            key=f"{name}:{doc_type}:{idx}",
            text=piece.page_content,
            payload={"source": name, "doc_type": doc_type, "page": piece.metadata.get("page", 0)},
        )
        for idx, piece in enumerate(pieces)
    ]
    count = await index_chunks(chunks, store, embedder)
    log.info("ingestion_complete", doc_type=doc_type, total_chunks=count)
    return count
