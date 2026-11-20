"""RDAP / VirusTotal / GreyNoise evidence, PDF export and Slack / Teams notifications (no network)."""
import io
import os
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from pypdf import PdfReader

os.environ.setdefault("KIMCHI_API_KEY", "test-key-for-unit-tests")

from app.agent import intel_reputation as rep  # noqa: E402
from app.agent import intel_tools as tools  # noqa: E402
from app.agent.investigation_models import InvestigationReport  # noqa: E402
from app.api.routes import exports  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.main import app  # noqa: E402
from app.models.schemas import SourceDoc  # noqa: E402
from app.services import notify  # noqa: E402
from app.services.pdf_export import build_pdf  # noqa: E402

RID = "6c1e0d3a-1111-4222-8333-444455556666"
REPORT = InvestigationReport(
    report_id=RID, ioc="CVE-2021-44228", ioc_type="cve", created_at="2026-11-20T01:02:03", parent_id="aaaaaaaa-0000-0000-0000-000000000000",
    final_report="# Threat Intelligence Report: CVE-2021-44228\n## Executive Summary\nCritical — patch now & isolate <hosts>.\n"
                 "## MITRE ATT&CK Coverage\n| Tactic | Technique | Evidence |\n|---|---|---|\n| Initial Access | T1190 | NVD |\n"
                 '<img src="http://169.254.169.254/latest/meta-data/">',
    sources=[SourceDoc(text="Exploit Public-Facing Application", source="MITRE ATT&CK Enterprise", doc_type="mitre_attack", score=0.9, ref_id="T1190")],
)


def _settings(**kw) -> Settings:
    return Settings(_env_file=None, **kw)


async def test_virustotal_counts_engines_and_names_the_threat(httpx_mock):
    httpx_mock.add_response(url="https://www.virustotal.com/api/v3/files/abc", match_headers={"x-apikey": "vt"}, json={"data": {"attributes": {
        "last_analysis_stats": {"malicious": 50, "suspicious": 2, "harmless": 0, "undetected": 20},
        "reputation": -80, "popular_threat_classification": {"suggested_threat_label": "trojan.emotet"}}}})
    out = await rep.virustotal("hash", "abc", "vt")
    assert out == "50 of 72 engines flag it malicious, 2 suspicious; community reputation -80; threat label trojan.emotet"
    httpx_mock.add_response(url="https://www.virustotal.com/api/v3/domains/unseen.example", status_code=404)
    assert await rep.virustotal("domain", "unseen.example", "vt") is None


async def test_greynoise_reports_scanners_and_ignores_unseen_ips(httpx_mock):
    httpx_mock.add_response(url="https://api.greynoise.io/v3/community/1.2.3.4", match_headers={"key": "gn"},
                            json={"noise": True, "riot": False, "classification": "malicious", "name": "unknown", "last_seen": "2026-11-19"})
    assert "internet-wide scanner: True" in await rep.greynoise("1.2.3.4", "gn")
    httpx_mock.add_response(url="https://api.greynoise.io/v3/community/5.6.7.8", json={"noise": False, "riot": False})
    assert await rep.greynoise("5.6.7.8", "gn") is None


async def test_rdap_follows_the_redirect_and_flags_a_new_domain(httpx_mock):
    registered = (date.today() - timedelta(days=3)).isoformat()
    httpx_mock.add_response(url="https://rdap.org/domain/fresh.example", status_code=302,
                            headers={"Location": "https://rdap.registry.example/domain/fresh.example"})
    httpx_mock.add_response(url="https://rdap.registry.example/domain/fresh.example", json={
        "events": [{"eventAction": "registration", "eventDate": registered + "T00:00:00Z"}],
        "entities": [{"roles": ["registrar"], "vcardArray": ["vcard", [["version", {}, "text", "4.0"], ["fn", {}, "text", "Cheap Names LLC"]]]}],
        "status": ["client transfer prohibited"]})
    out = await rep.rdap_domain("fresh.example")
    assert "3 days ago, NEWLY REGISTERED" in out and "Cheap Names LLC" in out


async def test_rdap_ip_names_the_network(httpx_mock):
    httpx_mock.add_response(url="https://rdap.org/ip/8.8.8.8", json={"name": "GOGL", "startAddress": "8.8.8.0", "endAddress": "8.8.8.255",
        "country": "US", "entities": [{"roles": ["registrant"], "vcardArray": ["vcard", [["fn", {}, "text", "Google LLC"]]]}]})
    assert await rep.rdap_ip("8.8.8.8") == "network GOGL (8.8.8.0 - 8.8.8.255); country US; holder Google LLC"


async def test_ip_tool_adds_greynoise_virustotal_and_rdap_when_keyed(httpx_mock):
    for url in ("https://internetdb.shodan.io/8.8.8.8", "https://api.greynoise.io/v3/community/8.8.8.8",
                "https://www.virustotal.com/api/v3/ip_addresses/8.8.8.8", "https://rdap.org/ip/8.8.8.8"):
        httpx_mock.add_response(url=url, status_code=404)
    keyed = MagicMock(abuseipdb_api_key="", otx_api_key="", abusech_auth_key="", virustotal_api_key="vt", greynoise_api_key="gn")
    with patch.object(tools, "get_settings", return_value=keyed):
        out = await tools.IPIntelTool()._arun("8.8.8.8")
    assert "GreyNoise: no records" in out and "VirusTotal: no records" in out and "RDAP: no records" in out


def test_pdf_holds_the_report_verbatim_and_never_renders_model_html():
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(build_pdf(REPORT))).pages)
    assert "R-6C1E0D" in text and "revision of R-AAAAAA" in text and "CVE-2021-44228" in text
    assert "T1190" in text and "Critical - patch now & isolate <hosts>." in text  # em dash mapped, IOC text intact
    assert '<img' in text and '169.254.169.254' in text  # printed as text, not fetched as an image
    assert "Knowledge-base sources" in text and "MITRE ATT&CK Enterprise (T1190)" in text


def test_notification_payloads():
    slack = notify._payload("slack", "T", "a < b & c", "https://app.example/investigate")
    assert slack == {"text": "*T*\na &lt; b &amp; c\n<https://app.example/investigate|Open ThreatRAG>"}
    card = notify._payload("teams", "T", "body", "")["attachments"][0]["content"]
    assert card["type"] == "AdaptiveCard" and card["body"][1]["text"] == "body" and "actions" not in card
    assert notify.summary(REPORT) == "Critical — patch now & isolate <hosts>."


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def test_export_routes(client, httpx_mock):
    slack_only = _settings(slack_webhook_url="https://hooks.slack.com/services/x", teams_webhook_url="http://not-https.example")
    with patch.object(notify, "get_settings", return_value=slack_only), patch.object(exports, "get_report", new=AsyncMock(return_value=REPORT)):
        assert (await client.get("/api/v1/investigate/exports")).json() == {"pdf": True, "slack": True, "teams": False}
        pdf = await client.get(f"/api/v1/investigate/reports/{RID}/pdf")
        assert pdf.headers["content-type"] == "application/pdf" and pdf.content.startswith(b"%PDF")
        assert (await client.post(f"/api/v1/investigate/reports/{RID}/notify", json={"channel": "teams"})).status_code == 409
        httpx_mock.add_response(url="https://hooks.slack.com/services/x", status_code=200)
        assert (await client.post(f"/api/v1/investigate/reports/{RID}/notify", json={"channel": "slack"})).json() == {"sent": "slack"}
        httpx_mock.add_response(url="https://hooks.slack.com/services/x", status_code=500)
        assert (await client.post(f"/api/v1/investigate/reports/{RID}/notify", json={"channel": "slack"})).status_code == 502
        assert (await client.post(f"/api/v1/investigate/reports/{RID}/notify", json={"channel": "email"})).status_code == 422
