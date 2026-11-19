"""API tests for the /chat endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_chat_endpoint_document_query(mocker):
    """Test /chat endpoint returning document RAG answer."""
    mocker.patch(
        "app.api.routes.chat.execute_assistant_workflow",
        new_callable=mocker.AsyncMock,
        return_value={
            "conversation_id": "conv_123",
            "answer": "Employees receive 24 paid leaves annually.",
            "intent": "document",
            "sources": [{"filename": "leave-policy.pdf", "page_number": 1}],
            "sql_results": None,
            "execution_metadata": {"rag_confidence": "high"},
        },
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"message": "What is our leave policy?", "conversation_id": "conv_123"}
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == "conv_123"
        assert data["intent"] == "document"
        assert "24 paid leaves" in data["answer"]
        assert len(data["sources"]) == 1
        assert "X-Correlation-ID" in response.headers


@pytest.mark.asyncio
async def test_chat_endpoint_sql_query(mocker):
    """Test /chat endpoint returning SQL Agent answer."""
    mocker.patch(
        "app.api.routes.chat.execute_assistant_workflow",
        new_callable=mocker.AsyncMock,
        return_value={
            "conversation_id": "conv_456",
            "answer": "The top customer is Alice Smith with $4,099.47 in revenue.",
            "intent": "sql",
            "sources": [],
            "sql_results": [{"first_name": "Alice", "revenue": 4099.47}],
            "execution_metadata": {"sql_row_count": 1},
        },
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"message": "Who is the top customer?"}
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "sql"
        assert "Alice Smith" in data["answer"]
        assert data["sql_results"] is not None


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test GET / root info endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "local-genai-assistant"
        assert data["docs"] == "/docs"
        assert data["health"] == "/api/v1/health"


@pytest.mark.asyncio
async def test_chat_endpoint_empty_message_validation():
    """Test validation rejection on empty message."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"message": ""}
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["error"]["category"] == "VALIDATION_ERROR"
