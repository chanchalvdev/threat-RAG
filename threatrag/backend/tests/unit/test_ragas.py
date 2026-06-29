"""Unit tests for RAGAs evaluation."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.evaluation.ragas_eval import RagasScores, evaluate_response


def _mock_scores(include_recall: bool = True):
    row = {
        "faithfulness": 0.9,
        "answer_relevancy": 0.85,
        "context_precision": 0.8,
    }
    if include_recall:
        row["context_recall"] = 0.75
    df_mock = MagicMock()
    df_mock.__getitem__ = lambda self, key: row.get(key, 0.0)
    df_mock.get = lambda key, default=0.0: row.get(key, default)
    return df_mock


@pytest.mark.asyncio
async def test_evaluate_response_handles_exception():
    """When ragas raises, evaluate_response returns zero scores without crashing."""
    def boom(*args, **kwargs):
        raise RuntimeError("ragas not installed")

    with patch.dict("sys.modules", {"ragas": None, "datasets": None}):
        result = await evaluate_response(
            question="test", answer="test", contexts=["context"]
        )

    assert isinstance(result, RagasScores)
    assert result.faithfulness == 0.0
    assert result.overall == 0.0


@pytest.mark.asyncio
async def test_evaluate_response_zero_scores_on_import_error():
    """Gracefully handles missing ragas installation."""
    import importlib
    import sys

    ragas_backup = sys.modules.get("ragas")
    datasets_backup = sys.modules.get("datasets")
    sys.modules["ragas"] = None  # type: ignore[assignment]
    sys.modules["datasets"] = None  # type: ignore[assignment]

    try:
        result = await evaluate_response(
            question="What is T1110?",
            answer="Brute Force.",
            contexts=["T1110 covers brute force"],
            ground_truth="Brute Force",
        )
        assert result.faithfulness == 0.0
        assert result.context_recall is None
    finally:
        if ragas_backup is not None:
            sys.modules["ragas"] = ragas_backup
        elif "ragas" in sys.modules:
            del sys.modules["ragas"]
        if datasets_backup is not None:
            sys.modules["datasets"] = datasets_backup
        elif "datasets" in sys.modules:
            del sys.modules["datasets"]


@pytest.mark.asyncio
async def test_ragas_scores_model():
    """RagasScores model validates correctly."""
    scores = RagasScores(
        faithfulness=0.9,
        answer_relevancy=0.85,
        context_precision=0.8,
        context_recall=0.75,
        overall=0.83,
    )
    assert scores.faithfulness == 0.9
    assert scores.context_recall == 0.75


@pytest.mark.asyncio
async def test_ragas_scores_without_recall():
    """RagasScores allows None context_recall."""
    scores = RagasScores(
        faithfulness=0.88,
        answer_relevancy=0.82,
        context_precision=0.79,
        context_recall=None,
        overall=0.83,
    )
    assert scores.context_recall is None
