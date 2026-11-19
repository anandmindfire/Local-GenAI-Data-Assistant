"""Unit tests for Grounded RAG Engine."""

import pytest

from app.domain.models.retrieval import RetrievedChunk
from app.modules.rag.prompts import format_context_block
from app.modules.rag.response_builder import compute_retrieval_confidence
from app.modules.rag.service import GroundedRAGService


def test_format_context_block():
    """Verify XML context boundaries are properly formatted."""
    items = ["[Source 1: leave.md]\n24 days leave."]
    block = format_context_block(items)
    assert block.startswith("<context>\n")
    assert block.endswith("\n</context>")
    assert "[Source 1: leave.md]" in block


def test_compute_retrieval_confidence():
    """Verify deterministic confidence calculation."""
    # None
    assert compute_retrieval_confidence([]) == "none"

    # High
    high_chunks = [
        RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            content="t",
            filename="f",
            file_type="md",
            chunk_index=0,
            score=0.85,
        ),
        RetrievedChunk(
            chunk_id="c2",
            document_id="d1",
            content="t",
            filename="f",
            file_type="md",
            chunk_index=1,
            score=0.80,
        ),
    ]
    assert compute_retrieval_confidence(high_chunks) == "high"

    # Medium
    med_chunks = [
        RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            content="t",
            filename="f",
            file_type="md",
            chunk_index=0,
            score=0.55,
        ),
    ]
    assert compute_retrieval_confidence(med_chunks) == "medium"


@pytest.mark.asyncio
async def test_rag_service_insufficient_context(mocker):
    """Test RAG service returns insufficient information response when no chunks match."""
    mock_chat = mocker.AsyncMock()
    mock_embed = mocker.AsyncMock()
    mock_embed.embed_query.return_value = [0.1, 0.2, 0.3, 0.4]

    mock_vector = mocker.AsyncMock()
    mock_vector.search.return_value = []  # No chunks found

    service = GroundedRAGService(
        chat_service=mock_chat,
        embedding_service=mock_embed,
        vector_service=mock_vector,
    )

    resp = await service.answer_question("What is our leave policy?")
    assert "insufficient information" in resp.answer
    assert resp.confidence == "none"
    assert len(resp.sources) == 0
    # Chat model should not be invoked when no evidence exists
    mock_chat.ainvoke.assert_not_called()


@pytest.mark.asyncio
async def test_rag_service_successful_answer(mocker):
    """Test RAG service with retrieved evidence."""
    mock_chat = mocker.AsyncMock()
    mock_chat.ainvoke.return_value = "Employees are entitled to 24 paid leaves per year."

    mock_embed = mocker.AsyncMock()
    mock_embed.embed_query.return_value = [0.1, 0.2, 0.3, 0.4]

    mock_vector = mocker.AsyncMock()
    mock_vector.search.return_value = [
        RetrievedChunk(
            chunk_id="chunk_01",
            document_id="doc_leave",
            content="Employees receive 24 paid leaves annually.",
            filename="leave-policy.pdf",
            file_type="pdf",
            page_number=1,
            chunk_index=0,
            score=0.91,
        )
    ]

    service = GroundedRAGService(
        chat_service=mock_chat,
        embedding_service=mock_embed,
        vector_service=mock_vector,
    )

    resp = await service.answer_question("How many leaves do employees get?")
    assert "24 paid leaves" in resp.answer
    assert len(resp.sources) == 1
    assert resp.sources[0].filename == "leave-policy.pdf"
    assert resp.sources[0].page_number == 1
    assert resp.sources[0].chunk_id == "chunk_01"
    assert resp.confidence in ["high", "medium"]
    mock_chat.ainvoke.assert_called_once()
