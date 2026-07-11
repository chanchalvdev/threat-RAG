import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from app.agent.graph import InvestigationRequest, run_investigation
from app.core.logging import get_logger

log = get_logger(__name__)
router = APIRouter(prefix="/investigate", tags=["investigate"])


class InvestigationSaveResponse(BaseModel):
    status: str
    ioc: str
    report_length: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"status": "saved", "ioc": "CVE-2021-44228", "report_length": 2140}
        }
    )


@router.post(
    "/stream",
    summary="Run a multi-agent investigation, streaming via SSE",
    description="Runs the Researcher → Critic → Reporter LangGraph loop for an IOC and streams "
    "`node_start`, `report_chunk`, and `done` events as the report is produced.",
    responses={
        200: {
            "description": "text/event-stream of investigation progress and report chunks",
            "content": {
                "text/event-stream": {
                    "example": (
                        'data: {"type": "node_start", "node": "researcher", "iteration": 1}\n\n'
                        'data: {"type": "report_chunk", "data": "# Threat Intelligence Report: CVE-2021-44228\\n'
                        '## Executive Summary..."}\n\n'
                        'data: {"type": "done", "ioc": "CVE-2021-44228"}\n\n'
                    )
                }
            },
        }
    },
)
async def investigate_stream(req: InvestigationRequest) -> StreamingResponse:
    async def _stream():
        yield f"data: {json.dumps({'type': 'node_start', 'node': 'researcher', 'iteration': 1})}\n\n"

        report = await run_investigation(req)

        for chunk in _split_chunks(report.final_report, 200):
            yield f"data: {json.dumps({'type': 'report_chunk', 'data': chunk})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'ioc': req.ioc})}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")


@router.post(
    "/save",
    response_model=InvestigationSaveResponse,
    summary="Run an investigation synchronously and persist the report",
    description="Same investigation as POST /investigate/stream, but runs to completion "
    "and returns a summary instead of streaming.",
)
async def save_investigation(req: InvestigationRequest) -> dict:
    report = await run_investigation(req)
    return {"status": "saved", "ioc": report.ioc, "report_length": len(report.final_report)}


def _split_chunks(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]
