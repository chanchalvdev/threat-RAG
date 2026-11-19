from functools import lru_cache

from app.core.config import get_settings
from app.rag.chain import ThreatRAGChain
from app.rag.embedder import get_embedder
from app.rag.reranker import get_reranker
from app.rag.retriever import Retriever
from app.rag.store import QdrantStore


@lru_cache
def get_store() -> QdrantStore:
    s = get_settings()
    return QdrantStore(
        url=s.qdrant_url,
        collection=s.qdrant_collection,
        vector_size=s.embedding_dim,
        api_key=s.qdrant_api_key,
    )


@lru_cache
def get_retriever() -> Retriever:
    return Retriever(store=get_store(), embedder=get_embedder(), reranker=get_reranker())


@lru_cache
def get_chain() -> ThreatRAGChain:
    return ThreatRAGChain(retriever=get_retriever())
