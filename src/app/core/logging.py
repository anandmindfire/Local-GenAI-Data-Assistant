"""Structured logging configuration for the application."""

import json
import logging
import sys
import time
from contextvars import ContextVar
from typing import Any

# Context variable for request correlation ID
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")


class StructuredJsonFormatter(logging.Formatter):
    """JSON log formatter adhering to production observability standards."""

    def format(self, record: logging.LogRecord) -> str:
        log_record: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_ctx.get(),
            "module": record.module,
            "line": record.lineno,
        }

        # Include custom attributes passed in extra dict
        if hasattr(record, "duration_ms"):
            log_record["duration_ms"] = record.duration_ms
        if hasattr(record, "category"):
            log_record["category"] = record.category
        if hasattr(record, "details"):
            log_record["details"] = record.details

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)


def configure_logging(level: str = "INFO", use_json: bool = True) -> None:
    """Initialize root logger with structured formatter."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if use_json:
        handler.setFormatter(StructuredJsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d]: %(message)s"
            )
        )
    root_logger.addHandler(handler)

    # Silence overly verbose external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


class ExecutionTimer:
    """Context manager to measure and log execution duration in milliseconds."""

    def __init__(self, logger: logging.Logger, operation: str) -> None:
        self.logger = logger
        self.operation = operation
        self.start_time: float = 0.0

    def __enter__(self) -> "ExecutionTimer":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        duration_ms = round((time.perf_counter() - self.start_time) * 1000, 2)
        if exc_type:
            self.logger.error(
                f"{self.operation} failed after {duration_ms}ms",
                extra={"duration_ms": duration_ms, "operation": self.operation},
            )
        else:
            self.logger.info(
                f"{self.operation} completed in {duration_ms}ms",
                extra={"duration_ms": duration_ms, "operation": self.operation},
            )
