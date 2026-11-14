"""Hybrid retrieval: exact identifier lookup, dense + lexical fusion, optional rerank, abstention."""
import re
from typing import Any, Literal

from pydantic import BaseModel

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import SourceDoc
from app.rag.embedder import BaseEmbedder
from app.rag.fusion import rrf
from app.rag.reranker import Reranker
from app.rag.sparse import encode_query, extract_ids
from app.rag.store import QdrantStore

log = get_logger(__name__)
Confidence = Literal["high", "low", "none"]
_EXACT_SECTION_ORDER = {"description": 0, "Overview": 0, "Description": 0}
# When a question names an ID, these words say which part of that entry it is asking about.
_SECTION_INTENT = [
    ("usage", re.compile(r"\b(groups?|actors?|apts?|campaigns?|used by|who uses|malware|tools?|software|attribut\w*)\b", re.I)),
    ("mitigations", re.compile(r"\b(mitigat\w*|prevent\w*|defen[cs]\w*|harden\w*|protect\w*|stop)\b", re.I)),
    ("detection", re.compile(r"\b(detect\w*|monitor\w*|hunt\w*|log|logs|events?|alerts?)\b", re.I)),
]


def section_intent(question: str) -> str | None:
    return next((section for section, pattern in _SECTION_INTENT if pattern.search(question)), None)


class Hit(BaseModel):
    id: Any
    payload: dict[str, Any]
    score: float = 0.0          # cosine similarity to the question
    exact: bool = False         # matched an identifier named in the question
    rerank: float | None = None

    def to_source(self) -> SourceDoc:
        p = self.payload
        return SourceDoc(text=p.get("text", ""), source=p.get("source", ""), doc_type=p.get("doc_type", ""),
                         score=round(self.score, 4), ref_id=_ref(p), exact=self.exact)


class Retrieval(BaseModel):
    hits: list[Hit]
    confidence: Confidence
    top_score: float

    @property
    def abstain(self) -> bool:
        return self.confidence == "none"


def _ref(payload: dict[str, Any]) -> str:
    return payload.get("technique_id") or payload.get("owasp_id") or ""


def _prefer_sections(hits: list["Hit"], intent: str | None) -> list["Hit"]:
    """Within one technique or risk, give its best-ranked slot to the section the question asks
    about, else its description. Each entry keeps the slots it earned; only its own chunks swap."""
    def preference(hit: "Hit") -> int:
        section = hit.payload.get("section", "")
        return 0 if intent and section == intent else 1 if section in _EXACT_SECTION_ORDER else 2

    slots: dict[str, list[int]] = {}
    for position, hit in enumerate(hits):
        slots.setdefault(_ref(hit.payload) or f"#{position}", []).append(position)
    ordered = list(hits)
    for positions in slots.values():
        for position, hit in zip(positions, sorted((hits[i] for i in positions), key=preference)):
            ordered[position] = hit
    return ordered


def diversify(hits: list["Hit"], k: int, per_ref: int, intent: str | None = None) -> list["Hit"]:
    """Top k with at most `per_ref` chunks of one technique, so its sections cannot fill the context."""
    hits = _prefer_sections(hits, intent)
    kept: list[Hit] = []
    seen: dict[str, int] = {}
    for hit in hits:
        ref = _ref(hit.payload)
        if hit.exact or not ref or seen.get(ref, 0) < per_ref:
            kept.append(hit)
            seen[ref] = seen.get(ref, 0) + 1
        if len(kept) == k:
            break
    return kept


def _exact_order(point: Any, ids: list[str], intent: str | None) -> tuple[int, int, int]:
    """Named ID first, then the section the question asks about, then the description."""
    p = point.payload or {}
    ref, section = _ref(p), p.get("section", "")
    rank = 0 if intent and section == intent else 1 + _EXACT_SECTION_ORDER.get(section, 1)
    return (ids.index(ref) if ref in ids else len(ids), rank, p.get("chunk_index", 0))


class Retriever:
    def __init__(self, store: QdrantStore, embedder: BaseEmbedder, reranker: Reranker | None = None):
        self._store, self._embedder, self._reranker = store, embedder, reranker

    async def retrieve(self, question: str, k: int | None = None, doc_types: list[str] | None = None) -> Retrieval:
        s = get_settings()
        k = k or s.retrieval_k
        pool = max(s.rerank_candidates, 3 * k)
        vector = await self._embedder.embed(question)
        sparse = encode_query(question) if s.retrieval_mode == "hybrid" else None
        dense, lexical = await self._store.candidates(vector, sparse, pool, doc_types)

        ids = extract_ids(question) if s.exact_match else []
        intent = section_intent(question)
        exact = sorted(await self._store.by_ids(ids), key=lambda p: _exact_order(p, ids, intent)) if ids else []
        if doc_types:
            exact = [p for p in exact if (p.payload or {}).get("doc_type") in doc_types]

        points = {p.id: p for p in [*lexical, *dense, *exact]}
        scores = {p.id: p.score for p in dense}
        exact_ids = [p.id for p in exact][: max(1, k // 2)]
        fused = [pid for pid, _ in rrf([[p.id for p in dense], [p.id for p in lexical]])]
        order = exact_ids + [pid for pid in fused if pid not in exact_ids]

        hits = [Hit(id=pid, payload=points[pid].payload or {}, exact=pid in exact_ids) for pid in order[:pool]]
        if self._reranker is not None and hits:
            ranks = await self._reranker.score(question, [h.payload.get("text", "") for h in hits])
            for hit, value in zip(hits, ranks):
                hit.rerank = value
            hits.sort(key=lambda h: (not h.exact, -(h.rerank or 0.0)))  # stable: exact matches stay first
        hits = diversify(hits, k, s.max_chunks_per_ref, intent)

        scores.update(await self._store.dense_scores(vector, [h.id for h in hits if h.id not in scores]))
        for hit in hits:
            hit.score = scores.get(hit.id, 0.0)
        top = max([h.score for h in hits] + [p.score for p in dense[:1]], default=0.0)
        confidence = self._confidence(top, any(h.exact for h in hits), bool(hits))
        log.info("retrieved", hits=len(hits), exact=len(exact_ids), top=round(top, 3), confidence=confidence)
        return Retrieval(hits=hits, confidence=confidence, top_score=top)

    @staticmethod
    def _confidence(top: float, exact: bool, any_hits: bool) -> Confidence:
        s = get_settings()
        if exact:
            return "high"
        if not any_hits or top < s.abstain_below:
            return "none"
        return "high" if top >= s.confident_above else "low"
