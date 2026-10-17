from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field

from app.core.logging import get_logger
from app.db.connection import get_pool, is_db_ready
from app.db.evaluations import EvaluationRecord, list_evaluations, save_evaluation
from app.evaluation.ragas_eval import RagasScores, evaluate_response

log = get_logger(__name__)
router = APIRouter(prefix="/evaluate", tags=["evaluate"])


class EvaluateRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    answer: str = Field(..., min_length=1, max_length=20000)
    contexts: list[str] = Field(..., min_length=1, max_length=20)
    ground_truth: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "What is T1110?",
                "answer": "T1110 is Brute Force, a MITRE ATT&CK technique for guessing credentials.",
                "contexts": [
                    "T1110 Brute Force: Adversaries may use brute force techniques to gain "
                    "access to accounts when passwords are unknown or when password hashes are obtained."
                ],
                "ground_truth": "T1110 Brute Force is a credential access technique.",
            }
        }
    )


@router.post(
    "",
    response_model=RagasScores,
    summary="Score a RAG answer with RAGAs metrics",
    description="Computes faithfulness, answer relevancy, context precision (and context recall "
    "if ground_truth is supplied), plus a weighted overall score. Persisted for /evaluate/history.",
)
async def evaluate(req: EvaluateRequest) -> RagasScores:
    scores = await evaluate_response(
        question=req.question,
        answer=req.answer,
        contexts=req.contexts,
        ground_truth=req.ground_truth,
    )
    if is_db_ready() and scores.overall > 0:
        try:
            async with get_pool().connection() as conn:
                await save_evaluation(req.question, req.answer, scores, conn)
        except Exception as exc:
            log.warning("evaluation_persist_failed", error=str(exc))
    return scores


@router.get(
    "/history",
    response_model=list[EvaluationRecord],
    summary="Recent evaluation scores, oldest first (for trend charts)",
)
async def history(limit: int = Query(default=50, ge=1, le=500)) -> list[EvaluationRecord]:
    if not is_db_ready():
        return []
    async with get_pool().connection() as conn:
        return await list_evaluations(limit, conn)
