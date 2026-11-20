"""ATT&CK release check: a conditional GET, and a re-index only when the bundle changed."""
import json
from pathlib import Path
from typing import Any

import httpx

from app.core.state import get_state
from app.rag.embedder import BaseEmbedder
from app.rag.ingest_mitre import MITRE_URL, ingest_mitre_attack
from app.rag.store import QdrantStore

ETAG_KEY = "feeds:mitre:etag"
BUNDLE_PATH = Path("data/sources/mitre_attack.json")  # also the cache POST /ingest/mitre reads


def latest_change(raw: bytes) -> str:
    """The bundle carries no release number, so name the release by its newest object change."""
    return max((str(o.get("modified", "")) for o in json.loads(raw).get("objects", [])), default="")[:10] or "unknown"


async def refresh(store: QdrantStore, embedder: BaseEmbedder, force: bool = False) -> dict[str, Any]:
    """Unchanged ETag: nothing is downloaded or indexed. Changed: re-index and prune, and only then
    remember the ETag, so a refresh that dies halfway is retried on the next run."""
    etag = None if force else await get_state().get(ETAG_KEY)
    async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
        r = await client.get(MITRE_URL, headers={"If-None-Match": etag} if etag else None)
    if r.status_code == 304:
        return {"changed": False}
    r.raise_for_status()
    BUNDLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BUNDLE_PATH.write_bytes(r.content)
    chunks = await ingest_mitre_attack(str(BUNDLE_PATH), store, embedder)
    if new_etag := r.headers.get("etag"):
        await get_state().set(ETAG_KEY, new_etag)
    return {"changed": True, "latest_change": latest_change(r.content), "chunks": chunks}
