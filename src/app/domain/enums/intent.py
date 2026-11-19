"""Intent enumeration for workflow routing."""

from enum import StrEnum


class UserIntent(StrEnum):
    """User intent classification."""

    DOCUMENT = "document"
    SQL = "sql"
    COMBINED = "combined"
    UNKNOWN = "unknown"
