"""Domain models for SQL generation, validation, and execution."""

from typing import Any

from pydantic import BaseModel, Field


class SQLValidationResult(BaseModel):
    """Result of SQLGlot AST validation."""

    is_valid: bool
    sanitized_sql: str | None = None
    tables_referenced: list[str] = Field(default_factory=list)
    error_message: str | None = None
    error_category: str | None = None


class SQLQueryResult(BaseModel):
    """Result of executing a validated SQL query."""

    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    execution_duration_ms: float = 0.0
    truncated: bool = False
