"""Grounded RAG Engine service coordinating retrieval, context construction, and generation."""

import logging

from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.infrastructure.llm.chat_model import LocalChatService, get_chat_service
from app.infrastructure.llm.embeddings import LocalEmbeddingService, get_embedding_service
from app.modules.rag.prompts import build_rag_system_message, format_context_block
from app.modules.rag.response_builder import RAGResponse, build_rag_response
from app.modules.retrieval.service import VectorRetrievalService, get_vector_service

logger = logging.getLogger(__name__)


class GroundedRAGService:
    """Orchestrates query vectorization, semantic search, evidence assembly, and answer synthesis."""

    def __init__(
        self,
        chat_service: LocalChatService | None = None,
        embedding_service: LocalEmbeddingService | None = None,
        vector_service: VectorRetrievalService | None = None,
    ) -> None:
        self.chat_service = chat_service or get_chat_service()
        self.embedding_service = embedding_service or get_embedding_service()
        self.vector_service = vector_service or get_vector_service()

    async def answer_question(
        self,
        question: str,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        document_id: str | None = None,
    ) -> RAGResponse:
        """Execute grounded document question-answering."""
        clean_question = question.strip()
        if not clean_question:
            return RAGResponse(
                answer="Please provide a valid, non-empty question.",
                sources=[],
                confidence="none",
            )

        k = top_k or settings.top_k
        threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else settings.similarity_threshold
        )

        # 1. Embed query vector
        query_vector = await self.embedding_service.embed_query(clean_question)

        # 2. Retrieve relevant chunks
        chunks = await self.vector_service.search(
            query_vector=query_vector,
            top_k=k,
            similarity_threshold=threshold,
            document_id=document_id,
        )

        # 3. If no evidence found above threshold, return insufficient context response immediately
        if not chunks:
            logger.info(
                f"No chunks retrieved above similarity threshold {threshold} for query '{clean_question}'"
            )
            return RAGResponse(
                answer="Based on the provided documents, there is insufficient information to answer this question.",
                sources=[],
                confidence="none",
            )

        # 4. Construct grounded context
        evidence_items: list[str] = []
        for i, chunk in enumerate(chunks, start=1):
            page_info = f"Page {chunk.page_number}" if chunk.page_number else "N/A"
            evidence_items.append(
                f"[Source {i}: {chunk.filename} ({page_info}, Chunk {chunk.chunk_id})]\n"
                f"{chunk.content}"
            )

        context_block = format_context_block(evidence_items)
        user_message_content = f"{context_block}\n\nQuestion: {clean_question}"

        # 5. Invoke LLM with strict grounding instructions
        messages = [
            build_rag_system_message(),
            HumanMessage(content=user_message_content),
        ]

        llm_answer = await self.chat_service.ainvoke(messages)

        # 6. Build structured response with sources and confidence
        return build_rag_response(answer=llm_answer, chunks=chunks)


_rag_service: GroundedRAGService | None = None


def get_rag_service() -> GroundedRAGService:
    """Get or instantiate singleton GroundedRAGService."""
    global _rag_service
    if _rag_service is None:
        _rag_service = GroundedRAGService()
    return _rag_service
