"""Callbacks attached to every chat model: in-process usage telemetry, plus Langfuse when configured."""
from functools import lru_cache
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.telemetry import UsageCallback

log = get_logger(__name__)


def _langfuse_handler() -> Any | None:
    s = get_settings()
    if not (s.langfuse_public_key and s.langfuse_secret_key):
        return None
    try:
        from langfuse import Langfuse
        from langfuse.langchain import CallbackHandler

        Langfuse(public_key=s.langfuse_public_key, secret_key=s.langfuse_secret_key, host=s.langfuse_host)
        log.info("langfuse_tracing_enabled", host=s.langfuse_host)
        return CallbackHandler(public_key=s.langfuse_public_key)
    except Exception as exc:  # tracing is optional; never block the app on it
        log.warning("langfuse_unavailable", error=str(exc)[:200])
        return None


@lru_cache
def llm_callbacks() -> list[Any]:
    handler = _langfuse_handler()
    return [UsageCallback(), *([handler] if handler is not None else [])]
