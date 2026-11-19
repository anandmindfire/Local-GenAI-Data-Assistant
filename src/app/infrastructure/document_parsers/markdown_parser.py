"""Markdown (.md) document parser."""

from pathlib import Path

from app.core.exceptions import DocumentParsingFailureException
from app.infrastructure.document_parsers.base import (
    BaseDocumentParser,
    ParsedDocument,
    ParsedPage,
)


class MarkdownParser(BaseDocumentParser):
    """Extracts and normalizes Markdown documents while preserving structure."""

    def parse(self, file_path_or_bytes: Path | bytes, filename: str) -> ParsedDocument:
        try:
            if isinstance(file_path_or_bytes, bytes):
                raw_bytes = file_path_or_bytes
            else:
                raw_bytes = Path(file_path_or_bytes).read_bytes()

            text = raw_bytes.decode("utf-8")
        except Exception as e:
            raise DocumentParsingFailureException(
                f"Failed to read Markdown file '{filename}': {e}",
                details={"filename": filename, "error": str(e)},
            ) from e

        cleaned_text = text.replace("\x00", "").strip()
        if not cleaned_text:
            raise DocumentParsingFailureException(
                f"Markdown file '{filename}' is empty.",
                details={"filename": filename},
            )

        pages = [ParsedPage(page_number=1, text=cleaned_text)]
        return ParsedDocument(
            filename=filename,
            file_type="md",
            pages=pages,
            total_characters=len(cleaned_text),
        )
