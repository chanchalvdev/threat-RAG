"""In-process telemetry: request latency per route, LLM tokens and cost, named counters.

Per-process by design (cheap, no dependency). For fleet-wide numbers, set the Langfuse keys:
every LLM call is then traced there as well.
"""
import time
from collections import defaultdict, deque
from typing import Any
from uuid import UUID

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult

from app.core.config import get_settings

_WINDOW = 500  # most recent samples kept per series


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(pct / 100 * (len(ordered) - 1)))]


class Telemetry:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._latency: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=_WINDOW))
        self._requests: dict[str, int] = defaultdict(int)
        self._errors: dict[str, int] = defaultdict(int)
        self._counters: dict[str, int] = defaultdict(int)
        self._llm: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._llm_latency: deque[float] = deque(maxlen=_WINDOW)

    def record_request(self, route: str, status: int, seconds: float) -> None:
        self._requests[route] += 1
        self._errors[route] += status >= 500
        self._latency[route].append(seconds * 1000)

    def record_llm(self, model: str, tokens_in: int, tokens_out: int, seconds: float) -> None:
        row = self._llm[model]
        row["calls"] += 1
        row["tokens_in"] += tokens_in
        row["tokens_out"] += tokens_out
        self._llm_latency.append(seconds * 1000)

    def count(self, name: str, by: int = 1) -> None:
        self._counters[name] += by

    def snapshot(self) -> dict[str, Any]:
        s = get_settings()
        routes = {
            route: {"requests": self._requests[route], "errors_5xx": self._errors[route],
                    "p50_ms": round(percentile(list(samples), 50), 1), "p95_ms": round(percentile(list(samples), 95), 1)}
            for route, samples in sorted(self._latency.items())
        }
        tokens_in = sum(r["tokens_in"] for r in self._llm.values())
        tokens_out = sum(r["tokens_out"] for r in self._llm.values())
        priced = s.llm_price_in_per_mtok > 0 or s.llm_price_out_per_mtok > 0
        cost = (tokens_in * s.llm_price_in_per_mtok + tokens_out * s.llm_price_out_per_mtok) / 1_000_000
        return {
            "routes": routes,
            "llm": {
                "calls": int(sum(r["calls"] for r in self._llm.values())),
                "tokens_in": int(tokens_in), "tokens_out": int(tokens_out),
                "p50_ms": round(percentile(list(self._llm_latency), 50), 1),
                "p95_ms": round(percentile(list(self._llm_latency), 95), 1),
                "estimated_cost_usd": round(cost, 6) if priced else None,  # None: no price configured
                "by_model": {m: {k: int(v) for k, v in row.items()} for m, row in self._llm.items()},
            },
            "counters": dict(self._counters),
        }


telemetry = Telemetry()


class UsageCallback(AsyncCallbackHandler):
    """Feeds every chat-model call into `telemetry` (tokens and wall time)."""

    def __init__(self) -> None:
        self._started: dict[UUID, tuple[float, str]] = {}

    async def on_chat_model_start(self, serialized: Any, messages: Any, *, run_id: UUID, **kwargs: Any) -> None:
        model = str((kwargs.get("metadata") or {}).get("ls_model_name") or "unknown")
        self._started[run_id] = (time.perf_counter(), model)

    async def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: Any) -> None:
        started, requested = self._started.pop(run_id, (time.perf_counter(), "unknown"))
        seconds = time.perf_counter() - started
        message = getattr(response.generations[0][0], "message", None) if response.generations and response.generations[0] else None
        usage = getattr(message, "usage_metadata", None) or {}
        meta = getattr(message, "response_metadata", None) or {}
        model = str(meta.get("model_name") or (response.llm_output or {}).get("model_name") or requested)
        telemetry.record_llm(model, int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0)), seconds)

    async def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        self._started.pop(run_id, None)
        telemetry.count("llm_errors")
