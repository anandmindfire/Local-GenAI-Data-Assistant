"""Unit tests for local LLM and embedding services."""

import pytest
from langchain_core.messages import AIMessage
from pydantic import BaseModel

from app.core.exceptions import EmbeddingFailureException, LLMUnavailableException
from app.infrastructure.llm.chat_model import LocalChatService
from app.infrastructure.llm.embeddings import LocalEmbeddingService


class SampleIntentSchema(BaseModel):
    intent: str
    confidence: float


@pytest.mark.asyncio
async def test_chat_service_ainvoke(mocker):
    """Test successful invocation of the local chat model."""
    mock_ainvoke = mocker.patch(
        "langchain_ollama.ChatOllama.ainvoke",
        new_callable=mocker.AsyncMock,
        return_value=AIMessage(content="Hello from local model"),
    )
    service = LocalChatService(model_name="test-chat", base_url="http://mock:11434")

    result = await service.ainvoke("Hi there")
    assert result == "Hello from local model"
    mock_ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_chat_service_structured_output(mocker):
    """Test structured output generation with Pydantic validation."""
    mock_structured = mocker.MagicMock()
    mock_structured.ainvoke = mocker.AsyncMock(
        return_value=SampleIntentSchema(intent="document", confidence=0.95)
    )
    mocker.patch(
        "langchain_ollama.ChatOllama.with_structured_output",
        return_value=mock_structured,
    )
    service = LocalChatService(model_name="test-chat", base_url="http://mock:11434")

    result = await service.generate_structured("Explain leave policy", SampleIntentSchema)
    assert isinstance(result, SampleIntentSchema)
    assert result.intent == "document"
    assert result.confidence == 0.95


@pytest.mark.asyncio
async def test_chat_service_failure_raises_llm_unavailable(mocker):
    """Test that connection failures map to LLMUnavailableException."""
    mocker.patch(
        "langchain_ollama.ChatOllama.ainvoke",
        side_effect=ConnectionError("Could not reach Ollama"),
    )
    service = LocalChatService(model_name="test-chat", base_url="http://mock:11434")

    with pytest.raises(LLMUnavailableException) as exc_info:
        await service.ainvoke("Test")
    assert "failed to respond" in str(exc_info.value)
    assert exc_info.value.category == "LLM_UNAVAILABLE"


@pytest.mark.asyncio
async def test_embedding_service_query(mocker):
    """Test query embedding generation."""
    mocker.patch(
        "langchain_ollama.OllamaEmbeddings.aembed_query",
        new_callable=mocker.AsyncMock,
        return_value=[0.1, 0.2, 0.3, 0.4],
    )
    service = LocalEmbeddingService(
        model_name="test-embed",
        expected_dimension=4,
    )

    vec = await service.embed_query("What is the refund policy?")
    assert len(vec) == 4
    assert vec == [0.1, 0.2, 0.3, 0.4]


@pytest.mark.asyncio
async def test_embedding_service_dimension_mismatch(mocker):
    """Test that a vector with unexpected dimension raises EmbeddingFailureException."""
    mocker.patch(
        "langchain_ollama.OllamaEmbeddings.aembed_query",
        new_callable=mocker.AsyncMock,
        return_value=[0.1, 0.2, 0.3, 0.4],
    )
    service = LocalEmbeddingService(
        model_name="test-embed",
        expected_dimension=768,
    )

    with pytest.raises(EmbeddingFailureException) as exc_info:
        await service.embed_query("test query")
    assert "dimension mismatch" in str(exc_info.value)
    assert exc_info.value.category == "EMBEDDING_FAILURE"


@pytest.mark.asyncio
async def test_embedding_service_batching(mocker):
    """Test batch embedding generation with chunking."""
    mocker.patch(
        "langchain_ollama.OllamaEmbeddings.aembed_documents",
        new_callable=mocker.AsyncMock,
        side_effect=[
            [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],  # batch 1
            [[0.7, 0.8, 0.9]],  # batch 2
        ],
    )
    service = LocalEmbeddingService(
        model_name="test-embed",
        batch_size=2,
        expected_dimension=3,
    )

    texts = ["doc 1", "doc 2", "doc 3"]
    vectors = await service.embed_documents(texts)
    assert len(vectors) == 3
    assert vectors[0] == [0.1, 0.2, 0.3]
    assert vectors[2] == [0.7, 0.8, 0.9]
