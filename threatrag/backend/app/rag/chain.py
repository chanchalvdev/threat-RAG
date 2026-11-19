from collections.abc import AsyncIterator

from langchain_openai import ChatOpenAI

from app.core.llm import get_llm
from app.core.logging import get_logger
from app.core.telemetry import telemetry
from app.models.schemas import QueryRequest, RAGResponse, SourceDoc
from app.rag.prompts import RAG_PROMPT
from app.rag.retriever import Retrieval, Retriever
from app.guard.untrusted import wrap_untrusted
from app.rag.sanitiser import StreamSanitiser, sanitise_output

log = get_logger(__name__)
ABSTAIN_ANSWER = (
    "I could not find anything relevant to this question in the knowledge base "
    "(MITRE ATT&CK, OWASP LLM Top 10, uploaded documents), so I will not guess. "
    "Try naming a technique, tactic, technique ID or OWASP LLM risk."
)


def _build_llm() -> ChatOpenAI:
    return get_llm(streaming=True)


def _format_context(sources: list[SourceDoc]) -> str:
    return wrap_untrusted("knowledge_base", "\n---\n".join(
        f"[Source: {s.source}{' · ' + s.ref_id if s.ref_id else ''} ({s.doc_type})]\n{s.text}" for s in sources
    ))


class ThreatRAGChain:
    def __init__(self, retriever: Retriever):
        self._retriever = retriever
        self._llm = _build_llm()

    async def _retrieve(self, req: QueryRequest) -> tuple[Retrieval, list[SourceDoc]]:
        found = await self._retriever.retrieve(req.question, k=req.k, doc_types=req.doc_types)
        return found, [h.to_source() for h in found.hits]

    async def query(self, req: QueryRequest) -> RAGResponse:
        found, sources = await self._retrieve(req)
        if found.abstain:
            log.info("rag_abstained", top=round(found.top_score, 3))
            telemetry.count("rag_abstained")
            return RAGResponse(answer=ABSTAIN_ANSWER, sources=[], confidence="none", abstained=True)

        prompt = RAG_PROMPT.format_messages(context=_format_context(sources), question=req.question)
        response = await self._llm.ainvoke(prompt)
        tokens = getattr(response, "usage_metadata", {}) or {}
        log.info("rag_query", sources=len(sources), confidence=found.confidence)
        return RAGResponse(
            answer=sanitise_output(str(response.content)),
            sources=sources,
            tokens_used=tokens.get("total_tokens", 0),
            confidence=found.confidence,
        )

    async def astream(self, req: QueryRequest) -> AsyncIterator[tuple[str, list[SourceDoc]]]:
        found, sources = await self._retrieve(req)
        if found.abstain:
            yield ("__sources__", [])
            yield (ABSTAIN_ANSWER, [])
            return

        yield ("__sources__", sources)
        prompt = RAG_PROMPT.format_messages(context=_format_context(sources), question=req.question)
        clean = StreamSanitiser()
        async for chunk in self._llm.astream(prompt):
            if text := clean.feed(str(chunk.content)):
                yield (text, [])
        if tail := clean.flush():
            yield (tail, [])
