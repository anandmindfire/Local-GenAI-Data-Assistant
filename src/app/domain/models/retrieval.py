"""Domain models for retrieval operations."""

from typing import Any

from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    """Represents a chunk retrieved from vector search with similarity score."""

    chunk_id: str
    document_id: str
    content: str
    filename: str
    file_type: str
    page_number: int | None = None
    chunk_index: int
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_source_dict(self) -> dict[str, Any]:
        """Convert to API source reference structure."""
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "page_number": self.page_number,
            "chunk_id": self.chunk_id,
            "score": round(self.score, 4),
        }
