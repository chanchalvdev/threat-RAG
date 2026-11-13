"""Real Qdrant: named dense + sparse vectors, exact lookup, lexical recall, filters, idempotency."""
import uuid

import pytest
from qdrant_client import models as qm

from app.rag.ingestion import Chunk, index_chunks
from app.rag.retriever import Retriever
from app.rag.store import LegacyCollectionError, QdrantStore
from tests.integration.conftest import DIM, FakeEmbedder, require

pytestmark = pytest.mark.integration


def _chunk(key: str, text: str, **payload) -> Chunk:
    return Chunk(key=key, text=text, payload={"source": "it", "doc_type": "mitre_attack", **payload})


CORPUS = [
    _chunk("a", "Technique: Password Spraying\nID: T1110.003\nOne password tried against many accounts.", technique_id="T1110.003", section="description"),
    _chunk("b", "Technique: Password Spraying\nID: T1110.003\nMitigations: multi-factor authentication.", technique_id="T1110.003", section="mitigations"),
    _chunk("c", "Technique: Kerberoasting\nID: T1558.003\nService tickets are cracked offline.", technique_id="T1558.003", section="description"),
    _chunk("d", "Technique: PowerShell\nID: T1059.001\nAdversaries abuse PowerShell commands.", technique_id="T1059.001", section="description"),
    _chunk("e", "OWASP LLM01 Prompt Injection: untrusted input alters model behaviour.", doc_type="owasp_llm", owasp_id="LLM01"),
    *[_chunk(f"n{i}", f"Unrelated filler document number {i} about network hardware inventory.") for i in range(30)],
]


@pytest.fixture
async def store(settings):
    require(settings.qdrant_url, 6333, "Qdrant")
    store = QdrantStore(url=settings.qdrant_url, collection=f"it_{uuid.uuid4().hex[:12]}", vector_size=DIM,
                        api_key=settings.qdrant_api_key)
    await store.ensure_collection()
    await index_chunks(CORPUS, store, FakeEmbedder())
    yield store
    await store._client.delete_collection(store.collection)


async def test_exact_identifier_lookup_returns_the_technique_description_first(store):
    found = await Retriever(store, FakeEmbedder()).retrieve("What is T1110.003?", k=4)
    assert found.hits[0].exact and found.hits[0].payload["technique_id"] == "T1110.003"
    assert found.hits[0].payload["section"] == "description" and found.confidence == "high"


async def test_lexical_side_finds_a_rare_term_that_random_dense_vectors_cannot(store):
    found = await Retriever(store, FakeEmbedder()).retrieve("how does kerberoasting work", k=3)
    assert "T1558.003" in [h.payload.get("technique_id") for h in found.hits]
    assert all(0.0 <= abs(h.score) <= 1.0 for h in found.hits)  # scores are cosine, never raw BM25


async def test_owasp_identifier_and_doc_type_filter(store):
    retriever = Retriever(store, FakeEmbedder())
    assert (await retriever.retrieve("Explain LLM01 please", k=3)).hits[0].payload["owasp_id"] == "LLM01"
    filtered = await retriever.retrieve("prompt injection untrusted input", k=5, doc_types=["owasp_llm"])
    assert {h.payload["doc_type"] for h in filtered.hits} == {"owasp_llm"}


async def test_reingest_overwrites_and_counts_by_doc_type(store):
    before = await store.total()
    await index_chunks(CORPUS, store, FakeEmbedder())
    assert await store.total() == before == len(CORPUS)
    assert await store.count_by_doc_type() == {"mitre_attack": len(CORPUS) - 1, "owasp_llm": 1}
    assert (await store.technique_names()).keys() == {"T1110.003", "T1558.003", "T1059.001"}


async def test_pre_hybrid_collection_is_refused(settings):
    require(settings.qdrant_url, 6333, "Qdrant")
    store = QdrantStore(url=settings.qdrant_url, collection=f"it_legacy_{uuid.uuid4().hex[:8]}", vector_size=DIM)
    await store._client.create_collection(store.collection, vectors_config=qm.VectorParams(size=DIM, distance=qm.Distance.COSINE))
    try:
        with pytest.raises(LegacyCollectionError):
            await store.ensure_collection()
    finally:
        await store._client.delete_collection(store.collection)
