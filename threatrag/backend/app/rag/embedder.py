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


class GeminiEmbedder(BaseEmbedder):
    """Hosted embedder (Gemini free tier) for deployments that cannot run Ollama."""

    _BASE = "https://generativelanguage.googleapis.com/v1beta"
    _MAX_BATCH = 100

    def __init__(self, api_key: str, model: str, dim: int):
        self._key = api_key
        self._model = model if model.startswith("models/") else f"models/{model}"
        self._dim = dim

    async def _call(self, texts: list[str], task_type: str) -> list[list[float]]:
        requests = [
            {"model": self._model, "content": {"parts": [{"text": t}]},
             "taskType": task_type, "outputDimensionality": self._dim}
            for t in texts
        ]
        async with httpx.AsyncClient(timeout=60) as client:
            for attempt in range(4):
                r = await client.post(
                    f"{self._BASE}/{self._model}:batchEmbedContents",
                    headers={"x-goog-api-key": self._key},
                    json={"requests": requests},
                )
                if r.status_code == 429 and attempt < 3:
                    await asyncio.sleep(2 ** attempt * 5)  # free-tier rate limit
                    continue
                r.raise_for_status()
                return [e["values"] for e in r.json()["embeddings"]]
        raise RuntimeError("unreachable")

    async def embed(self, text: str) -> list[float]:
        return (await self._call([text], "RETRIEVAL_QUERY"))[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), self._MAX_BATCH):
            out += await self._call(texts[i : i + self._MAX_BATCH], "RETRIEVAL_DOCUMENT")
        return out


def embedding_tag(settings: Settings | None = None) -> str:
    """Identifies the vector space; vectors from different tags must never share a collection."""
    s = settings or get_settings()
    return f"{s.embedding_provider}:{s.embedding_model}"


def get_embedder(settings: Settings | None = None) -> BaseEmbedder:
    s = settings or get_settings()
    if s.embedding_provider == "gemini":
        return GeminiEmbedder(s.gemini_api_key, s.embedding_model, s.embedding_dim)
    return OllamaEmbedder(base_url=s.ollama_url, model=s.embedding_model)
