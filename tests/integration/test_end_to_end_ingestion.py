"""Integration test verifying end-to-end parsing and chunking of all sample documents."""

from pathlib import Path

from app.core.constants import SUPPORTED_FILE_EXTENSIONS
from app.core.security import calculate_sha256
from app.infrastructure.document_parsers import get_parser_for_file
from app.modules.ingestion.chunker import DocumentChunker


def test_sample_documents_present_and_multi_format():
    """Verify that data/documents contains all 4 required formats and 5-10 files."""
    doc_dir = Path("data/documents")
    assert doc_dir.exists() and doc_dir.is_dir()

    files = [f for f in doc_dir.iterdir() if f.suffix.lower() in SUPPORTED_FILE_EXTENSIONS]
    assert 5 <= len(files) <= 15, f"Expected 5-10 files, found {len(files)}"

    extensions_found = {f.suffix.lower() for f in files}
    required_extensions = {".pdf", ".docx", ".txt", ".md"}
    assert required_extensions.issubset(extensions_found), (
        f"Missing required extensions. Found: {extensions_found}"
    )


def test_parse_and_chunk_all_sample_files():
    """Verify every sample file can be parsed and chunked without error."""
    doc_dir = Path("data/documents")
    chunker = DocumentChunker(chunk_size=500, chunk_overlap=100)

    for file_path in doc_dir.iterdir():
        if file_path.suffix.lower() not in SUPPORTED_FILE_EXTENSIONS:
            continue

        raw_bytes = file_path.read_bytes()
        assert len(raw_bytes) > 0, f"File {file_path.name} is empty"

        content_hash = calculate_sha256(raw_bytes)
        parser = get_parser_for_file(file_path.name)
        parsed = parser.parse(raw_bytes, file_path.name)

        assert len(parsed.pages) > 0, f"Parsed 0 pages for {file_path.name}"
        assert len(parsed.full_text.strip()) > 0, f"Empty text for {file_path.name}"

        chunks = chunker.chunk_document(parsed, content_hash)
        assert len(chunks) > 0, f"Generated 0 chunks for {file_path.name}"
        for chunk in chunks:
            assert chunk.chunk_id is not None
            assert chunk.document_id is not None
            assert len(chunk.content.strip()) > 0
            assert chunk.filename == file_path.name
