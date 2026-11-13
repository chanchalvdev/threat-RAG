"""Shared key-value state: chat history, ingest jobs and rate-limit counters.

In-memory by default (single process, lost on restart). Set REDIS_URL and the same calls are
backed by Redis, so state survives restarts and is shared between API workers.
"""
import time
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)
PREFIX = "threatrag:"


class StateStore(ABC):
    @abstractmethod
    async def get(self, key: str) -> str | None: ...

    @abstractmethod
    async def set(self, key: str, value: str, ttl_s: int | None = None) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def incr(self, key: str, ttl_s: int) -> int:
        """Increment a counter that expires `ttl_s` after its first increment."""

    async def close(self) -> None:
        return None


class MemoryState(StateStore):
    def __init__(self) -> None:
        self._data: dict[str, tuple[str, float | None]] = {}

    def _live(self, key: str) -> str | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        value, expires = entry
        if expires is not None and expires <= time.monotonic():
            del self._data[key]
            return None
        return value

    async def get(self, key: str) -> str | None:
        return self._live(key)

    async def set(self, key: str, value: str, ttl_s: int | None = None) -> None:
        self._data[key] = (value, time.monotonic() + ttl_s if ttl_s else None)

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def incr(self, key: str, ttl_s: int) -> int:
        current = self._live(key)
        expires = self._data[key][1] if current is not None else time.monotonic() + ttl_s
        count = int(current or 0) + 1
        self._data[key] = (str(count), expires)
        return count

    def clear(self) -> None:
        self._data.clear()


class RedisState(StateStore):
    def __init__(self, url: str) -> None:
        import redis.asyncio as redis

        self._client: Any = redis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> str | None:
        return await self._client.get(PREFIX + key)

    async def set(self, key: str, value: str, ttl_s: int | None = None) -> None:
        await self._client.set(PREFIX + key, value, ex=ttl_s)

    async def delete(self, key: str) -> None:
        await self._client.delete(PREFIX + key)

    async def incr(self, key: str, ttl_s: int) -> int:
        count = int(await self._client.incr(PREFIX + key))
        if count == 1:
            await self._client.expire(PREFIX + key, ttl_s)
        return count

    async def close(self) -> None:
        await self._client.aclose()


@lru_cache
def get_state() -> StateStore:
    url = get_settings().redis_url
    if url:
        log.info("state_backend", backend="redis")
        return RedisState(url)
    log.info("state_backend", backend="memory")
    return MemoryState()
