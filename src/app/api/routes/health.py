"""Health check and dependency readiness route."""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.schemas.common import HealthCheckResponse
from app.infrastructure.database.connection import check_database_health
from app.infrastructure.llm.ollama_client import check_ollama_health
from app.infrastructure.vector_store.qdrant_client import check_qdrant_health

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> JSONResponse:
    """Detailed health check endpoint evaluating all dependencies."""
    db_healthy = await check_database_health()
    qdrant_healthy = await check_qdrant_health()
    ollama_online, model_status = await check_ollama_health()

    dependencies = {
        "database": db_healthy,
        "qdrant": qdrant_healthy,
        "ollama": ollama_online,
        "chat_model_available": model_status["chat_model_available"],
        "embedding_model_available": model_status["embedding_model_available"],
    }

    # System is considered overall healthy if primary services are online
    is_healthy = db_healthy and qdrant_healthy and ollama_online
    status = "ok" if is_healthy else "degraded"
    status_code = 200 if is_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "app_version": "0.1.0",
            "dependencies": dependencies,
        },
    )
