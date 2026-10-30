"""Readiness probe: real dependency checks, cached so polling stays cheap."""
import time
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.db.connection import get_pool, is_db_ready
from app.models.schemas import ReadinessCheck

CACHE_TTL_S = 60
_cache: dict[str, Any] = {"data": None, "expires": 0.0}


def _llm_targets(s: Settings) -> list[tuple[str, str, str, str]]:
    """(check name, base URL, API key, model) for each configured provider."""
    if not s.kimchi_api_key:
        return [("llm", s.gemini_base_url, s.gemini_api_key, s.gemini_model)] if s.gemini_api_key else []
    targets = [("llm", s.kimchi_base_url, s.kimchi_api_key, s.llm_model)]
    if s.gemini_api_key:
        targets.append(("llm_fallback", s.gemini_base_url, s.gemini_api_key, s.gemini_model))
    return targets


async def _probe_llm(base: str, key: str, model: str) -> str:
    """1-token completion: `GET /models` answers 200 even when the account has no credits (G15)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
            )
        return "ok" if r.status_code == 200 else f"http_{r.status_code}"
    except Exception as e:
        return f"error: {e}"


async def _probe_qdrant(s: Settings) -> str:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(
                f"{s.qdrant_url}/collections/{s.qdrant_collection}",
                headers={"api-key": s.qdrant_api_key} if s.qdrant_api_key else {},
            )
        r.raise_for_status()
        return "ok"
    except Exception as e:
        return f"error: {e}"


async def _probe_ollama(s: Settings) -> str:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{s.ollama_url}/api/tags")
        models = [m["name"] for m in r.json().get("models", [])]
        return "ok" if any(s.embedding_model in m for m in models) else "model_not_pulled"
    except Exception as e:
        return f"error: {e}"


async def _probe_postgres() -> str:
    if not is_db_ready():
        return "error: not connected"
    try:
        async with get_pool().connection() as conn:
            await conn.execute("SELECT 1")
        return "ok"
    except Exception as e:
        return f"error: {e}"


async def check_readiness() -> ReadinessCheck:
    now = time.time()
    if _cache["data"] and now < _cache["expires"]:
        return _cache["data"]

    s = get_settings()
    checks = {"qdrant": await _probe_qdrant(s)}
    if s.embedding_provider == "ollama":
        checks["ollama"] = await _probe_ollama(s)
    for name, base, key, model in _llm_targets(s):
        checks[name] = await _probe_llm(base, key, model)
    checks["postgres"] = await _probe_postgres()

    status = "ready" if all(v == "ok" for v in checks.values()) else "degraded"
    result = ReadinessCheck(status=status, checks=checks)
    _cache.update({"data": result, "expires": now + CACHE_TTL_S})
    return result
