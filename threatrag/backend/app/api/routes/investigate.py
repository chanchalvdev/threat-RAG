from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.agent.investigation_models import InvestigationReport, InvestigationRequest, ReportSummary
from app.db import reports as repo
from app.db.connection import get_pool, is_db_ready
from app.services.investigation_service import investigate, investigate_sse

router = APIRouter(prefix="/investigate", tags=["investigate"])

_SSE_EXAMPLE = (
    'data: {"type": "node_start", "node": "researcher", "iteration": 1}\n\n'
    'data: {"type": "tool_call", "node": "researcher", "name": "nvd_cve_lookup", "input": "{\'cve_id\': \'CVE-2021-44228\'}"}\n\n'
    'data: {"type": "node_done", "node": "researcher", "summary": "3 tool calls · 2140 chars"}\n\n'
    'data: {"type": "node_start", "node": "critic", "iteration": 1}\n\n'
    'data: {"type": "routing", "from": "critic", "to": "reporter", "reason": "APPROVED"}\n\n'
    'data: {"type": "report_chunk", "data": "# Threat Intelligence Report: CVE-2021-44228"}\n\n'
    'data: {"type": "done", "ioc": "CVE-2021-44228", "report_id": "6c1e…", "similar": []}\n\n'
)


def _require_db() -> None:
    if not is_db_ready():
        raise HTTPException(status_code=503, detail="Report storage unavailable (PostgreSQL not connected)")


@router.post(
    "/stream",
    summary="Run a multi-agent investigation, streaming via SSE",
    description="Runs the Researcher → Critic → Reporter LangGraph loop for an IOC. Streams "
    "`node_start`, `tool_call`, `node_done`, `routing`, `report_chunk`, then `done` "
    "(with `report_id` and similar past reports) or `error`.",
    responses={200: {"content": {"text/event-stream": {"example": _SSE_EXAMPLE}}}},
)
async def investigate_stream(req: InvestigationRequest) -> StreamingResponse:
    return StreamingResponse(
        investigate_sse(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/save",
    response_model=InvestigationReport,
    summary="Run an investigation to completion and persist the report",
)
async def save_investigation(req: InvestigationRequest) -> InvestigationReport:
    return await investigate(req)


@router.get("/reports", response_model=list[ReportSummary], summary="List recent investigation reports")
async def list_reports(limit: int = Query(default=20, ge=1, le=100)) -> list[ReportSummary]:
    _require_db()
    async with get_pool().connection() as conn:
        return await repo.list_reports(limit, conn)


@router.get(
    "/reports/{report_id}",
    response_model=InvestigationReport,
    summary="Fetch a saved investigation report",
    responses={404: {"content": {"application/json": {"example": {"detail": "Report not found"}}}}},
)
async def get_report(report_id: str) -> InvestigationReport:
    _require_db()
    async with get_pool().connection() as conn:
        try:
            report = await repo.get_report(report_id, conn)
        except Exception:  # malformed UUID
            report = None
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
