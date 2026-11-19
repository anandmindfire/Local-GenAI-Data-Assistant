"""Unit tests for DocumentIngestionService with SQLite async database."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.database.models.base import Base
from app.modules.ingestion.service import DocumentIngestionService


@pytest.fixture
async def async_test_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_ingest_new_file(async_test_session, mocker):
    """Test ingesting a new markdown file."""
    mock_embedding = mocker.AsyncMock()
    mock_embedding.embed_documents.return_value = [[0.1, 0.2, 0.3, 0.4]]
    mock_vector = mocker.AsyncMock()

    service = DocumentIngestionService(
        embedding_service=mock_embedding,
        vector_service=mock_vector,
    )

    content = b"# Onboarding\nWelcome to our company!"
    res = await service.ingest_file(
        file_bytes=content,
        filename="onboarding.md",
        session=async_test_session,
    )

    assert res.status == "created"
    assert res.chunk_count >= 1
    assert res.filename == "onboarding.md"
    mock_vector.upsert_chunks.assert_called_once()

    # Re-ingest identical file -> should be skipped
    res_skip = await service.ingest_file(
        file_bytes=content,
        filename="onboarding.md",
        session=async_test_session,
    )
    assert res_skip.status == "skipped"


@pytest.mark.asyncio
async def test_delete_document_flow(async_test_session, mocker):
    """Test deleting an indexed document."""
    mock_embedding = mocker.AsyncMock()
    mock_embedding.embed_documents.return_value = [[0.1, 0.2, 0.3, 0.4]]
    mock_vector = mocker.AsyncMock()

    service = DocumentIngestionService(
        embedding_service=mock_embedding,
        vector_service=mock_vector,
    )

    content = b"Some secret document content."
    res = await service.ingest_file(
        file_bytes=content,
        filename="secret.txt",
        session=async_test_session,
    )

    # Delete
    deleted = await service.delete_document(res.document_id, async_test_session)
    assert deleted is True
    mock_vector.delete_document_vectors.assert_called_with(res.document_id)

    # Deleting non-existent document returns False
    not_found = await service.delete_document("doc_non_existent", async_test_session)
    assert not_found is False
