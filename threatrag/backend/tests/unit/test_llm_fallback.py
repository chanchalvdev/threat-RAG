"""Unit tests for the Gemini → Kimchi LLM fallback (no network)."""
from unittest.mock import AsyncMock, patch

import httpx
import openai
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.messages import AIMessageChunk
from langchain_core.tools import tool

from app.core import llm as llm_mod
from app.core.config import Settings


def _status_error(code: int) -> openai.APIStatusError:
    req = httpx.Request("POST", "http://x")
    return openai.APIStatusError("boom", response=httpx.Response(code, request=req), body=None)


def _settings(gemini_key: str = "g-key") -> Settings:
    return Settings(_env_file=None, kimchi_api_key="k", gemini_api_key=gemini_key)


def _result(text: str) -> ChatResult:
    return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])


@pytest.mark.parametrize("code,expected", [(402, True), (429, True), (500, True), (401, True), (400, False), (422, False)])
def test_should_fallback_by_status(code, expected):
    assert llm_mod.should_fallback(_status_error(code)) is expected


def test_should_fallback_on_bare_stream_api_error():
    err = openai.APIError("provider exhausted its credits", request=httpx.Request("POST", "http://x"), body=None)
    assert llm_mod.should_fallback(err)


def test_should_fallback_on_connection_error_but_not_value_error():
    assert llm_mod.should_fallback(openai.APIConnectionError(request=httpx.Request("POST", "http://x")))
    assert not llm_mod.should_fallback(ValueError("bug"))


def test_single_key_runs_that_provider_alone():
    only_gemini = Settings(_env_file=None, kimchi_api_key="", gemini_api_key="g")
    for settings, model in ((_settings(""), "kimi-k2.6"), (only_gemini, "gemini-3.5-flash-lite")):
        with patch("app.core.llm.get_settings", return_value=settings):
            client = llm_mod.get_llm()
            assert type(client).__name__ == "ChatOpenAI" and client.model_name == model
            assert not llm_mod.fallback_enabled()


def test_both_keys_make_gemini_primary_and_kimchi_fallback():
    with patch("app.core.llm.get_settings", return_value=_settings()):
        model = llm_mod.get_llm()
    assert isinstance(model, llm_mod.FallbackChatOpenAI)
    assert model.model_name == "gemini-3.5-flash-lite"
    assert model.fallback is not None and model.fallback.model_name == "kimi-k2.6"


class _Backup(llm_mod.ChatOpenAI):  # type: ignore[misc]
    """Distinct class so patches on ChatOpenAI (the primary's super()) never touch the fallback."""

    calls: list[dict] = []
    stream_text: str = "gem"

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):  # type: ignore[override]
        self.calls.append(kwargs)
        return _result("from gemini")

    async def _astream(self, *args, **kwargs):  # type: ignore[override]
        yield ChatGenerationChunk(message=AIMessageChunk(content=self.stream_text))


def _model(streaming: bool = False) -> llm_mod.FallbackChatOpenAI:
    backup = _Backup(model="gemini-test", api_key="x", base_url="http://backup", calls=[])
    return llm_mod.FallbackChatOpenAI(
        model="kimchi-test", api_key="x", base_url="http://primary", streaming=streaming, fallback=backup
    )


@pytest.mark.asyncio
async def test_agenerate_falls_back_on_402():
    model = _model()
    with patch.object(llm_mod.ChatOpenAI, "_agenerate", AsyncMock(side_effect=_status_error(402))) as primary:
        out = await model.ainvoke([HumanMessage(content="hi")])
    assert out.content == "from gemini"
    primary.assert_awaited_once()
    assert len(model.fallback.calls) == 1  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_agenerate_primary_success_never_touches_fallback():
    model = _model()
    with patch.object(llm_mod.ChatOpenAI, "_agenerate", AsyncMock(return_value=_result("from kimchi"))):
        out = await model.ainvoke([HumanMessage(content="hi")])
    assert out.content == "from kimchi"
    assert model.fallback.calls == []  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_agenerate_does_not_fall_back_on_bad_request():
    model = _model()
    with patch.object(llm_mod.ChatOpenAI, "_agenerate", AsyncMock(side_effect=_status_error(400))):
        with pytest.raises(openai.APIStatusError):
            await model.ainvoke([HumanMessage(content="hi")])
    assert model.fallback.calls == []  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_bind_tools_keeps_wrapper_and_replays_tools_on_fallback():
    @tool
    def ping(x: str) -> str:
        """Ping."""
        return x

    bound = _model().bind_tools([ping])
    assert isinstance(bound.bound, llm_mod.FallbackChatOpenAI)  # type: ignore[attr-defined]
    with patch.object(llm_mod.ChatOpenAI, "_agenerate", AsyncMock(side_effect=_status_error(402))):
        await bound.ainvoke([HumanMessage(content="hi")])
    assert "tools" in bound.bound.fallback.calls[0]  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_astream_falls_back_when_nothing_streamed_yet():
    async def failing(*_a, **_k):
        raise _status_error(402)
        yield  # pragma: no cover

    model = _model(streaming=True)
    with patch.object(llm_mod.ChatOpenAI, "_astream", failing):
        chunks = [c.content async for c in model.astream([HumanMessage(content="hi")])]
    assert "".join(str(c) for c in chunks) == "gem"  # LangChain appends an empty end-of-stream chunk


@pytest.mark.asyncio
async def test_astream_does_not_fall_back_after_tokens_were_sent():
    async def half_then_fail(*_a, **_k):
        yield ChatGenerationChunk(message=AIMessageChunk(content="par"))
        raise _status_error(500)

    model = _model(streaming=True)
    got: list[str] = []
    with patch.object(llm_mod.ChatOpenAI, "_astream", half_then_fail):
        with pytest.raises(openai.APIStatusError):
            async for c in model.astream([HumanMessage(content="hi")]):
                got.append(str(c.content))
    assert got == ["par"]  # no duplicated "gem" appended after partial output


def test_judge_uses_its_own_model_when_configured():
    settings = _settings("gem-key")
    settings.judge_model = "judge-model"
    with patch.object(llm_mod, "get_settings", return_value=settings):
        judge = llm_mod.get_judge_llm()
    assert judge.model_name == "judge-model" and judge.temperature == 0.0


def test_judge_falls_back_to_generator_when_unset():
    with patch.object(llm_mod, "get_settings", return_value=_settings("gem-key")):
        assert llm_mod.get_judge_llm().model_name == llm_mod.get_llm().model_name
