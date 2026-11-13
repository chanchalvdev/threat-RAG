"""Embedding-space guard (mixing embedders), readiness LLM probe (G15), technique check (G18)."""
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

os.environ.setdefault("KIMCHI_API_KEY", "test-key-for-unit-tests")

from app.agent.investigation_models import InvestigationReport  # noqa: E402
from app.agent.technique_check import validate_techniques  # noqa: E402
from app.rag.embedder import GeminiEmbedder, embedding_tag  # noqa: E402
from app.rag.store import EmbeddingMismatchError, QdrantStore  # noqa: E402
from app.services import investigation_service as svc  # noqa: E402
from app.services import readiness  # noqa: E402

NAMES = {
    "T1021": "Remote Services",
    "T1021.006": "Windows Remote Management",
    "T1059": "Command and Scripting Interpreter",
    "T1059.001": "PowerShell",
}


def _store(points: list) -> QdrantStore:
    store = QdrantStore.__new__(QdrantStore)
    store.collection = "threat_intel"
    store._client = MagicMock(scroll=AsyncMock(return_value=(points, None)))
    return store


async def test_assert_embedding_allows_empty_collection():
    await _store([]).assert_embedding("gemini:text-embedding-004")


async def test_assert_embedding_rejects_a_different_vector_space():
    point = MagicMock(payload={"text": "x", "embedding_model": "ollama:nomic-embed-text"})
    await _store([point]).assert_embedding("ollama:nomic-embed-text")
    with pytest.raises(EmbeddingMismatchError, match="QDRANT_COLLECTION"):
        await _store([point]).assert_embedding("gemini:text-embedding-004")


def test_embedding_tag_includes_provider():
    assert embedding_tag(MagicMock(embedding_provider="gemini", embedding_model="m")) == "gemini:m"


async def test_gemini_embedder_splits_batches_and_sets_task_type(httpx_mock):
    url = "https://generativelanguage.googleapis.com/v1beta/models/m:batchEmbedContents"
    httpx_mock.add_response(url=url, json={"embeddings": [{"values": [0.1]}] * 100})
    httpx_mock.add_response(url=url, json={"embeddings": [{"values": [0.2]}]})
    out = await GeminiEmbedder("k", "m", 768).embed_batch(["t"] * 101)
    assert len(out) == 101
    first = httpx_mock.get_requests()[0]
    assert first.headers["x-goog-api-key"] == "k"
    assert b"RETRIEVAL_DOCUMENT" in first.content


async def test_gemini_embedder_retries_after_rate_limit(httpx_mock):
    httpx_mock.add_response(status_code=429)
    httpx_mock.add_response(json={"embeddings": [{"values": [0.3]}]})
    with patch("app.rag.embedder.asyncio.sleep", new=AsyncMock()) as sleep:
        assert await GeminiEmbedder("k", "models/m", 768).embed("q") == [0.3]
    sleep.assert_awaited_once()


async def test_llm_probe_surfaces_402_that_models_endpoint_hides(httpx_mock):
    httpx_mock.add_response(url="https://llm.test/chat/completions", status_code=402)
    assert await readiness._probe_llm("https://llm.test", "k", "m") == "http_402"
    assert b'"max_tokens":1' in httpx_mock.get_requests()[0].content.replace(b" ", b"")


async def test_llm_probe_reports_connection_error(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("refused"))
    assert (await readiness._probe_llm("https://llm.test", "k", "m")).startswith("error:")


@pytest.mark.parametrize("kimchi,gemini,expected", [
    ("k", "g", ["llm", "llm_fallback"]),
    ("k", "", ["llm"]),
    ("", "g", ["llm"]),
    ("", "", []),
])
def test_llm_targets(kimchi, gemini, expected):
    s = MagicMock(kimchi_api_key=kimchi, gemini_api_key=gemini)
    assert [t[0] for t in readiness._llm_targets(s)] == expected


def test_llm_target_order_puts_gemini_first():
    s = MagicMock(kimchi_api_key="k", gemini_api_key="g", gemini_model="gem", llm_model="kim")
    assert [t[3] for t in readiness._llm_targets(s)] == ["gem", "kim"]


def test_technique_check_flags_wrong_name_from_g18():
    out = validate_techniques('- T1021.006 "Command and Scripting Interpreter"', NAMES)
    assert "Windows Remote Management" in out and "Command and Scripting Interpreter" in out


def test_technique_check_flags_name_before_the_id():
    assert "Windows Remote Management" in validate_techniques("Command and Scripting Interpreter (T1021.006)", NAMES)


def test_technique_check_flags_unknown_id():
    assert "`T9999`" in validate_techniques("See T9999 for details.", NAMES)


@pytest.mark.parametrize("line", [
    "T1059.001 PowerShell",
    "T1059.001 Command and Scripting Interpreter: PowerShell",
    "T1021.006 (Remote Services)",
    "Observed T1059.001 in the logs.",
    "T1059 used with PowerShell",
    "T1059.001 moved laterally over Windows Remote Management",
    "Technique T1059 PowerShell",
])
def test_technique_check_accepts_valid_citations(line):
    assert validate_techniques(line, NAMES) == ""


def test_technique_check_skipped_without_corpus():
    assert validate_techniques("T9999", {}) == ""


async def test_technique_notes_never_fail_the_report():
    report = InvestigationReport(ioc="x", ioc_type="cve", final_report="T1059")
    with patch.object(svc, "get_store", return_value=MagicMock(technique_names=AsyncMock(side_effect=OSError))):
        assert await svc._technique_notes(report) == ""
