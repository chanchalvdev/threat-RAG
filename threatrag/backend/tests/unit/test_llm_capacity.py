"""G47: provider capacity failures become 503 + Retry-After, not a bare 500 (no network)."""
from unittest.mock import AsyncMock, patch

import httpx
import openai
import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import HumanMessage

from app.api import deps
from app.core import llm as llm_mod
from app.core.llm_errors import ModelUnavailable, is_capacity, retry_after
from app.main import app

GEMINI_429 = ("Error code: 429 - [{'error': {'code': 429, 'message': 'You exceeded your current quota ... "
              "Please retry in 56.01395241s.', 'details': [{'retryDelay': '56s'}]}}]")


def _status(code: int, text: str = "boom") -> openai.APIStatusError:
    return openai.APIStatusError(text, response=httpx.Response(code, request=httpx.Request("POST", "http://x")), body=None)


def _bare(text: str) -> openai.APIError:
    return openai.APIError(text, request=httpx.Request("POST", "http://x"), body=None)


class _Fallback(llm_mod.ChatOpenAI):  # type: ignore[misc]
    """Distinct class so a patch on ChatOpenAI (the primary) does not reach the fallback."""

    error: object = None

    async def _agenerate(self, *args, **kwargs):  # type: ignore[override]
        raise self.error  # type: ignore[misc]

    async def _astream(self, *args, **kwargs):  # type: ignore[override]
        raise self.error  # type: ignore[misc]
        yield  # pragma: no cover


def _model(fallback_error: Exception | None, streaming: bool = False) -> llm_mod.FallbackChatOpenAI:
    backup = _Fallback(model="kimi", api_key="x", base_url="http://b", error=fallback_error) if fallback_error else None
    return llm_mod.FallbackChatOpenAI(model="gemini", api_key="x", base_url="http://a", streaming=streaming, fallback=backup)


def test_capacity_and_retry_hint():
    assert is_capacity(_status(429)) and is_capacity(_status(402)) and is_capacity(_bare("provider has exhausted its credits"))
    assert not is_capacity(_status(500)) and not is_capacity(_status(401)) and not is_capacity(ValueError("x"))
    assert retry_after(_status(429, GEMINI_429)) == 57 and retry_after(_status(429)) == 60


@pytest.mark.parametrize("streaming", [False, True])
async def test_rate_limited_primary_and_broke_fallback_raise_model_unavailable(streaming):
    model = _model(_bare("the provider has exhausted its credits"), streaming=streaming)
    target = "_astream" if streaming else "_agenerate"
    with patch.object(llm_mod.ChatOpenAI, target, side_effect=_status(429, GEMINI_429)), pytest.raises(ModelUnavailable) as err:
        if streaming:
            [c async for c in model.astream([HumanMessage(content="hi")])]
        else:
            await model.ainvoke([HumanMessage(content="hi")])
    assert err.value.retry_after_s == 57


async def test_other_failures_keep_their_own_error():
    with patch.object(llm_mod.ChatOpenAI, "_agenerate", side_effect=_status(429, GEMINI_429)), pytest.raises(openai.APIStatusError):
        await _model(_status(500)).ainvoke([HumanMessage(content="hi")])  # fallback broke for another reason
    with patch.object(llm_mod.ChatOpenAI, "_agenerate", side_effect=_status(400)), pytest.raises(openai.APIStatusError):
        await _model(None).ainvoke([HumanMessage(content="hi")])
    with patch.object(llm_mod.ChatOpenAI, "_agenerate", side_effect=_status(429, GEMINI_429)), pytest.raises(ModelUnavailable):
        await _model(None).ainvoke([HumanMessage(content="hi")])  # single provider, rate-limited


async def test_api_answers_503_with_retry_after():
    chain = AsyncMock()
    chain.query.side_effect = ModelUnavailable(57)
    app.dependency_overrides[deps.get_chain] = lambda: chain
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            r = await client.post("/api/v1/query", json={"question": "What is T1110?"})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503 and r.headers["retry-after"] == "57" and "try again in 57 s" in r.json()["detail"]
