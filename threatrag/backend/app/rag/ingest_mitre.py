"""MITRE ATT&CK ingestion: one chunk set per live technique, with mitigations, detections and users."""
import json
import re
from pathlib import Path

import httpx

from app.core.logging import get_logger
from app.rag.embedder import BaseEmbedder
from app.rag.ingestion import Chunk, index_chunks, splitter
from app.rag.mitre_parser import Technique, parse_techniques
from app.rag.store import QdrantStore

log = get_logger(__name__)
MITRE_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
_CITATION = re.compile(r"\s*\(Citation: [^)]*\)")
_LINK = re.compile(r"\[([^\]]+)\]\(https?://[^)]+\)")


def _clean(text: str) -> str:
    return _LINK.sub(r"\1", _CITATION.sub("", text)).strip()


def _sections(t: Technique) -> list[tuple[str, str]]:
    label = f"{t.name} ({t.technique_id})"
    sections = [("description", _clean(t.description))]
    if t.mitigations:
        sections.append(("mitigations", f"Mitigations for {label}:\n" + "\n".join(f"- {_clean(m)}" for m in t.mitigations)))
    if t.detections:
        sections.append(("detection", f"Detection of {label}:\n" + "\n".join(f"- {_clean(d)}" for d in t.detections)))
    if t.groups or t.software:
        used = [f"Threat groups known to use {label}: {', '.join(t.groups)}" if t.groups else "",
                f"Malware and tools that implement {label}: {', '.join(t.software)}" if t.software else ""]
        sections.append(("usage", "\n".join(line for line in used if line)))
    return sections


def technique_chunks(t: Technique) -> list[Chunk]:
    """Every chunk repeats the technique header, so a mitigation chunk is still findable by ID or name."""
    header = (
        f"Technique: {t.name}\nID: {t.technique_id}\n"
        f"Tactic: {', '.join(t.tactics)}\nPlatforms: {', '.join(t.platforms)}"
    )
    payload = {
        "source": "MITRE ATT&CK Enterprise", "doc_type": "mitre_attack", "technique_id": t.technique_id,
        "name": t.name, "tactic": ", ".join(t.tactics), "platforms": ", ".join(t.platforms),
    }
    chunks: list[Chunk] = []
    for section, body in _sections(t):
        for part, piece in enumerate(splitter().split_text(body) or [""]):
            chunks.append(Chunk(
                key=f"mitre:{t.stix_id}:{section}:{part}",
                text=f"{header}\n\n{piece}".strip(),
                payload={**payload, "section": section},
            ))
    return chunks


async def ingest_mitre_attack(path: str, store: QdrantStore, embedder: BaseEmbedder) -> int:
    source = Path(path)
    if not source.exists():
        log.info("downloading_mitre", url=MITRE_URL)
        source.parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.get(MITRE_URL)
            r.raise_for_status()
            source.write_bytes(r.content)

    techniques = parse_techniques(json.loads(source.read_text()))
    chunks = [chunk for t in techniques for chunk in technique_chunks(t)]
    count = await index_chunks(chunks, store, embedder)
    log.info("mitre_ingested", techniques=len(techniques), chunks=count)
    return count
