"""Offline evaluation over eval/golden.jsonl.

    python -m app.scripts.run_eval --label baseline            # retrieval metrics only
    python -m app.scripts.run_eval --label baseline --answers 20  # plus answer metrics on 20 items

Needs Qdrant and the embedder; --answers also needs the LLM and the judge.
"""
import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from app.api.deps import get_chain, get_retriever, get_store
from app.core.config import get_settings
from app.evaluation.golden import GoldenItem, load_golden, unknown_ids
from app.evaluation.harness import Answer, evaluate_answers, evaluate_retrieval
from app.evaluation.report import answer_table, retrieval_table
from app.evaluation.retrieval_metrics import Retrieved
from app.models.schemas import QueryRequest


async def _retrieve(question: str, k: int) -> list[Retrieved]:
    found = await get_retriever().retrieve(question, k=k)
    return [
        Retrieved(technique_id=h.payload.get("technique_id", ""), doc_type=h.payload.get("doc_type", ""),
                  text=h.payload.get("text", ""), score=found.top_score)
        for h in found.hits
    ]


async def _answer(question: str) -> Answer:
    response = await get_chain().query(QueryRequest(question=question))
    return Answer(text=response.answer, contexts=[s.text for s in response.sources], abstained=response.abstained)


def sample(items: list[GoldenItem], n: int) -> list[GoldenItem]:
    """Round-robin across categories so a small sample still covers every kind of question."""
    buckets: dict[str, list[GoldenItem]] = {}
    for item in items:
        buckets.setdefault(item.category, []).append(item)
    picked: list[GoldenItem] = []
    while len(picked) < min(n, len(items)):
        for bucket in buckets.values():
            if bucket and len(picked) < n:
                picked.append(bucket.pop(0))
    return picked


async def main(args: argparse.Namespace) -> None:
    items = load_golden(Path(args.golden))
    stale = unknown_ids(items, set(await get_store().technique_names()))
    if stale:
        raise SystemExit(f"Golden set names techniques missing from the corpus: {stale}")

    s = get_settings()
    result: dict = {
        "label": args.label, "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "collection": s.qdrant_collection, "embedding": f"{s.embedding_provider}:{s.embedding_model}",
        "retrieval_mode": s.retrieval_mode, "exact_match": s.exact_match, "reranker": s.reranker,
        "retrieval": await evaluate_retrieval(items, _retrieve, args.k),
    }
    print(f"## Retrieval — {args.label}\n\n{retrieval_table(result['retrieval'])}\n")
    if args.answers:
        result["generator"], result["judge"] = s.gemini_model if s.gemini_api_key else s.llm_model, s.judge_model or "same as generator"
        result["answers"] = await evaluate_answers(sample(items, args.answers), _answer, delay_s=args.delay)
        print(f"## Answers — {args.label}\n\n{answer_table(result['answers'])}\n")

    out = Path(args.out) / f"{args.label}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1))
    print(f"wrote {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", required=True, help="name of this run; becomes the results file name")
    parser.add_argument("--golden", default="eval/golden.jsonl")
    parser.add_argument("--out", default="eval/results")
    parser.add_argument("--k", type=int, default=6)
    parser.add_argument("--answers", type=int, default=0, help="number of items to generate and judge (0 = skip)")
    parser.add_argument("--delay", type=float, default=0.0, help="seconds between answer calls (rate limits)")
    asyncio.run(main(parser.parse_args()))
