import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent.session import session_manager
from app.core.logging import get_logger

log = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None


class SuggestionRequest(BaseModel):
    last_question: str
    last_answer: str


@router.post("/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    session_id = req.session_id or str(uuid.uuid4())
    agent = await session_manager.get_or_create(session_id)

    async def _stream():
        async for chunk in agent.stream(req.question, session_id):
            yield chunk

    headers = {"X-Session-ID": session_id}
    return StreamingResponse(_stream(), media_type="text/event-stream", headers=headers)


@router.get("/history/{session_id}")
async def get_history(session_id: str) -> list[dict[str, str]]:
    agent = await session_manager.get_or_create(session_id)
    return agent.get_history()


@router.delete("/history/{session_id}")
async def clear_history(session_id: str) -> dict[str, str]:
    agent = await session_manager.get_or_create(session_id)
    agent.clear_history()
    return {"status": "cleared"}


@router.post("/suggestions")
async def get_suggestions(req: SuggestionRequest) -> dict[str, list[str]]:
    from langchain_openai import ChatOpenAI
    from app.core.config import get_settings
    s = get_settings()
    llm = ChatOpenAI(
        model=s.llm_model,
        openai_api_key=s.kimchi_api_key,  # type: ignore[arg-type]
        openai_api_base=s.kimchi_base_url,
    )
    prompt = (
        f"Given this Q&A exchange, suggest 3 follow-up security questions (one per line, no numbering):\n"
        f"Q: {req.last_question}\nA: {req.last_answer[:300]}"
    )
    response = await llm.ainvoke(prompt)
    lines = [ln.strip() for ln in str(response.content).split("\n") if ln.strip()]
    return {"suggestions": lines[:3]}
