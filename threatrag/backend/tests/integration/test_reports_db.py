"""Real Postgres + pgvector: migrations, report round trip, similarity search."""
import uuid

import psycopg
import pytest

from app.agent.investigation_models import InvestigationReport
from app.db import reports as repo
from app.models.schemas import SourceDoc
from app.scripts.migrate import run_migrations
from tests.integration.conftest import require

pytestmark = pytest.mark.integration


def _vector(hot: int) -> list[float]:
    return [1.0 if i == hot else 0.0 for i in range(768)]


@pytest.fixture
async def conn(settings):
    require(settings.database_url.replace("postgresql://", "http://"), 5432, "Postgres")
    await run_migrations()
    await run_migrations()  # idempotent
    async with await psycopg.AsyncConnection.connect(settings.database_url) as connection:
        yield connection
        await connection.rollback()  # nothing these tests write is kept


async def test_report_round_trip_and_similarity_order(conn):
    marker = f"it-{uuid.uuid4().hex[:8]}"
    near = InvestigationReport(ioc=f"{marker}-near", ioc_type="cve", final_report="near report", iterations=2,
                               sources=[SourceDoc(text="t", source="s", doc_type="mitre_attack", score=0.9, ref_id="T1190")],
                               tool_calls=[{"name": "nvd_cve_lookup", "input": "x", "output": "y"}])
    far = InvestigationReport(ioc=f"{marker}-far", ioc_type="cve", final_report="far report")
    near_id = await repo.save_report(near, _vector(0), conn)
    far_id = await repo.save_report(far, _vector(500), conn)

    loaded = await repo.get_report(near_id, conn)
    assert loaded is not None and loaded.ioc == near.ioc and loaded.iterations == 2
    assert loaded.sources[0].ref_id == "T1190" and loaded.tool_calls[0]["name"] == "nvd_cve_lookup"

    similar = [s for s in await repo.find_similar_reports(_vector(0), 50, conn) if s.ioc.startswith(marker)]
    assert [s.id for s in similar] == [near_id, far_id] and similar[0].similarity == pytest.approx(1.0)
    assert near_id not in [s.id for s in await repo.find_similar_reports(_vector(0), 50, conn, exclude_id=near_id)]
    assert any(s.id == far_id for s in await repo.list_reports(50, conn))
