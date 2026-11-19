"""Domain models for documents and chunks."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """Represents an extracted chunk of text with structural metadata."""

    chunk_id: str
    document_id: str
    content: str
    filename: str
    file_type: str
    page_number: int | None = None
    chunk_index: int
    content_hash: str
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_qdrant_payload(self) -> dict[str, Any]:
        """Convert chunk metadata and text to a Qdrant payload dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "content": self.content,
            "filename": self.filename,
            "file_type": self.file_type,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "content_hash": self.content_hash,
            "ingested_at": self.ingested_at.isoformat(),
            **self.metadata,
        }


class DocumentRecord(BaseModel):
    """Represents an ingested document record stored in the database."""

    document_id: str
    filename: str
    file_type: str
    file_size_bytes: int
    content_hash: str
    chunk_count: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class IngestionResult(BaseModel):
    """Result summary of a document ingestion operation."""

    document_id: str
    filename: str
    file_type: str
    chunk_count: int
    status: str  # "created", "updated", "skipped"
    message: str
