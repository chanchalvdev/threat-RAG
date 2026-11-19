"""Lexical (BM25-style) sparse vectors, so exact terms like T1110.003 or CVE-2021-44228 match.

Term frequency is computed here; Qdrant applies inverse document frequency (Modifier.IDF),
so no corpus statistics need to be stored or kept in sync.
"""
import hashlib
import re
from collections import Counter

from qdrant_client.models import SparseVector

_TOKEN = re.compile(r"cve-\d{4}-\d{4,}|t\d{4}(?:\.\d{3})?|llm\d{2}|[a-z0-9]+")
_ID = re.compile(r"\b(?:T\d{4}(?:\.\d{3})?|LLM\d{2})\b", re.IGNORECASE)
_STOP = frozenset(
    "a an and are as at be by for from has have how in is it its of on or that the this to was "
    "what when where which who why will with does do did can may about into than then".split()
)
_K1, _B, _AVG_LEN = 1.2, 0.75, 120.0


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for tok in _TOKEN.findall(text.lower()):
        if tok in _STOP or len(tok) < 2:
            continue
        tokens.append(tok)
        if tok.startswith("t") and "." in tok:  # a sub-technique also answers for its parent
            tokens.append(tok.split(".")[0])
    return tokens


def _index(token: str) -> int:
    return int.from_bytes(hashlib.blake2b(token.encode(), digest_size=4).digest(), "big")


def _vector(weights: dict[int, float]) -> SparseVector:
    indices = sorted(weights)
    return SparseVector(indices=indices, values=[weights[i] for i in indices])


def encode_document(text: str) -> SparseVector:
    """BM25 term-frequency saturation with length normalisation."""
    tokens = tokenize(text)
    norm = _K1 * (1 - _B + _B * len(tokens) / _AVG_LEN)
    weights: dict[int, float] = {}
    for token, tf in Counter(tokens).items():
        weights[_index(token)] = tf * (_K1 + 1) / (tf + norm)  # hash collisions overwrite: rare at 32 bits
    return _vector(weights)


def encode_query(text: str) -> SparseVector:
    return _vector({_index(token): 1.0 for token in set(tokenize(text))})


def extract_ids(text: str) -> list[str]:
    """Technique (T1110.003) and OWASP (LLM01) identifiers named in the text, upper-cased, in order."""
    seen: dict[str, None] = {}
    for match in _ID.findall(text):
        seen.setdefault(match.upper(), None)
    return list(seen)
