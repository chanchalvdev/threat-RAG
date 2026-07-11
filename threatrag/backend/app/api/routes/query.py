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


@router.post(
    "",
    response_model=RAGResponse,
    summary="Ask a question against the RAG knowledge base",
    description="Runs retrieval-augmented generation over the ingested MITRE ATT&CK / "
    "OWASP corpus and returns a cited answer.",
    responses={
        400: {
            "description": "Prompt injection detected in the question",
            "content": {"application/json": {"example": {"detail": "Request rejected: potential prompt injection detected"}}},
        }
    },
)
async def query(req: QueryRequest, chain: ThreatRAGChain = Depends(get_chain)) -> RAGResponse:
    if is_injection(req.question):
        log.warning("injection_detected", question=req.question[:100])
        raise HTTPException(status_code=400, detail="Request rejected: potential prompt injection detected")
    return await chain.query(req)


@router.post(
    "/stream",
    summary="Ask a question and stream the answer via SSE",
    description="Same as POST /query but streams Server-Sent Events: `source` events "
    "(one per retrieved document), then `chunk` events (answer tokens), then a final `done` event.",
    responses={
        200: {
            "description": "text/event-stream of source, chunk, and done events",
            "content": {
                "text/event-stream": {
                    "example": (
                        'data: {"type": "source", "data": {"text": "T1110.001 Password Guessing...", '
                        '"source": "mitre_attack.json#T1110.001", "doc_type": "mitre_attack", "score": 0.87}}\n\n'
                        'data: {"type": "chunk", "data": "T1110.001 is a MITRE ATT&CK sub-technique..."}\n\n'
                        'data: {"type": "done"}\n\n'
                    )
                }
            },
        },
        400: {
            "description": "Prompt injection detected in the question",
            "content": {"application/json": {"example": {"detail": "Request rejected: potential prompt injection detected"}}},
        },
    },
)
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
