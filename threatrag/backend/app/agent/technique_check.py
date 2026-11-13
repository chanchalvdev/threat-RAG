"""Check MITRE technique IDs in a report against the ingested corpus (G18)."""
import re

_TECHNIQUE_ID = re.compile(r"\bT\d{4}(?:\.\d{3})?\b")
_SEPARATORS = " \t:-–—()[]|*`'\""


def _accepted_names(tid: str, names: dict[str, str]) -> set[str]:
    """Names that are fine beside `tid`: its own, its parent's, and its sub-techniques'."""
    family = (other for other in names if other == tid.split(".")[0] or other.startswith(f"{tid}."))
    return {names[other].lower() for other in (tid, *family) if names.get(other)}


def _wrong_name(before: str, after: str, tid: str, names: dict[str, str]) -> str | None:
    """Name of a different technique directly next to `tid`. Prose and bare IDs are not mismatches."""
    before, after = before.rstrip(_SEPARATORS).lower(), after.lstrip(_SEPARATORS).lower()
    accepted = _accepted_names(tid, names)
    if any(after.startswith(n) or before.endswith(n) for n in accepted):
        return None
    others = [n for n in names.values() if n and (after.startswith(n.lower()) or before.endswith(n.lower()))]
    return max(others, key=len) if others else None


def validate_techniques(report: str, names: dict[str, str]) -> str:
    """Return a Markdown section listing bad citations, or "" if there are none."""
    if not names:  # nothing ingested to check against
        return ""
    issues: dict[str, str] = {}
    for line in report.splitlines():
        for match in _TECHNIQUE_ID.finditer(line):
            tid = match.group()
            if tid not in names:
                issues.setdefault(tid, f"- `{tid}` is not in the ingested MITRE ATT&CK data.")
            elif (wrong := _wrong_name(line[: match.start()], line[match.end() :], tid, names)) is not None:
                issues.setdefault(tid, f"- `{tid}` is **{names[tid]}**, but the report calls it \"{wrong}\".")
    if not issues:
        return ""
    return "\n\n## Technique Validation\n\nAutomated check found citation problems:\n\n" + "\n".join(issues.values())
