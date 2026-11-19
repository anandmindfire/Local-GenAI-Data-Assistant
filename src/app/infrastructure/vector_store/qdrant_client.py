"""Qdrant client connection and lifecycle management."""

import logging

from qdrant_client import AsyncQdrantClient

from app.core.config import settings

logger = logging.getLogger(__name__)

_qdrant_client: AsyncQdrantClient | None = None


def get_qdrant_client() -> AsyncQdrantClient:
    """Get or create singleton AsyncQdrantClient instance."""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            grpc_port=settings.qdrant_grpc_port,
            timeout=settings.qdrant_timeout,
            prefer_grpc=False,
        )
    return _qdrant_client


async def close_qdrant_client() -> None:
    """Close Qdrant client session on shutdown."""
    global _qdrant_client
    if _qdrant_client is not None:
        await _qdrant_client.close()
        _qdrant_client = None
        logger.info("Qdrant client session closed")


async def check_qdrant_health() -> bool:
    """Check connectivity to Qdrant vector database."""
    try:
        client = get_qdrant_client()
        await client.get_collections()
        return True
    except Exception as e:
        logger.warning(f"Qdrant health check failed: {e}")
        return False
