"""Sparse encoding, rank fusion, the hybrid retriever and the reranker (no network)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.rag import reranker as reranker_mod
from app.rag import retriever as retriever_mod
from app.rag.fusion import rrf
from app.rag.retriever import Retriever
from app.rag.sparse import encode_document, encode_query, extract_ids, tokenize
from tests.conftest import make_point


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_tokenize_keeps_identifiers_whole_and_adds_the_parent_technique():
    assert tokenize("What is T1110.003 and CVE-2021-44228 in LLM01?") == ["t1110.003", "t1110", "cve-2021-44228", "llm01"]
    assert tokenize("the of a") == []


def test_extract_ids_is_ordered_and_deduplicated():
    assert extract_ids("t1110.003 vs T1059, llm07 and T1110.003") == ["T1110.003", "T1059", "LLM07"]
    assert extract_ids("no identifiers here, not even T12") == []


def test_document_encoding_saturates_term_frequency():
    once, many = encode_document("kerberos ticket"), encode_document("kerberos kerberos kerberos kerberos ticket")
    assert once.indices == sorted(once.indices) and len(once.indices) == 2
    assert max(many.values) < 2 * max(once.values)  # 4x the occurrences is far less than 4x the weight
    query = encode_query("kerberos kerberos")
    assert query.values == [1.0] and query.indices[0] in once.indices
    assert encode_query("the of").indices == []


def test_rrf_rewards_agreement_between_rankings():
    assert [item for item, _ in rrf([["a", "b", "c"], ["b", "d"]])][0] == "b"
    assert rrf([]) == [] and [i for i, _ in rrf([["x", "y"]])] == ["x", "y"]


async def test_hybrid_fuses_dense_and_lexical_candidates(mock_store, retriever):
    dense = [make_point("a", score=0.8), make_point("b", score=0.7)]
    lexical = [make_point("b", score=9.0), make_point("c", score=5.0)]
    mock_store.candidates.return_value = (dense, lexical)
    mock_store.dense_scores.return_value = {"c": 0.41}
    found = await retriever.retrieve("kerberos ticket abuse", k=3)
    assert [h.id for h in found.hits] == ["b", "a", "c"]
    assert [h.score for h in found.hits] == [0.7, 0.8, 0.41]  # always cosine, never the BM25 score
    mock_store.dense_scores.assert_awaited_once()
    assert found.confidence == "high" and found.top_score == 0.8


async def test_exact_identifier_goes_first_and_is_always_confident(mock_store, retriever):
    mock_store.candidates.return_value = ([make_point("x", score=0.3)], [])
    mock_store.by_ids.return_value = [
        make_point("m", technique_id="T1110.003", section="mitigations", chunk_index=5),
        make_point("d", technique_id="T1110.003", section="description", chunk_index=4),
    ]
    mock_store.dense_scores.return_value = {"d": 0.45, "m": 0.4}
    found = await retriever.retrieve("What is T1110.003?", k=4)
    assert [h.id for h in found.hits] == ["d", "m", "x"] and found.hits[0].exact
    assert found.confidence == "high" and not found.abstain
    mock_store.by_ids.assert_awaited_once_with(["T1110.003"])


async def test_exact_matches_respect_doc_type_filter(mock_store, retriever):
    mock_store.by_ids.return_value = [make_point("d", technique_id="T1110", doc_type="mitre_attack")]
    found = await retriever.retrieve("T1110 in OWASP?", k=4, doc_types=["owasp_llm"])
    assert found.hits == [] and found.abstain


@pytest.mark.parametrize("overrides,sparse_used,ids_used", [
    ({"retrieval_mode": "dense"}, False, True), ({"exact_match": False}, True, False),
])
async def test_ablation_switches(mock_store, retriever, overrides, sparse_used, ids_used):
    with patch.object(retriever_mod, "get_settings", return_value=_settings(**overrides)):
        await retriever.retrieve("What is T1110.003?", k=4)
    assert (mock_store.candidates.await_args.args[1] is not None) is sparse_used
    assert mock_store.by_ids.await_count == int(ids_used)


async def test_reranker_reorders_but_keeps_exact_matches_first(mock_store, mock_embedder):
    mock_store.candidates.return_value = ([make_point("a", score=0.9), make_point("b", score=0.8)], [])
    mock_store.by_ids.return_value = [make_point("e", technique_id="T1055")]
    rerank = MagicMock(score=AsyncMock(return_value=[0.1, 0.2, 0.9]))
    found = await Retriever(mock_store, mock_embedder, rerank).retrieve("T1055 process injection", k=3)
    assert [h.id for h in found.hits] == ["e", "b", "a"] and found.hits[1].rerank == 0.9


async def test_cross_encoder_loads_lazily_and_scores_off_the_loop():
    model = MagicMock(rerank=MagicMock(return_value=iter([1.5, -2.0])))
    encoder = reranker_mod.CrossEncoderReranker("some-model")
    assert await encoder.score("q", []) == [] and encoder._model is None
    with patch("fastembed.rerank.cross_encoder.TextCrossEncoder", return_value=model) as ctor:
        assert await encoder.score("q", ["a", "b"]) == [1.5, -2.0]
        await encoder.score("q", ["a"])
    ctor.assert_called_once_with(model_name="some-model")


def test_get_reranker_follows_settings():
    reranker_mod.get_reranker.cache_clear()
    with patch.object(reranker_mod, "get_settings", return_value=_settings(reranker="none")):
        assert reranker_mod.get_reranker() is None
    reranker_mod.get_reranker.cache_clear()
    with patch.object(reranker_mod, "get_settings", return_value=_settings(reranker="cross_encoder")):
        assert isinstance(reranker_mod.get_reranker(), reranker_mod.CrossEncoderReranker)
    reranker_mod.get_reranker.cache_clear()


async def test_one_technique_cannot_fill_the_context(mock_store, retriever):
    crowd = [make_point(f"k{i}", score=0.9 - i / 100, technique_id="T1110") for i in range(5)]
    mock_store.candidates.return_value = ([*crowd, make_point("other", score=0.6, technique_id="T1003")], [])
    found = await retriever.retrieve("credential guessing and dumping", k=3)
    assert [h.id for h in found.hits] == ["k0", "k1", "other"]
