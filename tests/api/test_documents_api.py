"""API tests for the /documents endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.dependencies import get_db
from app.domain.models.document import IngestionResult
from app.infrastructure.database.models.base import Base
from app.infrastructure.database.models.document import DocumentModel
from app.main import app


@pytest.fixture
async def override_db_session():
    """In-memory SQLite session override for API routes."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_db_override():
        async with session_maker() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db] = _get_db_override
    yield session_maker
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_upload_document_success(override_db_session, mocker):
    """Test successful document upload and ingestion."""
    mocker.patch(
        "app.modules.ingestion.service.DocumentIngestionService.ingest_file",
        new_callable=mocker.AsyncMock,
        return_value=IngestionResult(
            document_id="doc_test_123",
            filename="leave_policy.md",
            file_type="md",
            chunk_count=3,
            status="created",
            message="Document successfully created with 3 chunks indexed.",
        ),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("leave_policy.md", b"# Leave Policy\nContent here", "text/markdown")}
        response = await client.post("/api/v1/documents/ingest", files=files)
        assert response.status_code == 201
        data = response.json()
        assert data["document_id"] == "doc_test_123"
        assert data["chunk_count"] == 3
        assert data["status"] == "created"


@pytest.mark.asyncio
async def test_upload_unsupported_file_extension(override_db_session):
    """Test rejection of unsupported file extensions."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("script.py", b"print('hello')", "text/x-python")}
        response = await client.post("/api/v1/documents/ingest", files=files)
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["error"]["category"] == "SECURITY_VIOLATION"


@pytest.mark.asyncio
async def test_list_and_delete_documents(override_db_session, mocker):
    """Test listing paginated documents and cascading deletion."""
    # Pre-populate a document
    async with override_db_session() as session:
        doc = DocumentModel(
            document_id="doc_abc",
            filename="handbook.pdf",
            file_type="pdf",
            file_size_bytes=1024,
            content_hash="hash_abc",
            chunk_count=5,
        )
        session.add(doc)
        await session.commit()

    mocker.patch(
        "app.modules.retrieval.service.VectorRetrievalService.delete_document_vectors",
        new_callable=mocker.AsyncMock,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. List via versioned and root paths
        list_resp = await client.get("/api/v1/documents")
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total_count"] == 1
        assert data["items"][0]["document_id"] == "doc_abc"

        root_list_resp = await client.get("/documents")
        assert root_list_resp.status_code == 200
        assert root_list_resp.json()["total_count"] == 1

        # 2. Delete existing
        del_resp = await client.delete("/api/v1/documents/doc_abc")
        assert del_resp.status_code == 200
        assert "successfully deleted" in del_resp.json()["message"]

        # 3. Delete non-existent -> 404
        not_found_resp = await client.delete("/api/v1/documents/doc_abc")
        assert not_found_resp.status_code == 404
        assert not_found_resp.json()["error"]["category"] == "DOCUMENT_NOT_FOUND"
