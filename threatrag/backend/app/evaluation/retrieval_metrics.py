"""Retrieval metrics over a ranked list. Pure functions: no I/O, no model calls."""
import re
from collections.abc import Iterable

from pydantic import BaseModel

from app.evaluation.golden import GoldenItem

_WS = re.compile(r"\s+")


class Retrieved(BaseModel):
    technique_id: str = ""
    doc_type: str = ""
    text: str = ""
    score: float = 0.0


def _squash(text: str) -> str:
    """PDF extraction can split words ("pro mpt"); compare with whitespace removed."""
    return _WS.sub("", text).lower()


def is_relevant(item: GoldenItem, hit: Retrieved) -> bool:
    if item.expected_ids:
        return hit.technique_id in item.expected_ids
    if item.expected_doc_type and hit.doc_type == item.expected_doc_type:
        body = _squash(hit.text)
        return any(_squash(kw) in body for kw in item.keywords)
    return False


def first_relevant_rank(item: GoldenItem, hits: list[Retrieved]) -> int | None:
    """1-based rank of the first relevant hit, or None."""
    return next((rank for rank, hit in enumerate(hits, start=1) if is_relevant(item, hit)), None)


def hit_at_k(ranks: Iterable[int | None], k: int) -> float:
    values = list(ranks)
    return sum(1 for r in values if r is not None and r <= k) / len(values) if values else 0.0


def mrr(ranks: Iterable[int | None]) -> float:
    values = list(ranks)
    return sum(1 / r for r in values if r is not None) / len(values) if values else 0.0


def mean(values: Iterable[float]) -> float:
    items = list(values)
    return sum(items) / len(items) if items else 0.0
