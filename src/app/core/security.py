"""Security validation, sanitization, and hashing utilities."""

import hashlib
import re
from pathlib import Path

from app.core.constants import SUPPORTED_FILE_EXTENSIONS
from app.core.exceptions import AppBaseException


class SecurityException(AppBaseException):
    category = "SECURITY_VIOLATION"
    status_code = 400


def calculate_sha256(content: bytes) -> str:
    """Calculate the SHA-256 hex digest of a byte sequence."""
    hasher = hashlib.sha256()
    hasher.update(content)
    return hasher.hexdigest()


def calculate_string_sha256(text: str) -> str:
    """Calculate the SHA-256 hex digest of a UTF-8 string."""
    return calculate_sha256(text.encode("utf-8"))


def validate_file_extension(filename: str) -> str:
    """Validate that the filename has a supported document extension."""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_FILE_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_FILE_EXTENSIONS))
        raise SecurityException(
            f"Unsupported file extension '{suffix}'. Allowed: {allowed}",
            details={"filename": filename, "extension": suffix},
        )
    return suffix


def validate_file_size(size_bytes: int, max_size_mb: int = 25) -> None:
    """Validate that the file size is within limits."""
    max_bytes = max_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        size_mb = round(size_bytes / (1024 * 1024), 2)
        raise SecurityException(
            f"File size ({size_mb}MB) exceeds maximum limit of {max_size_mb}MB",
            details={"size_bytes": size_bytes, "max_size_mb": max_size_mb},
        )


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal attacks."""
    # Strip any directory path components
    basename = Path(filename).name
    # Keep only alphanumeric, hyphens, underscores, dots
    cleaned = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", basename)
    if not cleaned or cleaned.startswith("."):
        return f"document_{hashlib.md5(filename.encode()).hexdigest()[:8]}"
    return cleaned
