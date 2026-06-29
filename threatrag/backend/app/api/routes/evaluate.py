from fastapi import APIRouter
from pydantic import BaseModel

from app.evaluation.ragas_eval import RagasScores, evaluate_response

router = APIRouter(prefix="/evaluate", tags=["evaluate"])


class EvaluateRequest(BaseModel):
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str | None = None


@router.post("", response_model=RagasScores)
async def evaluate(req: EvaluateRequest) -> RagasScores:
    return await evaluate_response(
        question=req.question,
        answer=req.answer,
        contexts=req.contexts,
        ground_truth=req.ground_truth,
    )
