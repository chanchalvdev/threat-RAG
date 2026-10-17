"""Investigation orchestration: run graph → persist report → attach similar past reports."""
import json
from collections.abc import AsyncIterator
from typing import Any

from app.agent.graph import run_investigation, stream_investigation
from app.agent.investigation_models import InvestigationReport, InvestigationRequest, ReportSummary
from app.core.logging import get_logger
from app.db import reports as repo
from app.db.connection import get_pool, is_db_ready
from app.rag.embedder import get_embedder

log = get_logger(__name__)
SIMILAR_K = 3


def _sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"


async def persist(report: InvestigationReport) -> tuple[str | None, list[ReportSummary]]:
    """Save report + find similar ones. Never fails the investigation if the DB is down."""
    if not is_db_ready() or not report.final_report:
        return None, []
    try:
        embedding = await get_embedder().embed(f"{report.ioc}\n{report.final_report[:4000]}")
        async with get_pool().connection() as conn:
            report_id = await repo.save_report(report, embedding, conn)
            similar = await repo.find_similar_reports(embedding, SIMILAR_K, conn, exclude_id=report_id)
        return report_id, similar
    except Exception as exc:
        log.warning("report_persist_failed", ioc=report.ioc, error=str(exc))
        return None, []


async def investigate(req: InvestigationRequest) -> InvestigationReport:
    report = await run_investigation(req)
    report.report_id, _ = await persist(report)
    return report


async def investigate_sse(req: InvestigationRequest) -> AsyncIterator[str]:
    try:
        async for event in stream_investigation(req):
            if event["type"] != "complete":
                yield _sse(event)
                continue
            report: InvestigationReport = event["report"]
            report_id, similar = await persist(report)
            yield _sse({
                "type": "done",
                "ioc": report.ioc,
                "report_id": report_id,
                "iterations": report.iterations,
                "sources": [s.model_dump() for s in report.sources],
                "tool_calls": report.tool_calls,
                "similar": [s.model_dump() for s in similar],
            })
    except Exception as exc:
        log.error("investigation_failed", ioc=req.ioc, error=str(exc))
        yield _sse({"type": "error", "data": f"Investigation failed: {exc}"})
