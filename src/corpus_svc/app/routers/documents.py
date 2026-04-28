"""

This module implements the new design with centralized metadata storage
and no chunk table in PostgreSQL. All chunk content is stored only in
the vector database.
"""

import gzip
import hashlib
import json
import time
import uuid
from datetime import datetime
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging
from shared.telemetry_utils.telemetry import create_span

from ..db.connection import get_db_session
from ..db.models import Document
from ..repositories.document_repository import DocumentRepository
from ..repositories.usage_stats_repository import UsageStatsRepository
from ..schemas.document import (
    DocumentClassification,
    DocumentDeleteResponse,
    DocumentIngestionResponse,
    DocumentResponse,
    DocumentStatistics,
    DocumentType,
    DocumentUpdate,
)
from ..services.ingestion_service import get_ingest_service
from ..utils.auth import extract_jwt_token, extract_user_id_from_token, get_current_user

router = APIRouter()
logger = configure_logging("documents_router")


def get_repositories(
    session: AsyncSession,
) -> tuple[DocumentRepository, UsageStatsRepository]:
    """Get repository instances with a database session."""
    document_repo = DocumentRepository(session)
    usage_stats_repo = UsageStatsRepository(session)
    return document_repo, usage_stats_repo


def _transform_doc_for_response(
    doc: Document, include_preview: bool = False, preview_length: int = 1000
) -> dict[str, Any]:
    """Transform a document to response format."""
    # Map file type to DocumentType enum value (normalize MIME types to extensions)
    file_type_value = getattr(doc, "file_type", None)
    if file_type_value == "application/pdf":
        file_type_value = "pdf"
    elif (
        file_type_value == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        file_type_value = "docx"
    elif file_type_value == "text/plain":
        file_type_value = "txt"
    elif file_type_value == "text/html":
        file_type_value = "html"
    elif file_type_value == "application/json":
        file_type_value = "json"
    elif file_type_value is None:
        file_type_value = "unknown"

    # Map document status to DocumentState enum
    status_value = getattr(doc, "status", None)
    if status_value == "created":
        status_value = "pending"
    elif status_value == "processing":
        status_value = "processing"
    elif status_value == "completed":
        status_value = "processed"
    elif status_value == "failed":
        status_value = "failed"
    elif status_value is None:
        status_value = "pending"

    # Check if content is compressed (boolean flag, not the actual content)
    # Avoid accessing the BYTEA field directly to prevent lazy loading issues
    try:
        # Use the object's state to check if content_compressed exists without loading it
        has_content_compressed = doc.content_compressed is not None
    except Exception:
        # Fallback: assume processed documents have compressed content
        has_content_compressed = status_value == "processed"

    # Build response data matching the migration schema exactly
    response_data = {
        # Core identification
        "id": str(doc.id),
        # Document metadata
        "title": doc.title,
        "source": doc.source,
        "author": doc.author,
        "created_at": doc.created_at,
        "ingested_at": doc.ingested_at,
        "ingested_by": doc.ingested_by,
        # File information
        "original_file_name": (
            doc.original_file_name if doc.original_file_name is not None else "unknown.file"
        ),
        "file_type": file_type_value,
        "file_checksum": doc.file_checksum if doc.file_checksum is not None else "",
        "file_size": doc.file_size if doc.file_size is not None else 0,
        # Content storage (boolean flag only)
        "content_compressed": has_content_compressed,
        # Embedding configuration
        "embedding_model": doc.embedding_model,
        "embedding_provider": doc.embedding_provider,
        "embedding_dimensions": doc.embedding_dimensions,
        # Chunking information
        "num_chunks": doc.num_chunks,
        "avg_chunk_size_tokens": doc.avg_chunk_size_tokens,
        # Classification and organization
        "tags": doc.tags if doc.tags is not None else [],
        "classification": (
            doc.classification if doc.classification is not None else "unclassified"
        ),
        # Status tracking
        "status": status_value,
        "error_message": doc.error_message,
        # Additional metadata
        "metadata": doc.metadata_ if doc.metadata_ is not None else {},
        # Timestamps
        "updated_at": doc.updated_at,
        # Legacy fields for backward compatibility
        "uploaded_by": doc.ingested_by,  # Map to ingested_by
        "uploaded_at": doc.ingested_at,  # Map to ingested_at
        "processed_at": doc.updated_at if status_value == "processed" else None,
    }

    # Convert datetime fields to ISO format for JSON serialization
    datetime_fields = [
        "created_at",
        "updated_at",
        "ingested_at",
        "uploaded_at",
        "processed_at",
    ]
    for field in datetime_fields:
        if field in response_data and isinstance(response_data[field], datetime):
            response_data[field] = response_data[field].isoformat()

    return response_data


async def run_background_ingestion(
    document_id: str,
    user_id: str,
    embedding_model: str | None,
    auth_token: str | None,
    chunking_strategy: str = "recursive",
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    sample_size_tokens: int | None = None,
) -> None:
    """Run document ingestion in the background."""
    trace_id = f"bg-{document_id[:8]}-{int(time.time())}"
    logger.info(f"[{trace_id}] Background task ENTRY - document {document_id}")

    try:
        logger.info(
            f"[{trace_id}] Parameters: doc_id={document_id}, user={user_id}, model={embedding_model}, "
            f"chunking_strategy={chunking_strategy}, chunk_size={chunk_size}, chunk_overlap={chunk_overlap}"
        )
        logger.info(f"[{trace_id}] JWT token: {'Present' if auth_token else 'Missing'}")

        # Create fresh independent session for background processing
        logger.info(f"[{trace_id}] Creating database session...")
        from ..db.connection import get_session

        try:
            async with get_session() as bg_session:
                logger.info(f"[{trace_id}] Database session created successfully")
                bg_ingestion_service = await get_ingest_service(bg_session)
                logger.info(f"[{trace_id}] Ingestion service obtained")

                result = await bg_ingestion_service.process_document(
                    document_id,
                    user_id,
                    embedding_model,
                    auth_token=auth_token,
                    chunking_strategy=chunking_strategy,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
                logger.info(f"[{trace_id}] process_document returned: {result}")

        except Exception as session_error:
            logger.error(f"[{trace_id}] Database session error: {session_error}", exc_info=True)
            raise

        logger.info(f"[{trace_id}] Background processing completed for document {document_id}")

    except Exception as e:
        logger.error(
            f"[{trace_id}] Background processing failed for document {document_id}: {e}",
            exc_info=True,
        )
        try:
            logger.info(f"[{trace_id}] Attempting to update document status to failed...")
            from ..db.connection import get_session

            async with get_session() as error_session:
                error_document_repo = DocumentRepository(error_session)
                await error_document_repo.update_document_status(
                    uuid.UUID(document_id), "failed", str(e)
                )
                logger.info(f"[{trace_id}] Document status updated to failed")
        except Exception as update_error:
            logger.error(
                f"[{trace_id}] Failed to update document status: {update_error}",
                exc_info=True,
            )


@router.post(
    "/",
    response_model=DocumentIngestionResponse,
    status_code=202,
    description="Upload and ingest a document",
)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    source: str | None = Form(None),
    author: str | None = Form(None),
    classification_str: str | None = Form(None, alias="classification"),
    tags: str | None = Form(None),
    metadata: str | None = Form(None),
    collection_name: str | None = Form("default"),
    embedding_model: str | None = Form(None),
    embedding_provider: str | None = Form("openai"),
    chunking_config: str | None = Form(None),
    process_async: bool = Form(True),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> DocumentIngestionResponse:
    """Upload and ingest a document."""
    with create_span("upload_document") as span:
        try:
            # Extract user info
            user_uuid = extract_user_id_from_token(current_user)
            user_id_str = str(user_uuid)

            # Get repositories
            document_repo, _usage_stats_repo = get_repositories(session)

            # Read file content
            content_bytes = await file.read()
            file_size = len(content_bytes)
            file_name_str = file.filename or "unknown.txt"
            file_ext = file_name_str.split(".")[-1].lower() if "." in file_name_str else "txt"
            document_type_enum = DocumentType.from_extension(file_ext)

            # Calculate checksum before any use
            checksum = hashlib.sha256(content_bytes).hexdigest()

            # Reset file pointer after reading
            file.file.seek(0)

            # Extract text from PDF (for now, only handle PDF)
            import io

            extracted_text = None
            if document_type_enum.value == "pdf":
                import pdfplumber

                with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
                    extracted_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            else:
                # For other types, just decode as utf-8 (could be extended)
                extracted_text = content_bytes.decode("utf-8", errors="replace")

            compressed_text = gzip.compress((extracted_text or "").encode("utf-8"))

            logger.info(
                "Uploading document (%s bytes)",
                file_size,
                extra={"file_size": file_size, "user_id": user_id_str},
            )

            # Parse tags
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []

            # Parse classification
            classification_value = None
            if classification_str:
                try:
                    classification_enum = DocumentClassification(classification_str.lower())
                    classification_value = classification_enum.value
                except ValueError:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Invalid classification: {classification_str}",
                    )

            # Parse metadata
            parsed_metadata = {}
            if metadata:
                try:
                    parsed_metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    logger.warning("Invalid metadata JSON for document upload")

            # Parse chunking configuration
            parsed_chunking_config = None
            chunking_strategy = "recursive"  # Default strategy
            chunk_size = 512  # Default chunk size
            chunk_overlap = 50  # Default overlap
            sample_size_tokens = None  # Will use collection default if needed

            if chunking_config:
                try:
                    parsed_chunking_config = json.loads(chunking_config)

                    # Extract and validate strategy
                    chunking_strategy = parsed_chunking_config.get("strategy", "recursive")
                    valid_strategies = [
                        "auto",
                        "recursive",
                        "fixed_token",
                        "sliding_token",
                        "sentence_paragraph",
                        "heading_aware",
                        "table_aware",
                        "semantic_similarity",
                        "markdown_structure",
                    ]
                    if chunking_strategy not in valid_strategies:
                        logger.warning(
                            f"Invalid chunking strategy '{chunking_strategy}', using 'recursive'"
                        )
                        chunking_strategy = "recursive"

                    # Extract and validate chunk_size (must be positive, max 8192 to match current embedding model context windows)
                    chunk_size = parsed_chunking_config.get("chunk_size", 512)
                    if not isinstance(chunk_size, int) or chunk_size < 50 or chunk_size > 8192:
                        logger.warning(f"Invalid chunk_size {chunk_size}, using default 512")
                        chunk_size = 512

                    # Extract and validate chunk_overlap (must be less than chunk_size)
                    chunk_overlap = parsed_chunking_config.get("chunk_overlap", 50)
                    if (
                        not isinstance(chunk_overlap, int)
                        or chunk_overlap < 0
                        or chunk_overlap >= chunk_size
                    ):
                        logger.warning(f"Invalid chunk_overlap {chunk_overlap}, using default 50")
                        chunk_overlap = 50

                    # Extract sample_size_tokens for auto mode (1000-100000)
                    sample_size_tokens = parsed_chunking_config.get("sample_size_tokens")
                    if sample_size_tokens is not None and (
                        not isinstance(sample_size_tokens, int)
                        or sample_size_tokens < 1000
                        or sample_size_tokens > 100000
                    ):
                        logger.warning(
                            f"Invalid sample_size_tokens {sample_size_tokens}, will use collection default"
                        )
                        sample_size_tokens = None

                    logger.info(
                        f"Parsed chunking config: strategy={chunking_strategy}, "
                        f"chunk_size={chunk_size}, chunk_overlap={chunk_overlap}, "
                        f"sample_size_tokens={sample_size_tokens}"
                    )

                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid chunking_config JSON: {e}, using defaults")
                except Exception as e:
                    logger.error(f"Error parsing chunking_config: {e}, using defaults")

            # Look up collection by name
            from ..repositories.collection_repository import CollectionRepository

            collection_repo = CollectionRepository(session)
            collection = await collection_repo.get_by_name(collection_name or "default")
            if not collection:
                raise HTTPException(
                    status_code=404, detail=f"Collection '{collection_name}' not found"
                )
            collection_id = collection.id

            # Add collection info to metadata for frontend visibility
            parsed_metadata["collection_name"] = str(collection.name)
            parsed_metadata["collection_id"] = str(collection.id)

            # AUTO CHUNKING DETECTION (Task 2)
            if chunking_strategy == "auto":
                logger.info(
                    "Auto-detection mode enabled",
                    extra={"sample_tokens": sample_size_tokens or 10000},
                )

                # Get collection's preflight settings (from Task 6)
                # Cast Column values to actual Python types with error handling
                try:
                    collection_preflight_tokens = int(collection.preflight_sample_tokens)  # type: ignore[arg-type]
                except (TypeError, ValueError):
                    collection_preflight_tokens = 10000
                collection_sample_tokens = sample_size_tokens or collection_preflight_tokens

                try:
                    # Access the column value and convert to list
                    col_strats = collection.preflight_strategies
                    collection_preflight_strats = (
                        list(col_strats) if col_strats else None  # type: ignore[arg-type]
                    )
                except (TypeError, ValueError):
                    collection_preflight_strats = None

                collection_strategies = (
                    collection_preflight_strats
                    if collection_preflight_strats
                    else [
                        "sentence_paragraph",
                        "fixed_token",
                        "sliding_token",
                        "heading_aware",
                        "table_aware",
                    ]
                )

                logger.info(
                    f"Auto-detection: analyzing {collection_sample_tokens} tokens, "
                    f"testing {len(collection_strategies)} strategies"
                )

                try:
                    # Import preflight service
                    from ..schemas.chunking_enums import (
                        ChunkingStrategy as ChunkingStrategyEnum,
                    )
                    from ..services.chunking_service import ChunkingService
                    from ..services.preflight_service import PreflightAnalyzer

                    # Create analyzer instance
                    chunking_service = ChunkingService()
                    analyzer = PreflightAnalyzer(chunking_service)

                    # Convert strategy strings to enums
                    strategies_to_test = [ChunkingStrategyEnum(s) for s in collection_strategies]

                    # Run preflight analysis
                    logger.info("Running preflight analysis...")
                    start_time = time.time()

                    report = await analyzer.analyze(
                        text=extracted_text or "",
                        document_name=file_name_str,
                        document_type=file.content_type or "unknown",
                        document_size_bytes=file_size,
                        strategies_to_test=strategies_to_test,
                        max_sample_tokens=collection_sample_tokens,
                    )

                    analysis_time_ms = int((time.time() - start_time) * 1000)

                    # Use recommendation
                    selected_strategy = report.recommendation.strategy.value
                    confidence = report.recommendation.confidence

                    logger.info(
                        "Auto-selected strategy: %s",
                        selected_strategy,
                        extra={
                            "strategy": selected_strategy,
                            "confidence": confidence,
                            "analysis_time_ms": analysis_time_ms,
                            "scores": {
                                r.strategy.value: r.score for r in report.strategy_results[:3]
                            },
                        },
                    )

                    # Store decision details in metadata
                    parsed_metadata["chunking_auto_selected"] = True
                    parsed_metadata["chunking_confidence"] = confidence
                    parsed_metadata["chunking_sample_tokens"] = report.sample_size_tokens
                    parsed_metadata["chunking_alternatives_tested"] = [
                        r.strategy.value for r in report.strategy_results
                    ]
                    parsed_metadata["chunking_scores"] = {
                        r.strategy.value: r.score for r in report.strategy_results
                    }
                    parsed_metadata["chunking_reasoning"] = report.recommendation.reasoning
                    parsed_metadata["chunking_analysis_time_ms"] = analysis_time_ms

                    # Update the chunking_strategy variable
                    chunking_strategy = selected_strategy

                except Exception as preflight_error:
                    logger.error(
                        "Preflight analysis failed: %s",
                        preflight_error,
                        exc_info=True,
                    )
                    # Fallback to recursive strategy
                    logger.warning("Falling back to 'recursive' chunking strategy")
                    chunking_strategy = "recursive"
                    parsed_metadata["chunking_auto_selected"] = False
                    parsed_metadata["chunking_error"] = str(preflight_error)

            # Use collection's embedding configuration (override if not explicitly specified)
            # Explicitly convert to str to avoid SQLAlchemy Column type issues
            embedding_model_to_use = embedding_model
            col_model = collection.embedding_model
            if not embedding_model_to_use and col_model is not None:
                embedding_model_to_use = str(col_model)

            embedding_provider_to_use = embedding_provider
            col_provider = collection.embedding_provider
            if not embedding_provider_to_use and col_provider is not None:
                embedding_provider_to_use = str(col_provider)

            embedding_dimensions_to_use = None
            col_dims = collection.embedding_dimensions
            if col_dims is not None:
                embedding_dimensions_to_use = int(col_dims)  # type: ignore[arg-type]

            logger.info(
                "Using embedding config from collection '%s': model=%s, provider=%s, dims=%s",
                collection.name,
                embedding_model_to_use,
                embedding_provider_to_use,
                embedding_dimensions_to_use,
            )

            # Check for existing document with same checksum (deduplication)
            existing_document = await document_repo.get_document_by_checksum(checksum)

            if existing_document:
                logger.info(
                    f"Document with checksum {checksum} already exists (ID: {existing_document.id}). Updating metadata.",
                    extra={
                        "existing_document_id": str(existing_document.id),
                        "checksum": checksum,
                        "user_id": user_id_str,
                    },
                )

                # Update existing document metadata
                update_fields: dict[str, Any] = {}
                if title and title != existing_document.title:
                    update_fields["title"] = title
                if source and source != existing_document.source:
                    update_fields["source"] = source
                if author and author != existing_document.author:
                    update_fields["author"] = author
                if (
                    classification_value
                    and classification_value != existing_document.classification
                ):
                    update_fields["classification"] = classification_value
                # Safely compare tags
                existing_tags_col = existing_document.tags
                existing_tags: list[str] = list(existing_tags_col) if existing_tags_col else []  # type: ignore[arg-type]
                if tag_list and tag_list != existing_tags:
                    update_fields["tags"] = tag_list
                # Safely compare metadata
                existing_meta_col = existing_document.metadata_
                existing_meta: dict[str, Any] = dict(existing_meta_col) if existing_meta_col else {}  # type: ignore[arg-type]
                if parsed_metadata and parsed_metadata != existing_meta:
                    update_fields["metadata"] = parsed_metadata

                # Only update if there are actual changes
                if update_fields:
                    from uuid import UUID

                    updated_document = await document_repo.update_document(
                        UUID(str(existing_document.id)), **update_fields
                    )
                    document = updated_document if updated_document else existing_document
                else:
                    document = existing_document

                span.set_attribute("document.duplicate", True)

                # If a duplicate is found, delete existing vectors and re-process
                from ..repositories.vector_repository import get_vector_repository

                vector_repo = await get_vector_repository()
                await vector_repo.delete_by_document_id(str(existing_document.id))

                if process_async:
                    # Commit the updated document before queueing background task
                    await session.commit()

                    background_tasks.add_task(
                        run_background_ingestion,
                        document_id=str(document.id),
                        user_id=user_id_str,
                        embedding_model=embedding_model_to_use,
                        auth_token=extract_jwt_token(request),
                        chunking_strategy=chunking_strategy,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        sample_size_tokens=sample_size_tokens,
                    )
            else:
                # Create new document
                from uuid import UUID

                document = await document_repo.create_document(
                    title=title or file_name_str,
                    source=source,
                    author=author,
                    original_file_name=file_name_str,
                    file_type=document_type_enum.value,
                    file_checksum=checksum,
                    file_size=file_size,
                    content_compressed=compressed_text,
                    collection_id=UUID(str(collection_id)),  # type: ignore[arg-type]
                    embedding_model=embedding_model_to_use,
                    embedding_provider=embedding_provider_to_use,
                    embedding_dimensions=embedding_dimensions_to_use,
                    tags=tag_list,
                    classification=classification_value,
                    status="created",
                    ingested_by=user_id_str,
                    metadata=parsed_metadata,
                )

            document_id = str(document.id)
            span.set_attribute("document.id", document_id)

            if process_async:
                # Commit the document to the database before queueing background task
                # so the background task's independent session can find it
                await session.commit()

                # Use FastAPI's BackgroundTasks for reliable background processing
                logger.info(
                    f"Queuing background processing for document {document_id} using BackgroundTasks"
                )
                jwt_token = extract_jwt_token(request)
                background_tasks.add_task(
                    run_background_ingestion,
                    document_id=document_id,
                    user_id=user_id_str,
                    embedding_model=embedding_model_to_use,
                    auth_token=jwt_token,
                    chunking_strategy=chunking_strategy,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    sample_size_tokens=sample_size_tokens,
                )
                return DocumentIngestionResponse(
                    document_id=document_id,
                    status="accepted",
                    message="Document uploaded and queued for processing",
                )
            # Process synchronously
            # Extract JWT token for forwarding to embedding service
            jwt_token = extract_jwt_token(request)
            ingestion_service = await get_ingest_service(session)
            status = await ingestion_service.process_document(
                document_id,
                user_id_str,
                embedding_model_to_use,
                auth_token=jwt_token,
                extracted_text=extracted_text,
                extraction_metadata={},
                chunking_strategy=chunking_strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            if status.state == "completed":
                return DocumentIngestionResponse(
                    document_id=document_id,
                    status="completed",
                    message="Document uploaded and processed successfully",
                )
            return DocumentIngestionResponse(
                document_id=document_id,
                status="failed",
                message=f"Document processing failed: {status.error}",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Document upload failed: {e!s}", exc_info=True)
            if span:
                span.record_exception(e)
            raise HTTPException(status_code=500, detail=f"Document upload failed: {e!s}")


@router.get(
    "/stats",
    response_model=DocumentStatistics,
    description="Get document statistics",
)
async def get_document_statistics(
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> DocumentStatistics:
    """Get comprehensive document statistics."""
    with create_span("get_document_statistics") as span:
        try:
            document_repo, _usage_stats_repo = get_repositories(session)

            # Get comprehensive statistics
            stats_data = await document_repo.get_document_statistics()

            # Calculate processing success rate
            total_docs = stats_data.get("total_documents", 0)
            completed_docs = stats_data.get("completed_documents", 0)
            processing_success_rate = (completed_docs / total_docs * 100) if total_docs > 0 else 0

            # Get average chunks per document
            total_chunks = stats_data.get("total_chunks", 0)
            avg_chunks_per_document = (total_chunks / total_docs) if total_docs > 0 else 0

            # Convert to response format
            return DocumentStatistics(
                total_documents=total_docs,
                total_size_bytes=stats_data.get("total_file_size", 0),
                documents_by_type=stats_data.get(
                    "embedding_model_breakdown", {}
                ),  # Using embedding models as types
                documents_by_state={
                    "created": stats_data.get("created_documents", 0),
                    "processing": stats_data.get("processing_documents", 0),
                    "completed": stats_data.get("completed_documents", 0),
                    "failed": stats_data.get("failed_documents", 0),
                },
                documents_by_classification=stats_data.get("classification_breakdown", {}),
                recent_uploads=0,  # Could be calculated with date range query
                processing_success_rate=processing_success_rate,
                avg_chunks_per_document=avg_chunks_per_document,
                avg_processing_time_ms=None,  # Not tracked in current implementation
            )

        except Exception as e:
            logger.error(f"Error getting document statistics: {e!s}", exc_info=True)
            if span:
                span.record_exception(e)
            raise HTTPException(status_code=500, detail=f"Error getting document statistics: {e!s}")


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    description="Get a document by ID",
)
async def get_document(
    document_id: str,
    include_preview: bool = Query(False, description="Include document content preview"),
    preview_length: int = Query(1000, description="Length of content preview"),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> DocumentResponse:
    """Get a document by ID."""
    with create_span("get_document") as span:
        span.set_attribute("document.id", document_id)

        try:
            doc_uuid = uuid.UUID(document_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid document ID format")

        try:
            document_repo, usage_stats_repo = get_repositories(session)

            document = await document_repo.get_document_by_id(
                doc_uuid, include_content=include_preview
            )

            if not document:
                raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

            # Record access for analytics
            user_uuid = extract_user_id_from_token(current_user)
            try:
                await usage_stats_repo.record_retrieval(
                    document_id=doc_uuid,
                    chunk_ids=[],  # No specific chunks accessed
                    user_id=str(user_uuid),
                    query_text=None,
                    relevancy_scores=None,
                    metadata={
                        "access_type": "document_view",
                        "include_preview": include_preview,
                    },
                )
                # Don't commit here - let the session context manager handle it
            except Exception as e:
                logger.warning(f"Failed to record document access: {e}")

            response_data = _transform_doc_for_response(document, include_preview, preview_length)

            return DocumentResponse.model_validate(response_data)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting document {document_id}: {e!s}", exc_info=True)
            if span:
                span.record_exception(e)
            raise HTTPException(status_code=500, detail=f"Error getting document: {e!s}")


@router.patch(
    "/{document_id}",
    response_model=DocumentResponse,
    description="Update document metadata",
)
async def update_document(
    document_id: str,
    update_request: DocumentUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> DocumentResponse:
    """Update document metadata."""
    with create_span("update_document") as span:
        span.set_attribute("document.id", document_id)

        try:
            doc_uuid = uuid.UUID(document_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid document ID format")

        try:
            document_repo, _usage_stats_repo = get_repositories(session)

            # Convert update request to update fields
            update_data = update_request.model_dump(exclude_unset=True)

            # Map fields to model
            update_fields = {}
            if "title" in update_data:
                update_fields["title"] = update_data["title"]
            if "author" in update_data:
                update_fields["author"] = update_data["author"]
            if "source" in update_data:
                update_fields["source"] = update_data["source"]
            if "classification" in update_data:
                update_fields["classification"] = update_data["classification"]
            if "tags" in update_data:
                update_fields["tags"] = update_data["tags"]
            if "status" in update_data:
                update_fields["status"] = update_data["status"]
            if "errorMessage" in update_data:
                update_fields["error_message"] = update_data["errorMessage"]

            # Handle metadata updates
            if "metadata" in update_data:
                update_fields["metadata"] = update_data["metadata"]

            updated_document = await document_repo.update_document(doc_uuid, **update_fields)

            if not updated_document:
                raise HTTPException(
                    status_code=404,
                    detail=f"Document {document_id} not found for update",
                )

            response_data = _transform_doc_for_response(updated_document)
            return DocumentResponse.model_validate(response_data)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating document {document_id}: {e!s}", exc_info=True)
            if span:
                span.record_exception(e)
            raise HTTPException(status_code=500, detail=f"Error updating document: {e!s}")


@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
    summary="Soft delete a document and clean up associated vectors",
    status_code=status.HTTP_200_OK,
)
async def soft_delete_document(
    document_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> DocumentDeleteResponse:
    """Soft delete a document and remove its vectors from Qdrant."""
    doc_uuid = uuid.UUID(document_id)
    document_repo, _ = get_repositories(session)
    document = await document_repo.get_document_by_id(doc_uuid)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove vectors from Qdrant
    from ..repositories.vector_repository import get_vector_repository

    vector_repo = await get_vector_repository()
    try:
        await vector_repo.delete_vectors_by_document_id(document_id)
    except Exception as e:
        logger.error(f"Failed to delete vectors for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete vectors in Qdrant")

    # Soft delete the document
    await document_repo.update_document_status(doc_uuid, "deleted")

    return DocumentDeleteResponse(status="deleted", document_id=document_id)


@router.get(
    "/",
    response_model=list[DocumentResponse],
    description="List documents",
)
async def list_documents(
    limit: int = Query(10, description="Maximum number of documents to return"),
    offset: int = Query(0, description="Offset for pagination"),
    status_filter: str | None = Query(
        None, alias="status", description="Filter by document status"
    ),
    classification_filter: str | None = Query(
        None, alias="classification", description="Filter by classification"
    ),
    search_query: str | None = Query(None, alias="query", description="Search query for title"),
    embedding_model_filter: str | None = Query(
        None, alias="embedding_model", description="Filter by embedding model"
    ),
    include_deleted: bool = Query(False, description="Include deleted documents in results"),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[DocumentResponse]:
    """List documents with filtering and pagination."""
    with create_span("list_documents") as span:
        span.set_attribute("list.limit", limit)
        span.set_attribute("list.offset", offset)
        span.set_attribute("list.include_deleted", include_deleted)

        try:
            document_repo, _usage_stats_repo = get_repositories(session)

            if search_query:
                # Search by title
                documents = await document_repo.search_documents_by_title(
                    search_query, limit=limit + offset
                )
                documents = documents[offset : offset + limit]
            else:
                # Use advanced search with filters
                documents = await document_repo.search_documents(
                    query=search_query,
                    classification=classification_filter,
                    status=status_filter,
                    embedding_model=embedding_model_filter,
                    limit=limit,
                    offset=offset,
                )

            # Filter out deleted documents unless explicitly requested
            if not include_deleted:
                documents = [doc for doc in documents if str(doc.status) != "deleted"]

            # Convert to response format
            responses = []
            for document in documents:
                try:
                    response_data = _transform_doc_for_response(document)
                    responses.append(DocumentResponse.model_validate(response_data))
                except Exception as e:
                    logger.error(f"Error parsing document {document.id} for list response: {e}")

            # Log access
            user_uuid = extract_user_id_from_token(current_user)
            logger.info(
                f"Documents list accessed by user {user_uuid}",
                extra={"user_id": str(user_uuid), "count": len(responses)},
            )

            return responses

        except Exception as e:
            logger.error(f"Error listing documents: {e!s}", exc_info=True)
            if span:
                span.record_exception(e)
            raise HTTPException(status_code=500, detail=f"Error listing documents: {e!s}")


@router.post(
    "/{document_id}/process",
    response_model=dict[str, Any],
    description="Manually trigger document processing",
)
async def process_document(
    document_id: str,
    request: Request,
    embedding_model: str | None = Query(None, description="Embedding model to use"),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Manually trigger document processing."""
    with create_span("process_document") as span:
        span.set_attribute("document.id", document_id)

        try:
            doc_uuid = uuid.UUID(document_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid document ID format")

        try:
            document_repo, _usage_stats_repo = get_repositories(session)

            # Check if document exists
            document = await document_repo.get_document_by_id(doc_uuid)
            if not document:
                raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

            # Get user info
            user_uuid = extract_user_id_from_token(current_user)
            user_id_str = str(user_uuid)

            # Extract JWT token for forwarding to embedding service
            jwt_token = extract_jwt_token(request)

            # Start processing
            ingestion_service = await get_ingest_service(session)
            status = await ingestion_service.process_document(
                document_id, user_id_str, embedding_model, auth_token=jwt_token
            )

            return {
                "document_id": document_id,
                "status": status.state,
                "progress": status.progress,
                "chunks_processed": status.chunks_processed,
                "chunks_total": status.chunks_total,
                "started_at": (
                    status.started_at.isoformat()
                    if hasattr(status, "started_at") and isinstance(status.started_at, datetime)
                    else None
                ),
                "updated_at": (
                    status.updated_at.isoformat()
                    if hasattr(status, "updated_at") and isinstance(status.updated_at, datetime)
                    else None
                ),
                "completed_at": (
                    status.completed_at.isoformat()
                    if hasattr(status, "completed_at") and isinstance(status.completed_at, datetime)
                    else None
                ),
                "error": status.error,
                "duration": status.duration,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e!s}", exc_info=True)
            if span:
                span.record_exception(e)
            raise HTTPException(status_code=500, detail=f"Error processing document: {e!s}")


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    """Download document content."""
    import gzip

    with create_span("download_document") as span:
        span.set_attribute("document.id", document_id)

        try:
            doc_uuid = uuid.UUID(document_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid document ID format")

        try:
            document_repo, _ = get_repositories(session)

            # Get document with content
            document = await document_repo.get_document_by_id(doc_uuid, include_content=True)

            if not document:
                raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

            # Decompress content - stored as gzip
            content_compressed = document.content_compressed
            if content_compressed is not None:
                try:
                    content = gzip.decompress(content_compressed)  # type: ignore[arg-type]
                except Exception as decompress_error:
                    logger.error(f"Failed to decompress document content: {decompress_error}")
                    raise HTTPException(
                        status_code=500, detail="Failed to decompress document content"
                    )
            else:
                raise HTTPException(status_code=404, detail="Document content not available")

            # Content is always extracted text, not the original file
            # The file_type indicates the original file format, but we return text
            content_type = "text/plain; charset=utf-8"

            # Create filename indicating this is extracted text
            orig_filename = document.original_file_name
            base_filename = (
                str(orig_filename) if orig_filename is not None else f"document_{document_id}"
            )
            # Add .txt extension if not already present
            if not base_filename.lower().endswith(".txt"):
                filename = f"{base_filename}.txt"
            else:
                filename = base_filename

            doc_file_type = document.file_type
            file_type_str = str(doc_file_type) if doc_file_type is not None else "unknown"

            return Response(
                content=content,
                media_type=content_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "X-Original-File-Type": file_type_str,
                },
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error downloading document {document_id}: {e!s}", exc_info=True)
            if span:
                span.record_exception(e)
            raise HTTPException(status_code=500, detail=f"Error downloading document: {e!s}")


@router.get(
    "/{document_id}/status",
    response_model=dict[str, Any],
    description="Get document processing status",
)
async def get_document_status(
    document_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Get document processing status."""
    with create_span("get_document_status") as span:
        span.set_attribute("document.id", document_id)

        try:
            # Convert document_id to UUID first to catch format errors early
            try:
                doc_uuid = uuid.UUID(document_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid document ID format")

            # Always check document in database first (more reliable than in-memory status)
            document_repo, _ = get_repositories(session)
            document = await document_repo.get_document_by_id(doc_uuid)

            if not document:
                raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

            # Try to get detailed status from ingestion service (may not exist for background tasks)
            try:
                ingestion_service = await get_ingest_service(session)
                in_memory_status = await ingestion_service.get_status(document_id)

                if in_memory_status:
                    # Return detailed status from memory
                    return {
                        "document_id": document_id,
                        "status": in_memory_status.state,
                        "progress": in_memory_status.progress,
                        "chunks_processed": in_memory_status.chunks_processed,
                        "chunks_total": in_memory_status.chunks_total,
                        "started_at": in_memory_status.started_at.isoformat(),
                        "updated_at": in_memory_status.updated_at.isoformat(),
                        "completed_at": (
                            in_memory_status.completed_at.isoformat()
                            if in_memory_status.completed_at
                            else None
                        ),
                        "error": in_memory_status.error,
                        "duration": in_memory_status.duration,
                        "is_complete": in_memory_status.is_complete,
                    }
            except Exception as service_error:
                # Log but don't fail - fall back to database status
                logger.warning(
                    f"Could not get in-memory status for document {document_id}: {service_error}"
                )

            # Fallback: Return basic status from document database record
            # Map database status to response format
            doc_status_col = document.status
            doc_status = str(doc_status_col) if doc_status_col is not None else "unknown"
            mapped_status = doc_status
            if doc_status == "created":
                mapped_status = "pending"
            elif doc_status == "completed":
                mapped_status = "completed"

            created_at_val = getattr(document, "created_at", None)
            updated_at_val = getattr(document, "updated_at", None)

            # Safely format datetime objects
            def format_datetime(dt_val: Any) -> str | None:
                if dt_val is None:
                    return None
                if isinstance(dt_val, datetime):
                    return dt_val.isoformat()
                # If it's already a string, return as-is
                if isinstance(dt_val, str):
                    return dt_val
                # Try to convert to string as fallback
                return str(dt_val)

            return {
                "document_id": document_id,
                "state": mapped_status,  # Use 'state' to match in-memory status format
                "status": mapped_status,  # Also include 'status' for compatibility
                "error_message": getattr(document, "error_message", None),
                "chunks_count": (
                    getattr(document, "num_chunks", None)
                    if getattr(document, "num_chunks", None) is not None
                    else 0
                ),
                "embedding_model": getattr(document, "embedding_model", None),
                "created_at": format_datetime(created_at_val),
                "updated_at": format_datetime(updated_at_val),
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting document status {document_id}: {e!s}", exc_info=True)
            if span:
                span.record_exception(e)
            raise HTTPException(status_code=500, detail=f"Error getting document status: {e!s}")
