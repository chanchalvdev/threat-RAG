"""Post a saved report's summary to Slack or Microsoft Teams.

Webhook URLs come from settings only, never from a request, so the API cannot be pointed at an
arbitrary address.
"""
import re
from typing import Any, Literal

import httpx

from app.agent.investigation_models import InvestigationReport
from app.core.config import get_settings
from app.services.pdf_export import serial

Channel = Literal["slack", "teams"]
SUMMARY_CHARS = 1500
_SECTION = re.compile(r"^##\s*Executive Summary\s*\n(.*?)(?=^##\s|\Z)", re.S | re.M)


class ChannelNotConfigured(Exception):
    """The channel's webhook URL is not set (or is not https)."""


def configured(channel: Channel) -> str:
    s = get_settings()
    url = s.slack_webhook_url if channel == "slack" else s.teams_webhook_url
    return url if url.startswith("https://") else ""


def summary(report: InvestigationReport) -> str:
    found = _SECTION.search(report.final_report)
    text = (found.group(1) if found else report.final_report).strip()
    return text[:SUMMARY_CHARS] + ("…" if len(text) > SUMMARY_CHARS else "")


def _payload(channel: Channel, title: str, text: str, link: str) -> dict[str, Any]:
    if channel == "slack":  # Slack's mrkdwn needs only &, < and > escaped
        esc = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return {"text": f"*{title}*\n{esc}" + (f"\n<{link}|Open ThreatRAG>" if link else "")}
    card: dict[str, Any] = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json", "type": "AdaptiveCard", "version": "1.4",
        "body": [{"type": "TextBlock", "text": title, "weight": "Bolder", "wrap": True},
                 {"type": "TextBlock", "text": text, "wrap": True}],
    }
    if link:
        card["actions"] = [{"type": "Action.OpenUrl", "title": "Open ThreatRAG", "url": link}]
    return {"type": "message", "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "content": card}]}


async def send(report: InvestigationReport, channel: Channel) -> None:
    url = configured(channel)
    if not url:
        raise ChannelNotConfigured(f"{channel} is not configured (set {channel.upper()}_WEBHOOK_URL to an https URL)")
    base = get_settings().public_base_url.rstrip("/")
    title = f"ThreatRAG {serial(report.report_id or '')}: {report.ioc_type.upper()} {report.ioc}"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json=_payload(channel, title, summary(report), f"{base}/investigate" if base else ""))
    r.raise_for_status()
