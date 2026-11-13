"""Integration tests run against real Qdrant, Redis and Postgres (docker compose).

No model server is needed: embeddings come from a deterministic fake, so what is tested is the
storage and retrieval machinery, not embedding quality (the offline eval covers that).
Each service's tests skip when that service is not reachable.
"""
import hashlib
import os
import random
import socket
from urllib.parse import urlparse

import pytest

from app.core.config import get_settings
from app.rag.embedder import BaseEmbedder

REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://127.0.0.1:6380/15")
DIM = 32


def _reachable(url: str, default_port: int) -> bool:
    parsed = urlparse(url)
    try:
        with socket.create_connection((parsed.hostname or "localhost", parsed.port or default_port), timeout=1):
            return True
    except OSError:
        return False


def require(url: str, default_port: int, name: str) -> None:
    if not _reachable(url, default_port):
        pytest.skip(f"{name} is not reachable at {url}")


class FakeEmbedder(BaseEmbedder):
    """Same text -> same unit vector. Unrelated texts get unrelated vectors."""

    async def embed(self, text: str) -> list[float]:
        rng = random.Random(hashlib.sha256(text.encode()).digest())
        vector = [rng.gauss(0, 1) for _ in range(DIM)]
        norm = sum(v * v for v in vector) ** 0.5
        return [v / norm for v in vector]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]


@pytest.fixture
def settings():
    return get_settings()
