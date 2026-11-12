"""Telemetry registry, the LLM usage callback, tracing setup and the /metrics route."""
import os
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

os.environ.setdefault("KIMCHI_API_KEY", "test-key-for-unit-tests")

from app.core import telemetry as tel  # noqa: E402
from app.core import tracing  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def registry():
    tel.telemetry.reset()
    yield tel.telemetry
    tel.telemetry.reset()


def test_percentile():
    assert tel.percentile([], 95) == 0.0
    assert tel.percentile([10, 20, 30, 40, 50], 50) == 30
    assert tel.percentile(list(range(1, 101)), 95) == 95


def test_snapshot_reports_latency_errors_tokens_and_unknown_cost(registry):
    for ms in (100, 200, 300):
        registry.record_request("POST /api/v1/query", 200, ms / 1000)
    registry.record_request("POST /api/v1/query", 500, 0.4)
    registry.record_llm("gemini", 1000, 200, 1.5)
    registry.count("guard_blocked")
    snap = registry.snapshot()
    route = snap["routes"]["POST /api/v1/query"]
    assert (route["requests"], route["errors_5xx"], route["p50_ms"], route["p95_ms"]) == (4, 1, 300.0, 400.0)
    assert snap["llm"]["calls"] == 1 and snap["llm"]["tokens_in"] == 1000 and snap["llm"]["tokens_out"] == 200
    assert snap["llm"]["estimated_cost_usd"] is None and snap["counters"] == {"guard_blocked": 1}


def test_cost_uses_configured_prices(registry):
    registry.record_llm("gemini", 1_000_000, 500_000, 1.0)
    priced = Settings(_env_file=None, llm_price_in_per_mtok=0.1, llm_price_out_per_mtok=0.4)
    with patch.object(tel, "get_settings", return_value=priced):
        assert registry.snapshot()["llm"]["estimated_cost_usd"] == pytest.approx(0.3)


async def test_usage_callback_records_tokens_and_errors(registry):
    callback, run_id = tel.UsageCallback(), uuid4()
    message = AIMessage(content="hi", usage_metadata={"input_tokens": 12, "output_tokens": 3, "total_tokens": 15},
                        response_metadata={"model_name": "gemini-x"})
    await callback.on_chat_model_start({}, [], run_id=run_id)
    await callback.on_llm_end(LLMResult(generations=[[ChatGeneration(message=message)]]), run_id=run_id)
    await callback.on_llm_error(RuntimeError("x"), run_id=uuid4())
    snap = registry.snapshot()
    assert snap["llm"]["by_model"]["gemini-x"] == {"calls": 1, "tokens_in": 12, "tokens_out": 3}
    assert snap["counters"]["llm_errors"] == 1


def test_tracing_adds_langfuse_only_when_keys_are_set():
    tracing.llm_callbacks.cache_clear()
    with patch.object(tracing, "get_settings", return_value=Settings(_env_file=None)):
        assert [type(c).__name__ for c in tracing.llm_callbacks()] == ["UsageCallback"]
    tracing.llm_callbacks.cache_clear()
    keyed = Settings(_env_file=None, langfuse_public_key="pk", langfuse_secret_key="sk")
    with patch.object(tracing, "get_settings", return_value=keyed), \
            patch("langfuse.Langfuse") as client, patch("langfuse.langchain.CallbackHandler", return_value=MagicMock()):
        assert len(tracing.llm_callbacks()) == 2
        client.assert_called_once()
    tracing.llm_callbacks.cache_clear()
    with patch.object(tracing, "get_settings", return_value=keyed), patch("langfuse.Langfuse", side_effect=RuntimeError("no net")):
        assert len(tracing.llm_callbacks()) == 1  # tracing is optional
    tracing.llm_callbacks.cache_clear()


async def test_metrics_route_reports_requests_by_route_template(registry):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/health")
        body = (await client.get("/api/v1/metrics")).json()
    assert body["routes"]["GET /health"]["requests"] == 1
    assert set(body) == {"routes", "llm", "counters"}
