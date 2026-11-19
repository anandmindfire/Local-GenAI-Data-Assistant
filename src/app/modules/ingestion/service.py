"""Document ingestion service coordinating parsing, chunking, deduplication, and vectorization."""

import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DocumentParsingFailureException
from app.core.security import (
    calculate_sha256,
    sanitize_filename,
    validate_file_extension,
    validate_file_size,
)
from app.domain.models.document import IngestionResult
from app.infrastructure.database.models.document import DocumentModel
from app.infrastructure.document_parsers import get_parser_for_file
from app.infrastructure.llm.embeddings import LocalEmbeddingService, get_embedding_service
from app.modules.ingestion.chunker import DocumentChunker
from app.modules.ingestion.deduplication import (
    DocumentDeduplicationStatus,
    check_document_status,
)
from app.modules.retrieval.service import VectorRetrievalService, get_vector_service

logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """Coordinates parsing, deduplication, chunking, embedding, and indexing."""

    def __init__(
        self,
        embedding_service: LocalEmbeddingService | None = None,
        vector_service: VectorRetrievalService | None = None,
        chunker: DocumentChunker | None = None,
    ) -> None:
        self.embedding_service = embedding_service or get_embedding_service()
        self.vector_service = vector_service or get_vector_service()
        self.chunker = chunker or DocumentChunker()

    async def ingest_file(
        self,
        file_bytes: bytes,
        filename: str,
        session: AsyncSession,
        max_size_mb: int = 25,
    ) -> IngestionResult:
        """Process and index a single document from raw bytes."""
        clean_filename = sanitize_filename(filename)
        ext = validate_file_extension(clean_filename)
        validate_file_size(len(file_bytes), max_size_mb=max_size_mb)

        content_hash = calculate_sha256(file_bytes)
        status, existing_doc = await check_document_status(
            session=session,
            filename=clean_filename,
            content_hash=content_hash,
        )

        if status == DocumentDeduplicationStatus.UNCHANGED and existing_doc:
            logger.info(
                f"Document '{clean_filename}' is identical to existing document_id='{existing_doc.document_id}'. Skipping."
            )
            return IngestionResult(
                document_id=existing_doc.document_id,
                filename=clean_filename,
                file_type=ext.lstrip("."),
                chunk_count=existing_doc.chunk_count,
                status="skipped",
                message="Document with identical content already indexed.",
            )

        # Parse document
        parser = get_parser_for_file(clean_filename)
        parsed_doc = parser.parse(file_bytes, clean_filename)

        # Chunk document
        chunks = self.chunker.chunk_document(parsed_doc, content_hash)
        if not chunks:
            raise DocumentParsingFailureException(
                f"Document '{clean_filename}' resulted in 0 text chunks.",
                details={"filename": clean_filename},
            )

        # Generate embeddings in batch
        chunk_texts = [c.content for c in chunks]
        embeddings = await self.embedding_service.embed_documents(chunk_texts)

        document_id = chunks[0].document_id

        # If modified, remove old vectors before upserting new ones
        if status == DocumentDeduplicationStatus.MODIFIED and existing_doc:
            logger.info(
                f"Document '{clean_filename}' was modified. Removing old vectors for '{existing_doc.document_id}'"
            )
            await self.vector_service.delete_document_vectors(existing_doc.document_id)
            # Delete old db record
            await session.delete(existing_doc)
            await session.flush()

        # Upsert new vectors to Qdrant
        await self.vector_service.upsert_chunks(chunks, embeddings)

        # Persist document metadata in PostgreSQL
        doc_record = DocumentModel(
            document_id=document_id,
            filename=clean_filename,
            file_type=ext.lstrip("."),
            file_size_bytes=len(file_bytes),
            content_hash=content_hash,
            chunk_count=len(chunks),
        )
        session.add(doc_record)
        await session.flush()

        action_status = "updated" if status == DocumentDeduplicationStatus.MODIFIED else "created"
        logger.info(
            f"Successfully ingested '{clean_filename}' (document_id='{document_id}', {len(chunks)} chunks)"
        )
        return IngestionResult(
            document_id=document_id,
            filename=clean_filename,
            file_type=ext.lstrip("."),
            chunk_count=len(chunks),
            status=action_status,
            message=f"Document successfully {action_status} with {len(chunks)} chunks indexed.",
        )

    async def ingest_from_path(
        self,
        file_path: Path,
        session: AsyncSession,
    ) -> IngestionResult:
        """Ingest a document directly from a filesystem Path."""
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_bytes = file_path.read_bytes()
        return await self.ingest_file(
            file_bytes=file_bytes,
            filename=file_path.name,
            session=session,
        )

    async def delete_document(
        self,
        document_id: str,
        session: AsyncSession,
    ) -> bool:
        """Cascade delete a document from both PostgreSQL and Qdrant."""
        stmt = select(DocumentModel).where(DocumentModel.document_id == document_id)
        res = await session.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            return False

        # Delete vectors in Qdrant
        await self.vector_service.delete_document_vectors(document_id)

        # Delete database metadata
        await session.delete(doc)
        await session.flush()
        logger.info(f"Document '{document_id}' completely removed from DB and vector store.")
        return True
