"""Export a saved investigation as a STIX 2.1 bundle (pure functions, deterministic IDs)."""
import ipaddress
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from app.agent.investigation_models import InvestigationReport

_NAMESPACE = uuid.UUID("6f2c1d6e-3a0b-5c1f-9e57-7f0e2b5a4c11")
_TECHNIQUE = re.compile(r"\bT\d{4}(?:\.\d{3})?\b")
_HASH_NAMES = {32: "MD5", 40: "SHA-1", 64: "SHA-256"}


def _id(kind: str, key: str) -> str:
    return f"{kind}--{uuid.uuid5(_NAMESPACE, f'{kind}:{key}')}"


def _timestamp(value: str | None) -> str:
    try:
        moment = datetime.fromisoformat(value.replace(" ", "T")) if value else datetime.now(UTC)
    except ValueError:
        moment = datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def _quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _pattern(ioc: str, ioc_type: str) -> str | None:
    if ioc_type == "ip":
        kind = "ipv6-addr" if ipaddress.ip_address(ioc).version == 6 else "ipv4-addr"
        return f"[{kind}:value = '{_quote(ioc)}']"
    if ioc_type == "domain":
        return f"[domain-name:value = '{_quote(ioc)}']"
    if ioc_type == "hash" and len(ioc) in _HASH_NAMES:
        return f"[file:hashes.'{_HASH_NAMES[len(ioc)]}' = '{_quote(ioc)}']"
    return None


def _attack_pattern(tid: str, name: str, common: dict[str, Any]) -> dict[str, Any]:
    url = f"https://attack.mitre.org/techniques/{tid.replace('.', '/')}/"
    return {**common, "type": "attack-pattern", "id": _id("attack-pattern", tid), "name": name or tid,
            "external_references": [{"source_name": "mitre-attack", "external_id": tid, "url": url}]}


def build_bundle(report: InvestigationReport, technique_names: dict[str, str]) -> dict[str, Any]:
    """Report + the investigated indicator + every ATT&CK technique the report cites that exists
    in the ingested corpus (unknown IDs are left out rather than exported as fact)."""
    now = _timestamp(report.created_at)
    identity = {"type": "identity", "spec_version": "2.1", "id": _id("identity", "threatrag"), "created": now,
                "modified": now, "name": "ThreatRAG", "identity_class": "system"}
    common = {"spec_version": "2.1", "created": now, "modified": now, "created_by_ref": identity["id"]}

    cited = list(dict.fromkeys(_TECHNIQUE.findall(report.final_report)))
    if report.ioc_type == "technique" and report.ioc not in cited:
        cited.insert(0, report.ioc)
    techniques = [_attack_pattern(tid, technique_names[tid], common) for tid in cited if tid in technique_names]

    subject: dict[str, Any] | None = None
    verb = "indicates"
    if report.ioc_type == "cve":
        subject = {**common, "type": "vulnerability", "id": _id("vulnerability", report.ioc), "name": report.ioc,
                   "external_references": [{"source_name": "cve", "external_id": report.ioc}]}
        verb = "targets"
    elif (pattern := _pattern(report.ioc, report.ioc_type)) is not None:
        subject = {**common, "type": "indicator", "id": _id("indicator", report.ioc), "name": report.ioc,
                   "pattern": pattern, "pattern_type": "stix", "valid_from": now, "indicator_types": ["unknown"]}

    relationships: list[dict[str, Any]] = []
    if subject is not None:
        for technique in techniques:
            source, target = (technique, subject) if verb == "targets" else (subject, technique)
            relationships.append({**common, "type": "relationship", "relationship_type": verb,
                                  "id": _id("relationship", f"{source['id']}:{verb}:{target['id']}"),
                                  "source_ref": source["id"], "target_ref": target["id"]})

    members = [*([subject] if subject else []), *techniques, *relationships]
    summary = {**common, "type": "report", "id": _id("report", report.report_id or report.ioc),
               "name": f"Threat Intelligence Report: {report.ioc}", "report_types": ["threat-report"],
               "published": now, "description": report.final_report,
               "object_refs": [m["id"] for m in members] or [identity["id"]]}
    objects = [identity, summary, *members]
    return {"type": "bundle", "id": _id("bundle", str(summary["id"])), "objects": objects}
