import pytest
from unittest.mock import AsyncMock, MagicMock

from app.rag.store import QdrantStore
from app.rag.embedder import BaseEmbedder


@pytest.fixture
def mock_store() -> QdrantStore:
    store = MagicMock(spec=QdrantStore)
    store.upsert = AsyncMock()
    store.search = AsyncMock(return_value=[])
    store.ensure_collection = AsyncMock()
    return store


@pytest.fixture
def mock_embedder() -> BaseEmbedder:
    embedder = MagicMock(spec=BaseEmbedder)
    embedder.embed = AsyncMock(return_value=[0.1] * 768)
    embedder.embed_batch = AsyncMock(return_value=[[0.1] * 768])
    return embedder
