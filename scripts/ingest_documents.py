"""Batch document ingestion script for populating the vector knowledge base."""

import asyncio
import logging
from pathlib import Path

from app.core.config import settings
from app.core.constants import SUPPORTED_FILE_EXTENSIONS
from app.infrastructure.database.connection import db_context, init_tables
from app.infrastructure.vector_store.collections import init_collections
from app.modules.ingestion.service import DocumentIngestionService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def ingest_all_documents(directory: Path | None = None) -> None:
    """Scan directory and index all supported documents."""
    target_dir = directory or settings.documents_directory
    if not target_dir.exists():
        logger.error(f"Documents directory does not exist: {target_dir}")
        return

    # Find all supported files
    files: list[Path] = []
    for ext in SUPPORTED_FILE_EXTENSIONS:
        files.extend(target_dir.glob(f"*{ext}"))

    if not files:
        logger.warning(f"No supported documents found in {target_dir}")
        return

    logger.info(f"Found {len(files)} documents to process in '{target_dir}'")

    # Initialize collections and tables if needed
    await init_tables()
    await init_collections()

    service = DocumentIngestionService()
    success_count = 0
    skipped_count = 0
    failure_count = 0

    async with db_context() as session:
        for f in files:
            try:
                result = await service.ingest_from_path(f, session=session)
                if result.status == "skipped":
                    skipped_count += 1
                    logger.info(f"[SKIPPED]   {f.name}: {result.message}")
                else:
                    success_count += 1
                    logger.info(
                        f"[INDEXED]   {f.name}: {result.chunk_count} chunks indexed (ID: {result.document_id})"
                    )
            except Exception as e:
                failure_count += 1
                logger.error(f"[FAILED]    {f.name}: {e}")

    logger.info("==================================================")
    logger.info(
        f"Batch Ingestion Complete: {success_count} indexed, {skipped_count} skipped, {failure_count} failed."
    )
    logger.info("==================================================")


def main() -> None:
    """CLI entrypoint for document ingestion."""
    asyncio.run(ingest_all_documents())


if __name__ == "__main__":
    main()
