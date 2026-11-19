"""PDF document parser utilizing PyMuPDF (fitz) for page-accurate text extraction."""

from pathlib import Path

import pymupdf

from app.core.exceptions import DocumentParsingFailureException
from app.infrastructure.document_parsers.base import (
    BaseDocumentParser,
    ParsedDocument,
    ParsedPage,
)


class PDFParser(BaseDocumentParser):
    """Extracts text content and preserves page numbers from PDF files."""

    def parse(self, file_path_or_bytes: Path | bytes, filename: str) -> ParsedDocument:
        pages: list[ParsedPage] = []

        try:
            if isinstance(file_path_or_bytes, bytes):
                doc = pymupdf.open(stream=file_path_or_bytes, filetype="pdf")
            else:
                doc = pymupdf.open(str(file_path_or_bytes))

            with doc:
                if doc.page_count == 0:
                    raise DocumentParsingFailureException(
                        f"PDF '{filename}' contains no pages.",
                        details={"filename": filename},
                    )

                for page_num, page in enumerate(doc, start=1):
                    raw_text = page.get_text("text")
                    cleaned_text = self._clean_text(raw_text)
                    if cleaned_text:
                        pages.append(ParsedPage(page_number=page_num, text=cleaned_text))

        except Exception as e:
            if isinstance(e, DocumentParsingFailureException):
                raise
            raise DocumentParsingFailureException(
                f"Failed to parse PDF document '{filename}': {e}",
                details={"filename": filename, "error": str(e)},
            ) from e

        if not pages:
            raise DocumentParsingFailureException(
                f"PDF '{filename}' yielded no readable text content (may be empty or image-only).",
                details={"filename": filename},
            )

        total_chars = sum(len(p.text) for p in pages)
        return ParsedDocument(
            filename=filename,
            file_type="pdf",
            pages=pages,
            total_characters=total_chars,
        )

    def _clean_text(self, text: str) -> str:
        """Strip control characters, null bytes, and collapse excessive empty lines."""
        if not text:
            return ""
        # Remove null bytes and non-printable control chars except standard whitespace
        text = text.replace("\x00", "")
        lines = [line.strip() for line in text.splitlines()]
        # Filter multiple empty lines into at most one blank line
        cleaned_lines: list[str] = []
        prev_blank = False
        for line in lines:
            if line:
                cleaned_lines.append(line)
                prev_blank = False
            elif not prev_blank:
                cleaned_lines.append("")
                prev_blank = True
        return "\n".join(cleaned_lines).strip()
