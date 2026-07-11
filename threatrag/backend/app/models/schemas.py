from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


_SOURCE_DOC_EXAMPLE: dict[str, Any] = {
    "text": "T1110.001 Password Guessing: Adversaries may use a single or small "
    "list of commonly used passwords against many different accounts...",
    "source": "mitre_attack.json#T1110.001",
    "doc_type": "mitre_attack",
    "score": 0.87,
}


class SourceDoc(BaseModel):
    text: str
    source: str
    doc_type: str
    score: float

    model_config = ConfigDict(json_schema_extra={"example": _SOURCE_DOC_EXAMPLE})


class RAGResponse(BaseModel):
    answer: str
    sources: list[SourceDoc]
    tokens_used: int = 0
    confidence: Literal["high", "medium", "low"] = "high"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "answer": "T1110.001 Password Guessing is a MITRE ATT&CK sub-technique where "
                "adversaries try commonly used passwords against many accounts to gain access "
                "while evading account lockout policies.",
                "sources": [_SOURCE_DOC_EXAMPLE],
                "tokens_used": 342,
                "confidence": "high",
            }
        }
    )


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=10, max_length=2000)
    doc_types: list[str] | None = None
    k: int = Field(default=6, ge=1, le=20)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "What is T1110.001 Password Guessing?",
                "doc_types": ["mitre_attack"],
                "k": 6,
            }
        }
    )


class IngestJob(BaseModel):
    job_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    chunks_processed: int = 0
    total_chunks: int = 0
    error: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "3f1a9e2c-6b7d-4e5a-9c1b-2d8f7a6e4b3c",
                "status": "completed",
                "chunks_processed": 812,
                "total_chunks": 812,
                "error": None,
            }
        }
    )


class IngestAccepted(BaseModel):
    status: str = "accepted"
    job_id: str
    filename: str = ""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "accepted",
                "job_id": "3f1a9e2c-6b7d-4e5a-9c1b-2d8f7a6e4b3c",
                "filename": "owasp_llm_top10.pdf",
            }
        }
    )


class IngestStats(BaseModel):
    collection: str
    total_vectors: int
    doc_type_counts: dict[str, int]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "collection": "threat_intel",
                "total_vectors": 1524,
                "doc_type_counts": {"mitre_attack": 812, "owasp_llm": 210, "custom": 502},
            }
        }
    )


class HealthCheck(BaseModel):
    status: str

    model_config = ConfigDict(json_schema_extra={"example": {"status": "ok"}})


class ReadinessCheck(BaseModel):
    status: str
    checks: dict[str, str]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ready",
                "checks": {"qdrant": "ok", "ollama": "ok", "llm": "ok"},
            }
        }
    )
