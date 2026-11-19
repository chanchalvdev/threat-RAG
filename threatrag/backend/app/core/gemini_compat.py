"""Gemini quirks behind its OpenAI-compatible endpoint, kept out of the rest of the app.

1. Gemini 3 rejects a tool-call turn in the history unless it carries the `thought_signature`
   the model produced with it. LangChain's OpenAI client drops that field, so it is captured
   from responses here and put back on the way out. History that Gemini did not produce
   (another provider, an older session) gets the placeholder Google accepts for that case.
2. While streaming, usage arrives on several chunks as a running total. LangChain adds chunk
   usage together, which over-counts by an order of magnitude, so chunks are rewritten to deltas.
"""
from collections import OrderedDict
from collections.abc import AsyncIterator
from typing import Any

import openai
from langchain_core.messages import AIMessageChunk
from langchain_core.messages.ai import UsageMetadata
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_openai import ChatOpenAI
from pydantic import PrivateAttr

PLACEHOLDER_SIGNATURE = "skip_thought_signature_validator"
_MAX_SIGNATURES = 512


def _signature(tool_call: dict[str, Any]) -> str | None:
    return ((tool_call.get("extra_content") or {}).get("google") or {}).get("thought_signature")


class GeminiCompatChatOpenAI(ChatOpenAI):  # type: ignore[override]  # pydantic __replace__ stub quirk
    google_compat: bool = False
    _signatures: OrderedDict[str, str] = PrivateAttr(default_factory=OrderedDict)

    def _remember(self, tool_calls: list[dict[str, Any]] | None) -> None:
        for call in tool_calls or []:
            signature, call_id = _signature(call), call.get("id")
            if signature and call_id:
                self._signatures[call_id] = signature
                while len(self._signatures) > _MAX_SIGNATURES:
                    self._signatures.popitem(last=False)

    def _create_chat_result(self, response: dict | openai.BaseModel, generation_info: dict | None = None) -> ChatResult:
        if self.google_compat:
            raw = response if isinstance(response, dict) else response.model_dump()
            for choice in raw.get("choices") or []:
                self._remember((choice.get("message") or {}).get("tool_calls"))
        return super()._create_chat_result(response, generation_info)

    def _convert_chunk_to_generation_chunk(
        self, chunk: dict, default_chunk_class: type, base_generation_info: dict | None,
    ) -> ChatGenerationChunk | None:
        if self.google_compat:
            for choice in chunk.get("choices") or []:
                self._remember((choice.get("delta") or {}).get("tool_calls"))
        return super()._convert_chunk_to_generation_chunk(chunk, default_chunk_class, base_generation_info)

    def _get_request_payload(self, input_: Any, *, stop: list[str] | None = None, **kwargs: Any) -> dict:
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        if self.google_compat:
            for message in payload.get("messages", []):
                for call in message.get("tool_calls") or [] if message.get("role") == "assistant" else []:
                    signature = self._signatures.get(call.get("id", ""), PLACEHOLDER_SIGNATURE)
                    call.setdefault("extra_content", {"google": {"thought_signature": signature}})
        return payload

    async def _astream(self, *args: Any, **kwargs: Any) -> AsyncIterator[ChatGenerationChunk]:
        seen_in = seen_out = 0
        async for chunk in super()._astream(*args, **kwargs):
            message = chunk.message
            if self.google_compat and isinstance(message, AIMessageChunk) and message.usage_metadata:
                usage = message.usage_metadata
                delta_in = max(0, usage["input_tokens"] - seen_in)
                delta_out = max(0, usage["output_tokens"] - seen_out)
                seen_in, seen_out = max(seen_in, usage["input_tokens"]), max(seen_out, usage["output_tokens"])
                message.usage_metadata = UsageMetadata(
                    input_tokens=delta_in, output_tokens=delta_out, total_tokens=delta_in + delta_out,
                )
            yield chunk
