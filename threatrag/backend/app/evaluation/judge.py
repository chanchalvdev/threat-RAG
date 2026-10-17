"""LLM-as-judge implementations of the four RAGAs metric definitions.

The `ragas` package is incompatible with the LangChain 1.x stack this project runs on,
so the metrics are computed directly with Kimchi (judge) + Ollama (embeddings).
"""
import json
import math
import re
from typing import Any

from app.core.llm import get_llm
from app.rag.embedder import get_embedder

_JSON_RE = re.compile(r"\{.*\}|\[.*\]", re.DOTALL)


async def _judge(prompt: str, key: str) -> list[Any]:
    """Ask the judge for {key: [...]}; tolerates a bare top-level list from weaker models."""
    response = await get_llm(temperature=0.0).ainvoke(prompt + "\nRespond with JSON only.")
    match = _JSON_RE.search(str(response.content))
    if not match:
        raise ValueError("Judge did not return JSON")
    data = json.loads(match.group(0))
    items = data if isinstance(data, list) else data.get(key, [])
    return list(items) if isinstance(items, list) else []


def _truthy(value: Any) -> bool:
    """Judges return true / "true" / "yes"; bool("false") would be True, so coerce explicitly."""
    return value is True or str(value).strip().lower() in ("true", "yes", "1")


def _flag(item: Any, field: str) -> bool:
    return _truthy(item.get(field)) if isinstance(item, dict) else _truthy(item)


def _ctx(contexts: list[str]) -> str:
    return "\n".join(f"[{i}] {c[:1500]}" for i, c in enumerate(contexts))


async def faithfulness(answer: str, contexts: list[str]) -> float:
    """Share of answer claims that are supported by the retrieved contexts."""
    claims = await _judge(
        "Split the ANSWER into atomic factual claims and mark each as supported (true) only if "
        'it can be inferred from CONTEXT. JSON: {"claims": [{"claim": str, "supported": bool}]}\n'
        f"CONTEXT:\n{_ctx(contexts)}\n\nANSWER:\n{answer[:4000]}",
        "claims",
    )
    return sum(_flag(c, "supported") for c in claims) / len(claims) if claims else 0.0


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


async def answer_relevancy(question: str, answer: str) -> float:
    """Mean cosine similarity between the question and questions reverse-generated from the answer."""
    questions = await _judge(
        'Write 3 different questions that the ANSWER below would directly answer. JSON: {"questions": [str]}\n'
        f"ANSWER:\n{answer[:4000]}",
        "questions",
    )
    generated = [q for q in questions if isinstance(q, str) and q.strip()][:3]
    if not generated:
        return 0.0
    vectors = await get_embedder().embed_batch([question, *generated])
    return max(0.0, sum(_cosine(vectors[0], v) for v in vectors[1:]) / len(generated))


async def context_precision(question: str, reference: str, contexts: list[str]) -> float:
    """Average precision@k over contexts judged useful for producing the reference answer."""
    raw = await _judge(
        "For each numbered CONTEXT say whether it is useful for answering QUESTION with the "
        'REFERENCE answer. JSON: {"verdicts": [bool, ...]} in context order.\n'
        f"QUESTION: {question}\nREFERENCE: {reference[:2000]}\nCONTEXT:\n{_ctx(contexts)}",
        "verdicts",
    )
    verdicts = [_truthy(v) for v in raw][: len(contexts)]
    hits, total = 0, 0.0
    for k, useful in enumerate(verdicts, start=1):
        if useful:
            hits += 1
            total += hits / k
    return total / hits if hits else 0.0


async def context_recall(ground_truth: str, contexts: list[str]) -> float:
    """Share of ground-truth sentences attributable to the retrieved contexts."""
    sentences = await _judge(
        "Split GROUND TRUTH into sentences; mark each attributed (true) if CONTEXT supports it. "
        'JSON: {"sentences": [{"sentence": str, "attributed": bool}]}\n'
        f"CONTEXT:\n{_ctx(contexts)}\n\nGROUND TRUTH:\n{ground_truth[:2000]}",
        "sentences",
    )
    return sum(_flag(s, "attributed") for s in sentences) / len(sentences) if sentences else 0.0
