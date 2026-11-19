"""DOCX document parser using python-docx."""

import io
from pathlib import Path

import docx

from app.core.exceptions import DocumentParsingFailureException
from app.infrastructure.document_parsers.base import (
    BaseDocumentParser,
    ParsedDocument,
    ParsedPage,
)


class DOCXParser(BaseDocumentParser):
    """Extracts text paragraphs and table contents from Microsoft Word DOCX files."""

    def parse(self, file_path_or_bytes: Path | bytes, filename: str) -> ParsedDocument:
        extracted_sections: list[str] = []

        try:
            if isinstance(file_path_or_bytes, bytes):
                source = io.BytesIO(file_path_or_bytes)
            else:
                source = str(file_path_or_bytes)

            doc = docx.Document(source)

            # Extract body paragraphs
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    extracted_sections.append(text)

            # Extract table cells
            for table in doc.tables:
                for row in table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_cells:
                        extracted_sections.append(" | ".join(row_cells))

        except Exception as e:
            raise DocumentParsingFailureException(
                f"Failed to parse DOCX document '{filename}': {e}",
                details={"filename": filename, "error": str(e)},
            ) from e

        combined_text = "\n\n".join(extracted_sections).strip()
        if not combined_text:
            raise DocumentParsingFailureException(
                f"DOCX '{filename}' contains no readable text content.",
                details={"filename": filename},
            )

        pages = [ParsedPage(page_number=1, text=combined_text)]
        return ParsedDocument(
            filename=filename,
            file_type="docx",
            pages=pages,
            total_characters=len(combined_text),
        )
