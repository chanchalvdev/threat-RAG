"""Feedback → golden-set drafts. Drafts are for a human to check, never added to the eval automatically."""
import json
import re

from app.db import feedback as repo
from app.db.connection import get_pool

_TECHNIQUE = re.compile(r"\bT\d{4}(?:\.\d{3})?\b")
_OWASP = re.compile(r"\bLLM(?:0[1-9]|10)\b", re.IGNORECASE)


def draft(fb_id: str, question: str, answer: str, note: str) -> dict:
    """A golden-set line pre-filled from the question. `review` explains why it was flagged;
    `load_golden` ignores it, so a reviewed line can be pasted in as-is once expectations are right."""
    ids = sorted(set(_TECHNIQUE.findall(question.upper())))
    owasp = sorted({m.upper() for m in _OWASP.findall(question)})
    item: dict = {"id": f"fb-{fb_id[:8]}", "question": question, "answerable": True}
    if ids:
        item |= {"category": "id_lookup", "expected_ids": ids}
    elif owasp:
        item |= {"category": "owasp", "expected_doc_type": "owasp_llm", "keywords": owasp}
    else:
        item |= {"category": "paraphrase", "expected_ids": []}  # reviewer fills in the right technique(s)
    item["review"] = {"analyst_note": note, "answer_excerpt": answer[:400]}
    return item


async def candidates_jsonl() -> str:
    async with get_pool().connection() as conn:
        rows = await repo.down_voted_answers(conn)
    return "".join(json.dumps(draft(*row)) + "\n" for row in rows)
