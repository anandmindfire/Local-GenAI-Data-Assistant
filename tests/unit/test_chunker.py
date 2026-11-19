"""Unit tests for document chunking."""

from app.infrastructure.document_parsers.base import ParsedDocument, ParsedPage
from app.modules.ingestion.chunker import DocumentChunker


def test_chunker_basic_splitting():
    """Verify text chunking preserves pages and produces stable chunk IDs."""
    chunker = DocumentChunker(chunk_size=50, chunk_overlap=10)

    parsed_doc = ParsedDocument(
        filename="policy.txt",
        file_type="txt",
        pages=[
            ParsedPage(
                page_number=1,
                text="This is page one text that is longer than fifty characters in total length.",
            ),
            ParsedPage(
                page_number=2,
                text="This is page two text that also exceeds the fifty character limit easily.",
            ),
        ],
    )

    chunks = chunker.chunk_document(parsed_doc, content_hash="hash123")
    assert len(chunks) >= 2
    assert chunks[0].page_number == 1
    assert chunks[-1].page_number == 2
    assert chunks[0].document_id.startswith("doc_")
    assert chunks[0].chunk_id == f"{chunks[0].document_id}_chunk_0000"
    assert chunks[1].chunk_id == f"{chunks[0].document_id}_chunk_0001"
