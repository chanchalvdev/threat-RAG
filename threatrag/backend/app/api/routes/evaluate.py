from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.evaluation.ragas_eval import RagasScores, evaluate_response

router = APIRouter(prefix="/evaluate", tags=["evaluate"])


class EvaluateRequest(BaseModel):
    question: str
    answer: str
    contexts: list[str]
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
    "if ground_truth is supplied), plus a weighted overall score.",
)
async def evaluate(req: EvaluateRequest) -> RagasScores:
    return await evaluate_response(
        question=req.question,
        answer=req.answer,
        contexts=req.contexts,
        ground_truth=req.ground_truth,
    )
