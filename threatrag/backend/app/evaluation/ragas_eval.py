import asyncio

from pydantic import BaseModel, ConfigDict

from app.core.logging import get_logger
from app.evaluation import judge

log = get_logger(__name__)


class RagasScores(BaseModel):
    faithfulness: float = 0.0
    answer_relevancy: float = 0.0
    context_precision: float = 0.0
    context_recall: float | None = None
    overall: float = 0.0

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "faithfulness": 0.92,
                "answer_relevancy": 0.88,
                "context_precision": 0.95,
                "context_recall": 0.90,
                "overall": 0.91,
            }
        }
    )


def _overall(vals: list[float], recall: float | None) -> float:
    if recall is not None:
        return sum(v * w for v, w in zip([*vals, recall], [0.3, 0.3, 0.2, 0.2]))
    return sum(v * w for v, w in zip(vals, [0.35, 0.35, 0.3]))


async def evaluate_response(
    question: str,
    answer: str,
    contexts: list[str],
    ground_truth: str | None = None,
) -> RagasScores:
    """Score an answer on RAGAs metrics. Returns zeros (never raises) if the judge fails."""
    try:
        reference = ground_truth or answer
        tasks = [
            judge.faithfulness(answer, contexts),
            judge.answer_relevancy(question, answer),
            judge.context_precision(question, reference, contexts),
        ]
        if ground_truth is not None:
            tasks.append(judge.context_recall(ground_truth, contexts))
        results = await asyncio.gather(*tasks)
        vals = [round(float(v), 4) for v in results[:3]]
        recall = round(float(results[3]), 4) if ground_truth is not None else None
        return RagasScores(
            faithfulness=vals[0],
            answer_relevancy=vals[1],
            context_precision=vals[2],
            context_recall=recall,
            overall=round(_overall(vals, recall), 4),
        )
    except Exception as exc:
        log.error("ragas_eval_failed", error=str(exc))
        return RagasScores()
