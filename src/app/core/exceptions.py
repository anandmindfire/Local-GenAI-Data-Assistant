"""Centralized application exception hierarchy.

Categorized according to system observability standards with actionable messages
and sanitized error structures for API responses.
"""

from typing import Any


class AppBaseException(Exception):
    """Base class for all application domain exceptions."""

    category: str = "INTERNAL_ERROR"
    status_code: int = 500

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        category: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        if category:
            self.category = category
        if status_code:
            self.status_code = status_code

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to structured dictionary for API responses."""
        return {
            "category": self.category,
            "message": self.message,
            "details": self.details,
        }


class LLMUnavailableException(AppBaseException):
    category = "LLM_UNAVAILABLE"
    status_code = 503


class EmbeddingFailureException(AppBaseException):
    category = "EMBEDDING_FAILURE"
    status_code = 502


class VectorStoreFailureException(AppBaseException):
    category = "VECTOR_STORE_FAILURE"
    status_code = 503


class DocumentParsingFailureException(AppBaseException):
    category = "DOCUMENT_PARSING_FAILURE"
    status_code = 422


class RetrievalFailureException(AppBaseException):
    category = "RETRIEVAL_FAILURE"
    status_code = 500


class SQLValidationFailureException(AppBaseException):
    category = "SQL_VALIDATION_FAILURE"
    status_code = 400


class SQLExecutionFailureException(AppBaseException):
    category = "SQL_EXECUTION_FAILURE"
    status_code = 500


class DatabaseUnavailableException(AppBaseException):
    category = "DATABASE_UNAVAILABLE"
    status_code = 503


class GraphExecutionFailureException(AppBaseException):
    category = "GRAPH_EXECUTION_FAILURE"
    status_code = 500


class ConversationNotFoundException(AppBaseException):
    category = "CONVERSATION_NOT_FOUND"
    status_code = 404


class DocumentNotFoundException(AppBaseException):
    category = "DOCUMENT_NOT_FOUND"
    status_code = 404
