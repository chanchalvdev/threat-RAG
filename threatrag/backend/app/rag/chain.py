from collections.abc import AsyncIterator

from langchain_openai import ChatOpenAI
from qdrant_client.models import ScoredPoint

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import QueryRequest, RAGResponse, SourceDoc
from app.rag.embedder import BaseEmbedder
from app.rag.prompts import RAG_PROMPT
from app.rag.sanitiser import sanitise_output
from app.rag.store import QdrantStore

log = get_logger(__name__)


def _build_llm() -> ChatOpenAI:
    s = get_settings()
    return ChatOpenAI(
        model=s.llm_model,
        openai_api_key=s.kimchi_api_key,  # type: ignore[arg-type]
        openai_api_base=s.kimchi_base_url,
        streaming=True,
    )


def _point_to_source(p: ScoredPoint) -> SourceDoc:
    payload = p.payload or {}
    return SourceDoc(
        text=payload.get("text", ""),
        source=payload.get("source", ""),
        doc_type=payload.get("doc_type", ""),
        score=p.score,
    )


def _format_context(sources: list[SourceDoc]) -> str:
    return "\n---\n".join(
        f"[Source: {s.source} ({s.doc_type})]\n{s.text}" for s in sources
    )


class ThreatRAGChain:
    def __init__(self, store: QdrantStore, embedder: BaseEmbedder):
        self._store = store
        self._embedder = embedder
        self._llm = _build_llm()

    async def query(self, req: QueryRequest) -> RAGResponse:
        s = get_settings()
        vector = await self._embedder.embed(req.question)
        hits = await self._store.search(vector, k=req.k or s.retrieval_k, doc_types=req.doc_types)
        sources = [_point_to_source(h) for h in hits]

        confidence = "low" if len(sources) < 2 else "high"
        context = _format_context(sources)
        prompt = RAG_PROMPT.format_messages(context=context, question=req.question)

        response = await self._llm.ainvoke(prompt)
        answer = sanitise_output(str(response.content))
        tokens = getattr(response, "usage_metadata", {}) or {}

        log.info("rag_query", sources=len(sources), confidence=confidence)
        return RAGResponse(
            answer=answer,
            sources=sources,
            tokens_used=tokens.get("total_tokens", 0),
            confidence=confidence,
        )

    async def astream(self, req: QueryRequest) -> AsyncIterator[tuple[str, list[SourceDoc]]]:
        s = get_settings()
        vector = await self._embedder.embed(req.question)
        hits = await self._store.search(vector, k=req.k or s.retrieval_k, doc_types=req.doc_types)
        sources = [_point_to_source(h) for h in hits]

        yield ("__sources__", sources)

        context = _format_context(sources)
        prompt = RAG_PROMPT.format_messages(context=context, question=req.question)

        async for chunk in self._llm.astream(prompt):
            text = sanitise_output(str(chunk.content))
            if text:
                yield (text, [])
