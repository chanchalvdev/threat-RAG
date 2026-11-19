"""OWASP Top 10 for LLM Applications (2025) ingestion from the project's Markdown sources.

The Markdown is used instead of the PDF because PDF text extraction splits words apart.
"""
import asyncio
import re
from pathlib import Path

import httpx

from app.core.logging import get_logger
from app.rag.embedder import BaseEmbedder
from app.rag.ingestion import Chunk, index_chunks, splitter
from app.rag.store import QdrantStore

log = get_logger(__name__)
OWASP_BASE = "https://raw.githubusercontent.com/OWASP/www-project-top-10-for-large-language-model-applications/main/2_0_vulns"
OWASP_FILES = [
    "LLM01_PromptInjection.md", "LLM02_SensitiveInformationDisclosure.md", "LLM03_SupplyChain.md",
    "LLM04_DataModelPoisoning.md", "LLM05_ImproperOutputHandling.md", "LLM06_ExcessiveAgency.md",
    "LLM07_SystemPromptLeakage.md", "LLM08_VectorAndEmbeddingWeaknesses.md", "LLM09_Misinformation.md",
    "LLM10_UnboundedConsumption.md",
]
CACHE_DIR = Path("data/sources/owasp_llm_2025")
# Lists of URLs and framework IDs: they match many questions lexically and answer none of them.
LINK_SECTIONS = {"Reference Links", "Related Frameworks and Taxonomies"}
_TITLE = re.compile(r"^##\s+(LLM\d{2}):2025\s+(.+)$", re.MULTILINE)
_SECTION = re.compile(r"^###\s+(.+)$", re.MULTILINE)


def owasp_chunks(markdown: str, filename: str) -> list[Chunk]:
    """Split one risk page by its `###` sections; each chunk carries the risk ID and title."""
    title = _TITLE.search(markdown)
    owasp_id, name = (title.group(1), title.group(2).strip()) if title else (filename[:5], filename)
    header = f"OWASP Top 10 for LLM Applications 2025 — {owasp_id}: {name}"
    parts = _SECTION.split(markdown[title.end() if title else 0 :])
    sections = [("Overview", parts[0])] + list(zip(parts[1::2], parts[2::2]))
    sections = [(name, body) for name, body in sections if name.strip() not in LINK_SECTIONS]
    chunks: list[Chunk] = []
    for section, body in sections:
        for part, piece in enumerate(splitter().split_text(body.strip())):
            chunks.append(Chunk(
                key=f"owasp2025:{owasp_id}:{section}:{part}",
                text=f"{header}\nSection: {section.strip()}\n\n{piece}",
                payload={"source": "OWASP LLM Top 10 2025", "doc_type": "owasp_llm", "owasp_id": owasp_id,
                         "name": name, "section": section.strip()},
            ))
    return chunks


async def _fetch(client: httpx.AsyncClient, filename: str) -> str:
    cached = CACHE_DIR / filename
    if cached.exists():
        return cached.read_text()
    r = await client.get(f"{OWASP_BASE}/{filename}")
    r.raise_for_status()
    cached.write_text(r.text)
    return r.text


async def ingest_owasp_llm(store: QdrantStore, embedder: BaseEmbedder) -> int:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        pages = await asyncio.gather(*[_fetch(client, name) for name in OWASP_FILES])
    chunks = [chunk for page, name in zip(pages, OWASP_FILES) for chunk in owasp_chunks(page, name)]
    await store.delete_doc_type("owasp_llm")  # the source is replaced wholesale; no stale sections survive
    count = await index_chunks(chunks, store, embedder)
    log.info("owasp_ingested", risks=len(OWASP_FILES), chunks=count)
    return count
