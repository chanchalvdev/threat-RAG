"""Offline evaluation over the golden set: retrieval metrics, then optional answer metrics."""
import asyncio
import re
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel

from app.evaluation import judge
from app.evaluation.golden import GoldenItem
from app.evaluation.retrieval_metrics import Retrieved, first_relevant_rank, hit_at_k, mean, mrr

RetrieveFn = Callable[[str, int], Awaitable[list[Retrieved]]]
AnswerFn = Callable[[str], Awaitable["Answer"]]
_REFUSAL = re.compile(
    r"(does not|doesn't|do not|don't) (contain|provide|include|have)|not enough information|"
    r"cannot answer|can't answer|unable to answer|no (relevant )?information|outside (the|my) (scope|knowledge)",
    re.IGNORECASE,
)
_TECHNIQUE = re.compile(r"\bT\d{4}(?:\.\d{3})?\b")


class Answer(BaseModel):
    text: str
    contexts: list[str] = []
    abstained: bool = False  # the pipeline declined before generating


def looks_like_refusal(answer: Answer) -> bool:
    """Declined at retrieval, or the model itself said the context does not cover the question."""
    return answer.abstained or bool(_REFUSAL.search(answer.text[:600]))


async def _retry(call: Callable[[], Awaitable[Any]], attempts: int = 4, base_delay_s: float = 5.0) -> Any:
    """Providers shed load with 429/503; one busy minute must not void a whole evaluation run."""
    for attempt in range(attempts):
        try:
            return await call()
        except Exception:
            if attempt == attempts - 1:
                raise
            await asyncio.sleep(base_delay_s * 2**attempt)


def _summary(rows: list[dict[str, Any]], k: int) -> dict[str, float]:
    ranks = [r["rank"] for r in rows]
    return {"n": len(rows), "hit@1": hit_at_k(ranks, 1), "hit@3": hit_at_k(ranks, 3), f"hit@{k}": hit_at_k(ranks, k), "mrr": mrr(ranks)}


async def evaluate_retrieval(items: list[GoldenItem], retrieve: RetrieveFn, k: int) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for item in items:
        hits = await retrieve(item.question, k)
        rows.append({
            "id": item.id, "category": item.category, "answerable": item.answerable,
            "rank": first_relevant_rank(item, hits) if item.answerable else None,
            "top_score": hits[0].score if hits else 0.0,
            "retrieved": [h.technique_id or h.doc_type for h in hits],
        })
    answerable = [r for r in rows if r["answerable"]]
    by_category = {
        cat: _summary([r for r in answerable if r["category"] == cat], k)
        for cat in sorted({r["category"] for r in answerable})
    }
    return {
        "k": k,
        "overall": _summary(answerable, k),
        "by_category": by_category,
        "top_score": {
            "answerable": mean(r["top_score"] for r in answerable),
            "unanswerable": mean(r["top_score"] for r in rows if not r["answerable"]),
        },
        "rows": rows,
    }


async def evaluate_answers(items: list[GoldenItem], answer: AnswerFn, delay_s: float = 0.0) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for item in items:
        result = await _retry(lambda item=item: answer(item.question))  # type: ignore[misc]
        refused = looks_like_refusal(result)
        row: dict[str, Any] = {"id": item.id, "category": item.category, "answerable": item.answerable, "refused": refused}
        if item.answerable and not refused:
            row["cited"] = "[Source:" in result.text
            if item.expected_ids:
                row["id_correct"] = bool(set(_TECHNIQUE.findall(result.text)) & set(item.expected_ids))
            if result.contexts:
                row["faithfulness"] = await _retry(lambda r=result: judge.faithfulness(r.text, r.contexts))  # type: ignore[misc]
        rows.append(row)
        if delay_s:
            await asyncio.sleep(delay_s)
    answered = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    return {
        "n": len(rows),
        "faithfulness": mean(r["faithfulness"] for r in answered if "faithfulness" in r),
        "citation_rate": mean(float(r["cited"]) for r in answered if "cited" in r),
        "technique_id_accuracy": mean(float(r["id_correct"]) for r in answered if "id_correct" in r),
        "correct_abstention": mean(float(r["refused"]) for r in unanswerable),
        "false_abstention": mean(float(r["refused"]) for r in answered),
        "rows": rows,
    }
