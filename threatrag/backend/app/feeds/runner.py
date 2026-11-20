"""One refresh run: lock, each feed in isolation, the eval guard after an ATT&CK change, a record."""
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from app.api.deps import get_store
from app.core.logging import get_logger
from app.core.state import get_state
from app.feeds import eval_guard, kev, mitre_release, taxii
from app.rag.embedder import get_embedder

log = get_logger(__name__)
LOCK_KEY, LAST_KEY = "feeds:lock", "feeds:last_run"
LOCK_TTL_S = 3 * 3600  # an ATT&CK re-index on CPU embeddings takes minutes, not hours


class FeedStatus(BaseModel):
    at: str | None = None
    ok: bool | None = None
    regressed: bool = False
    steps: dict[str, Any] = {}


async def _step(name: str, steps: dict[str, Any], work: Any) -> Any:
    """One failing feed is recorded and never stops the others."""
    try:
        steps[name] = await work
    except Exception as exc:
        log.error("feed_failed", feed=name, error=str(exc))
        steps[name] = {"error": f"{type(exc).__name__}: {exc}"[:300]}
    return steps[name]


async def _count(work: Any) -> dict[str, int]:
    return {"items": await work}


async def run_once(force_mitre: bool = False) -> FeedStatus | None:
    """None when another run holds the lock (two schedulers, or a run that is still going)."""
    state = get_state()
    if await state.incr(LOCK_KEY, ttl_s=LOCK_TTL_S) != 1:
        log.warning("feeds_locked")
        return None
    try:
        store, embedder = get_store(), get_embedder()
        steps: dict[str, Any] = {}
        await store.ensure_collection()
        if await _step("baseline", steps, eval_guard.ensure_baseline()) is None:
            steps.pop("baseline")  # one already exists; nothing to report
        mitre = await _step("mitre", steps, mitre_release.refresh(store, embedder, force=force_mitre))
        await _step("kev", steps, _count(kev.refresh()))
        await _step("taxii", steps, taxii.pull(store, embedder))
        if isinstance(mitre, dict) and mitre.get("changed"):
            await _step("eval", steps, eval_guard.check())
        status = FeedStatus(
            at=datetime.now(UTC).isoformat(timespec="seconds"),
            ok=not any(isinstance(v, dict) and "error" in v for v in steps.values()),
            regressed=bool(steps.get("eval", {}).get("regressed")), steps=steps,
        )
        await state.set(LAST_KEY, status.model_dump_json())
        log.info("feeds_refreshed", ok=status.ok, regressed=status.regressed)
        return status
    finally:
        await state.delete(LOCK_KEY)


async def last_run() -> FeedStatus:
    raw = await get_state().get(LAST_KEY)
    return FeedStatus(**json.loads(raw)) if raw else FeedStatus()
