import pytest
from unittest.mock import AsyncMock, MagicMock

from app.rag.store import QdrantStore
from app.rag.embedder import BaseEmbedder


@pytest.fixture
def mock_store() -> QdrantStore:
    store = MagicMock(spec=QdrantStore)
    store.upsert = AsyncMock()
    store.search = AsyncMock(return_value=[])
    store.candidates = AsyncMock(return_value=([], []))
    store.by_ids = AsyncMock(return_value=[])
    store.dense_scores = AsyncMock(return_value={})
    store.assert_embedding = AsyncMock()
    store.ensure_collection = AsyncMock()
    return store


@pytest.fixture
def mock_embedder() -> BaseEmbedder:
    embedder = MagicMock(spec=BaseEmbedder)
    embedder.embed = AsyncMock(return_value=[0.1] * 768)
    embedder.embed_batch = AsyncMock(side_effect=lambda texts: [[0.1] * 768 for _ in texts])
    return embedder


def make_point(pid: str, text: str = "text", score: float = 0.9, **payload) -> MagicMock:
    """A Qdrant point as the store returns it."""
    return MagicMock(id=pid, score=score, payload={"text": text, "source": "test.json", "doc_type": "mitre_attack", **payload})


@pytest.fixture
def retriever(mock_store, mock_embedder):
    from app.rag.retriever import Retriever

    return Retriever(store=mock_store, embedder=mock_embedder)
