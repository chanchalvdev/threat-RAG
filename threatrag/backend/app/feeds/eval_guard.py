"""After an ATT&CK re-index, the retrieval eval decides whether the refresh made retrieval worse."""
from pathlib import Path
from typing import Any

from app.api.deps import get_store
from app.core.state import get_state
from app.evaluation.golden import DEFAULT_PATH, load_golden, unknown_ids
from app.evaluation.harness import evaluate_retrieval
from app.scripts.run_eval import retrieve

LAST_KEY = "feeds:eval:hit"
MAX_DROP = 0.03
K = 6


async def ensure_baseline(golden: Path = DEFAULT_PATH) -> dict[str, Any] | None:
    """Before the first ATT&CK refresh, score the current index, so the first re-index is compared
    with something instead of becoming the baseline unchecked. None when a baseline exists."""
    if await get_state().get(LAST_KEY) is not None:
        return None
    hit, _ = await _hit(golden)
    await get_state().set(LAST_KEY, str(hit))
    return {f"hit@{K}": hit}


async def _hit(golden: Path) -> tuple[float, list[str]]:
    """hit@6 over the golden set, leaving out (and returning) questions about techniques the
    current index does not have, so a retired technique is not mistaken for a retrieval loss."""
    items = load_golden(golden)
    stale = unknown_ids(items, set(await get_store().technique_names()))
    items = [i for i in items if not set(i.expected_ids) & set(stale)]
    hit = (await evaluate_retrieval(items, retrieve, K))["overall"][f"hit@{K}"] if items else 0.0
    return round(hit, 4), stale


async def check(golden: Path = DEFAULT_PATH) -> dict[str, Any]:
    """hit@6 against the last accepted run. A regression does not replace the baseline, so the next
    refresh is still compared with the last good index."""
    hit, stale = await _hit(golden)
    previous = await get_state().get(LAST_KEY)
    regressed = previous is not None and float(previous) - hit > MAX_DROP
    if not regressed:
        await get_state().set(LAST_KEY, str(hit))
    return {f"hit@{K}": hit, "previous": float(previous) if previous else None, "regressed": regressed,
            "retired_golden_ids": stale}
