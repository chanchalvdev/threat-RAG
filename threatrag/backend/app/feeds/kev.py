"""CISA KEV catalogue in shared state: one copy for every API worker, refreshed by the feed job."""
import json
from typing import Any

import httpx

from app.core.state import get_state

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
KEY = "feeds:kev"
TTL_S = 26 * 3600  # the job runs daily; a missed run still leaves slack before lookups refetch
FIELDS = ("vulnerabilityName", "dateAdded", "knownRansomwareCampaignUse")


async def refresh() -> int:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(KEV_URL)
    r.raise_for_status()
    items = {v["cveID"]: {f: v.get(f) for f in FIELDS} for v in r.json()["vulnerabilities"]}
    await get_state().set(KEY, json.dumps(items), ttl_s=TTL_S)
    return len(items)


async def lookup(cve_id: str) -> dict[str, Any] | None:
    raw = await get_state().get(KEY)
    if raw is None:  # first lookup, or the job has not run: fetch once and share it
        await refresh()
        raw = await get_state().get(KEY)
    return json.loads(raw or "{}").get(cve_id)
