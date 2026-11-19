"""FastAPI dependency injection providers."""

import uuid
from collections.abc import AsyncGenerator

from fastapi import Header
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import correlation_id_ctx
from app.infrastructure.database.connection import get_session_factory
from app.infrastructure.vector_store.qdrant_client import get_qdrant_client


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency providing an async database session for request scope."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_vector_client() -> AsyncQdrantClient:
    """Dependency providing the async Qdrant client."""
    return get_qdrant_client()


def get_correlation_id(
    x_correlation_id: str | None = Header(None, alias="X-Correlation-ID"),
) -> str:
    """Dependency extracting or generating a unique correlation ID for the request."""
    correlation_id = x_correlation_id or str(uuid.uuid4())
    correlation_id_ctx.set(correlation_id)
    return correlation_id
