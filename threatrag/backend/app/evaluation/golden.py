"""Golden question set: what the retriever must find and what the generator must refuse."""
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, model_validator

Category = Literal["id_lookup", "name_lookup", "paraphrase", "owasp", "unanswerable"]
DEFAULT_PATH = Path("eval/golden.jsonl")


class GoldenItem(BaseModel):
    id: str
    category: Category
    question: str
    expected_ids: list[str] = []          # MITRE technique IDs; any one in the top-k is a hit
    expected_doc_type: str | None = None  # with `keywords`: a chunk of this type containing one is a hit
    keywords: list[str] = []
    answerable: bool = True

    @model_validator(mode="after")
    def _has_expectation(self) -> "GoldenItem":
        if self.answerable and not (self.expected_ids or (self.expected_doc_type and self.keywords)):
            raise ValueError(f"{self.id}: answerable item needs expected_ids or doc_type + keywords")
        if not self.answerable and (self.expected_ids or self.keywords):
            raise ValueError(f"{self.id}: unanswerable item must not list expectations")
        return self


def load_golden(path: Path = DEFAULT_PATH) -> list[GoldenItem]:
    items = [GoldenItem(**json.loads(line)) for line in path.read_text().splitlines() if line.strip()]
    ids = [i.id for i in items]
    if len(ids) != len(set(ids)):
        raise ValueError("golden set contains duplicate ids")
    return items


def unknown_ids(items: list[GoldenItem], corpus_ids: set[str]) -> list[str]:
    """Expected technique IDs that the ingested corpus does not contain (a stale golden set)."""
    return sorted({tid for item in items for tid in item.expected_ids if tid not in corpus_ids})
