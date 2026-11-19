"""Report/evaluation repositories and the investigation service, against a fake connection."""
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent.investigation_models import InvestigationReport, InvestigationRequest
from app.db import evaluations, reports
from app.evaluation.ragas_eval import RagasScores
from app.models.schemas import SourceDoc
from app.services import investigation_service as svc


class FakeConn:
    def __init__(self, rows: list[tuple[Any, ...]] | None = None):
        self.rows = rows or []
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> MagicMock:
        self.calls.append((sql, params))
        return MagicMock(fetchall=AsyncMock(return_value=self.rows),
                         fetchone=AsyncMock(return_value=self.rows[0] if self.rows else None))


def _report(text: str = "report") -> InvestigationReport:
    source = SourceDoc(text="t", source="s", doc_type="mitre_attack", score=0.9)
    return InvestigationReport(ioc="CVE-2021-44228", ioc_type="cve", final_report=text, sources=[source])


def _pool(conn: FakeConn) -> MagicMock:
    ctx = MagicMock(__aenter__=AsyncMock(return_value=conn), __aexit__=AsyncMock(return_value=False))
    return MagicMock(connection=MagicMock(return_value=ctx))


async def test_save_report_serialises_sources_and_vector():
    conn = FakeConn()
    report_id = await reports.save_report(_report(), [0.5, 0.25], conn)
    params = conn.calls[0][1]
    assert params[0] == report_id
    assert json.loads(params[4])[0]["source"] == "s"
    assert params[6] == "[0.500000,0.250000]"


async def test_find_similar_rounds_score_and_excludes_id():
    conn = FakeConn([("id1", "ioc", "cve", "summary", "2026-01-01", 0.123456)])
    out = await reports.find_similar_reports([0.1], 3, conn, exclude_id="abc")
    assert out[0].similarity == 0.1235
    assert conn.calls[0][1][1:3] == ("abc", "abc")


async def test_list_reports_maps_rows():
    out = await reports.list_reports(5, FakeConn([("id1", "ioc", "cve", "s", "2026-01-01")]))
    assert out[0].id == "id1" and out[0].similarity is None


async def test_get_report_rebuilds_model_and_handles_missing():
    row = ("ioc", "cve", "text", [{"text": "t", "source": "s", "doc_type": "d", "score": 0.5}], None, None, "2026")
    report = await reports.get_report("id1", FakeConn([row]))
    assert report is not None
    assert report.sources[0].source == "s" and report.tool_calls == [] and report.iterations == 1
    assert await reports.get_report("id1", FakeConn()) is None


async def test_evaluations_round_trip_oldest_first():
    scores = RagasScores(faithfulness=0.5, answer_relevancy=0.5, context_precision=0.5, context_recall=0.5, overall=0.5)
    conn = FakeConn([("new", "q", 1, 1, 1, 1, 1, "2"), ("old", "q", 0, 0, 0, 0, 0, "1")])
    await evaluations.save_evaluation("q", "a", scores, conn)
    assert conn.calls[0][1][:2] == ("q", "a")
    assert [r.id for r in await evaluations.list_evaluations(2, conn)] == ["old", "new"]


async def test_persist_skips_when_db_down():
    with patch.object(svc, "is_db_ready", return_value=False):
        assert await svc.persist(_report()) == (None, [])


async def test_persist_survives_db_failure():
    with patch.object(svc, "is_db_ready", return_value=True), \
            patch.object(svc, "get_embedder", return_value=MagicMock(embed=AsyncMock(side_effect=OSError("down")))):
        assert await svc.persist(_report()) == (None, [])


async def test_persist_saves_then_finds_similar():
    with patch.object(svc, "is_db_ready", return_value=True), \
            patch.object(svc, "get_embedder", return_value=MagicMock(embed=AsyncMock(return_value=[0.1]))), \
            patch.object(svc, "get_pool", return_value=_pool(FakeConn())):
        report_id, similar = await svc.persist(_report())
    assert report_id and similar == []


async def _events(*events: dict[str, Any]):
    for event in events:
        yield event


def _req() -> InvestigationRequest:
    return InvestigationRequest(ioc="CVE-2021-44228", ioc_type="cve")


async def test_sse_appends_validation_notes_before_done():
    report = _report("T9999")
    store = MagicMock(technique_names=AsyncMock(return_value={"T1059": "Command and Scripting Interpreter"}))
    with patch.object(svc, "stream_investigation", return_value=_events({"type": "node_start"}, {"type": "complete", "report": report})), \
            patch.object(svc, "get_store", return_value=store), \
            patch.object(svc, "persist", new=AsyncMock(return_value=("rid", []))):
        frames = [json.loads(f.removeprefix("data: ")) async for f in svc.investigate_sse(_req())]
    assert [f["type"] for f in frames] == ["node_start", "report_chunk", "done"]
    assert "T9999" in frames[1]["data"] and "Technique Validation" in report.final_report
    assert frames[2]["report_id"] == "rid"


async def test_sse_reports_failure_as_event():
    def boom(_req):
        raise RuntimeError("graph down")

    with patch.object(svc, "stream_investigation", side_effect=boom):
        frames = [f async for f in svc.investigate_sse(_req())]
    assert "graph down" in frames[0] and '"error"' in frames[0]


async def test_investigate_runs_notes_then_persists():
    with patch.object(svc, "run_investigation", new=AsyncMock(return_value=_report("x"))), \
            patch.object(svc, "_technique_notes", new=AsyncMock(return_value=" notes")), \
            patch.object(svc, "persist", new=AsyncMock(return_value=("rid", []))) as persist:
        report = await svc.investigate(_req())
    assert report.final_report == "x notes" and report.report_id == "rid"
    persist.assert_awaited_once()
