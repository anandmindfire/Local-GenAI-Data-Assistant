"""Response builder and deterministic confidence scoring for RAG."""

from pydantic import BaseModel, Field

from app.domain.models.retrieval import RetrievedChunk


class RAGSource(BaseModel):
    """Source reference for retrieved evidence."""

    document_id: str
    filename: str
    page_number: int | None = None
    chunk_id: str
    score: float


class RAGResponse(BaseModel):
    """Structured response from the Grounded RAG Engine."""

    answer: str
    sources: list[RAGSource] = Field(default_factory=list)
    confidence: str = "medium"  # "high", "medium", "low", "none"


def compute_retrieval_confidence(chunks: list[RetrievedChunk]) -> str:
    """Compute confidence level deterministically based on retrieval scores."""
    if not chunks:
        return "none"

    scores = [c.score for c in chunks]
    max_score = max(scores)
    avg_score = sum(scores) / len(scores)

    if max_score >= 0.75 and avg_score >= 0.65:
        return "high"
    elif max_score >= 0.50:
        return "medium"
    elif max_score >= 0.40:
        return "low"
    else:
        return "none"


def build_rag_response(
    answer: str,
    chunks: list[RetrievedChunk],
) -> RAGResponse:
    """Construct RAGResponse mapping chunks to sources and calculating confidence."""
    confidence = compute_retrieval_confidence(chunks)

    # Map chunks to sources
    sources: list[RAGSource] = []
    seen_chunks: set[str] = set()

    for chunk in chunks:
        if chunk.chunk_id not in seen_chunks:
            sources.append(
                RAGSource(
                    document_id=chunk.document_id,
                    filename=chunk.filename,
                    page_number=chunk.page_number,
                    chunk_id=chunk.chunk_id,
                    score=round(chunk.score, 4),
                )
            )
            seen_chunks.add(chunk.chunk_id)

    return RAGResponse(
        answer=answer.strip(),
        sources=sources,
        confidence=confidence,
    )
