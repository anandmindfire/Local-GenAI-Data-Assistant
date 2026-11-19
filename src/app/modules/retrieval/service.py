"""Vector storage and semantic retrieval service using Qdrant."""

import logging
import uuid
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
)

from app.core.config import settings
from app.core.exceptions import RetrievalFailureException, VectorStoreFailureException
from app.domain.models.document import DocumentChunk
from app.domain.models.retrieval import RetrievedChunk
from app.infrastructure.vector_store.qdrant_client import get_qdrant_client

logger = logging.getLogger(__name__)


def generate_point_id(chunk_id: str) -> str:
    """Generate a deterministic UUID v5 from chunk_id for stable Qdrant point IDs."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"urn:chunk:{chunk_id}"))


class VectorRetrievalService:
    """Service abstracting Qdrant vector operations, search, and cascading deletions."""

    def __init__(
        self,
        client: AsyncQdrantClient | None = None,
        collection_name: str | None = None,
    ) -> None:
        self.client = client or get_qdrant_client()
        self.collection_name = collection_name or settings.qdrant_collection

    async def upsert_chunks(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> None:
        """Batch upsert chunks and corresponding embedding vectors into Qdrant."""
        if not chunks:
            return

        if len(chunks) != len(embeddings):
            raise VectorStoreFailureException(
                f"Chunk count ({len(chunks)}) does not match embedding count ({len(embeddings)})",
                details={"chunk_count": len(chunks), "embedding_count": len(embeddings)},
            )

        points: list[PointStruct] = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            point_id = generate_point_id(chunk.chunk_id)
            payload = chunk.to_qdrant_payload()
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
            )

        try:
            # Batch upsert points
            batch_size = 64
            for i in range(0, len(points), batch_size):
                batch = points[i : i + batch_size]
                await self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch,
                    wait=True,
                )
            logger.info(
                f"Successfully upserted {len(points)} vectors into collection '{self.collection_name}'"
            )
        except Exception as e:
            logger.error(
                f"Failed to upsert vectors into Qdrant collection '{self.collection_name}': {e}"
            )
            raise VectorStoreFailureException(
                f"Vector upsert failed: {e}",
                details={"collection": self.collection_name, "error": str(e)},
            ) from e

    async def search(
        self,
        query_vector: list[float],
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        document_id: str | None = None,
        filename: str | None = None,
    ) -> list[RetrievedChunk]:
        """Perform semantic search against vector store with score thresholding and metadata filters."""
        k = top_k or settings.top_k
        threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else settings.similarity_threshold
        )

        filter_conditions: list[FieldCondition] = []
        if document_id:
            filter_conditions.append(
                FieldCondition(key="document_id", match=MatchValue(value=document_id))
            )
        if filename:
            filter_conditions.append(
                FieldCondition(key="filename", match=MatchValue(value=filename))
            )

        query_filter = Filter(must=filter_conditions) if filter_conditions else None

        try:
            # Qdrant client query / search points (query_points in modern qdrant-client)
            if hasattr(self.client, "query_points"):
                raw_res = await self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=k,
                    score_threshold=threshold,
                    query_filter=query_filter,
                    with_payload=True,
                )
                search_results = (
                    raw_res.points
                    if hasattr(raw_res, "points")
                    else (raw_res if isinstance(raw_res, list) else [])
                )
            else:
                search_results = await self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=k,
                    score_threshold=threshold,
                    query_filter=query_filter,
                    with_payload=True,
                )

            retrieved: list[RetrievedChunk] = []
            for hit in search_results:
                payload: dict[str, Any] = hit.payload or {}
                chunk = RetrievedChunk(
                    chunk_id=str(payload.get("chunk_id", hit.id)),
                    document_id=str(payload.get("document_id", "")),
                    content=str(payload.get("content", "")),
                    filename=str(payload.get("filename", "")),
                    file_type=str(payload.get("file_type", "")),
                    page_number=payload.get("page_number"),
                    chunk_index=int(payload.get("chunk_index", 0)),
                    score=float(hit.score),
                    metadata={
                        k: v
                        for k, v in payload.items()
                        if k
                        not in [
                            "chunk_id",
                            "document_id",
                            "content",
                            "filename",
                            "file_type",
                            "page_number",
                            "chunk_index",
                        ]
                    },
                )
                retrieved.append(chunk)

            logger.info(
                f"Semantic search retrieved {len(retrieved)} chunks "
                f"(top_k={k}, score_threshold={threshold})"
            )
            return retrieved

        except Exception as e:
            logger.error(f"Semantic search query failed on '{self.collection_name}': {e}")
            raise RetrievalFailureException(
                f"Failed to execute semantic search: {e}",
                details={"collection": self.collection_name, "error": str(e)},
            ) from e

    async def delete_document_vectors(self, document_id: str) -> None:
        """Cascade delete all vectors in Qdrant associated with a document_id."""
        try:
            selector = FilterSelector(
                filter=Filter(
                    must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
                )
            )
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=selector,
                wait=True,
            )
            logger.info(
                f"Deleted all vectors for document_id='{document_id}' from '{self.collection_name}'"
            )
        except Exception as e:
            logger.error(
                f"Failed to delete vectors for document_id='{document_id}' in '{self.collection_name}': {e}"
            )
            raise VectorStoreFailureException(
                f"Failed to delete document vectors: {e}",
                details={"document_id": document_id, "error": str(e)},
            ) from e


_vector_service: VectorRetrievalService | None = None


def get_vector_service() -> VectorRetrievalService:
    """Get or instantiate singleton VectorRetrievalService."""
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorRetrievalService()
    return _vector_service
