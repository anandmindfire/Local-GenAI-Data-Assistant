"""Plain text (.txt) document parser."""

from pathlib import Path

from app.core.exceptions import DocumentParsingFailureException
from app.infrastructure.document_parsers.base import (
    BaseDocumentParser,
    ParsedDocument,
    ParsedPage,
)


class TextParser(BaseDocumentParser):
    """Extracts and normalizes UTF-8 plain text documents."""

    def parse(self, file_path_or_bytes: Path | bytes, filename: str) -> ParsedDocument:
        try:
            if isinstance(file_path_or_bytes, bytes):
                raw_bytes = file_path_or_bytes
            else:
                raw_bytes = Path(file_path_or_bytes).read_bytes()

            # Attempt UTF-8 decode, fallback to latin-1
            try:
                text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text = raw_bytes.decode("latin-1")

        except Exception as e:
            raise DocumentParsingFailureException(
                f"Failed to read text file '{filename}': {e}",
                details={"filename": filename, "error": str(e)},
            ) from e

        cleaned_text = text.replace("\x00", "").strip()
        if not cleaned_text:
            raise DocumentParsingFailureException(
                f"Text file '{filename}' is empty.",
                details={"filename": filename},
            )

        pages = [ParsedPage(page_number=1, text=cleaned_text)]
        return ParsedDocument(
            filename=filename,
            file_type="txt",
            pages=pages,
            total_characters=len(cleaned_text),
        )
