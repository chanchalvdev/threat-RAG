"""Request and response contracts for the /chat routes."""
from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=4000)
    session_id: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "What CVEs affect Apache Log4j?",
                "session_id": None,
            }
        }
    )


class SuggestionRequest(BaseModel):
    last_question: str
    last_answer: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "last_question": "What CVEs affect Apache Log4j?",
                "last_answer": "CVE-2021-44228 (Log4Shell) is a critical RCE in Apache Log4j 2.",
            }
        }
    )


class ChatHistoryMessage(BaseModel):
    role: str
    content: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"role": "user", "content": "What CVEs affect Apache Log4j?"}}
    )


class ChatStatusResponse(BaseModel):
    status: str

    model_config = ConfigDict(json_schema_extra={"example": {"status": "cleared"}})


class SuggestionsResponse(BaseModel):
    suggestions: list[str]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "suggestions": [
                    "What versions of Log4j are affected by CVE-2021-44228?",
                    "How does Log4Shell map to MITRE ATT&CK techniques?",
                    "What mitigations are recommended for Log4Shell?",
                ]
            }
        }
    )
