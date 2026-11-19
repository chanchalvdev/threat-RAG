"""TAXII 2.1 pull: objects added since the stored cursor, indexed as doc_type=taxii."""
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.state import get_state
from app.guard.heuristic import BLOCK_AT, score
from app.rag.embedder import BaseEmbedder
from app.rag.ingestion import Chunk, index_chunks, splitter
from app.rag.store import QdrantStore

log = get_logger(__name__)
ACCEPT = "application/taxii+json;version=2.1"
CURSOR_KEY = "feeds:taxii:added_after"
TYPES = {"report", "indicator", "malware", "intrusion-set", "threat-actor", "campaign", "attack-pattern", "tool", "vulnerability"}
MAX_PAGES = 20


def _text(o: dict[str, Any]) -> str:
    lines = [f"{o['type'].replace('-', ' ').title()}: {o.get('name') or o['id']}", o.get("description", "")]
    if o.get("pattern"):
        lines.append(f"Pattern: {o['pattern']}")
    for field in ("aliases", "labels", "malware_types", "indicator_types"):
        if o.get(field):
            lines.append(f"{field.replace('_', ' ').capitalize()}: {', '.join(map(str, o[field]))}")
    return "\n".join(line for line in lines if line).strip()


def object_chunks(objects: list[dict[str, Any]], source: str) -> tuple[list[Chunk], int]:
    """Chunks for the useful object types. Feed text is written by others and later read by the
    model, so an object whose text reads like instructions is dropped (and counted)."""
    chunks, dropped = [], 0
    for o in objects:
        if o.get("type") not in TYPES or o.get("revoked"):
            continue
        text = _text(o)
        if score(text).score >= BLOCK_AT:
            dropped += 1
            continue
        payload = {"source": source, "doc_type": "taxii", "stix_id": o["id"], "stix_type": o["type"]}
        chunks += [Chunk(key=f"taxii:{o['id']}:{i}", text=piece, payload=payload)
                   for i, piece in enumerate(splitter().split_text(text) or [text])]
    return chunks, dropped


async def pull(store: QdrantStore, embedder: BaseEmbedder) -> dict[str, Any]:
    s = get_settings()
    if not s.taxii_url:
        return {"skipped": "TAXII_URL not set"}
    url = s.taxii_url.rstrip("/") + "/objects/"
    source = f"TAXII {urlparse(url).hostname}"
    cursor = await get_state().get(CURSOR_KEY)
    params: dict[str, str] = {"added_after": cursor} if cursor else {}
    auth = (s.taxii_user, s.taxii_password) if s.taxii_user else None
    indexed = dropped = 0
    async with httpx.AsyncClient(timeout=60, auth=auth, headers={"Accept": ACCEPT}) as client:
        for _ in range(MAX_PAGES):
            r = await client.get(url, params=params)
            r.raise_for_status()
            envelope = r.json() if r.content else {}
            chunks, n_dropped = object_chunks(envelope.get("objects", []), source)
            indexed, dropped = indexed + (await index_chunks(chunks, store, embedder) if chunks else 0), dropped + n_dropped
            cursor = r.headers.get("X-TAXII-Date-Added-Last", cursor)
            if not (envelope.get("more") and envelope.get("next")):
                break
            params = {**params, "next": envelope["next"]}
    if cursor:
        await get_state().set(CURSOR_KEY, cursor)
    log.info("taxii_pulled", chunks=indexed, dropped=dropped, cursor=cursor)
    return {"chunks": indexed, "dropped_instruction_like": dropped, "cursor": cursor}
