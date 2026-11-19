"""Structured query audit logger for SQL agent operations."""

import logging
from typing import Any

from app.core.logging import correlation_id_ctx

logger = logging.getLogger("app.sql_agent.audit")


def log_sql_execution(
    sql: str,
    duration_ms: float,
    status: str,  # "SUCCESS", "VALIDATION_FAILED", "EXECUTION_FAILED", "TIMEOUT"
    row_count: int = 0,
    error_message: str | None = None,
    error_category: str | None = None,
    extra_details: dict[str, Any] | None = None,
) -> None:
    """Log SQL execution details in structured JSON format without exposing sensitive data."""
    log_data: dict[str, Any] = {
        "correlation_id": correlation_id_ctx.get(),
        "sql": sql,
        "duration_ms": round(duration_ms, 2),
        "status": status,
        "row_count": row_count,
    }

    if error_message:
        log_data["error_message"] = error_message
    if error_category:
        log_data["error_category"] = error_category
    if extra_details:
        log_data["details"] = extra_details

    if status == "SUCCESS":
        logger.info(f"SQL Executed [{status}] in {duration_ms:.2f}ms", extra=log_data)
    else:
        logger.warning(f"SQL Failed [{status}]: {error_message}", extra=log_data)
