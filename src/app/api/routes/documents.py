"""Document ingestion, management, and deletion API routes."""

import logging
import math

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_correlation_id, get_db
from app.api.schemas.documents import (
    DocumentIngestionResponse,
    DocumentListResponse,
    DocumentMetadataResponse,
)
from app.core.exceptions import DocumentNotFoundException
from app.infrastructure.database.models.document import DocumentModel
from app.modules.ingestion.service import DocumentIngestionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/ingest",
    response_model=DocumentIngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_document(
    file: UploadFile = File(..., description="Document file (.pdf, .docx, .txt, .md)"),
    session: AsyncSession = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id),
) -> DocumentIngestionResponse:
    """Upload and index a document into the grounded RAG knowledge base."""
    filename = file.filename or "uploaded_document"
    logger.info(f"Received file upload for ingestion: '{filename}' [CID: {correlation_id}]")

    file_bytes = await file.read()
    service = DocumentIngestionService()

    result = await service.ingest_file(
        file_bytes=file_bytes,
        filename=filename,
        session=session,
    )

    return DocumentIngestionResponse(
        document_id=result.document_id,
        filename=result.filename,
        file_type=result.file_type,
        chunk_count=result.chunk_count,
        status=result.status,
        message=result.message,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """List indexed documents with pagination."""
    # Count total items
    count_stmt = select(func.count(DocumentModel.document_id))
    total_count = (await session.execute(count_stmt)).scalar() or 0

    # Query page
    offset = (page - 1) * page_size
    stmt = (
        select(DocumentModel)
        .order_by(DocumentModel.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items_raw = (await session.execute(stmt)).scalars().all()

    items = [
        DocumentMetadataResponse(
            document_id=doc.document_id,
            filename=doc.filename,
            file_type=doc.file_type,
            file_size_bytes=doc.file_size_bytes,
            content_hash=doc.content_hash,
            chunk_count=doc.chunk_count,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
        for doc in items_raw
    ]

    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

    return DocumentListResponse(
        items=items,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    document_id: str,
    session: AsyncSession = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id),
) -> dict[str, str]:
    """Delete a document and cascade delete all its vector embeddings from Qdrant."""
    logger.info(f"Received request to delete document '{document_id}' [CID: {correlation_id}]")
    service = DocumentIngestionService()
    deleted = await service.delete_document(document_id, session=session)

    if not deleted:
        raise DocumentNotFoundException(
            f"Document with ID '{document_id}' not found.",
            details={"document_id": document_id},
        )

    return {
        "status": "success",
        "message": f"Document '{document_id}' and all associated vector embeddings successfully deleted.",
    }
