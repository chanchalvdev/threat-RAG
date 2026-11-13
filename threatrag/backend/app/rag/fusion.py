"""Reciprocal-rank fusion: combine rankings whose scores are not comparable (cosine vs BM25)."""
from collections.abc import Hashable, Sequence

RRF_K = 60  # standard damping constant; larger values flatten the advantage of rank 1


def rrf(rankings: Sequence[Sequence[Hashable]], k: int = RRF_K) -> list[tuple[Hashable, float]]:
    """Fuse ranked ID lists. Returns (id, score) sorted best first; ties keep first-seen order."""
    scores: dict[Hashable, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
