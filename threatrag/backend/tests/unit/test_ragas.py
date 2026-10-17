"""Unit tests for RAGAs-style evaluation (judge calls mocked — no network)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.evaluation import judge
from app.evaluation.ragas_eval import RagasScores, evaluate_response


def _patch_judge(**overrides: float):
    vals = {"faithfulness": 0.9, "answer_relevancy": 0.8, "context_precision": 1.0, "context_recall": 0.5}
    vals.update(overrides)
    return patch.multiple(
        "app.evaluation.judge",
        **{name: AsyncMock(return_value=v) for name, v in vals.items()},
    )


@pytest.mark.asyncio
async def test_evaluate_with_ground_truth_uses_four_metric_weights():
    with _patch_judge():
        r = await evaluate_response("q?", "a", ["ctx"], ground_truth="gt")
    assert r.context_recall == 0.5
    assert r.overall == round(0.9 * 0.3 + 0.8 * 0.3 + 1.0 * 0.2 + 0.5 * 0.2, 4)


@pytest.mark.asyncio
async def test_evaluate_without_ground_truth_skips_recall():
    recall = AsyncMock(return_value=0.5)
    with _patch_judge(), patch("app.evaluation.judge.context_recall", recall):
        r = await evaluate_response("q?", "a", ["ctx"])
    assert r.context_recall is None
    assert r.overall == round(0.9 * 0.35 + 0.8 * 0.35 + 1.0 * 0.3, 4)
    recall.assert_not_called()


@pytest.mark.asyncio
async def test_evaluate_returns_zero_scores_when_judge_fails():
    with _patch_judge(), patch(
        "app.evaluation.judge.faithfulness", AsyncMock(side_effect=RuntimeError("llm down"))
    ):
        r = await evaluate_response("q?", "a", ["ctx"])
    assert r == RagasScores()


def _llm_returning(text: str) -> MagicMock:
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content=text))
    return llm


@pytest.mark.asyncio
async def test_faithfulness_counts_supported_claims():
    reply = 'Sure: {"claims": [{"claim": "a", "supported": true}, {"claim": "b", "supported": false}]}'
    with patch("app.evaluation.judge.get_llm", return_value=_llm_returning(reply)):
        assert await judge.faithfulness("a. b.", ["ctx"]) == 0.5


@pytest.mark.asyncio
async def test_context_precision_is_average_precision():
    with patch("app.evaluation.judge.get_llm", return_value=_llm_returning('{"verdicts": [false, true, true]}')):
        score = await judge.context_precision("q", "ref", ["c1", "c2", "c3"])
    assert score == pytest.approx(((1 / 2) + (2 / 3)) / 2)


@pytest.mark.asyncio
async def test_judge_without_json_raises():
    with patch("app.evaluation.judge.get_llm", return_value=_llm_returning("no json here")):
        with pytest.raises(ValueError):
            await judge.context_recall("gt", ["ctx"])


@pytest.mark.asyncio
async def test_judge_accepts_bare_list_with_string_booleans():
    with patch("app.evaluation.judge.get_llm", return_value=_llm_returning('["true", "false", "yes"]')):
        score = await judge.context_precision("q", "ref", ["c1", "c2", "c3"])
    assert score == pytest.approx((1 + 2 / 3) / 2)


def test_cosine_similarity():
    assert judge._cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert judge._cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert judge._cosine([0.0, 0.0], [1.0, 0.0]) == 0.0
