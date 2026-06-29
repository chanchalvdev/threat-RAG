import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.agent.graph import InvestigationRequest, run_investigation
from app.core.logging import get_logger

log = get_logger(__name__)
router = APIRouter(prefix="/investigate", tags=["investigate"])


@router.post("/stream")
async def investigate_stream(req: InvestigationRequest) -> StreamingResponse:
    async def _stream():
        yield f"data: {json.dumps({'type': 'node_start', 'node': 'researcher', 'iteration': 1})}\n\n"

        report = await run_investigation(req)

        for chunk in _split_chunks(report.final_report, 200):
            yield f"data: {json.dumps({'type': 'report_chunk', 'data': chunk})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'ioc': req.ioc})}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")


@router.post("/save")
async def save_investigation(req: InvestigationRequest) -> dict:
    report = await run_investigation(req)
    return {"status": "saved", "ioc": report.ioc, "report_length": len(report.final_report)}


def _split_chunks(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]
