"""Golden set, retrieval metrics and the offline harness (no network)."""
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.evaluation.golden import GoldenItem, load_golden, unknown_ids
from app.evaluation.harness import Answer, evaluate_answers, evaluate_retrieval, looks_like_refusal
from app.evaluation.report import answer_table, retrieval_table
from app.evaluation.retrieval_metrics import Retrieved, first_relevant_rank, hit_at_k, mrr
from app.scripts.run_eval import sample

GOLDEN = Path(__file__).parents[2] / "eval" / "golden.jsonl"


def _item(**kw) -> GoldenItem:
    return GoldenItem(**{"id": "x1", "category": "id_lookup", "question": "q", "expected_ids": ["T1110.003"], **kw})


def test_shipped_golden_set_is_valid_and_covers_every_category():
    items = load_golden(GOLDEN)
    assert len(items) >= 60
    assert {i.category for i in items} == {"id_lookup", "name_lookup", "paraphrase", "owasp", "unanswerable"}
    assert all(not i.answerable for i in items if i.category == "unanswerable")


def test_golden_item_rejects_missing_or_contradictory_expectations():
    with pytest.raises(ValueError):
        GoldenItem(id="a", category="paraphrase", question="q")
    with pytest.raises(ValueError):
        GoldenItem(id="a", category="unanswerable", question="q", answerable=False, expected_ids=["T1110"])


def test_load_golden_rejects_duplicate_ids(tmp_path):
    line = _item().model_dump_json()
    path = tmp_path / "g.jsonl"
    path.write_text(f"{line}\n{line}\n")
    with pytest.raises(ValueError, match="duplicate"):
        load_golden(path)


def test_unknown_ids_reports_stale_expectations():
    assert unknown_ids([_item()], {"T1059"}) == ["T1110.003"]
    assert unknown_ids([_item()], {"T1110.003"}) == []


def test_rank_by_technique_id_and_by_keyword_ignoring_pdf_spacing():
    hits = [Retrieved(technique_id="T1059"), Retrieved(technique_id="T1110.003")]
    assert first_relevant_rank(_item(), hits) == 2
    owasp = GoldenItem(id="o", category="owasp", question="q", expected_doc_type="owasp_llm", keywords=["prompt injection"])
    assert first_relevant_rank(owasp, [Retrieved(doc_type="owasp_llm", text="Pro mpt  Injec tion risks")]) == 1
    assert first_relevant_rank(owasp, [Retrieved(doc_type="mitre_attack", text="prompt injection")]) is None


def test_hit_and_mrr():
    ranks = [1, 3, None, 2]
    assert hit_at_k(ranks, 1) == 0.25
    assert hit_at_k(ranks, 3) == 0.75
    assert mrr(ranks) == pytest.approx((1 + 1 / 3 + 0 + 1 / 2) / 4)
    assert hit_at_k([], 3) == 0.0 and mrr([]) == 0.0


async def test_evaluate_retrieval_summarises_by_category_and_skips_unanswerable():
    items = [_item(), _item(id="x2", expected_ids=["T9999"]), GoldenItem(id="u1", category="unanswerable", question="q", answerable=False)]

    async def retrieve(question: str, k: int) -> list[Retrieved]:
        return [Retrieved(technique_id="T1110.003", score=0.8)]

    result = await evaluate_retrieval(items, retrieve, k=6)
    assert result["overall"] == {"n": 2, "hit@1": 0.5, "hit@3": 0.5, "hit@6": 0.5, "mrr": 0.5}
    assert set(result["by_category"]) == {"id_lookup"}
    assert "id_lookup" in retrieval_table(result)


def test_refusal_uses_explicit_flag_before_heuristic():
    assert looks_like_refusal(Answer(text="The context does not contain that."))
    assert not looks_like_refusal(Answer(text="T1110.003 is Password Spraying."))
    assert not looks_like_refusal(Answer(text="The context does not contain that.", abstained=False))
    assert looks_like_refusal(Answer(text="anything", abstained=True))


async def test_evaluate_answers_scores_grounding_and_abstention():
    items = [_item(), GoldenItem(id="u1", category="unanswerable", question="capital?", answerable=False)]

    async def answer(question: str) -> Answer:
        if question == "capital?":
            return Answer(text="I cannot answer that from the knowledge base.")
        return Answer(text="`T1110.003` is Password Spraying [Source: mitre]", contexts=["ctx"])

    with patch("app.evaluation.judge.faithfulness", AsyncMock(return_value=0.75)):
        result = await evaluate_answers(items, answer)
    assert result["faithfulness"] == 0.75
    assert result["citation_rate"] == 1.0 and result["technique_id_accuracy"] == 1.0
    assert result["correct_abstention"] == 1.0 and result["false_abstention"] == 0.0
    assert "faithfulness" in answer_table(result)


def test_sample_takes_from_every_category_first():
    picked = sample(load_golden(GOLDEN), 5)
    assert len({i.category for i in picked}) == 5
