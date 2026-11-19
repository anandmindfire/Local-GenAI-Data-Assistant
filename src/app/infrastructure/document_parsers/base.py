"""Base interface for document parsers."""

from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel, Field


class ParsedPage(BaseModel):
    """Represents text extracted from a distinct section or page of a document."""

    page_number: int | None = None
    text: str = Field(..., min_length=1)


class ParsedDocument(BaseModel):
    """Container for parsed document content and pages."""

    filename: str
    file_type: str
    pages: list[ParsedPage] = Field(default_factory=list)
    total_characters: int = 0

    @property
    def full_text(self) -> str:
        """Combine text across all pages."""
        return "\n\n".join(p.text for p in self.pages)


class BaseDocumentParser(ABC):
    """Abstract base class for format-specific document parsers."""

    @abstractmethod
    def parse(self, file_path_or_bytes: Path | bytes, filename: str) -> ParsedDocument:
        """Extract structured text and page information from a document."""
        pass
