"""Single construction point for the Kimchi (OpenAI-compatible) chat model."""
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.core.config import get_settings


def get_llm(streaming: bool = False, temperature: float = 0.1) -> ChatOpenAI:
    s = get_settings()
    return ChatOpenAI(
        model=s.llm_model,
        api_key=SecretStr(s.kimchi_api_key or "not-set"),
        base_url=s.kimchi_base_url,
        temperature=temperature,
        streaming=streaming,
        timeout=s.llm_timeout_s,
        max_completion_tokens=s.llm_max_tokens,
        max_retries=2,
    )
