"""Reputation and registration sources: VirusTotal, GreyNoise Community and RDAP (no key).

Each returns one line of evidence, or None if it has no record, like `intel_sources`.
"""
from datetime import date
from typing import Any

from app.agent.intel_sources import _clean, _join, _json

NEW_DOMAIN_DAYS = 30  # recently registered domains are a classic phishing / C2 signal
VT_KINDS = {"hash": "files", "ip": "ip_addresses", "domain": "domains"}


async def virustotal(ioc_type: str, value: str, key: str) -> str | None:
    d = await _json("GET", f"https://www.virustotal.com/api/v3/{VT_KINDS[ioc_type]}/{value}", headers={"x-apikey": key})
    attrs = ((d or {}).get("data") or {}).get("attributes")
    if not attrs:
        return None
    stats: dict[str, int] = attrs.get("last_analysis_stats") or {}
    label = (attrs.get("popular_threat_classification") or {}).get("suggested_threat_label")
    return (
        f"{stats.get('malicious', 0)} of {sum(stats.values())} engines flag it malicious, "
        f"{stats.get('suspicious', 0)} suspicious; community reputation {attrs.get('reputation', 'n/a')}"
        + (f"; threat label {_clean(label, 60)}" if label else "")
    )


async def greynoise(ip: str, key: str) -> str | None:
    d = await _json("GET", f"https://api.greynoise.io/v3/community/{ip}", headers={"key": key})
    if not d or not (d.get("noise") or d.get("riot")):
        return None
    return (
        f"internet-wide scanner: {d.get('noise')}; known business service (RIOT): {d.get('riot')}; "
        f"classification {_clean(d.get('classification'), 20)}; name {_clean(d.get('name'), 40)}; "
        f"last seen {_clean(d.get('last_seen'), 12)}"
    )


def _vcard_name(entity: dict[str, Any]) -> str:
    fields = (entity.get("vcardArray") or [None, []])[1]
    return next((str(f[3]) for f in fields if isinstance(f, list) and len(f) > 3 and f[0] == "fn"), "")


async def rdap_domain(domain: str) -> str | None:
    d = await _json("GET", f"https://rdap.org/domain/{domain}")
    if not d:
        return None
    events = {e.get("eventAction"): str(e.get("eventDate", ""))[:10] for e in d.get("events", [])}
    registrar = next((_vcard_name(e) for e in d.get("entities", []) if "registrar" in e.get("roles", [])), "")
    registered, age = events.get("registration"), ""
    if registered:
        days = (date.today() - date.fromisoformat(registered)).days
        age = f" ({days} days ago{', NEWLY REGISTERED' if days < NEW_DOMAIN_DAYS else ''})"
    return (
        f"registered {registered or 'unknown'}{age}; expires {events.get('expiration') or 'unknown'}; "
        f"registrar {_clean(registrar or 'unknown', 60)}; status {_join(d.get('status'))}"
    )


async def rdap_ip(ip: str) -> str | None:
    d = await _json("GET", f"https://rdap.org/ip/{ip}")
    if not d:
        return None
    org = next((_vcard_name(e) for e in d.get("entities", []) if {"registrant", "administrative"} & set(e.get("roles", []))), "")
    return (
        f"network {_clean(d.get('name'), 40)} ({_clean(d.get('startAddress'), 40)} - {_clean(d.get('endAddress'), 40)}); "
        f"country {_clean(d.get('country') or 'unknown', 10)}; holder {_clean(org or 'unknown', 60)}"
    )
