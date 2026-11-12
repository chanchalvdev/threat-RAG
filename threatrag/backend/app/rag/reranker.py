"""Optional cross-encoder reranker. Scores (query, passage) pairs jointly, off the event loop."""
import asyncio
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)


class Reranker(ABC):
    @abstractmethod
    async def score(self, query: str, texts: list[str]) -> list[float]: ...


class CrossEncoderReranker(Reranker):
    """ONNX cross-encoder via fastembed (CPU, no torch). The model downloads on first use."""

    def __init__(self, model_name: str):
        self._model_name = model_name
        self._model: Any = None

    def _score_sync(self, query: str, texts: list[str]) -> list[float]:
        if self._model is None:
            from fastembed.rerank.cross_encoder import TextCrossEncoder

            self._model = TextCrossEncoder(model_name=self._model_name)
            log.info("reranker_loaded", model=self._model_name)
        return [float(s) for s in self._model.rerank(query, texts)]

    async def score(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        return await asyncio.to_thread(self._score_sync, query, texts)


@lru_cache
def get_reranker() -> Reranker | None:
    s = get_settings()
    return CrossEncoderReranker(s.reranker_model) if s.reranker == "cross_encoder" else None
