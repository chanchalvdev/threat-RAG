"""Ingest, investigate, evaluate and readiness routes, including their degraded paths."""
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("KIMCHI_API_KEY", "test-key-for-unit-tests")

from app.api.deps import get_store  # noqa: E402
from app.api.routes import evaluate as eval_routes  # noqa: E402
from app.api.routes import ingest as ingest_routes  # noqa: E402
from app.api.routes import investigate as inv_routes  # noqa: E402
from app.evaluation.ragas_eval import RagasScores  # noqa: E402
from app.main import app  # noqa: E402
from app.services import readiness  # noqa: E402


@pytest.fixture
async def client():
    store = MagicMock(collection="threat_intel", total=AsyncMock(return_value=5),
                      count_by_doc_type=AsyncMock(side_effect=OSError("no facet")))
    app.dependency_overrides[get_store] = lambda: store
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c
    app.dependency_overrides.clear()


async def test_stats_tolerates_facet_failure(client):
    body = (await client.get("/api/v1/ingest/stats")).json()
    assert body == {"collection": "threat_intel", "total_vectors": 5, "doc_type_counts": {}}


@pytest.mark.parametrize("path", ["mitre", "owasp"])
async def test_ingest_job_is_pollable_before_background_task_runs(client, path):
    with patch.object(ingest_routes, "_run", new=AsyncMock()):
        job_id = (await client.post(f"/api/v1/ingest/{path}")).json()["job_id"]
    assert (await client.get(f"/api/v1/ingest/status/{job_id}")).json()["status"] == "pending"


async def test_status_unknown_job_404(client):
    assert (await client.get("/api/v1/ingest/status/nope")).status_code == 404


@pytest.mark.parametrize("name,body,doc_type,status", [
    ("a.pdf", b"not a pdf", "custom", 400),
    ("a.pdf", b"%PDF-1.7", "Bad Type!", 400),
    ("a.exe", b"%PDF-1.7", "custom", 400),
])
async def test_upload_rejections(client, name, body, doc_type, status):
    r = await client.post("/api/v1/ingest/pdf", files={"file": (name, body)}, data={"doc_type": doc_type})
    assert r.status_code == status


async def test_upload_too_large_413(client):
    with patch.object(ingest_routes, "get_settings", return_value=MagicMock(max_upload_mb=0)):
        r = await client.post("/api/v1/ingest/pdf", files={"file": ("a.pdf", b"%PDF-1.7")})
    assert r.status_code == 413


async def test_upload_accepted_writes_basename_only(client, tmp_path):
    with patch.object(ingest_routes, "DATA_DIR", tmp_path), patch.object(ingest_routes, "_run", new=AsyncMock()):
        r = await client.post("/api/v1/ingest/pdf", files={"file": ("../../x.pdf", b"%PDF-1.7")})
    assert r.status_code == 202
    assert (tmp_path / "x.pdf").exists()


async def test_run_jobs_record_failure(client):
    await ingest_routes._run("j1", AsyncMock(side_effect=ValueError("bad")))
    job = (await client.get("/api/v1/ingest/status/j1")).json()
    assert job["status"] == "failed" and job["error"] == "bad"


async def test_run_jobs_record_success(client):
    await ingest_routes._run("j2", AsyncMock(return_value=7))
    assert (await client.get("/api/v1/ingest/status/j2")).json()["chunks_processed"] == 7


async def test_reports_503_when_db_down(client):
    with patch.object(inv_routes, "is_db_ready", return_value=False):
        assert (await client.get("/api/v1/investigate/reports")).status_code == 503
        assert (await client.get("/api/v1/investigate/reports/abc")).status_code == 503


async def test_report_malformed_id_is_404(client):
    ctx = MagicMock(__aenter__=AsyncMock(return_value=MagicMock()), __aexit__=AsyncMock(return_value=False))
    with patch.object(inv_routes, "is_db_ready", return_value=True), \
            patch.object(inv_routes, "get_pool", return_value=MagicMock(connection=MagicMock(return_value=ctx))), \
            patch.object(inv_routes.repo, "get_report", new=AsyncMock(side_effect=ValueError)):
        assert (await client.get("/api/v1/investigate/reports/not-a-uuid")).status_code == 404


async def test_investigate_rejects_invalid_ioc(client):
    r = await client.post("/api/v1/investigate/save", json={"ioc": "not-a-cve", "ioc_type": "cve"})
    assert r.status_code == 422


async def test_evaluate_history_empty_without_db(client):
    with patch.object(eval_routes, "is_db_ready", return_value=False):
        assert (await client.get("/api/v1/evaluate/history")).json() == []


async def test_evaluate_survives_persist_failure(client):
    scores = RagasScores(faithfulness=1, answer_relevancy=1, context_precision=1, context_recall=1, overall=1)
    with patch.object(eval_routes, "evaluate_response", new=AsyncMock(return_value=scores)), \
            patch.object(eval_routes, "is_db_ready", return_value=True), \
            patch.object(eval_routes, "get_pool", side_effect=OSError("down")):
        r = await client.post("/api/v1/evaluate", json={"question": "abc", "answer": "a", "contexts": ["c"]})
    assert r.status_code == 200 and r.json()["overall"] == 1


async def test_readiness_is_degraded_on_402_and_cached(client, httpx_mock):
    s = MagicMock(qdrant_url="http://q", qdrant_collection="c", qdrant_api_key="", embedding_provider="gemini",
                  kimchi_api_key="k", kimchi_base_url="http://llm", llm_model="m", gemini_api_key="")
    httpx_mock.add_response(url="http://q/collections/c", json={})
    httpx_mock.add_response(url="http://llm/chat/completions", status_code=402)
    readiness._cache.update({"data": None, "expires": 0.0})
    with patch.object(readiness, "get_settings", return_value=s), \
            patch.object(readiness, "is_db_ready", return_value=False):
        first = (await client.get("/health/ready")).json()
        second = (await client.get("/health/ready")).json()
    readiness._cache.update({"data": None, "expires": 0.0})
    assert first["status"] == "degraded" and first["checks"]["llm"] == "http_402"
    assert "ollama" not in first["checks"] and second == first
    assert len(httpx_mock.get_requests()) == 2
