"""API tests for the /health endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_check_healthy(mocker):
    """Test /health when all dependencies are healthy."""
    mocker.patch("app.api.routes.health.check_database_health", return_value=True)
    mocker.patch("app.api.routes.health.check_qdrant_health", return_value=True)
    mocker.patch(
        "app.api.routes.health.check_ollama_health",
        return_value=(True, {"chat_model_available": True, "embedding_model_available": True}),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["dependencies"]["database"] is True
        assert data["dependencies"]["qdrant"] is True
        assert data["dependencies"]["ollama"] is True
        assert data["dependencies"]["chat_model_available"] is True

        # Test direct root endpoint /health
        root_resp = await client.get("/health")
        assert root_resp.status_code == 200
        assert root_resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_check_degraded(mocker):
    """Test /health when one dependency is offline."""
    mocker.patch("app.api.routes.health.check_database_health", return_value=False)
    mocker.patch("app.api.routes.health.check_qdrant_health", return_value=True)
    mocker.patch(
        "app.api.routes.health.check_ollama_health",
        return_value=(True, {"chat_model_available": True, "embedding_model_available": True}),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["dependencies"]["database"] is False
