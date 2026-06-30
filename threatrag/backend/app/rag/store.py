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

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)


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

    async def count_by_doc_type(self) -> dict[str, int]:
        settings = get_settings()
        info = await self._client.get_collection(settings.qdrant_collection)
        return {"total": info.points_count or 0}
