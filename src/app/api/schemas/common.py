"""Common API request and response schemas."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class APIResponse(BaseModel, Generic[DataT]):
    """Standardized API response wrapper."""

    success: bool = True
    data: DataT | None = None
    error: dict[str, Any] | None = None
    correlation_id: str | None = None


class ErrorResponse(BaseModel):
    """Standardized error response body."""

    success: bool = False
    error: dict[str, Any] = Field(
        ...,
        example={
            "category": "SQL_VALIDATION_FAILURE",
            "message": "Only SELECT queries are permitted.",
            "details": {},
        },
    )
    correlation_id: str | None = None


class HealthCheckResponse(BaseModel):
    """System health check status response."""

    status: str = "ok"  # "ok" or "degraded"
    app_version: str = "0.1.0"
    dependencies: dict[str, bool] = Field(
        ...,
        example={
            "database": True,
            "qdrant": True,
            "ollama": True,
            "chat_model_available": True,
            "embedding_model_available": True,
        },
    )
