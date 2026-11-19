"""Unit tests for security utilities."""

import pytest

from app.core.security import (
    SecurityException,
    calculate_sha256,
    calculate_string_sha256,
    sanitize_filename,
    validate_file_extension,
    validate_file_size,
)


def test_calculate_sha256():
    """Verify SHA-256 calculation."""
    data = b"Hello, World!"
    # Known SHA-256 for "Hello, World!"
    expected = "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
    assert calculate_sha256(data) == expected
    assert calculate_string_sha256("Hello, World!") == expected


def test_validate_file_extension_valid():
    """Verify supported file extensions are accepted."""
    assert validate_file_extension("document.pdf") == ".pdf"
    assert validate_file_extension("handbook.DOCX") == ".docx"
    assert validate_file_extension("notes.txt") == ".txt"
    assert validate_file_extension("guide.md") == ".md"


def test_validate_file_extension_invalid():
    """Verify unsupported extensions raise SecurityException."""
    with pytest.raises(SecurityException) as exc_info:
        validate_file_extension("malware.exe")
    assert "Unsupported file extension" in str(exc_info.value)
    assert exc_info.value.category == "SECURITY_VIOLATION"


def test_validate_file_size():
    """Verify file size validation."""
    # Under limit
    validate_file_size(1024 * 1024, max_size_mb=10)

    # Exceed limit
    with pytest.raises(SecurityException) as exc_info:
        validate_file_size(15 * 1024 * 1024, max_size_mb=10)
    assert "exceeds maximum limit" in str(exc_info.value)


def test_sanitize_filename():
    """Verify directory traversal and dangerous characters are stripped."""
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("my file (1).pdf") == "my_file__1_.pdf"
    assert sanitize_filename("policy-v2.md") == "policy-v2.md"
