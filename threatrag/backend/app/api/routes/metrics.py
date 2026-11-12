from typing import Any

from fastapi import APIRouter

from app.core.telemetry import telemetry

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get(
    "",
    summary="Runtime telemetry for this API process",
    description="Per-route request counts and latency (p50/p95 over the last 500 requests; for SSE "
    "routes this is time to first byte), LLM calls, tokens and estimated cost (null until "
    "LLM_PRICE_IN_PER_MTOK / LLM_PRICE_OUT_PER_MTOK are set), and guard/abstention counters. "
    "Counters reset when the process restarts.",
)
async def metrics() -> dict[str, Any]:
    return telemetry.snapshot()
