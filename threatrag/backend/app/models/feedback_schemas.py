"""Contracts for analyst feedback on chat answers and investigation reports."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Target = Literal["answer", "report"]


class FeedbackRequest(BaseModel):
    target: Target
    target_id: str = Field(..., min_length=1, max_length=200, description="Report ID, or '<session id>:<turn>' for an answer")
    rating: Literal[-1, 1]
    note: str = Field(default="", max_length=2000)
    question: str = Field(default="", max_length=2000, description="What was asked (answers) or the IOC (reports)")
    answer: str = Field(default="", max_length=20000, description="The answer or report text being rated")

    model_config = ConfigDict(json_schema_extra={"example": {
        "target": "answer", "target_id": "b3f1c2d4:1", "rating": -1,
        "note": "Missed that APT29 also uses this technique",
        "question": "Which groups use T1558.003?", "answer": "T1558.003 (Kerberoasting) is used by...",
    }})


class FeedbackRecord(BaseModel):
    id: str
    target: Target
    target_id: str
    rating: int
    note: str
    question: str
    created_at: str


class TargetCounts(BaseModel):
    up: int = 0
    down: int = 0


class FeedbackSummary(BaseModel):
    answer: TargetCounts = TargetCounts()
    report: TargetCounts = TargetCounts()
    recent_down: list[FeedbackRecord] = []
