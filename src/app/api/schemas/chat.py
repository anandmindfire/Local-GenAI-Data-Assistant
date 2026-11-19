"""Chat API request and response schemas."""

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """User chat request payload."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        example="What is our leave policy, and how many orders were placed last month?",
    )
    conversation_id: str | None = Field(
        default=None,
        example="conv_8f3b2a9c12345678",
        description="Optional session identifier for multi-turn context. Auto-generated if omitted.",
    )


class ChatResponse(BaseModel):
    """Structured response from the Assistant workflow."""

    conversation_id: str
    answer: str
    intent: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    sql_results: list[dict[str, Any]] | None = None
    execution_metadata: dict[str, Any] = Field(default_factory=dict)
