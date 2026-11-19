"""Local Ollama Chat Model adapter with structured output and resilience."""

import logging
from typing import Any, TypeVar

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.exceptions import LLMUnavailableException

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LocalChatService:
    """Service wrapping ChatOllama with resilience, timeout control, and structured outputs."""

    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        timeout: float | None = None,
    ) -> None:
        self.model_name = model_name or settings.chat_model
        self.base_url = base_url or settings.ollama_base_url
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.timeout = timeout if timeout is not None else settings.llm_timeout

        self._llm = ChatOllama(
            model=self.model_name,
            base_url=self.base_url,
            temperature=self.temperature,
            timeout=self.timeout,
        )

    def get_llm(self) -> ChatOllama:
        """Return the underlying LangChain ChatOllama instance."""
        return self._llm

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def ainvoke(
        self,
        messages: list[BaseMessage] | str,
        **kwargs: Any,
    ) -> str:
        """Asynchronously invoke the chat model with resilience and timeout handling."""
        try:
            if isinstance(messages, str):
                formatted_messages = [HumanMessage(content=messages)]
            else:
                formatted_messages = messages

            response = await self._llm.ainvoke(formatted_messages, **kwargs)
            return str(response.content)
        except Exception as e:
            logger.error(
                f"Error invoking local chat model '{self.model_name}' at {self.base_url}: {e}"
            )
            raise LLMUnavailableException(
                f"Local chat model '{self.model_name}' failed to respond: {e}",
                details={
                    "model": self.model_name,
                    "base_url": self.base_url,
                    "error": str(e),
                },
            ) from e

    async def generate_structured(
        self,
        messages: list[BaseMessage] | str,
        schema: type[T],
    ) -> T:
        """Generate structured output adhering to a Pydantic schema using with_structured_output."""
        try:
            structured_llm = self._llm.with_structured_output(schema)
            if isinstance(messages, str):
                formatted = [HumanMessage(content=messages)]
            else:
                formatted = messages

            result = await structured_llm.ainvoke(formatted)
            if not isinstance(result, schema):
                # Attempt to parse if dict returned
                if isinstance(result, dict):
                    return schema.model_validate(result)
                raise ValueError(f"Expected output of type {schema.__name__}, got {type(result)}")
            return result
        except Exception as e:
            logger.error(f"Structured generation failed with schema {schema.__name__}: {e}")
            if isinstance(e, LLMUnavailableException):
                raise
            raise LLMUnavailableException(
                f"Failed to generate structured output for {schema.__name__}: {e}",
                details={
                    "schema": schema.__name__,
                    "model": self.model_name,
                    "error": str(e),
                },
            ) from e


# Global chat service factory
_chat_service: LocalChatService | None = None


def get_chat_service() -> LocalChatService:
    """Obtain or instantiate the global singleton LocalChatService."""
    global _chat_service
    if _chat_service is None:
        _chat_service = LocalChatService()
    return _chat_service
