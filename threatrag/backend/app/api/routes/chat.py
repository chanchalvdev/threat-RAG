import re
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.agent.session import session_manager
from app.core.llm import get_llm
from app.core.logging import get_logger
from app.rag.sanitiser import is_injection

log = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])
_LIST_MARKER = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*")


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=4000)
    session_id: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "What CVEs affect Apache Log4j?",
                "session_id": None,
            }
        }
    )


class SuggestionRequest(BaseModel):
    last_question: str
    last_answer: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "last_question": "What CVEs affect Apache Log4j?",
                "last_answer": "CVE-2021-44228 (Log4Shell) is a critical RCE in Apache Log4j 2.",
            }
        }
    )


class ChatHistoryMessage(BaseModel):
    role: str
    content: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"role": "user", "content": "What CVEs affect Apache Log4j?"}}
    )


class ChatStatusResponse(BaseModel):
    status: str

    model_config = ConfigDict(json_schema_extra={"example": {"status": "cleared"}})


class SuggestionsResponse(BaseModel):
    suggestions: list[str]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "suggestions": [
                    "What versions of Log4j are affected by CVE-2021-44228?",
                    "How does Log4Shell map to MITRE ATT&CK techniques?",
                    "What mitigations are recommended for Log4Shell?",
                ]
            }
        }
    )


@router.post(
    "/stream",
    summary="Chat with the ReAct agent, streaming via SSE",
    description="Streams `thought`, `tool_call`, `tool_result`, `chunk`, `done` and `error` events. "
    "Pass the returned `X-Session-ID` back as `session_id` to continue the conversation.",
    responses={
        200: {
            "description": "text/event-stream of agent thought/tool/chunk events",
            "content": {
                "text/event-stream": {
                    "example": (
                        'data: {"type": "thought", "data": "I should look up this CVE."}\n\n'
                        'data: {"type": "tool_call", "data": {"name": "nvd_cve_lookup", '
                        '"input": "CVE-2021-44228", "tool_use_id": "call_1"}}\n\n'
                        'data: {"type": "tool_result", "data": "Log4Shell RCE, CVSS 10.0", "tool_use_id": "call_1"}\n\n'
                        'data: {"type": "chunk", "data": "CVE-2021-44228 (Log4Shell) is a critical RCE..."}\n\n'
                        'data: {"type": "done", "session_id": "b3f1...", "total_tokens": 512}\n\n'
                    )
                }
            },
        }
    },
)
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    if is_injection(req.question):
        log.warning("injection_detected", route="chat", question=req.question[:100])
        raise HTTPException(status_code=400, detail="Request rejected: potential prompt injection detected")
    session_id = req.session_id or str(uuid.uuid4())
    agent = await session_manager.get_or_create(session_id)

    async def _stream():
        async for chunk in agent.stream(req.question, session_id):
            yield chunk

    headers = {"X-Session-ID": session_id}
    return StreamingResponse(_stream(), media_type="text/event-stream", headers=headers)


@router.get(
    "/history/{session_id}",
    response_model=list[ChatHistoryMessage],
    summary="Get a session's conversation history",
)
async def get_history(session_id: str) -> list[dict[str, str]]:
    agent = await session_manager.get_or_create(session_id)
    return agent.get_history()


@router.delete(
    "/history/{session_id}",
    response_model=ChatStatusResponse,
    summary="Clear a session's conversation history",
)
async def clear_history(session_id: str) -> dict[str, str]:
    agent = await session_manager.get_or_create(session_id)
    agent.clear_history()
    return {"status": "cleared"}


@router.post(
    "/suggestions",
    response_model=SuggestionsResponse,
    summary="Generate follow-up question suggestions",
    description="Given the last Q&A exchange, asks the LLM for 3 relevant follow-up security questions.",
)
async def get_suggestions(req: SuggestionRequest) -> dict[str, list[str]]:
    llm = get_llm(temperature=0.5)
    prompt = (
        f"Given this Q&A exchange, suggest 3 follow-up security questions (one per line, no numbering):\n"
        f"Q: {req.last_question}\nA: {req.last_answer[:300]}"
    )
    response = await llm.ainvoke(prompt)
    lines = [_LIST_MARKER.sub("", ln).strip() for ln in str(response.content).split("\n") if ln.strip()]
    return {"suggestions": lines[:3]}
