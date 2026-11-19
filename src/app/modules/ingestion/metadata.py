"""Metadata generation utilities for stable document and chunk identifiers."""

import hashlib
from datetime import UTC, datetime


def generate_document_id(filename: str, content_hash: str) -> str:
    """Generate a stable, deterministic document ID from filename and content hash."""
    raw = f"{filename}:{content_hash[:16]}"
    return f"doc_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def generate_chunk_id(document_id: str, chunk_index: int) -> str:
    """Generate a stable, deterministic chunk ID from document ID and chunk index."""
    return f"{document_id}_chunk_{chunk_index:04d}"


def get_utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(UTC)
