"""Document deduplication and change detection."""

import logging
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.document import DocumentModel

logger = logging.getLogger(__name__)


class DocumentDeduplicationStatus(StrEnum):
    """Status indicating how an incoming document compares to stored records."""

    NEW = "new"
    UNCHANGED = "unchanged"
    MODIFIED = "modified"


async def check_document_status(
    session: AsyncSession,
    filename: str,
    content_hash: str,
) -> tuple[DocumentDeduplicationStatus, DocumentModel | None]:
    """Check whether a document is new, identical/unchanged, or modified."""
    # First check if identical content_hash exists
    hash_stmt = select(DocumentModel).where(DocumentModel.content_hash == content_hash)
    res = await session.execute(hash_stmt)
    existing_by_hash = res.scalar_one_or_none()

    if existing_by_hash:
        return DocumentDeduplicationStatus.UNCHANGED, existing_by_hash

    # Check if a document with the same filename exists with a different hash
    name_stmt = select(DocumentModel).where(DocumentModel.filename == filename)
    name_res = await session.execute(name_stmt)
    existing_by_name = name_res.scalar_one_or_none()

    if existing_by_name:
        return DocumentDeduplicationStatus.MODIFIED, existing_by_name

    return DocumentDeduplicationStatus.NEW, None
