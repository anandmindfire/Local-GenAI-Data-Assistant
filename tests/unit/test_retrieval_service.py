"""Unit tests for vector storage and retrieval operations."""

import pytest
from qdrant_client.http.models import ScoredPoint

from app.domain.models.document import DocumentChunk
from app.modules.retrieval.service import VectorRetrievalService, generate_point_id


def test_generate_point_id_stable():
    """Verify point ID is deterministic from chunk ID."""
    p1 = generate_point_id("doc_01_chunk_0000")
    p2 = generate_point_id("doc_01_chunk_0000")
    p3 = generate_point_id("doc_01_chunk_0001")
    assert p1 == p2
    assert p1 != p3


@pytest.mark.asyncio
async def test_upsert_chunks(mocker):
    """Test batch upsert into Qdrant."""
    mock_client = mocker.AsyncMock()
    service = VectorRetrievalService(client=mock_client, collection_name="test_col")

    chunks = [
        DocumentChunk(
            chunk_id="chunk_01",
            document_id="doc_01",
            content="Sample text",
            filename="sample.txt",
            file_type="txt",
            page_number=1,
            chunk_index=0,
            content_hash="h1",
        )
    ]
    embeddings = [[0.1, 0.2, 0.3, 0.4]]

    await service.upsert_chunks(chunks, embeddings)
    mock_client.upsert.assert_called_once()
    args, kwargs = mock_client.upsert.call_args
    assert kwargs["collection_name"] == "test_col"
    assert len(kwargs["points"]) == 1
    assert kwargs["points"][0].payload["chunk_id"] == "chunk_01"


@pytest.mark.asyncio
async def test_search_chunks(mocker):
    """Test semantic search with score threshold and mapping."""
    mock_client = mocker.AsyncMock()
    scored_points = [
        ScoredPoint(
            id="uuid-1",
            version=1,
            score=0.88,
            payload={
                "chunk_id": "chunk_01",
                "document_id": "doc_01",
                "content": "Employees have 24 days leave.",
                "filename": "leave.md",
                "file_type": "md",
                "page_number": 1,
                "chunk_index": 0,
            },
            vector=None,
        )
    ]
    mock_client.query_points.return_value = mocker.MagicMock(points=scored_points)
    mock_client.search.return_value = scored_points

    service = VectorRetrievalService(client=mock_client, collection_name="test_col")
    results = await service.search(
        query_vector=[0.1, 0.2, 0.3, 0.4],
        top_k=3,
        similarity_threshold=0.5,
    )

    assert len(results) == 1
    assert results[0].chunk_id == "chunk_01"
    assert results[0].score == 0.88
    assert "24 days leave" in results[0].content


@pytest.mark.asyncio
async def test_delete_document_vectors(mocker):
    """Test deleting all vectors associated with a document ID."""
    mock_client = mocker.AsyncMock()
    service = VectorRetrievalService(client=mock_client, collection_name="test_col")

    await service.delete_document_vectors("doc_01")
    mock_client.delete.assert_called_once()
    args, kwargs = mock_client.delete.call_args
    assert kwargs["collection_name"] == "test_col"
