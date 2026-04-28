"""

This repository implements the new design that centralizes all document
metadata in a master table without storing chunk content in the database.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer
from sqlalchemy.sql import text

from shared.logging_utils.fastapi import configure_logging

from ..db.models import AnalyticsQueries, Document, DocumentStats

logger = configure_logging(service_name="document_repository")


class DocumentRepository:
    """
    Refactored document repository for managing document operations with SQLAlchemy.

    This repository implements the new design with centralized metadata
    and no chunk content storage in the database.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_document(
        self,
        title: str,
        source: str | None = None,
        author: str | None = None,
        original_file_name: str | None = None,
        file_type: str | None = None,
        file_checksum: str | None = None,
        file_size: int | None = None,
        content_compressed: bytes | None = None,
        collection_id: UUID | None = None,
        embedding_model: str | None = None,
        embedding_provider: str | None = None,
        embedding_dimensions: int | None = None,
        num_chunks: int | None = None,
        avg_chunk_size_tokens: int | None = None,
        tags: list[str] | None = None,
        classification: str | None = None,
        status: str = "created",
        ingested_by: str | None = None,
        metadata: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> Document:
        """
        Create a new document with centralized metadata.
        """
        try:
            if file_checksum:
                existing_doc = await self.get_document_by_checksum(file_checksum)
                if existing_doc:
                    logger.info(
                        f"Document with checksum {file_checksum} already exists: {existing_doc.id}"
                    )
                    return existing_doc

            document = Document(
                title=title,
                source=source,
                author=author,
                original_file_name=original_file_name,
                file_type=file_type,
                file_checksum=file_checksum,
                file_size=file_size,
                content_compressed=content_compressed,
                collection_id=collection_id,
                embedding_model=embedding_model,
                embedding_provider=embedding_provider,
                embedding_dimensions=embedding_dimensions,
                num_chunks=num_chunks,
                avg_chunk_size_tokens=avg_chunk_size_tokens,
                tags=tags or [],
                classification=classification,
                status=status,
                ingested_by=ingested_by,
                metadata_=metadata or {},
                error_message=error_message,
            )

            self.session.add(document)
            await self.session.flush()
            await self.session.refresh(document)

            logger.info("Created document: %s", document.id)
            return document

        except Exception as e:
            logger.error(f"Error creating document: {e}", exc_info=True)
            raise

    async def get_document_by_id(
        self, document_id: uuid.UUID, include_content: bool = False
    ) -> Document | None:
        """Get document by ID."""
        try:
            query = select(Document).where(Document.id == document_id)
            if not include_content:
                query = query.options(defer(Document.content_compressed))  # type: ignore[arg-type]

            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching document {document_id}: {e}", exc_info=True)
            raise

    async def get_document_by_checksum(self, checksum: str) -> Document | None:
        """Get document by file checksum."""
        try:
            query = select(Document).where(Document.file_checksum == checksum)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching document by checksum {checksum}: {e}", exc_info=True)
            raise

    async def get_documents_by_status(self, status: str, limit: int = 100) -> list[Document]:
        """Get documents by status."""
        try:
            query = select(Document).where(Document.status == status).limit(limit)
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error fetching documents by status {status}: {e}", exc_info=True)
            raise

    async def search_documents_by_title(self, search_term: str, limit: int = 10) -> list[Document]:
        """Search documents by title."""
        try:
            query = select(Document).where(Document.title.ilike(f"%{search_term}%")).limit(limit)
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(
                f"Error searching documents by title '{search_term}': {e}",
                exc_info=True,
            )
            raise

    async def update_document(
        self, document_id: uuid.UUID, **update_fields: Any
    ) -> Document | None:
        """Update document with provided fields."""
        try:
            if not update_fields:
                return await self.get_document_by_id(document_id)

            if "metadata" in update_fields:
                current_doc = await self.get_document_by_id(document_id)
                if not current_doc:
                    return None
                # Safely extract metadata as dict - metadata_ is JSON column type
                current_meta = current_doc.metadata_
                if isinstance(current_meta, dict):
                    current_metadata: dict[str, Any] = current_meta.copy()  # type: ignore[assignment]
                else:
                    current_metadata = {}
                current_metadata.update(update_fields["metadata"])
                update_fields["metadata_"] = current_metadata
                del update_fields["metadata"]

            query = (
                update(Document)
                .where(Document.id == document_id)
                .values(**update_fields)
                .returning(Document)
            )
            result = await self.session.execute(query)
            await self.session.flush()
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error updating document {document_id}: {e}", exc_info=True)
            raise

    async def update_document_status(
        self, document_id: uuid.UUID, status: str, error_message: str | None = None
    ) -> None:
        """Update the status of a document and optionally set error message."""
        try:
            if error_message:
                await self.session.execute(
                    text(
                        "UPDATE documents SET status = :status, error_message = :error_message, updated_at = NOW() WHERE id = :id"
                    ),
                    {
                        "status": status,
                        "error_message": error_message,
                        "id": str(document_id),
                    },
                )
            else:
                await self.session.execute(
                    text(
                        "UPDATE documents SET status = :status, updated_at = NOW() WHERE id = :id"
                    ),
                    {"status": status, "id": str(document_id)},
                )
            await self.session.commit()
            logger.info(f"Document {document_id} status updated to '{status}'")
        except Exception as e:
            logger.error(f"Failed to update status for document {document_id}: {e}")
            raise

    async def update_embedding_info(
        self,
        document_id: uuid.UUID,
        embedding_model: str,
        embedding_provider: str,
        embedding_dimensions: int,
        num_chunks: int,
        avg_chunk_size_tokens: int | None = None,
    ) -> Document | None:
        """Update document with embedding and chunking information."""
        try:
            return await self.update_document(
                document_id,
                embedding_model=embedding_model,
                embedding_provider=embedding_provider,
                embedding_dimensions=embedding_dimensions,
                num_chunks=num_chunks,
                avg_chunk_size_tokens=avg_chunk_size_tokens,
                status="completed",
            )
        except Exception as e:
            logger.error(
                f"Error updating embedding info for document {document_id}: {e}",
                exc_info=True,
            )
            raise

    async def delete_document(self, document_id: uuid.UUID) -> bool:
        """Delete document by ID."""
        try:
            query = delete(Document).where(Document.id == document_id)
            result = await self.session.execute(query)
            rowcount = getattr(result, "rowcount", None)
            return rowcount is not None and rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}", exc_info=True)
            raise

    async def get_all_documents(self, offset: int = 0, limit: int = 100) -> list[Document]:
        """Get all documents with pagination."""
        try:
            query = (
                select(Document).order_by(Document.created_at.desc()).offset(offset).limit(limit)
            )
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error fetching all documents: {e}", exc_info=True)
            raise

    async def count_documents(self) -> int:
        """Count total number of documents."""
        try:
            query = select(func.count()).select_from(Document)  # type: ignore
            result = await self.session.execute(query)
            return result.scalar_one()
        except Exception as e:
            logger.error(f"Error counting documents: {e}", exc_info=True)
            raise

    async def get_document_statistics(self) -> dict[str, Any]:
        """Get comprehensive document statistics."""
        try:
            total_docs = await self.count_documents()

            status_query = select(Document.status, func.count()).group_by(Document.status)  # type: ignore
            status_result = await self.session.execute(status_query)
            status_counts: dict[str, int] = {
                str(row[0]): int(row[1]) for row in status_result.all()  # type: ignore[misc]
            }

            classification_query = (
                select(Document.classification, func.count())  # type: ignore
                .where(Document.classification.isnot(None))
                .group_by(Document.classification)
            )
            classification_result = await self.session.execute(classification_query)
            classification_counts: dict[str, int] = {
                str(row[0]): int(row[1])
                for row in classification_result.all()  # type: ignore[misc]
            }

            embedding_query = (
                select(Document.embedding_model, func.count())  # type: ignore
                .where(Document.embedding_model.isnot(None))
                .group_by(Document.embedding_model)
            )
            embedding_result = await self.session.execute(embedding_query)
            embedding_counts: dict[str, int] = {
                str(row[0]): int(row[1]) for row in embedding_result.all()  # type: ignore[misc]
            }

            size_query = select(
                func.sum(Document.file_size),
                func.avg(Document.file_size),
                func.sum(Document.num_chunks),
            ).where(Document.file_size.isnot(None))
            size_result = await self.session.execute(size_query)
            total_size, avg_size, total_chunks = size_result.one()

            return {
                "total_documents": total_docs,
                "created_documents": status_counts.get("created", 0),
                "processing_documents": status_counts.get("processing", 0),
                "completed_documents": status_counts.get("completed", 0),
                "failed_documents": status_counts.get("failed", 0),
                "deleted_documents": status_counts.get("deleted", 0),
                "unique_classifications": len(classification_counts),
                "unique_embedding_models": len(embedding_counts),
                "total_chunks": total_chunks or 0,
                "total_file_size": total_size or 0,
                "avg_file_size": avg_size or 0,
                "classification_breakdown": classification_counts,
                "embedding_model_breakdown": embedding_counts,
            }
        except Exception as e:
            logger.error(f"Error fetching document statistics: {e}", exc_info=True)
            raise

    async def get_document_access_stats(
        self, document_id: uuid.UUID, days_back: int = 30
    ) -> DocumentStats | None:
        """Get access statistics for a specific document."""
        try:
            return await AnalyticsQueries.get_document_stats(self.session, document_id, days_back)
        except Exception as e:
            logger.error(
                f"Error fetching access stats for document {document_id}: {e}",
                exc_info=True,
            )
            raise

    async def search_documents(
        self,
        query: str | None = None,
        classification: str | None = None,
        status: str | None = None,
        tags: list[str] | None = None,
        embedding_model: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Document]:
        """Search documents with multiple filters."""
        try:
            stmt = select(Document)
            if query:
                stmt = stmt.where(Document.title.ilike(f"%{query}%"))
            if classification:
                stmt = stmt.where(Document.classification == classification)
            if status:
                stmt = stmt.where(Document.status == status)
            if embedding_model:
                stmt = stmt.where(Document.embedding_model == embedding_model)
            if tags:
                # Check if any of the provided tags exist in the document's tags array
                # Using PostgreSQL array overlap operator (&&)
                from sqlalchemy import ARRAY, cast
                from sqlalchemy import String as SQLString

                stmt = stmt.where(Document.tags.op("&&")(cast(tags, ARRAY(SQLString))))  # type: ignore[attr-defined]

            stmt = stmt.order_by(Document.created_at.desc()).offset(offset).limit(limit)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error searching documents: {e}", exc_info=True)
            raise

    async def get_documents_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        date_field: str = "created_at",
        limit: int = 100,
    ) -> list[Document]:
        """Get documents within a date range."""
        try:
            allowed_date_fields = ["created_at", "updated_at", "ingested_at"]
            if date_field not in allowed_date_fields:
                raise ValueError(f"Invalid date field: {date_field}")

            stmt = (
                select(Document)
                .where(
                    getattr(Document, date_field) >= start_date,
                    getattr(Document, date_field) < end_date,
                )
                .order_by(getattr(Document, date_field).desc())
                .limit(limit)
            )

            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error fetching documents by date range: {e}", exc_info=True)
            raise

    async def add_tags_to_document(
        self, document_id: uuid.UUID, new_tags: list[str]
    ) -> Document | None:
        """Add tags to a document."""
        try:
            doc = await self.get_document_by_id(document_id)
            if not doc:
                return None

            doc_tags: list[str] = list(doc.tags) if doc.tags else []  # type: ignore[arg-type]
            current_tags = set(doc_tags)
            current_tags.update(new_tags)

            return await self.update_document(document_id, tags=list(current_tags))
        except Exception as e:
            logger.error(f"Error adding tags to document {document_id}: {e}", exc_info=True)
            raise

    async def remove_tags_from_document(
        self, document_id: uuid.UUID, tags_to_remove: list[str]
    ) -> Document | None:
        """Remove tags from a document."""
        try:
            doc = await self.get_document_by_id(document_id)
            if not doc:
                return None

            doc_tags: list[str] = list(doc.tags) if doc.tags else []  # type: ignore[arg-type]
            current_tags = set(doc_tags)
            updated_tags = [tag for tag in current_tags if tag not in tags_to_remove]

            return await self.update_document(document_id, tags=updated_tags)
        except Exception as e:
            logger.error(f"Error removing tags from document {document_id}: {e}", exc_info=True)
            raise

    async def get_documents_by_embedding_model(
        self, embedding_model: str, limit: int = 100
    ) -> list[Document]:
        """Get documents by embedding model."""
        try:
            stmt = (
                select(Document)
                .where(Document.embedding_model == embedding_model)
                .order_by(Document.created_at.desc())
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(
                f"Error fetching documents by embedding model {embedding_model}: {e}",
                exc_info=True,
            )
            raise

    async def cleanup_failed_documents(self, days_old: int = 7) -> int:
        """Clean up old failed documents."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            stmt = delete(Document).where(
                Document.status == "failed", Document.created_at < cutoff_date
            )

            result = await self.session.execute(stmt)
            deleted_count = getattr(result, "rowcount", 0) or 0

            logger.info(f"Cleaned up {deleted_count} failed documents older than {days_old} days")
            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up failed documents: {e}", exc_info=True)
            raise
