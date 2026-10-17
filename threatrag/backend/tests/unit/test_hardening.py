"""Unit tests for Phase 4 hardening: upload safety, API key guard, chat memory."""
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

os.environ.setdefault("KIMCHI_API_KEY", "test-key-for-unit-tests")

from app.agent.react_agent import MAX_HISTORY_MESSAGES, ThreatIntelAgent  # noqa: E402
from app.api.routes.ingest import _safe_pdf_name  # noqa: E402
from app.api.security import require_api_key  # noqa: E402


@pytest.mark.parametrize("raw,expected", [
    ("../../etc/evil.pdf", "evil.pdf"),
    ("/abs/path/report.PDF", "report.PDF"),
    ("we ird;name.pdf", "we_ird_name.pdf"),
    ("..pdf", "pdf") ,
])
def test_safe_pdf_name_strips_traversal(raw, expected):
    if not expected.lower().endswith(".pdf"):
        with pytest.raises(HTTPException):
            _safe_pdf_name(raw)
    else:
        assert _safe_pdf_name(raw) == expected


def test_safe_pdf_name_rejects_non_pdf():
    with pytest.raises(HTTPException) as e:
        _safe_pdf_name("payload.sh")
    assert e.value.status_code == 400


@pytest.mark.asyncio
async def test_api_key_guard_open_when_unset():
    with patch("app.api.security.get_settings", return_value=MagicMock(api_key="")):
        await require_api_key(None)


@pytest.mark.asyncio
async def test_api_key_guard_rejects_wrong_key():
    with patch("app.api.security.get_settings", return_value=MagicMock(api_key="s3cret")):
        with pytest.raises(HTTPException) as e:
            await require_api_key("nope")
        assert e.value.status_code == 401
        await require_api_key("s3cret")


def test_agent_memory_includes_prior_turns_and_is_bounded():
    agent = ThreatIntelAgent(tools=[])
    agent._remember("What is Log4Shell?", "CVE-2021-44228 ...")
    payload = agent._input("What is its CVSS score?")["messages"]
    assert [m.content for m in payload] == ["What is Log4Shell?", "CVE-2021-44228 ...", "What is its CVSS score?"]

    for i in range(30):
        agent._remember(f"q{i}", f"a{i}")
    assert len(agent._messages) == MAX_HISTORY_MESSAGES
    assert agent.get_history()[-1] == {"role": "assistant", "content": "a29"}
