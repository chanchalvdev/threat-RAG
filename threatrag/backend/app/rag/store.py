from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    Filter,
    FieldCondition,
    MatchValue,
    PointStruct,
    ScoredPoint,
    VectorParams,
    PayloadSchemaType,
)

from app.core.logging import get_logger

log = get_logger(__name__)
LEGACY_EMBEDDING_TAG = "ollama:nomic-embed-text"  # points ingested before tagging existed


class EmbeddingMismatchError(RuntimeError):
    """The collection holds vectors from a different embedder than the one configured."""


class QdrantStore:
    def __init__(self, url: str, collection: str, vector_size: int = 768, api_key: str = ""):
        self.collection = collection
        self.vector_size = vector_size
        kwargs: dict = {"url": url}
        if api_key:
            kwargs["api_key"] = api_key
        self._client = AsyncQdrantClient(**kwargs)

    async def ensure_collection(self) -> None:
        existing = await self._client.get_collections()
        names = [c.name for c in existing.collections]
        if self.collection not in names:
            await self._client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )
            for field in ("source", "doc_type", "chunk_index"):
                await self._client.create_payload_index(
                    collection_name=self.collection,
                    field_name=field,
                    field_schema=PayloadSchemaType.KEYWORD,
                )
            log.info("collection_created", name=self.collection)

    async def assert_embedding(self, tag: str) -> None:
        """Refuse to mix vector spaces: same dimension does not mean comparable vectors."""
        points, _ = await self._client.scroll(collection_name=self.collection, limit=1, with_payload=True)
        if not points:
            return
        found = (points[0].payload or {}).get("embedding_model", LEGACY_EMBEDDING_TAG)
        if found != tag:
            raise EmbeddingMismatchError(
                f"Collection '{self.collection}' was built with {found}, but {tag} is configured. "
                "Set QDRANT_COLLECTION to a new name and re-ingest."
            )

    async def technique_names(self) -> dict[str, str]:
        """Map of MITRE technique ID -> canonical name from the ingested corpus."""
        names: dict[str, str] = {}
        doc_filter = Filter(must=[FieldCondition(key="doc_type", match=MatchValue(value="mitre_attack"))])
        offset = None
        while True:
            points, offset = await self._client.scroll(
                collection_name=self.collection, scroll_filter=doc_filter, limit=500,
                with_payload=["technique_id", "name"], offset=offset,
            )
            for p in points:
                payload = p.payload or {}
                if payload.get("technique_id"):
                    names[payload["technique_id"]] = payload.get("name", "")
            if offset is None:
                return names

    async def upsert(self, points: list[PointStruct]) -> None:
        await self._client.upsert(collection_name=self.collection, points=points)

    async def search(
        self,
        vector: list[float],
        k: int,
        doc_types: list[str] | None = None,
    ) -> list[ScoredPoint]:
        query_filter: Filter | None = None
        if doc_types:
            query_filter = Filter(
                should=[
                    FieldCondition(key="doc_type", match=MatchValue(value=dt))
                    for dt in doc_types
                ]
            )
        result = await self._client.query_points(
            collection_name=self.collection,
            query=vector,
            limit=k,
            query_filter=query_filter,
            with_payload=True,
        )
        return result.points

    async def total(self) -> int:
        info = await self._client.get_collection(self.collection)
        return info.points_count or 0

    async def count_by_doc_type(self) -> dict[str, int]:
        result = await self._client.facet(collection_name=self.collection, key="doc_type", limit=50, exact=True)
        return {str(hit.value): hit.count for hit in result.hits}
