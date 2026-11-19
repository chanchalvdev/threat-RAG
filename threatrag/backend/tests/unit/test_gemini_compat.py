"""Gemini OpenAI-endpoint quirks: tool-call thought signatures and cumulative stream usage."""
from unittest.mock import patch

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGenerationChunk
from langchain_openai import ChatOpenAI

from app.core.gemini_compat import PLACEHOLDER_SIGNATURE, GeminiCompatChatOpenAI


def _model(google: bool = True) -> GeminiCompatChatOpenAI:
    return GeminiCompatChatOpenAI(model="m", api_key="k", base_url="http://x", google_compat=google)


def _history(call_id: str) -> list:
    call = {"name": "lookup", "args": {"cve_id": "CVE-2021-44228"}, "id": call_id, "type": "tool_call"}
    return [HumanMessage("q"), AIMessage(content="", tool_calls=[call]), ToolMessage(content="CVSS 10", tool_call_id=call_id)]


def _raw_call(call_id: str, signature: str) -> dict:
    return {"id": call_id, "type": "function", "function": {"name": "lookup", "arguments": "{}"},
            "extra_content": {"google": {"thought_signature": signature}}}


def _sent_signature(model: GeminiCompatChatOpenAI, call_id: str) -> str | None:
    assistant = model._get_request_payload(_history(call_id))["messages"][1]
    return (assistant["tool_calls"][0].get("extra_content") or {}).get("google", {}).get("thought_signature")


def test_signature_from_a_response_is_sent_back_with_the_same_tool_call():
    model = _model()
    response = {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [_raw_call("c1", "sig-1")]},
                             "finish_reason": "tool_calls"}], "model": "m"}
    model._create_chat_result(response)
    assert _sent_signature(model, "c1") == "sig-1"


def test_signature_is_captured_from_stream_chunks():
    model = _model()
    chunk = {"choices": [{"delta": {"role": "assistant", "tool_calls": [{**_raw_call("c2", "sig-2"), "index": 0}]}, "index": 0}]}
    model._convert_chunk_to_generation_chunk(chunk, AIMessageChunk, None)
    assert _sent_signature(model, "c2") == "sig-2"


def test_history_from_elsewhere_gets_the_placeholder_and_other_providers_get_nothing():
    assert _sent_signature(_model(), "unknown") == PLACEHOLDER_SIGNATURE
    assert _sent_signature(_model(google=False), "unknown") is None


def test_signature_store_is_bounded():
    model = _model()
    model._remember([_raw_call(f"c{i}", "s") for i in range(600)])
    assert len(model._signatures) == 512 and "c0" not in model._signatures and "c599" in model._signatures


async def _stream(google: bool) -> list[dict | None]:
    def chunk(tokens_in: int, tokens_out: int) -> ChatGenerationChunk:
        usage = {"input_tokens": tokens_in, "output_tokens": tokens_out, "total_tokens": tokens_in + tokens_out}
        return ChatGenerationChunk(message=AIMessageChunk(content="x", usage_metadata=usage))

    async def running_totals(self, *args, **kwargs):
        for totals in ((100, 5), (100, 12), (100, 20)):
            yield chunk(*totals)
        yield ChatGenerationChunk(message=AIMessageChunk(content="y"))

    with patch.object(ChatOpenAI, "_astream", running_totals):
        return [c.message.usage_metadata async for c in _model(google)._astream([HumanMessage("q")])]


async def test_cumulative_stream_usage_becomes_deltas_that_sum_to_the_total():
    usage = [u for u in await _stream(google=True) if u]
    assert [(u["input_tokens"], u["output_tokens"]) for u in usage] == [(100, 5), (0, 7), (0, 8)]
    assert sum(u["total_tokens"] for u in usage) == 120


async def test_other_providers_stream_usage_is_left_alone():
    usage = [u for u in await _stream(google=False) if u]
    assert [u["output_tokens"] for u in usage] == [5, 12, 20]
