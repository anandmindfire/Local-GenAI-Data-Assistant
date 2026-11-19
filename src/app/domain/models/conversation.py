"""Domain models for conversations and messages."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MessageRole(StrEnum):
    """Role of the message author."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """Represents a single message in a conversation thread."""

    message_id: str
    conversation_id: str
    role: MessageRole
    content: str
    intent: str | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)
    sql_query: str | None = None
    sql_results: list[dict[str, Any]] | None = None
    execution_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Conversation(BaseModel):
    """Represents a conversational session."""

    conversation_id: str
    title: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    messages: list[Message] = Field(default_factory=list)
