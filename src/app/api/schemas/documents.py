"""Document API request and response schemas."""

from datetime import datetime

from pydantic import BaseModel


class DocumentMetadataResponse(BaseModel):
    """Metadata response for an indexed document."""

    document_id: str
    filename: str
    file_type: str
    file_size_bytes: int
    content_hash: str
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Paginated list of indexed documents."""

    items: list[DocumentMetadataResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class DocumentIngestionResponse(BaseModel):
    """Response returned upon completing document ingestion."""

    document_id: str
    filename: str
    file_type: str
    chunk_count: int
    status: str
    message: str
