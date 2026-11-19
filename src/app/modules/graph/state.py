"""Strongly typed LangGraph state definition for the assistant workflow."""

from typing import Any, TypedDict


class AssistantState(TypedDict):
    """Execution state passed through the LangGraph workflow nodes."""

    # Identifiers & user inputs
    conversation_id: str
    question: str
    contextualized_question: str
    intent: str  # "document", "sql", "combined", "unknown"

    # Intermediate execution artifacts
    retrieved_documents: list[dict[str, Any]]
    generated_sql: str | None
    sql_results: list[dict[str, Any]] | None

    # Error tracking & outputs
    execution_errors: list[str]
    answer: str
    sources: list[dict[str, Any]]
    execution_metadata: dict[str, Any]
