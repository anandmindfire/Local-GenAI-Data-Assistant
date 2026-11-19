"""Conversation memory service managing PostgreSQL session persistence and isolation."""

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.domain.models.conversation import Conversation, Message, MessageRole
from app.infrastructure.database.models.conversation import ConversationModel, MessageModel

logger = logging.getLogger(__name__)


class ConversationService:
    """Provides conversational session persistence, message history, and isolation."""

    async def get_or_create_conversation(
        self,
        conversation_id: str | None,
        session: AsyncSession,
        title: str | None = None,
    ) -> Conversation:
        """Retrieve existing conversation or create a new isolated session."""
        if conversation_id:
            stmt = (
                select(ConversationModel)
                .where(ConversationModel.conversation_id == conversation_id)
                .options(selectinload(ConversationModel.messages))
            )
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()
            if existing:
                return self._to_domain_conversation(existing)

        # Generate new conversation ID if omitted or not found
        new_id = conversation_id or f"conv_{uuid.uuid4().hex[:16]}"
        new_model = ConversationModel(
            conversation_id=new_id,
            title=title or "New Conversation",
        )
        session.add(new_model)
        await session.flush()
        logger.info(f"Created new conversation session: {new_id}")
        return Conversation(conversation_id=new_id, title=new_model.title, messages=[])

    async def get_conversation_history(
        self,
        conversation_id: str,
        session: AsyncSession,
        limit: int | None = None,
    ) -> list[Message]:
        """Fetch windowed message history for a conversation thread strictly isolated by conversation_id."""
        max_msgs = limit or settings.max_history_messages
        stmt = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.created_at.desc())
            .limit(max_msgs)
        )
        res = await session.execute(stmt)
        messages_desc = res.scalars().all()

        # Re-order to chronological order
        messages_asc = list(reversed(messages_desc))
        return [self._to_domain_message(m) for m in messages_asc]

    async def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        session: AsyncSession,
        intent: str | None = None,
        sources: list[dict[str, Any]] | None = None,
        sql_query: str | None = None,
        sql_results: list[dict[str, Any]] | None = None,
        execution_metadata: dict[str, Any] | None = None,
    ) -> Message:
        """Persist a message within the specified conversation thread."""
        message_id = f"msg_{uuid.uuid4().hex[:16]}"
        msg_model = MessageModel(
            message_id=message_id,
            conversation_id=conversation_id,
            role=role.value if isinstance(role, MessageRole) else role,
            content=content,
            intent=intent,
            sources=sources or [],
            sql_query=sql_query,
            sql_results=sql_results,
            execution_metadata=execution_metadata or {},
        )
        session.add(msg_model)
        await session.flush()
        return self._to_domain_message(msg_model)

    def _to_domain_conversation(self, model: ConversationModel) -> Conversation:
        """Convert SQLAlchemy ConversationModel to domain Conversation."""
        return Conversation(
            conversation_id=model.conversation_id,
            title=model.title,
            created_at=model.created_at,
            updated_at=model.updated_at,
            messages=[self._to_domain_message(m) for m in model.messages],
        )

    def _to_domain_message(self, model: MessageModel) -> Message:
        """Convert SQLAlchemy MessageModel to domain Message."""
        return Message(
            message_id=model.message_id,
            conversation_id=model.conversation_id,
            role=MessageRole(model.role),
            content=model.content,
            intent=model.intent,
            sources=model.sources or [],
            sql_query=model.sql_query,
            sql_results=model.sql_results,
            execution_metadata=model.execution_metadata or {},
            created_at=model.created_at,
        )


_conversation_service: ConversationService | None = None


def get_conversation_service() -> ConversationService:
    """Get or instantiate singleton ConversationService."""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service
