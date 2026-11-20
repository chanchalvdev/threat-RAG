"""Single construction point for the chat model: providers tried in `LLM_ORDER` (llm_providers.py).

Every provider speaks the OpenAI chat protocol, so each fallback is another `ChatOpenAI` pointed at
the next provider's endpoint, chained in order. With one key, that provider runs alone. The wrapper
subclass (rather than `.with_fallbacks()`) keeps `bind_tools()` working for LangGraph's ReAct agent:
tool kwargs flow through `_agenerate`/`_astream` and are replayed on the fallback.
"""
from collections.abc import AsyncIterator
from typing import Any

import openai
from langchain_core.callbacks import AsyncCallbackManagerForLLMRun
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.core.config import Settings, get_settings
from app.core.gemini_compat import GeminiCompatChatOpenAI
from app.core.llm_errors import unavailable
from app.core.llm_providers import Provider, by_name, providers
from app.core.logging import get_logger
from app.core.tracing import llm_callbacks

log = get_logger(__name__)
# A malformed request fails the same way on any provider; everything else is worth a retry elsewhere.
_NO_FALLBACK_STATUS = {400, 422}


def should_fallback(exc: Exception) -> bool:
    if isinstance(exc, openai.APIStatusError):
        return exc.status_code not in _NO_FALLBACK_STATUS
    # Mid-stream provider errors (e.g. Kimchi's 402 "credits exhausted") surface as bare APIError;
    # connection and timeout errors are subclasses of it.
    return isinstance(exc, openai.APIError)


class FallbackChatOpenAI(GeminiCompatChatOpenAI):  # type: ignore[override]  # pydantic __replace__ stub quirk
    """ChatOpenAI that retries a failed call (or a stream that produced nothing) on `fallback`."""

    fallback: ChatOpenAI | None = None

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        try:
            return await super()._agenerate(messages, stop, run_manager, **kwargs)
        except Exception as exc:
            if self.fallback is None or not should_fallback(exc):
                raise unavailable(exc) or exc
            log.warning("llm_fallback", primary=self.model_name, fallback=self.fallback.model_name, error=str(exc)[:200])
            primary = exc
        try:
            return await self.fallback._agenerate(messages, stop, run_manager, **kwargs)
        except Exception as exc:
            raise unavailable(primary, exc) or exc

    async def _astream(self, *args: Any, **kwargs: Any) -> AsyncIterator[ChatGenerationChunk]:
        started = False
        try:
            async for chunk in super()._astream(*args, **kwargs):
                started = True
                yield chunk
            return
        except Exception as exc:
            # Once tokens reached the client a mid-stream switch would duplicate output.
            if started or self.fallback is None or not should_fallback(exc):
                raise (None if started else unavailable(exc)) or exc
            log.warning("llm_fallback", primary=self.model_name, fallback=self.fallback.model_name, error=str(exc)[:200])
            primary = exc
        try:
            async for chunk in self.fallback._astream(*args, **kwargs):
                yield chunk
        except Exception as exc:
            raise unavailable(primary, exc) or exc


def _client(s: Settings, p: Provider, *, streaming: bool, temperature: float, last: bool = True) -> dict[str, Any]:
    return {
        "model": p.model,
        "api_key": SecretStr(p.key or "not-set"),
        "base_url": p.base_url,
        "temperature": temperature,
        "streaming": streaming,
        "timeout": s.llm_timeout_s,
        "max_completion_tokens": s.llm_max_tokens,
        # A provider with a fallback behind it fails over at once instead of sitting out a 429 backoff.
        "max_retries": 2 if last else 0,
        "stream_usage": True,
        "callbacks": llm_callbacks(),
        "google_compat": "googleapis.com" in p.base_url,
        # OpenRouter attributes traffic by these optional headers; other providers ignore them.
        "default_headers": {"X-Title": "ThreatRAG"} if "openrouter.ai" in p.base_url else None,
    }


def fallback_enabled() -> bool:
    return len(providers(get_settings())) > 1


def _chain(s: Settings, configured: list[Provider], *, streaming: bool, temperature: float) -> FallbackChatOpenAI:
    """Primary with each later provider as the previous one's fallback."""
    model: FallbackChatOpenAI | None = None
    for p in reversed(configured):
        kw = _client(s, p, streaming=streaming, temperature=temperature, last=model is None)
        model = FallbackChatOpenAI(**kw, fallback=model)
    assert model is not None
    return model


def get_llm(streaming: bool = False, temperature: float = 0.1) -> ChatOpenAI:
    s = get_settings()
    # No keys: build the first provider anyway so the call fails with the provider's own error.
    first = by_name(s, (s.llm_order.split(",") or ["gemini"])[0]) or by_name(s, "gemini")
    configured = providers(s) or [first]  # type: ignore[list-item]
    return _chain(s, configured, streaming=streaming, temperature=temperature)


def get_judge_llm() -> ChatOpenAI:
    """Evaluation judge. Uses JUDGE_MODEL when set; otherwise the generator model at temperature 0."""
    s = get_settings()
    if not s.judge_model:
        return get_llm(temperature=0.0)
    configured = providers(s)
    named = by_name(s, s.judge_provider) if s.judge_provider else None
    base = named or (configured[0] if configured else Provider("", "", s.gemini_base_url))
    judge = Provider(s.judge_model, s.judge_api_key or base.key, s.judge_base_url or base.base_url)
    return FallbackChatOpenAI(**_client(s, judge, streaming=False, temperature=0.0))
