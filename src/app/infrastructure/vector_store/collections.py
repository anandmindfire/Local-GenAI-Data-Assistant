"""Qdrant collection initialization and schema validation."""

import logging

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, PayloadSchemaType, VectorParams

from app.core.config import settings
from app.core.exceptions import VectorStoreFailureException

logger = logging.getLogger(__name__)


async def init_collections(client: AsyncQdrantClient | None = None) -> None:
    """Ensure Qdrant collections exist with correct vector parameters and payload indexes."""
    if client is None:
        from app.infrastructure.vector_store.qdrant_client import get_qdrant_client

        client = get_qdrant_client()

    collection_name = settings.qdrant_collection
    expected_dim = settings.embedding_dimension

    try:
        collections = await client.get_collections()
        existing_names = [col.name for col in collections.collections]

        if collection_name not in existing_names:
            logger.info(
                f"Creating Qdrant collection '{collection_name}' "
                f"with dimension={expected_dim}, distance=Cosine"
            )
            await client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=expected_dim,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Collection '{collection_name}' created successfully")
        else:
            # Validate existing collection configuration
            info = await client.get_collection(collection_name)
            # In Qdrant client, vectors_config can be VectorParams or dict
            config = info.config.params.vectors
            actual_dim = getattr(config, "size", None)
            if actual_dim is None and isinstance(config, dict):
                actual_dim = config.get("size")

            if actual_dim and actual_dim != expected_dim:
                raise VectorStoreFailureException(
                    f"Qdrant collection '{collection_name}' has dimension {actual_dim}, "
                    f"but expected {expected_dim}",
                    details={
                        "collection": collection_name,
                        "actual_dimension": actual_dim,
                        "expected_dimension": expected_dim,
                    },
                )
            logger.info(f"Collection '{collection_name}' validated with dimension {expected_dim}")

        # Ensure payload field indexes for efficient metadata filtering and deletion
        for field_name in ["document_id", "filename", "file_type"]:
            try:
                await client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=PayloadSchemaType.KEYWORD,
                )
            except Exception:
                # Index already exists or supported
                pass

    except Exception as e:
        logger.error(f"Error initializing Qdrant collection '{collection_name}': {e}")
        if isinstance(e, VectorStoreFailureException):
            raise
        raise VectorStoreFailureException(
            f"Failed to initialize Qdrant collection '{collection_name}': {e}",
            details={"collection": collection_name, "error": str(e)},
        ) from e
