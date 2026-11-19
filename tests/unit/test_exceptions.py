"""Unit tests for centralized exceptions."""

from app.core.exceptions import (
    ConversationNotFoundException,
    DatabaseUnavailableException,
    DocumentParsingFailureException,
    EmbeddingFailureException,
    GraphExecutionFailureException,
    LLMUnavailableException,
    RetrievalFailureException,
    SQLExecutionFailureException,
    SQLValidationFailureException,
    VectorStoreFailureException,
)


def test_exception_categories_and_status_codes():
    """Verify standard error categories and HTTP status codes."""
    exc_map = [
        (LLMUnavailableException("model down"), "LLM_UNAVAILABLE", 503),
        (EmbeddingFailureException("embed failed"), "EMBEDDING_FAILURE", 502),
        (VectorStoreFailureException("qdrant down"), "VECTOR_STORE_FAILURE", 503),
        (DocumentParsingFailureException("corrupt pdf"), "DOCUMENT_PARSING_FAILURE", 422),
        (RetrievalFailureException("search failed"), "RETRIEVAL_FAILURE", 500),
        (SQLValidationFailureException("unsafe sql"), "SQL_VALIDATION_FAILURE", 400),
        (SQLExecutionFailureException("syntax error"), "SQL_EXECUTION_FAILURE", 500),
        (DatabaseUnavailableException("postgres down"), "DATABASE_UNAVAILABLE", 503),
        (GraphExecutionFailureException("state error"), "GRAPH_EXECUTION_FAILURE", 500),
        (ConversationNotFoundException("session missing"), "CONVERSATION_NOT_FOUND", 404),
    ]

    for exc, expected_category, expected_status in exc_map:
        assert exc.category == expected_category
        assert exc.status_code == expected_status
        d = exc.to_dict()
        assert d["category"] == expected_category
        assert d["message"] == exc.message
