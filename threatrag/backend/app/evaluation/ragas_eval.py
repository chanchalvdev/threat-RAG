from pydantic import BaseModel

from app.core.logging import get_logger

log = get_logger(__name__)


class RagasScores(BaseModel):
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float | None = None
    overall: float


async def evaluate_response(
    question: str,
    answer: str,
    contexts: list[str],
    ground_truth: str | None = None,
) -> RagasScores:
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, context_precision, faithfulness

        data: dict = {
            "question": [question],
            "answer": [answer],
            "contexts": [contexts],
        }
        metrics = [faithfulness, answer_relevancy, context_precision]

        if ground_truth is not None:
            from ragas.metrics import context_recall
            data["ground_truth"] = [ground_truth]
            metrics.append(context_recall)

        dataset = Dataset.from_dict(data)
        result = evaluate(dataset, metrics=metrics)
        scores = result.to_pandas().iloc[0]

        recall = float(scores.get("context_recall", 0.0)) if ground_truth else None
        weights = [0.3, 0.3, 0.2, 0.2] if recall is not None else [0.35, 0.35, 0.3]
        vals = [
            float(scores.get("faithfulness", 0.0)),
            float(scores.get("answer_relevancy", 0.0)),
            float(scores.get("context_precision", 0.0)),
        ]
        if recall is not None:
            vals.append(recall)
        overall = sum(v * w for v, w in zip(vals, weights))

        return RagasScores(
            faithfulness=vals[0],
            answer_relevancy=vals[1],
            context_precision=vals[2],
            context_recall=recall,
            overall=round(overall, 4),
        )
    except Exception as exc:
        log.error("ragas_eval_failed", error=str(exc))
        return RagasScores(faithfulness=0.0, answer_relevancy=0.0, context_precision=0.0, overall=0.0)
