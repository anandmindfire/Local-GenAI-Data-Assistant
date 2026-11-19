"""Local Ollama Embeddings adapter supporting batch processing and dimension validation."""

import logging

from langchain_ollama import OllamaEmbeddings
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.exceptions import EmbeddingFailureException

logger = logging.getLogger(__name__)


class LocalEmbeddingService:
    """Service wrapping Ollama embeddings with batch processing and validation."""

    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        batch_size: int | None = None,
        expected_dimension: int | None = None,
    ) -> None:
        self.model_name = model_name or settings.embedding_model
        self.base_url = base_url or settings.ollama_base_url
        self.batch_size = batch_size or settings.embedding_batch_size
        self.expected_dimension = expected_dimension or settings.embedding_dimension

        self._embeddings = OllamaEmbeddings(
            model=self.model_name,
            base_url=self.base_url,
        )

    def get_embeddings(self) -> OllamaEmbeddings:
        """Return the underlying LangChain OllamaEmbeddings instance."""
        return self._embeddings

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def embed_query(self, text: str) -> list[float]:
        """Generate a single vector embedding for a search query."""
        if not text or not text.strip():
            raise EmbeddingFailureException("Cannot embed empty query text.")

        try:
            vector = await self._embeddings.aembed_query(text.strip())
            self._validate_dimension(vector)
            return vector
        except Exception as e:
            logger.error(f"Embedding generation failed for query using '{self.model_name}': {e}")
            if isinstance(e, EmbeddingFailureException):
                raise
            raise EmbeddingFailureException(
                f"Failed to generate query embedding: {e}",
                details={"model": self.model_name, "error": str(e)},
            ) from e

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of document texts in configurable batches."""
        if not texts:
            return []

        cleaned_texts = [t.strip() if t.strip() else " " for t in texts]
        all_embeddings: list[list[float]] = []

        try:
            for i in range(0, len(cleaned_texts), self.batch_size):
                batch = cleaned_texts[i : i + self.batch_size]
                batch_vectors = await self._embeddings.aembed_documents(batch)
                for vec in batch_vectors:
                    self._validate_dimension(vec)
                all_embeddings.extend(batch_vectors)

            return all_embeddings
        except Exception as e:
            logger.error(f"Batch embedding generation failed using '{self.model_name}': {e}")
            if isinstance(e, EmbeddingFailureException):
                raise
            raise EmbeddingFailureException(
                f"Failed to generate batch document embeddings: {e}",
                details={
                    "model": self.model_name,
                    "batch_count": len(texts),
                    "error": str(e),
                },
            ) from e

    def _validate_dimension(self, vector: list[float]) -> None:
        """Ensure generated vector matches the expected dimensionality."""
        if len(vector) != self.expected_dimension:
            raise EmbeddingFailureException(
                f"Embedding vector dimension mismatch: expected {self.expected_dimension}, "
                f"got {len(vector)} from model '{self.model_name}'",
                details={
                    "expected_dimension": self.expected_dimension,
                    "actual_dimension": len(vector),
                    "model": self.model_name,
                },
            )


# Global embedding service factory
_embedding_service: LocalEmbeddingService | None = None


def get_embedding_service() -> LocalEmbeddingService:
    """Obtain or instantiate the global singleton LocalEmbeddingService."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = LocalEmbeddingService()
    return _embedding_service
