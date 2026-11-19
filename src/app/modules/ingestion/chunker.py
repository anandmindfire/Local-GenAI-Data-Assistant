"""Document chunking module using RecursiveCharacterTextSplitter with page preservation."""

import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.core.security import calculate_string_sha256
from app.domain.models.document import DocumentChunk
from app.infrastructure.document_parsers.base import ParsedDocument
from app.modules.ingestion.metadata import (
    generate_chunk_id,
    generate_document_id,
    get_utc_now,
)

logger = logging.getLogger(__name__)


class DocumentChunker:
    """Splits parsed documents into semantically coherent chunks while preserving page numbers."""

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk_document(
        self,
        parsed_doc: ParsedDocument,
        content_hash: str,
    ) -> list[DocumentChunk]:
        """Split parsed document into DocumentChunk objects with page tracking."""
        document_id = generate_document_id(parsed_doc.filename, content_hash)
        chunks: list[DocumentChunk] = []
        global_chunk_index = 0
        ingested_at = get_utc_now()

        for page in parsed_doc.pages:
            page_text = page.text.strip()
            if not page_text:
                continue

            # Split text on this specific page
            page_splits = self._splitter.split_text(page_text)
            for split_text in page_splits:
                cleaned_split = split_text.strip()
                if not cleaned_split:
                    continue

                chunk_id = generate_chunk_id(document_id, global_chunk_index)
                chunk_hash = calculate_string_sha256(cleaned_split)

                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    content=cleaned_split,
                    filename=parsed_doc.filename,
                    file_type=parsed_doc.file_type,
                    page_number=page.page_number,
                    chunk_index=global_chunk_index,
                    content_hash=chunk_hash,
                    ingested_at=ingested_at,
                    metadata={
                        "character_length": len(cleaned_split),
                    },
                )
                chunks.append(chunk)
                global_chunk_index += 1

        logger.info(
            f"Document '{parsed_doc.filename}' split into {len(chunks)} chunks "
            f"(chunk_size={self.chunk_size}, overlap={self.chunk_overlap})"
        )
        return chunks
