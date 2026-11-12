"""ThreatRAGChain: answers from retrieved context, abstains when retrieval finds nothing relevant."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.schemas import QueryRequest
from app.rag.chain import ABSTAIN_ANSWER, ThreatRAGChain
from tests.conftest import make_point


@pytest.fixture
def mock_llm():
    response = MagicMock(content="T1110.001 is Password Guessing [Source: test.json].", usage_metadata={"total_tokens": 200})
    return MagicMock(ainvoke=AsyncMock(return_value=response))


@pytest.fixture
def chain(retriever, mock_llm):
    with patch("app.rag.chain._build_llm", return_value=mock_llm):
        return ThreatRAGChain(retriever=retriever)


async def test_query_answers_with_sources_and_token_count(chain, mock_store, mock_llm):
    mock_store.candidates.return_value = ([make_point("a", "Password Guessing", 0.92, technique_id="T1110.001"),
                                           make_point("b", "OWASP item", 0.8, doc_type="owasp_llm")], [])
    result = await chain.query(QueryRequest(question="How does password guessing work?"))
    assert "Password Guessing" in result.answer and result.tokens_used == 200
    assert [(s.ref_id, s.score, s.doc_type) for s in result.sources] == [("T1110.001", 0.92, "mitre_attack"), ("", 0.8, "owasp_llm")]
    assert result.confidence == "high" and not result.abstained
    context = mock_llm.ainvoke.await_args.args[0][1].content
    assert "[Source: test.json · T1110.001 (mitre_attack)]" in context


async def test_query_passes_doc_type_filter(chain, mock_store):
    await chain.query(QueryRequest(question="What MITRE techniques exist?", doc_types=["mitre_attack"]))
    assert mock_store.candidates.await_args.args[3] == ["mitre_attack"]


async def test_weak_match_is_low_confidence(chain, mock_store):
    mock_store.candidates.return_value = ([make_point("a", score=0.6)], [])
    assert (await chain.query(QueryRequest(question="What is this rare technique?"))).confidence == "low"


@pytest.mark.parametrize("points", [[], [make_point("a", score=0.31)]])
async def test_abstains_without_calling_the_llm(chain, mock_store, mock_llm, points):
    mock_store.candidates.return_value = (points, [])
    result = await chain.query(QueryRequest(question="What is the capital of Australia?"))
    assert result.abstained and result.confidence == "none" and result.sources == []
    assert result.answer == ABSTAIN_ANSWER
    mock_llm.ainvoke.assert_not_awaited()


async def test_stream_yields_sources_then_chunks(chain, mock_store, mock_llm):
    mock_store.candidates.return_value = ([make_point("a", score=0.9)], [])

    async def tokens(_prompt):
        for text in ("Hello ", "", "world"):
            yield MagicMock(content=text)

    mock_llm.astream = tokens
    events = [e async for e in chain.astream(QueryRequest(question="How does password guessing work?"))]
    assert events[0][0] == "__sources__" and len(events[0][1]) == 1
    assert [text for text, _ in events[1:]] == ["Hello ", "world"]


async def test_stream_abstains(chain):
    events = [e async for e in chain.astream(QueryRequest(question="What is the capital of Australia?"))]
    assert events == [("__sources__", []), (ABSTAIN_ANSWER, [])]
