"""LLM_ORDER: provider selection, the fallback chain, the judge's provider (no network)."""
from unittest.mock import AsyncMock, patch

import httpx
import openai
import pytest

from app.core import llm as llm_mod
from app.core.config import Settings
from app.core.llm_errors import ModelUnavailable, is_capacity, retry_after, unavailable
from app.core.llm_providers import order, providers


def _s(**kw) -> Settings:
    return Settings(_env_file=None, **kw)


def test_order_skips_unkeyed_providers_and_keeps_priority():
    s = _s(llm_order="openrouter,gemini", openrouter_api_key="o", gemini_api_key="g", kimchi_api_key="k")
    assert [p.name for p in providers(s)] == ["openrouter", "gemini"]  # kimchi not listed: never used


def test_order_rejects_unknown_names_and_drops_duplicates():
    with pytest.raises(ValueError, match="unknown provider"):
        order(_s(llm_order="openrouter,claude"))
    assert order(_s(llm_order=" Groq , groq,gemini ")) == ["groq", "gemini"]


def test_three_keys_make_a_chain_in_order():
    s = _s(llm_order="openrouter,groq,gemini", openrouter_api_key="o", groq_api_key="q", gemini_api_key="g")
    with patch("app.core.llm.get_settings", return_value=s):
        model = llm_mod.get_llm()
    names = []
    while model is not None:
        names.append(model.openai_api_base)
        model = model.fallback
    assert names == [s.openrouter_base_url, s.groq_base_url, s.gemini_base_url]


def test_openrouter_gets_attribution_header_and_others_do_not():
    s = _s(llm_order="openrouter,gemini", openrouter_api_key="o", gemini_api_key="g")
    with patch("app.core.llm.get_settings", return_value=s):
        model = llm_mod.get_llm()
    assert model.default_headers == {"X-Title": "ThreatRAG"}
    assert model.fallback is not None and not model.fallback.default_headers


def test_judge_provider_takes_that_providers_key_and_url():
    s = _s(llm_order="openrouter,gemini", openrouter_api_key="o", gemini_api_key="g",
           judge_model="gemini-3.1-flash-lite", judge_provider="gemini")
    with patch("app.core.llm.get_settings", return_value=s):
        judge = llm_mod.get_judge_llm()
    assert judge.openai_api_base == s.gemini_base_url and judge.openai_api_key.get_secret_value() == "g"


def test_judge_defaults_to_primary_provider():
    s = _s(llm_order="groq,gemini", groq_api_key="q", gemini_api_key="g", judge_model="j")
    with patch("app.core.llm.get_settings", return_value=s):
        assert llm_mod.get_judge_llm().openai_api_base == s.groq_base_url


def _status(code: int) -> openai.APIStatusError:
    req = httpx.Request("POST", "http://x")
    return openai.APIStatusError("busy", response=httpx.Response(code, request=req), body=None)


def test_nested_chain_at_capacity_counts_as_capacity():
    inner = ModelUnavailable(42)
    assert is_capacity(inner) and retry_after(inner) == 42
    assert isinstance(unavailable(_status(429), inner), ModelUnavailable)


async def test_chain_reaches_the_third_provider():
    s = _s(llm_order="openrouter,groq,gemini", openrouter_api_key="o", groq_api_key="q", gemini_api_key="g")
    with patch("app.core.llm.get_settings", return_value=s):
        model = llm_mod.get_llm()
    seen: list[str] = []

    async def fake(self, *a, **k):
        seen.append(self.openai_api_base)
        if len(seen) < 3:
            raise _status(429)
        return "third"

    with patch.object(llm_mod.ChatOpenAI, "_agenerate", new=fake):
        assert await model._agenerate([]) == "third"
    assert seen == [s.openrouter_base_url, s.groq_base_url, s.gemini_base_url]


async def test_all_providers_at_capacity_raise_model_unavailable():
    s = _s(llm_order="openrouter,gemini", openrouter_api_key="o", gemini_api_key="g")
    with patch("app.core.llm.get_settings", return_value=s):
        model = llm_mod.get_llm()
    with patch.object(llm_mod.ChatOpenAI, "_agenerate", new=AsyncMock(side_effect=_status(429))):
        with pytest.raises(ModelUnavailable):
            await model._agenerate([])


def test_only_the_last_provider_retries():
    s = _s(llm_order="groq,openrouter,gemini", groq_api_key="q", openrouter_api_key="o", gemini_api_key="g")
    with patch("app.core.llm.get_settings", return_value=s):
        model = llm_mod.get_llm()
    retries = []
    while model is not None:
        retries.append(model.max_retries)
        model = model.fallback
    assert retries == [0, 0, 2]
