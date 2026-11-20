"""The model providers ThreatRAG can call, and the order it tries them in.

Every provider speaks the OpenAI chat protocol, so each is just (model, key, base URL).
`LLM_ORDER` lists them by name; a provider without a key is skipped, and the first one with a
key is the primary. The rest form the fallback chain in that order.
"""
from typing import NamedTuple

from app.core.config import Settings

KNOWN = ("openrouter", "groq", "cerebras", "gemini", "kimchi")


class Provider(NamedTuple):
    model: str
    key: str
    base_url: str
    name: str = ""


def _table(s: Settings) -> dict[str, Provider]:
    return {
        "openrouter": Provider(s.openrouter_model, s.openrouter_api_key, s.openrouter_base_url, "openrouter"),
        "groq": Provider(s.groq_model, s.groq_api_key, s.groq_base_url, "groq"),
        "cerebras": Provider(s.cerebras_model, s.cerebras_api_key, s.cerebras_base_url, "cerebras"),
        "gemini": Provider(s.gemini_model, s.gemini_api_key, s.gemini_base_url, "gemini"),
        "kimchi": Provider(s.llm_model, s.kimchi_api_key, s.kimchi_base_url, "kimchi"),
    }


def order(s: Settings) -> list[str]:
    names = [n.strip().lower() for n in s.llm_order.split(",") if n.strip()]
    unknown = [n for n in names if n not in KNOWN]
    if unknown:
        raise ValueError(f"LLM_ORDER names unknown provider(s) {unknown}; known: {', '.join(KNOWN)}")
    return list(dict.fromkeys(names))


def providers(s: Settings) -> list[Provider]:
    """Configured providers (those with a key) in priority order."""
    table = _table(s)
    return [table[n] for n in order(s) if table[n].key]


def by_name(s: Settings, name: str) -> Provider | None:
    return _table(s).get(name.strip().lower())
