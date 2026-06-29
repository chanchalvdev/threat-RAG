"""Unit tests for ThreatRAGChain."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_client.models import ScoredPoint

from app.models.schemas import QueryRequest, RAGResponse
from app.rag.chain import ThreatRAGChain


def _make_scored_point(text: str, doc_type: str, score: float = 0.9) -> ScoredPoint:
    p = MagicMock(spec=ScoredPoint)
    p.payload = {"text": text, "source": "test.json", "doc_type": doc_type}
    p.score = score
    return p


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    response = MagicMock()
    response.content = "T1110.001 is Password Guessing, a brute-force technique."
    response.usage_metadata = {"total_tokens": 200}
    llm.ainvoke = AsyncMock(return_value=response)
    llm.astream = AsyncMock()
    return llm


@pytest.fixture
def chain(mock_store, mock_embedder, mock_llm):
    with patch("app.rag.chain._build_llm", return_value=mock_llm):
        c = ThreatRAGChain(store=mock_store, embedder=mock_embedder)
        c._llm = mock_llm
        return c


@pytest.mark.asyncio
async def test_query_returns_rag_response(chain, mock_store):
    mock_store.search.return_value = [
        _make_scored_point("Password Guessing is T1110.001", "mitre_attack", 0.95),
        _make_scored_point("OWASP Top 10 item", "owasp_llm", 0.80),
        _make_scored_point("Another source", "mitre_attack", 0.75),
    ]

    req = QueryRequest(question="What is T1110.001 Password Guessing?", k=6)
    result = await chain.query(req)

    assert isinstance(result, RAGResponse)
    assert len(result.sources) == 3
    assert "Password Guessing" in result.answer
    assert result.tokens_used == 200


@pytest.mark.asyncio
async def test_query_sources_have_correct_fields(chain, mock_store):
    mock_store.search.return_value = [
        _make_scored_point("T1110 text", "mitre_attack", 0.92),
    ]

    req = QueryRequest(question="What is brute force technique?")
    result = await chain.query(req)

    src = result.sources[0]
    assert src.doc_type == "mitre_attack"
    assert src.score == 0.92
    assert src.source == "test.json"


@pytest.mark.asyncio
async def test_query_with_doc_type_filter_passes_filter(chain, mock_store):
    mock_store.search.return_value = []
    req = QueryRequest(question="What MITRE techniques exist?", doc_types=["mitre_attack"])

    await chain.query(req)

    call_kwargs = mock_store.search.call_args
    assert call_kwargs.kwargs.get("doc_types") == ["mitre_attack"]


@pytest.mark.asyncio
async def test_query_low_confidence_when_few_sources(chain, mock_store):
    mock_store.search.return_value = [
        _make_scored_point("One source only", "mitre_attack", 0.60),
    ]
    req = QueryRequest(question="What is this rare technique?")
    result = await chain.query(req)
    assert result.confidence == "low"


@pytest.mark.asyncio
async def test_query_high_confidence_with_multiple_sources(chain, mock_store):
    mock_store.search.return_value = [
        _make_scored_point("Source 1", "mitre_attack", 0.9),
        _make_scored_point("Source 2", "mitre_attack", 0.85),
    ]
    req = QueryRequest(question="What is T1055 Process Injection?")
    result = await chain.query(req)
    assert result.confidence == "high"
