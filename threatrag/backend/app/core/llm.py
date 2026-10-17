"""Single construction point for the chat model: Kimchi primary, Gemini fallback.

Both providers speak the OpenAI chat protocol, so the fallback is a second `ChatOpenAI`
pointed at Gemini's OpenAI-compatible endpoint. The wrapper subclass (rather than
`.with_fallbacks()`) keeps `bind_tools()` working for LangGraph's ReAct agent: tool
kwargs flow through `_agenerate`/`_astream` and are replayed on the fallback.
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
from app.core.logging import get_logger

log = get_logger(__name__)
# A malformed request fails the same way on any provider; everything else is worth a retry elsewhere.
_NO_FALLBACK_STATUS = {400, 422}


def should_fallback(exc: Exception) -> bool:
    if isinstance(exc, openai.APIStatusError):
        return exc.status_code not in _NO_FALLBACK_STATUS
    # Mid-stream provider errors (e.g. Kimchi's 402 "credits exhausted") surface as bare APIError;
    # connection and timeout errors are subclasses of it.
    return isinstance(exc, openai.APIError)


class FallbackChatOpenAI(ChatOpenAI):  # type: ignore[override]  # pydantic __replace__ stub quirk
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
                raise
            log.warning("llm_fallback", primary=self.model_name, fallback=self.fallback.model_name, error=str(exc)[:200])
            return await self.fallback._agenerate(messages, stop, run_manager, **kwargs)

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
                raise
            log.warning("llm_fallback", primary=self.model_name, fallback=self.fallback.model_name, error=str(exc)[:200])
        async for chunk in self.fallback._astream(*args, **kwargs):
            yield chunk


def _client(s: Settings, *, model: str, key: str, base_url: str, streaming: bool, temperature: float) -> dict[str, Any]:
    return {
        "model": model,
        "api_key": SecretStr(key or "not-set"),
        "base_url": base_url,
        "temperature": temperature,
        "streaming": streaming,
        "timeout": s.llm_timeout_s,
        "max_completion_tokens": s.llm_max_tokens,
        "max_retries": 2,
    }


def fallback_enabled() -> bool:
    return bool(get_settings().gemini_api_key)


def get_llm(streaming: bool = False, temperature: float = 0.1) -> ChatOpenAI:
    s = get_settings()
    primary = _client(s, model=s.llm_model, key=s.kimchi_api_key, base_url=s.kimchi_base_url,
                      streaming=streaming, temperature=temperature)
    if not fallback_enabled():
        return ChatOpenAI(**primary)
    backup = ChatOpenAI(**_client(s, model=s.gemini_model, key=s.gemini_api_key, base_url=s.gemini_base_url,
                                  streaming=streaming, temperature=temperature))
    return FallbackChatOpenAI(**primary, fallback=backup)
