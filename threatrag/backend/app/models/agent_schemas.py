import json
from typing import Annotated, Literal, Union

from pydantic import BaseModel


class ToolCallData(BaseModel):
    name: str
    input: str
    tool_use_id: str


class AgentThought(BaseModel):
    type: Literal["thought"] = "thought"
    data: str


class AgentToolCall(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    data: ToolCallData


class AgentToolResult(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    data: str
    tool_use_id: str


class AgentChunk(BaseModel):
    type: Literal["chunk"] = "chunk"
    data: str


class AgentDone(BaseModel):
    type: Literal["done"] = "done"
    session_id: str
    total_tokens: int = 0


class AgentError(BaseModel):
    type: Literal["error"] = "error"
    data: str


AgentStreamEvent = Annotated[
    Union[AgentThought, AgentToolCall, AgentToolResult, AgentChunk, AgentDone, AgentError],
    "discriminated by type",
]


def to_sse(event: BaseModel) -> str:
    return f"data: {json.dumps(event.model_dump())}\n\n"
