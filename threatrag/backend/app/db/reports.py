import json
import uuid
from typing import Any

from app.agent.graph import InvestigationReport
from app.core.logging import get_logger

log = get_logger(__name__)


class ReportSummary:
    def __init__(self, id: str, ioc: str, ioc_type: str, summary: str, created_at: str):
        self.id = id
        self.ioc = ioc
        self.ioc_type = ioc_type
        self.summary = summary
        self.created_at = created_at


async def save_report(
    report: InvestigationReport,
    embedding: list[float],
    conn: Any,
) -> str:
    report_id = str(uuid.uuid4())
    await conn.execute(
        """
        INSERT INTO reports (id, ioc, ioc_type, final_report, sources, ragas_scores, embedding)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            report_id,
            report.ioc,
            report.ioc_type,
            report.final_report,
            json.dumps([s.model_dump() for s in report.sources]),
            json.dumps(report.ragas_scores.model_dump() if report.ragas_scores else {}),
            embedding,
        ),
    )
    log.info("report_saved", report_id=report_id, ioc=report.ioc)
    return report_id


async def find_similar_reports(
    embedding: list[float], k: int, conn: Any
) -> list[ReportSummary]:
    rows = await conn.fetchall(
        """
        SELECT id, ioc, ioc_type,
               left(final_report, 300) AS summary,
               created_at::text
        FROM reports
        ORDER BY embedding <=> %s
        LIMIT %s
        """,
        (embedding, k),
    )
    return [ReportSummary(id=r[0], ioc=r[1], ioc_type=r[2], summary=r[3], created_at=r[4]) for r in rows]


async def get_report(report_id: str, conn: Any) -> InvestigationReport | None:
    row = await conn.fetchone(
        "SELECT ioc, ioc_type, final_report FROM reports WHERE id = %s", (report_id,)
    )
    if not row:
        return None
    return InvestigationReport(ioc=row[0], ioc_type=row[1], final_report=row[2])
