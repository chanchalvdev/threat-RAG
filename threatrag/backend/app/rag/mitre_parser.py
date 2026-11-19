"""Parse an ATT&CK STIX bundle into techniques with their mitigations, detections and users."""
from collections import defaultdict
from typing import Any

from pydantic import BaseModel

_MAX_NAMES = 25


class Technique(BaseModel):
    stix_id: str
    technique_id: str
    name: str
    tactics: list[str] = []
    platforms: list[str] = []
    description: str = ""
    mitigations: list[str] = []   # "M1032 Multi-factor Authentication: how it applies"
    detections: list[str] = []
    groups: list[str] = []
    software: list[str] = []


def _external_id(obj: dict[str, Any]) -> str:
    refs = obj.get("external_references", [])
    return next((r.get("external_id", "") for r in refs if r.get("source_name") == "mitre-attack"), "")


def _retired(obj: dict[str, Any]) -> bool:
    return bool(obj.get("revoked")) or bool(obj.get("x_mitre_deprecated"))


def _detection_text(strategy: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> list[str]:
    analytics = [by_id.get(ref, {}) for ref in strategy.get("x_mitre_analytic_refs", [])]
    notes = [
        f"[{', '.join(a.get('x_mitre_platforms', [])) or 'any'}] {a.get('description', '').strip()}"
        for a in analytics if a.get("description")
    ]
    return notes or [strategy.get("name", "")]


def parse_techniques(stix: dict[str, Any]) -> list[Technique]:
    """Live (not revoked or deprecated) techniques, each joined to its related objects."""
    objects = stix.get("objects", [])
    by_id = {o["id"]: o for o in objects if "id" in o}
    related: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    for rel in objects:
        if rel.get("type") != "relationship" or _retired(rel):
            continue
        source, target = by_id.get(rel.get("source_ref", "")), rel.get("target_ref", "")
        if source is None or _retired(source) or not target.startswith("attack-pattern--"):
            continue
        kind, bucket = rel.get("relationship_type"), related[target]
        if kind == "mitigates":
            note = (rel.get("description") or source.get("description") or "").strip()
            bucket["mitigations"].append(f"{_external_id(source)} {source.get('name', '')}: {note}")
        elif kind == "detects":
            bucket["detections"].extend(_detection_text(source, by_id))
        elif kind == "uses" and source["type"] == "intrusion-set":
            bucket["groups"].append(source.get("name", ""))
        elif kind == "uses" and source["type"] in ("malware", "tool"):
            bucket["software"].append(source.get("name", ""))

    techniques: list[Technique] = []
    for obj in objects:
        if obj.get("type") != "attack-pattern" or _retired(obj):
            continue
        extra = related.get(obj["id"], {})
        techniques.append(Technique(
            stix_id=obj["id"],
            technique_id=_external_id(obj),
            name=obj.get("name", ""),
            tactics=[p.get("phase_name", "") for p in obj.get("kill_chain_phases", [])],
            platforms=obj.get("x_mitre_platforms", []),
            description=(obj.get("description") or "").strip(),
            mitigations=sorted(set(extra.get("mitigations", []))),
            detections=list(dict.fromkeys(extra.get("detections", []))),
            groups=sorted(set(extra.get("groups", [])))[:_MAX_NAMES],
            software=sorted(set(extra.get("software", [])))[:_MAX_NAMES],
        ))
    return techniques
