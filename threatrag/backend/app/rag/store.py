import asyncio
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client import models as qm
from qdrant_client.models import PointStruct, ScoredPoint, SparseVector

from app.core.logging import get_logger

log = get_logger(__name__)
DENSE, SPARSE = "dense", "sparse"
_KEYWORD_FIELDS = ("source", "doc_type", "technique_id", "owasp_id")


class EmbeddingMismatchError(RuntimeError):
    """The collection holds vectors from a different embedder than the one configured."""


class LegacyCollectionError(RuntimeError):
    """The collection predates hybrid search (single unnamed vector) and must be re-ingested."""


def _doc_filter(doc_types: list[str] | None) -> qm.Filter | None:
    if not doc_types:
        return None
    return qm.Filter(must=[qm.FieldCondition(key="doc_type", match=qm.MatchAny(any=doc_types))])


class QdrantStore:
    def __init__(self, url: str, collection: str, vector_size: int = 768, api_key: str = ""):
        self.collection = collection
        self.vector_size = vector_size
        kwargs: dict[str, Any] = {"url": url, "check_compatibility": False}
        if api_key:
            kwargs["api_key"] = api_key
        self._client = AsyncQdrantClient(**kwargs)

    async def ensure_collection(self) -> None:
        existing = await self._client.get_collections()
        if self.collection in [c.name for c in existing.collections]:
            vectors = (await self._client.get_collection(self.collection)).config.params.vectors
            if not isinstance(vectors, dict) or DENSE not in vectors:
                raise LegacyCollectionError(
                    f"Collection '{self.collection}' has no named dense/sparse vectors. "
                    "Set QDRANT_COLLECTION to a new name (e.g. threat_intel_v2) and re-ingest."
                )
            return
        await self._client.create_collection(
            collection_name=self.collection,
            vectors_config={DENSE: qm.VectorParams(size=self.vector_size, distance=qm.Distance.COSINE)},
            sparse_vectors_config={SPARSE: qm.SparseVectorParams(modifier=qm.Modifier.IDF)},
        )
        for field in _KEYWORD_FIELDS:
            await self._client.create_payload_index(
                collection_name=self.collection, field_name=field, field_schema=qm.PayloadSchemaType.KEYWORD,
            )
        log.info("collection_created", name=self.collection)

    async def assert_embedding(self, tag: str) -> None:
        """Refuse to mix vector spaces: same dimension does not mean comparable vectors."""
        points, _ = await self._client.scroll(collection_name=self.collection, limit=1, with_payload=True)
        found = (points[0].payload or {}).get("embedding_model") if points else None
        if found and found != tag:
            raise EmbeddingMismatchError(
                f"Collection '{self.collection}' was built with {found}, but {tag} is configured. "
                "Set QDRANT_COLLECTION to a new name and re-ingest."
            )

    async def upsert(self, points: list[PointStruct]) -> None:
        await self._client.upsert(collection_name=self.collection, points=points)

    async def _query(self, query: Any, using: str, limit: int, flt: qm.Filter | None) -> list[ScoredPoint]:
        result = await self._client.query_points(
            collection_name=self.collection, query=query, using=using, limit=limit, query_filter=flt, with_payload=True,
        )
        return result.points

    async def search(self, vector: list[float], k: int, doc_types: list[str] | None = None) -> list[ScoredPoint]:
        """Dense (semantic) search only."""
        return await self._query(vector, DENSE, k, _doc_filter(doc_types))

    async def candidates(
        self, vector: list[float], sparse: SparseVector | None, limit: int, doc_types: list[str] | None = None,
    ) -> tuple[list[ScoredPoint], list[ScoredPoint]]:
        """Dense and lexical candidate lists for fusion. `sparse=None` skips the lexical side."""
        flt = _doc_filter(doc_types)
        if sparse is None or not sparse.indices:
            return await self._query(vector, DENSE, limit, flt), []
        dense, lexical = await asyncio.gather(
            self._query(vector, DENSE, limit, flt), self._query(sparse, SPARSE, limit, flt),
        )
        return dense, lexical

    async def by_ids(self, ids: list[str], limit: int = 40) -> list[Any]:
        """Chunks whose technique_id or owasp_id is one of `ids` (exact identifier lookup)."""
        match = qm.MatchAny(any=ids)
        flt = qm.Filter(should=[qm.FieldCondition(key=f, match=match) for f in ("technique_id", "owasp_id")])
        points, _ = await self._client.scroll(
            collection_name=self.collection, scroll_filter=flt, limit=limit, with_payload=True,
        )
        return list(points)

    async def dense_scores(self, vector: list[float], point_ids: list[Any]) -> dict[Any, float]:
        """Cosine similarity of specific points to `vector` (for hits the dense search did not return)."""
        if not point_ids:
            return {}
        flt = qm.Filter(must=[qm.HasIdCondition(has_id=point_ids)])
        return {p.id: p.score for p in await self._query(vector, DENSE, len(point_ids), flt)}

    async def technique_names(self) -> dict[str, str]:
        """Map of MITRE technique ID -> canonical name from the ingested corpus."""
        names: dict[str, str] = {}
        flt = qm.Filter(must=[qm.FieldCondition(key="doc_type", match=qm.MatchValue(value="mitre_attack"))])
        offset = None
        while True:
            points, offset = await self._client.scroll(
                collection_name=self.collection, scroll_filter=flt, limit=500,
                with_payload=["technique_id", "name"], offset=offset,
            )
            for p in points:
                payload = p.payload or {}
                if payload.get("technique_id"):
                    names[payload["technique_id"]] = payload.get("name", "")
            if offset is None:
                return names

    async def total(self) -> int:
        info = await self._client.get_collection(self.collection)
        return info.points_count or 0

    async def count_by_doc_type(self) -> dict[str, int]:
        result = await self._client.facet(collection_name=self.collection, key="doc_type", limit=50, exact=True)
        return {str(hit.value): hit.count for hit in result.hits}
