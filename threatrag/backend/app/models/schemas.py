from typing import Literal

from pydantic import BaseModel, Field


class SourceDoc(BaseModel):
    text: str
    source: str
    doc_type: str
    score: float


class RAGResponse(BaseModel):
    answer: str
    sources: list[SourceDoc]
    tokens_used: int = 0
    confidence: Literal["high", "medium", "low"] = "high"


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=10, max_length=2000)
    doc_types: list[str] | None = None
    k: int = Field(default=6, ge=1, le=20)


class IngestJob(BaseModel):
    job_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    chunks_processed: int = 0
    total_chunks: int = 0
    error: str | None = None


class IngestAccepted(BaseModel):
    status: str = "accepted"
    job_id: str
    filename: str = ""


class IngestStats(BaseModel):
    collection: str
    total_vectors: int
    doc_type_counts: dict[str, int]


class HealthCheck(BaseModel):
    status: str


class ReadinessCheck(BaseModel):
    status: str
    checks: dict[str, str]
