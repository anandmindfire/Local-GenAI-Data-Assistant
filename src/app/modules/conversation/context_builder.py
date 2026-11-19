"""Follow-up question contextualization and resolution."""

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.domain.models.conversation import Message
from app.infrastructure.llm.chat_model import LocalChatService, get_chat_service

logger = logging.getLogger(__name__)

CONTEXTUALIZE_SYSTEM_PROMPT = """You are a conversational query rewriting assistant.
Given a chat history between a user and assistant, and a follow-up question from the user:
Rewrite the follow-up question into a standalone, fully self-contained question that can be understood without the chat history.

RULES:
1. Resolve all pronouns (e.g. 'they', 'it', 'those', 'them') into specific names, entities, or concepts mentioned in the history.
2. If the user question is already standalone, return it exactly as is.
3. Do NOT answer the question. Only output the rewritten question string.
4. Keep the rewritten question concise and natural."""


class ContextualizerService:
    """Resolves conversational anaphora and references into standalone queries."""

    def __init__(self, chat_service: LocalChatService | None = None) -> None:
        self.chat_service = chat_service or get_chat_service()

    async def contextualize_question(
        self,
        current_question: str,
        history: list[Message],
    ) -> str:
        """Rewrite question into standalone query using dialog history."""
        clean_question = current_question.strip()
        if not history:
            return clean_question

        # Format history preview (last 6 messages)
        history_lines = []
        for msg in history[-6:]:
            role_label = "User" if msg.role == "user" else "Assistant"
            history_lines.append(f"{role_label}: {msg.content}")

        history_text = "\n".join(history_lines)
        prompt = (
            f"CHAT HISTORY:\n{history_text}\n\n"
            f"FOLLOW-UP QUESTION: {clean_question}\n\n"
            f"REWRITTEN STANDALONE QUESTION:"
        )

        messages = [
            SystemMessage(content=CONTEXTUALIZE_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        try:
            rewritten = await self.chat_service.ainvoke(messages)
            cleaned = rewritten.strip().strip('"').strip("'")
            if cleaned:
                logger.info(f"Contextualized question: '{clean_question}' -> '{cleaned}'")
                return cleaned
            return clean_question
        except Exception as e:
            logger.warning(
                f"Question contextualization failed ({e}). Falling back to original question."
            )
            return clean_question


_contextualizer_service: ContextualizerService | None = None


def get_contextualizer_service() -> ContextualizerService:
    """Get or instantiate singleton ContextualizerService."""
    global _contextualizer_service
    if _contextualizer_service is None:
        _contextualizer_service = ContextualizerService()
    return _contextualizer_service
