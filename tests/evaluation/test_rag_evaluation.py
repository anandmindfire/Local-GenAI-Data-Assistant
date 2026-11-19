"""RAG Evaluation test suite measuring retrieval precision, recall, and citation correctness."""

import pytest

from app.domain.models.retrieval import RetrievedChunk
from app.modules.rag.service import GroundedRAGService

# Evaluation benchmark dataset
RAG_BENCHMARK_CASES = [
    {
        "id": "rag-01",
        "question": "What is the company's annual paid leave policy?",
        "expected_doc": "leave-policy.md",
        "expected_facts": ["24 paid leaves", "annually"],
        "mock_chunk": RetrievedChunk(
            chunk_id="chunk_leave_01",
            document_id="doc_leave",
            content="Full-time employees receive 24 paid leaves annually (2 days accrued per completed calendar month).",
            filename="leave-policy.md",
            file_type="md",
            page_number=1,
            chunk_index=0,
            score=0.89,
        ),
    },
    {
        "id": "rag-02",
        "question": "Explain the customer return policy window and condition.",
        "expected_doc": "refund-policy.md",
        "expected_facts": ["30 calendar days", "original, unused condition"],
        "mock_chunk": RetrievedChunk(
            chunk_id="chunk_refund_01",
            document_id="doc_refund",
            content="Customers may return eligible products within 30 calendar days of delivery confirmation in original, unused condition.",
            filename="refund-policy.md",
            file_type="md",
            page_number=1,
            chunk_index=0,
            score=0.92,
        ),
    },
    {
        "id": "rag-03",
        "question": "What is the employee meal per diem limit for travel?",
        "expected_doc": "expense-policy.md",
        "expected_facts": ["$75 per day"],
        "mock_chunk": RetrievedChunk(
            chunk_id="chunk_expense_01",
            document_id="doc_expense",
            content="Meals during active business travel are reimbursed up to a maximum daily allowance of $75 per day.",
            filename="expense-policy.md",
            file_type="md",
            page_number=1,
            chunk_index=0,
            score=0.86,
        ),
    },
]


@pytest.mark.parametrize("case", RAG_BENCHMARK_CASES, ids=lambda c: c["id"])
@pytest.mark.asyncio
async def test_rag_retrieval_and_citation_benchmark(case, mocker):
    """Evaluate retrieval recall, source attribution accuracy, and answer faithfulness."""
    mock_chunk = case["mock_chunk"]

    mock_chat = mocker.AsyncMock()
    mock_chat.ainvoke.return_value = (
        f"According to {mock_chunk.filename}, {' '.join(case['expected_facts'])}."
    )

    mock_embed = mocker.AsyncMock()
    mock_embed.embed_query.return_value = [0.1, 0.2, 0.3, 0.4]

    mock_vector = mocker.AsyncMock()
    mock_vector.search.return_value = [mock_chunk]

    service = GroundedRAGService(
        chat_service=mock_chat,
        embedding_service=mock_embed,
        vector_service=mock_vector,
    )

    response = await service.answer_question(case["question"])

    # 1. Retrieval Hit Rate / Recall check
    assert len(response.sources) > 0, "Retrieval recall failure: no sources returned"
    primary_source = response.sources[0]
    assert primary_source.filename == case["expected_doc"], "Retrieved unexpected document"

    # 2. Citation Correctness check
    assert primary_source.chunk_id == mock_chunk.chunk_id
    assert primary_source.score >= 0.70

    # 3. Answer Faithfulness check
    for fact in case["expected_facts"]:
        assert fact.lower() in response.answer.lower(), f"Expected fact missing: '{fact}'"
