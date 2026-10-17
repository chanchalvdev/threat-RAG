"""State, request/response contracts for the Researcher → Critic → Reporter graph."""
import ipaddress
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import TypedDict

from app.evaluation.ragas_eval import RagasScores
from app.models.schemas import SourceDoc

IOCType = Literal["ip", "hash", "domain", "cve", "technique"]
NodeStatus = Literal["researching", "critiquing", "reporting", "done", "error"]

_IOC_PATTERNS: dict[str, re.Pattern[str]] = {
    "cve": re.compile(r"^CVE-\d{4}-\d{4,}$"),
    "technique": re.compile(r"^T\d{4}(\.\d{3})?$"),
    "hash": re.compile(r"^([a-f0-9]{32}|[a-f0-9]{40}|[a-f0-9]{64})$"),
    "domain": re.compile(r"^(?=.{1,253}$)([a-z0-9-]{1,63}\.)+[a-z]{2,63}$"),
}


class ToolCallRecord(TypedDict):
    name: str
    input: str
    output: str


class InvestigationState(TypedDict, total=False):
    ioc: str
    ioc_type: IOCType
    researcher_output: str
    critic_feedback: str
    final_report: str
    sources: list[SourceDoc]
    tool_calls: list[ToolCallRecord]
    iteration: int
    status: NodeStatus


class InvestigationRequest(BaseModel):
    ioc: str = Field(..., min_length=3, max_length=256)
    ioc_type: IOCType
    session_id: str | None = None

    model_config = ConfigDict(
        json_schema_extra={"example": {"ioc": "CVE-2021-44228", "ioc_type": "cve", "session_id": None}}
    )

    @model_validator(mode="after")
    def _validate_ioc(self) -> "InvestigationRequest":
        value = self.ioc.strip()
        value = value.upper() if self.ioc_type in ("cve", "technique") else value.lower()
        if self.ioc_type == "ip":
            ipaddress.ip_address(value)  # raises ValueError → 422
        elif not _IOC_PATTERNS[self.ioc_type].match(value):
            raise ValueError(f"'{self.ioc}' is not a valid {self.ioc_type} indicator")
        self.ioc = value
        return self


class InvestigationReport(BaseModel):
    ioc: str
    ioc_type: str
    final_report: str
    sources: list[SourceDoc] = []
    tool_calls: list[ToolCallRecord] = []
    critic_feedback: str = ""
    iterations: int = 1
    ragas_scores: RagasScores | None = None
    report_id: str | None = None
    created_at: str | None = None


class ReportSummary(BaseModel):
    id: str
    ioc: str
    ioc_type: str
    summary: str
    created_at: str
    similarity: float | None = None
