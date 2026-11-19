"""Document parser factory and exports."""

from pathlib import Path

from app.core.exceptions import DocumentParsingFailureException
from app.infrastructure.document_parsers.base import (
    BaseDocumentParser,
    ParsedDocument,
    ParsedPage,
)
from app.infrastructure.document_parsers.docx_parser import DOCXParser
from app.infrastructure.document_parsers.markdown_parser import MarkdownParser
from app.infrastructure.document_parsers.pdf_parser import PDFParser
from app.infrastructure.document_parsers.text_parser import TextParser


def get_parser_for_file(filename: str) -> BaseDocumentParser:
    """Return the appropriate parser instance based on file extension."""
    suffix = Path(filename).suffix.lower()
    match suffix:
        case ".pdf":
            return PDFParser()
        case ".docx":
            return DOCXParser()
        case ".txt":
            return TextParser()
        case ".md":
            return MarkdownParser()
        case _:
            raise DocumentParsingFailureException(
                f"No parser available for file extension '{suffix}'",
                details={"filename": filename, "extension": suffix},
            )


__all__ = [
    "BaseDocumentParser",
    "ParsedDocument",
    "ParsedPage",
    "PDFParser",
    "DOCXParser",
    "TextParser",
    "MarkdownParser",
    "get_parser_for_file",
]
