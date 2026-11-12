"""Score the injection guard on eval/injection_suite.jsonl.

    python -m app.scripts.run_guard_eval            # heuristic only (offline)
    GUARD_MODE=llm python -m app.scripts.run_guard_eval   # judge model reviews borderline input

`dev` rows were used while writing the rules; `holdout` rows were written afterwards and are the
honest number.
"""
import asyncio
import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.guard import guard

SUITE = Path("eval/injection_suite.jsonl")


def load_suite(path: Path = SUITE) -> list[dict[str, str]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def summarise(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for split in sorted({r["split"] for r in rows}):
        attacks = [r for r in rows if r["split"] == split and r["label"] == "attack"]
        benign = [r for r in rows if r["split"] == split and r["label"] == "benign"]
        out[split] = {
            "attacks": len(attacks), "benign": len(benign),
            "block_rate": sum(r["blocked"] for r in attacks) / len(attacks) if attacks else 0.0,
            "false_positive_rate": sum(r["blocked"] for r in benign) / len(benign) if benign else 0.0,
        }
    return out


async def main() -> None:
    mode = get_settings().guard_mode
    rows: list[dict[str, Any]] = []
    for item in load_suite():
        verdict = await guard.check(item["text"])
        rows.append({**item, "blocked": verdict.blocked, "score": verdict.score, "decided_by": verdict.decided_by})
    summary = summarise(rows)
    print(f"## Injection guard — mode: {mode}\n\n| Split | attacks | benign | block rate | false-positive rate |\n|---|---|---|---|---|")
    for split, s in summary.items():
        print(f"| {split} | {s['attacks']} | {s['benign']} | {s['block_rate']:.2f} | {s['false_positive_rate']:.2f} |")
    wrong = [r for r in rows if r["blocked"] != (r["label"] == "attack")]
    for r in wrong:
        print(f"- {'missed' if r['label'] == 'attack' else 'false positive'} [{r['id']}] {r['text'][:90]!r}")
    out = Path("eval/results") / f"guard-{mode}.json"
    out.write_text(json.dumps({"mode": mode, "summary": summary, "rows": rows}, indent=1))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
