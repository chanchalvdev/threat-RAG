import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.deps import get_chain
from app.core.logging import get_logger
from app.models.schemas import QueryRequest, RAGResponse
from app.rag.chain import ThreatRAGChain
from app.rag.sanitiser import is_injection

log = get_logger(__name__)
router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=RAGResponse)
async def query(req: QueryRequest, chain: ThreatRAGChain = Depends(get_chain)) -> RAGResponse:
    if is_injection(req.question):
        log.warning("injection_detected", question=req.question[:100])
        raise HTTPException(status_code=400, detail="Request rejected: potential prompt injection detected")
    return await chain.query(req)


@router.post("/stream")
async def query_stream(req: QueryRequest, chain: ThreatRAGChain = Depends(get_chain)) -> StreamingResponse:
    if is_injection(req.question):
        raise HTTPException(status_code=400, detail="Request rejected: potential prompt injection detected")

    async def _event_stream():
        async for text, sources in chain.astream(req):
            if text == "__sources__":
                for s in sources:
                    yield f"data: {json.dumps({'type': 'source', 'data': s.model_dump()})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'chunk', 'data': text})}\n\n"
        yield 'data: {"type":"done"}\n\n'

    return StreamingResponse(_event_stream(), media_type="text/event-stream")
