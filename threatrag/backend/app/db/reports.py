"""Report persistence + pgvector similarity search."""
import json
import uuid

from psycopg import AsyncConnection

from app.agent.investigation_models import InvestigationReport, ReportSummary
from app.core.logging import get_logger
from app.models.schemas import SourceDoc

log = get_logger(__name__)


def _vec(embedding: list[float]) -> str:
    return "[" + ",".join(f"{v:.6f}" for v in embedding) + "]"


async def save_report(report: InvestigationReport, embedding: list[float], conn: AsyncConnection) -> str:
    report_id = str(uuid.uuid4())
    await conn.execute(
        """
        INSERT INTO reports (id, ioc, ioc_type, final_report, sources, ragas_scores,
                             embedding, tool_calls, iterations)
        VALUES (%s, %s, %s, %s, %s, %s, %s::vector, %s, %s)
        """,
        (
            report_id, report.ioc, report.ioc_type, report.final_report,
            json.dumps([s.model_dump() for s in report.sources]),
            json.dumps(report.ragas_scores.model_dump() if report.ragas_scores else {}),
            _vec(embedding), json.dumps(report.tool_calls), report.iterations,
        ),
    )
    log.info("report_saved", report_id=report_id, ioc=report.ioc)
    return report_id


async def find_similar_reports(
    embedding: list[float], k: int, conn: AsyncConnection, exclude_id: str | None = None
) -> list[ReportSummary]:
    cur = await conn.execute(
        """
        SELECT id::text, ioc, ioc_type, left(final_report, 300), created_at::text,
               1 - (embedding <=> %s::vector) AS similarity
        FROM reports
        WHERE embedding IS NOT NULL AND (%s::uuid IS NULL OR id <> %s::uuid)
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (_vec(embedding), exclude_id, exclude_id, _vec(embedding), k),
    )
    return [
        ReportSummary(id=r[0], ioc=r[1], ioc_type=r[2], summary=r[3], created_at=r[4], similarity=round(r[5], 4))
        for r in await cur.fetchall()
    ]


async def list_reports(limit: int, conn: AsyncConnection) -> list[ReportSummary]:
    cur = await conn.execute(
        "SELECT id::text, ioc, ioc_type, left(final_report, 300), created_at::text "
        "FROM reports ORDER BY created_at DESC LIMIT %s",
        (limit,),
    )
    return [
        ReportSummary(id=r[0], ioc=r[1], ioc_type=r[2], summary=r[3], created_at=r[4])
        for r in await cur.fetchall()
    ]


async def get_report(report_id: str, conn: AsyncConnection) -> InvestigationReport | None:
    cur = await conn.execute(
        "SELECT ioc, ioc_type, final_report, sources, tool_calls, iterations, created_at::text "
        "FROM reports WHERE id = %s",
        (report_id,),
    )
    row = await cur.fetchone()
    if not row:
        return None
    return InvestigationReport(
        report_id=report_id, ioc=row[0], ioc_type=row[1], final_report=row[2],
        sources=[SourceDoc(**s) for s in (row[3] or [])], tool_calls=row[4] or [],
        iterations=row[5] or 1, created_at=row[6],
    )
