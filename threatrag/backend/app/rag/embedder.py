import asyncio
from abc import ABC, abstractmethod

import httpx

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

log = get_logger(__name__)
_BATCH_SEMAPHORE = asyncio.Semaphore(5)


class BaseEmbedder(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class OllamaEmbedder(BaseEmbedder):
    def __init__(self, base_url: str, model: str):
        self._url = f"{base_url}/api/embeddings"
        self._model = model

    async def embed(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(self._url, json={"model": self._model, "prompt": text})
            r.raise_for_status()
            return r.json()["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        async def _one(t: str) -> list[float]:
            async with _BATCH_SEMAPHORE:
                return await self.embed(t)

        return list(await asyncio.gather(*[_one(t) for t in texts]))


class NomicEmbedder(BaseEmbedder):
    """Production embedder using Nomic Atlas API (OpenAI-compatible)."""

    def __init__(self, api_key: str, model: str = "nomic-embed-text-v1.5"):
        self._api_key = api_key
        self._model = model
        self._url = "https://api-atlas.nomic.ai/v1/embedding/text"

    async def embed(self, text: str) -> list[float]:
        result = await self.embed_batch([text])
        return result[0]

    async def embed_batch(
        self, texts: list[str], task_type: str = "search_document"
    ) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                self._url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": self._model, "texts": texts, "task_type": task_type},
            )
            r.raise_for_status()
            return r.json()["embeddings"]


def get_embedder(settings: Settings | None = None) -> BaseEmbedder:
    s = settings or get_settings()
    return OllamaEmbedder(base_url=s.ollama_url, model=s.embedding_model)
