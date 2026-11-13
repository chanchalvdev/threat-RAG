"""Render evaluation results as a Markdown table (for the README and CI logs)."""
from typing import Any


def _pct(value: float) -> str:
    return f"{value:.2f}"


def retrieval_table(result: dict[str, Any]) -> str:
    k = result["k"]
    cols = ["hit@1", "hit@3", f"hit@{k}", "mrr"]
    lines = [f"| Category | n | {' | '.join(cols)} |", f"|---|---|{'---|' * len(cols)}"]
    for name, row in [*result["by_category"].items(), ("**overall**", result["overall"])]:
        lines.append(f"| {name} | {row['n']} | {' | '.join(_pct(row[c]) for c in cols)} |")
    scores = result["top_score"]
    lines.append(f"\nMean top score: answerable {scores['answerable']:.3f}, unanswerable {scores['unanswerable']:.3f}")
    return "\n".join(lines)


def answer_table(result: dict[str, Any]) -> str:
    keys = ["faithfulness", "citation_rate", "technique_id_accuracy", "correct_abstention", "false_abstention"]
    lines = [f"| n | {' | '.join(keys)} |", f"|---|{'---|' * len(keys)}"]
    lines.append(f"| {result['n']} | {' | '.join(_pct(result[key]) for key in keys)} |")
    return "\n".join(lines)
