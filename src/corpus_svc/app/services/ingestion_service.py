"""
This service implements the new design that centralizes all document metadata
in a master table and eliminates chunk-level metadata storage in PostgreSQL.
Chunk content is stored only in the vector database (Qdrant).
"""

import time
import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from fastapi import Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging
from shared.telemetry_utils.telemetry import create_span

from ..clients import EmbeddingServiceClient
from ..db.connection import get_db_session
from ..processing.chunking import ChunkingService
from ..processing.extraction import MetadataExtractor, TextExtractor
from ..repositories.document_repository import DocumentRepository
from ..repositories.usage_stats_repository import UsageStatsRepository
from ..repositories.vector_repository import QdrantRepository, get_vector_repository
from ..schemas.document import DocumentType as DocTypeEnum
from ..utils.embeddings import get_embedding_client

logger = configure_logging(service_name="ingestion_service")

_ingest_service_instance: Optional["DocumentIngestService"] = None


class IngestionStatus(BaseModel):
    """Status information for document ingestion."""

    document_id: str = Field(..., description="Document ID")
    state: str = Field(..., description="Current state of ingestion")
    progress: float = Field(0.0, description="Progress as a percentage (0-100)")
    chunks_processed: int = Field(0, description="Number of chunks processed")
    chunks_total: int = Field(0, description="Total number of chunks")
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Start time"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last update time"
    )
    completed_at: datetime | None = Field(None, description="Completion time")
    error: str | None = Field(None, description="Error message if failed")

    @classmethod
    def check_progress_range(cls, v: float) -> float:
        """Validate progress is between 0 and 100."""
        if not 0 <= v <= 100:
            raise ValueError("Progress must be between 0 and 100")
        return v

    @property
    def duration(self) -> float:
        """Calculate duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return (datetime.now(UTC) - self.started_at).total_seconds()

    @property
    def is_complete(self) -> bool:
        """Check if ingestion is complete."""
        return self.state in ["completed", "failed"]


class DocumentIngestService:
    """
    This service coordinates the document ingestion flow:
    1. Retrieve document from storage
    2. Extract text and metadata
    3. Chunk text into segments
    4. Generate embeddings for chunks
    5. Store embeddings in Qdrant (with chunk content)
    6. Update document metadata with embedding info
    7. No chunk table in PostgreSQL - only usage tracking
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        usage_stats_repository: UsageStatsRepository,
        embedding_client: EmbeddingServiceClient | None,
        vector_repository: QdrantRepository,
        text_extractor: TextExtractor,
        metadata_extractor: MetadataExtractor,
        chunking_service: ChunkingService,
    ):
        """Initialize the Document Ingest Service."""
        self.document_repository = document_repository
        self.usage_stats_repository = usage_stats_repository
        self.embedding_client = embedding_client
        self.vector_repository = vector_repository
        self.text_extractor = text_extractor
        self.metadata_extractor = metadata_extractor
        self.chunking_service = chunking_service

        # Status tracking for in-progress ingestions
        self._status_tracking: dict[str, IngestionStatus] = {}

    async def process_document(
        self,
        document_id: str,
        user_id: str,
        model: str | None = None,
        auth_token: str | None = None,
        extracted_text: str | None = None,
        extraction_metadata: dict | None = None,  # noqa: ARG002
        chunking_strategy: str = "recursive",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ) -> IngestionStatus:
        """
        All metadata is stored in the documents table, chunk content only in vector DB.
        """
        with create_span("document_ingest_service.process_document") as span:
            span.set_attribute("document.id", document_id)
            span.set_attribute("user.id", user_id)

            # Initialize status tracking
            status = IngestionStatus(
                document_id=document_id,
                state="starting",
                progress=0.0,
                chunks_processed=0,
                chunks_total=0,
                completed_at=None,
                error=None,
            )
            self._status_tracking[document_id] = status

            try:
                start_time = time.time()
                doc_uuid = uuid.UUID(document_id)

                # Update status
                self._update_status(document_id, state="retrieving_document")

                # Get document from database
                document = await self.document_repository.get_document_by_id(doc_uuid)
                if not document:
                    logger.error(f"Document {document_id} not found for processing")
                    self._update_status(
                        document_id,
                        state="failed",
                        error=f"Document {document_id} not found",
                        completed_at=datetime.now(UTC),
                    )
                    return self._status_tracking[document_id]

                # Update document status to processing
                await self.document_repository.update_document_status(doc_uuid, "processing")

                # Use in-memory extracted text if provided, otherwise fetch and decompress from DB
                if extracted_text is not None:
                    text = extracted_text
                else:
                    # Get document content (already extracted text, compressed)
                    document_with_content = await self.document_repository.get_document_by_id(
                        doc_uuid, include_content=True
                    )
                    if (
                        not document_with_content
                        or document_with_content.content_compressed is None
                    ):
                        logger.error(f"Document {document_id} has no compressed content")
                        self._update_status(
                            document_id,
                            state="failed",
                            error=f"Document {document_id} has no content",
                            completed_at=datetime.now(UTC),
                        )
                        return self._status_tracking[document_id]

                    # Decompress content (move to thread pool to avoid blocking event loop)
                    import asyncio
                    import gzip

                    if not isinstance(document_with_content.content_compressed, bytes):
                        logger.error(
                            f"Document {document_id} content_compressed is not bytes; got {type(document_with_content.content_compressed)}"
                        )
                        self._update_status(
                            document_id,
                            state="failed",
                            error=f"Document {document_id} content_compressed is not bytes",
                            completed_at=datetime.now(UTC),
                        )
                        return self._status_tracking[document_id]
                    try:
                        text_bytes = await asyncio.to_thread(
                            gzip.decompress, document_with_content.content_compressed
                        )
                        text = text_bytes.decode("utf-8")
                    except Exception as e:
                        logger.error(
                            f"Failed to decompress content for document {document_id}: {e}"
                        )
                        self._update_status(
                            document_id,
                            state="failed",
                            error=f"Content decompression failed: {e!s}",
                            completed_at=datetime.now(UTC),
                        )
                        return self._status_tracking[document_id]

                # At this point, text is the extracted text (from memory or DB)
                # Proceed to chunking and embedding

                # Update status
                self._update_status(document_id, state="chunking_text")

                doc_type_enum = (
                    DocTypeEnum(str(getattr(document, "file_type", "")))
                    if getattr(document, "file_type", None) is not None
                    else DocTypeEnum.UNKNOWN
                )
                # Safely extract metadata as dict
                doc_meta = document.metadata_
                metadata_dict: dict[str, Any] = {}
                if doc_meta is not None and isinstance(doc_meta, dict):
                    metadata_dict = dict(doc_meta)  # type: ignore[arg-type]

                chunks = await self.chunking_service.chunk_text(
                    text=text,
                    document_id=document_id,
                    document_type=doc_type_enum,
                    metadata=metadata_dict,
                    chunking_strategy=chunking_strategy,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )

                # Store chunking strategy in document metadata for UI visibility
                current_metadata = metadata_dict.copy() if metadata_dict else {}
                current_metadata["chunking_strategy"] = "recursive"  # Current default strategy

                # Update document metadata with chunking strategy
                from uuid import UUID

                await self.document_repository.update_document(
                    UUID(document_id), metadata=current_metadata
                )

                # Update status with total chunks
                self._update_status(
                    document_id,
                    state="creating_embeddings",
                    chunks_total=len(chunks),
                )

                # Generate embeddings for chunks
                chunk_texts = [chunk.content for chunk in chunks]

                if not self.embedding_client:
                    logger.error("Embedding client is not available/configured")
                    self._update_status(
                        document_id,
                        state="failed",
                        error="Embedding service is not configured or unavailable",
                        completed_at=datetime.now(UTC),
                    )
                    await self.document_repository.update_document_status(
                        doc_uuid, "failed", "Embedding service not configured"
                    )
                    return self._status_tracking[document_id]

                # Get embedding model info - ensure we always have a valid model
                embedding_model_str = (
                    model
                    or (self.embedding_client.model_name if self.embedding_client else None)
                    or "all-minilm-l6-v2"
                )  # Default to actual available model
                logger.info(f"Using embedding model: {embedding_model_str}")
                embedding_provider = "openai"  # Default, could be configurable

                # Generate embeddings
                embedding_objects = await self.embedding_client.embed_texts(
                    texts=chunk_texts,
                    model=model,
                    auth_token=auth_token,
                )

                if not embedding_objects:
                    logger.error(f"Failed to generate embeddings for document {document_id}")
                    self._update_status(
                        document_id,
                        state="failed",
                        error="Failed to generate embeddings for chunks",
                        completed_at=datetime.now(UTC),
                    )
                    await self.document_repository.update_document_status(
                        doc_uuid, "failed", "Embedding generation failed"
                    )
                    return self._status_tracking[document_id]

                embeddings: list[list[float]] = [emb_obj.embedding for emb_obj in embedding_objects]

                # Update status
                self._update_status(
                    document_id,
                    state="storing_vectors",
                    chunks_processed=len(chunks),
                )

                # Prepare payloads for vector storage (include chunk content)
                payloads = []
                ids = []
                chunk_uuids = []

                for _i, chunk_data in enumerate(chunks):
                    chunk_uuid = uuid.uuid4()
                    chunk_uuids.append(chunk_uuid)
                    tags_val = getattr(document, "tags", None)
                    if tags_val is not None and not isinstance(tags_val, list):
                        tags_val = list(tags_val)
                    elif tags_val is None:
                        tags_val = []
                    payload = {
                        "document_id": str(document_id),
                        "chunk_id": str(chunk_uuid),
                        "chunk_index": chunk_data.chunk_index,
                        "text": chunk_data.content,  # Store chunk content in vector DB
                        "created_at": datetime.now().isoformat(),
                        "metadata": chunk_data.metadata,
                        # Add document metadata for search
                        "document_title": getattr(document, "title", None),
                        "document_author": getattr(document, "author", None),
                        "document_classification": getattr(document, "classification", None),
                        "document_tags": tags_val,
                        "document_source": getattr(document, "source", None),
                    }
                    payloads.append(payload)
                    ids.append(str(chunk_uuid))  # Use pure UUID string, no prefix

                # Store vectors in Qdrant (collection-aware)
                if embeddings:
                    # Get document's collection to find correct Qdrant collection
                    from uuid import UUID

                    document = await self.document_repository.get_document_by_id(UUID(document_id))
                    doc_collection_id = document.collection_id if document else None
                    if document and doc_collection_id is not None:
                        # Look up collection's Qdrant collection name
                        from uuid import UUID

                        from ..repositories.collection_repository import (
                            CollectionRepository,
                        )
                        from ..repositories.vector_repository import (
                            VectorRepositoryConfig,
                        )

                        collection_repo = CollectionRepository(self.document_repository.session)
                        collection = await collection_repo.get_by_id(UUID(str(doc_collection_id)))

                        qdrant_col_name = collection.qdrant_collection_name if collection else None
                        if collection and qdrant_col_name is not None:
                            # Create collection-specific vector repository
                            base_config = self.vector_repository.config
                            qdrant_config = VectorRepositoryConfig(
                                url=base_config.url,
                                port=base_config.port,
                                api_key=base_config.api_key,
                                prefer_grpc=base_config.prefer_grpc,
                                timeout=base_config.timeout,
                                collection_name=str(qdrant_col_name),
                                vector_size=int(collection.embedding_dimensions),  # type: ignore[arg-type]
                                distance=base_config.distance,
                                m=base_config.m,
                                ef_construct=base_config.ef_construct,
                                ef_search=base_config.ef_search,
                                default_limit=base_config.default_limit,
                                default_offset=base_config.default_offset,
                                indexing_threshold=base_config.indexing_threshold,
                            )
                            from ..repositories.vector_repository import (
                                QdrantRepository as QdrantRepo,
                            )

                            collection_vector_repo = QdrantRepo(qdrant_config)

                            # Initialize collection if it doesn't exist
                            await collection_vector_repo.initialize_collection(force_recreate=False)

                            logger.info(
                                "Storing vectors in collection-specific Qdrant collection: %s",
                                collection.id,
                            )

                            await collection_vector_repo.store_vectors(
                                vectors=embeddings,
                                payloads=payloads,
                                ids=ids,
                            )
                        else:
                            # Fallback to default repository
                            logger.warning(
                                f"Collection not found for document {document_id}, using default"
                            )
                            await self.vector_repository.store_vectors(
                                vectors=embeddings,
                                payloads=payloads,
                                ids=ids,
                            )
                    else:
                        # No collection_id, use default
                        await self.vector_repository.store_vectors(
                            vectors=embeddings,
                            payloads=payloads,
                            ids=ids,
                        )

                    # Update status after processing all chunks
                    self._update_status(
                        document_id,
                        state="updating_document",
                        progress=95.0,
                        chunks_processed=len(chunks),
                    )
                else:
                    logger.warning(f"No embeddings generated for document {document_id}")
                    self._update_status(
                        document_id,
                        state="updating_document",
                        progress=95.0,
                        chunks_processed=0,
                    )

                # Update document with embedding and chunking information
                embedding_dimensions = len(embeddings[0]) if embeddings else 0
                avg_chunk_size = (
                    sum(len(chunk.content) for chunk in chunks) // len(chunks) if chunks else 0
                )

                await self.document_repository.update_embedding_info(
                    doc_uuid,
                    embedding_model=embedding_model_str,
                    embedding_provider=embedding_provider,
                    embedding_dimensions=embedding_dimensions,
                    num_chunks=len(chunks),
                    avg_chunk_size_tokens=avg_chunk_size,
                )

                # Calculate processing time
                processing_time = time.time() - start_time

                # Update final status
                self._update_status(
                    document_id,
                    state="completed",
                    progress=100.0,
                    completed_at=datetime.now(UTC),
                )

                # Log processing completion
                logger.info(
                    f"Document {document_id} processed successfully in {processing_time:.2f}s",
                    extra={
                        "document_id": document_id,
                        "processing_time": processing_time,
                        "chunks_count": len(chunks),
                        "text_length": len(text),
                        "user_id": user_id,
                        "embedding_model": embedding_model_str,
                        "embedding_dimensions": embedding_dimensions,
                    },
                )

                return self._status_tracking[document_id]

            except Exception as e:
                # Update document with error state
                try:
                    await self.document_repository.update_document_status(
                        doc_uuid, "failed", str(e)
                    )
                except Exception as update_error:
                    logger.error(
                        f"Failed to update document {document_id} error state: {update_error!s}",
                        exc_info=True,
                    )

                # Update status tracking
                self._update_status(
                    document_id,
                    state="failed",
                    error=str(e),
                    completed_at=datetime.now(UTC),
                )

                logger.error(
                    f"Document processing failed: {e!s}",
                    extra={"document_id": document_id, "user_id": user_id},
                    exc_info=True,
                )
                span.record_exception(e)

                return self._status_tracking[document_id]

    def _update_status(
        self,
        document_id: str,
        state: str | None = None,
        progress: float | None = None,
        chunks_processed: int | None = None,
        chunks_total: int | None = None,
        error: str | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        """Update status tracking for a document."""
        # Get current status
        status = self._status_tracking.get(document_id)
        if not status:
            status = IngestionStatus(
                document_id=document_id,
                state=state or "unknown",
                progress=progress or 0.0,
                chunks_processed=chunks_processed or 0,
                chunks_total=chunks_total or 0,
                completed_at=completed_at,
                error=error,
            )

        # Update fields
        if state is not None:
            status.state = state

        if progress is not None:
            status.progress = progress

        if chunks_processed is not None:
            status.chunks_processed = chunks_processed

            # Auto-update progress if not explicitly set
            if progress is None and status.chunks_total > 0:
                status.progress = min(95.0, (chunks_processed / status.chunks_total) * 100.0)

        if chunks_total is not None:
            status.chunks_total = chunks_total

        if error is not None:
            status.error = error

        if completed_at is not None:
            status.completed_at = completed_at

        # Always update timestamp
        status.updated_at = datetime.now(UTC)

        # Save updated status
        self._status_tracking[document_id] = status

        # Log status update
        logger.debug(
            f"Document {document_id} ingestion status: {status.state} "
            f"({status.progress:.1f}%, {status.chunks_processed}/{status.chunks_total} chunks, "
            f"duration: {status.duration:.2f}s)"
        )

    async def get_status(self, document_id: str) -> IngestionStatus | None:
        """Get the current status of document ingestion."""
        return self._status_tracking.get(document_id)

    async def retry_document(
        self,
        document_id: str,
        user_id: str,
        model: str | None = None,
    ) -> IngestionStatus:
        """Retry processing a document."""
        # Clear any existing status
        if document_id in self._status_tracking:
            del self._status_tracking[document_id]

        # Start fresh processing
        return await self.process_document(document_id, user_id, model)


# Factory function for creating DocumentIngestService with dependencies
async def get_ingest_service(
    session: AsyncSession,
) -> DocumentIngestService:
    """
    Get or create a DocumentIngestService instance.

    This function creates a DocumentIngestService with all required dependencies.
    """
    # Initialize repositories
    document_repository = DocumentRepository(session)
    usage_stats_repository = UsageStatsRepository(session)

    # Get embedding client and vector repository
    embedding_client: EmbeddingServiceClient | None = await get_embedding_client()
    vector_repository = await get_vector_repository()

    # Initialize extractors
    text_extractor = TextExtractor()
    metadata_extractor = MetadataExtractor()

    # Initialize chunking service
    chunking_service = ChunkingService()

    # Create and return service
    return DocumentIngestService(
        document_repository=document_repository,
        usage_stats_repository=usage_stats_repository,
        embedding_client=embedding_client,
        vector_repository=vector_repository,
        text_extractor=text_extractor,
        metadata_extractor=metadata_extractor,
        chunking_service=chunking_service,
    )


async def get_document_ingest_service(
    session: AsyncSession = Depends(get_db_session),
) -> DocumentIngestService:
    """
    Get the DocumentIngestService instance for dependency injection.
    """
    # The global instance is removed to ensure session safety.
    # A new service instance is created for each request.
    return await get_ingest_service(session)
