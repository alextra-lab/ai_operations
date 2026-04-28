"""
This module defines the SQLAlchemy ORM models for the `collections`, `documents`
and `usage_stats` tables, centralizing all document information and tracking
usage statistics.

Migration 016 adds collection-based organization with embedding model consistency.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

from shared.db.connection import Base
from shared.logging_utils.fastapi import configure_logging

logger = configure_logging(service_name="models_refactored")


class Collection(Base):
    """
    SQLAlchemy ORM model for document collections.

    Collections organize documents with enforced embedding model consistency.
    Each collection is bound to a specific embedding model to ensure semantic
    search correctness (query embeddings must match document embeddings).

    See ADR-021: Collection-Based Document Management
    """

    __tablename__ = "collections"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text)

    # Embedding model binding (immutable after creation)
    embedding_model = Column(String(255), nullable=False)
    embedding_provider = Column(String(100), nullable=False)
    embedding_dimensions = Column(Integer, nullable=False)

    # Qdrant mapping
    qdrant_collection_name = Column(String(255), unique=True, nullable=False)

    # Flags
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_system_managed = Column(Boolean, default=False)

    # Preflight/Auto-chunking configuration (P4-DOC-07)
    preflight_sample_tokens = Column(Integer, nullable=False, default=10000)
    preflight_strategies = Column(  # type: ignore[var-annotated]
        ARRAY(String),
        nullable=False,
        default=[
            "sentence_paragraph",
            "fixed_token",
            "sliding_token",
            "heading_aware",
            "table_aware",
        ],
    )
    auto_chunk_enabled = Column(Boolean, nullable=False, default=True)

    # Metadata
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    document_count = Column(Integer, default=0)

    # Relationships
    documents = relationship("Document", back_populates="collection")


class Document(Base):
    """
    SQLAlchemy ORM model for the master documents table.
    """

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    source = Column(String)
    author = Column(String)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    ingested_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    ingested_by = Column(String)
    original_file_name = Column(String)
    file_type = Column(String)
    file_checksum = Column(String, unique=True)
    file_size = Column(Integer)
    content_compressed = Column(LargeBinary)

    # Collection relationship (added in migration 016)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id"), nullable=False)

    # Embedding metadata (must match collection's embedding model)
    embedding_model = Column(String)
    embedding_provider = Column(String)
    embedding_dimensions = Column(Integer)

    num_chunks = Column(Integer)
    avg_chunk_size_tokens = Column(Integer)
    tags = Column(ARRAY(String), default=[])  # type: ignore[var-annotated]
    classification = Column(String)
    status = Column(String, default="created")
    error_message = Column(Text)
    metadata_ = Column("metadata", JSON, default={})

    # Relationships
    collection = relationship("Collection", back_populates="documents")


class UsageStats(Base):
    """
    SQLAlchemy ORM model for the usage statistics table.
    """

    __tablename__ = "usage_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), nullable=False)
    chunk_ids = Column(ARRAY(UUID(as_uuid=True)), default=[])  # type: ignore[var-annotated]
    accessed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    user_id = Column(String)
    query_text = Column(Text)
    relevancy_scores = Column(ARRAY(Float), default=[])  # type: ignore[var-annotated]
    metadata_ = Column("metadata", JSON, default={})
    average_relevancy = Column(Float)
    rag_confidence = Column(Float)
    total_results_found = Column(Integer)
    source_document_count = Column(Integer)
    run_id = Column(UUID(as_uuid=True), nullable=True)

    @classmethod
    async def record_retrieval(
        cls,
        session: AsyncSession,
        document_id: uuid.UUID | None,
        chunk_ids: list[uuid.UUID],
        user_id: str | None = None,
        query_text: str | None = None,
        relevancy_scores: list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        average_relevancy: float | None = None,
        rag_confidence: float | None = None,
        total_results_found: int | None = None,
        source_document_count: int | None = None,
        run_id: uuid.UUID | None = None,
    ) -> "UsageStats":
        """
        Record a retrieval event.

        This class method creates and saves a new usage statistics record.
        """
        try:
            usage_stat = cls(
                document_id=document_id,
                chunk_ids=chunk_ids,
                user_id=user_id,
                query_text=query_text,
                relevancy_scores=relevancy_scores or [],
                metadata_=metadata or {},
                average_relevancy=average_relevancy,
                rag_confidence=rag_confidence,
                total_results_found=total_results_found,
                source_document_count=source_document_count,
                run_id=run_id,
            )

            session.add(usage_stat)
            await session.flush()
            await session.refresh(usage_stat)

            logger.info(f"Recorded retrieval for document {document_id}")
            return usage_stat

        except Exception as e:
            logger.error(
                f"Error recording retrieval for document {document_id}: {e}",
                exc_info=True,
            )
            raise

    @classmethod
    async def get_by_document_id(
        cls,
        session: AsyncSession,
        document_id: uuid.UUID,
        limit: int = 100,
        days_back: int = 30,
    ) -> list["UsageStats"]:
        """Get usage statistics for a specific document."""
        from sqlalchemy import select

        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days_back)

            query = (
                select(cls)
                .where(cls.document_id == document_id, cls.accessed_at >= cutoff_date)
                .order_by(cls.accessed_at.desc())
                .limit(limit)
            )

            result = await session.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(
                f"Error fetching usage stats for document {document_id}: {e}",
                exc_info=True,
            )
            raise

    @classmethod
    async def get_by_user_id(
        cls, session: AsyncSession, user_id: str, limit: int = 100, days_back: int = 30
    ) -> list["UsageStats"]:
        """Get usage statistics for a specific user."""
        from sqlalchemy import select

        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days_back)

            query = (
                select(cls)
                .where(cls.user_id == user_id, cls.accessed_at >= cutoff_date)
                .order_by(cls.accessed_at.desc())
                .limit(limit)
            )

            result = await session.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error fetching usage stats for user {user_id}: {e}", exc_info=True)
            raise


# Pydantic models for analytics queries remain unchanged as they are not ORM models.
from pydantic import BaseModel


class HotDocument(BaseModel):
    id: uuid.UUID
    title: str
    classification: str | None
    ingested_at: datetime
    access_count: int
    last_accessed: datetime | None
    unique_users: int


class HotChunk(BaseModel):
    chunk_id: uuid.UUID
    access_count: int
    document_count: int
    unique_users: int
    last_accessed: datetime | None
    avg_relevancy: float | None


class DocumentStats(BaseModel):
    total_accesses: int
    unique_users: int
    avg_relevancy: float | None
    first_access: datetime | None
    last_access: datetime | None


class ChunkStats(BaseModel):
    total_accesses: int
    unique_documents: int
    unique_users: int
    avg_relevancy: float | None
    first_access: datetime | None
    last_access: datetime | None


class AnalyticsQueries:
    """Static class containing analytics query methods."""

    @staticmethod
    async def get_hot_documents(
        session: AsyncSession, limit: int = 50, days_back: int = 30
    ) -> list[HotDocument]:
        """Get the most frequently accessed documents."""
        query = text(
            f"""
            SELECT
                d.id,
                d.title,
                d.classification,
                d.ingested_at,
                COUNT(us.id) as access_count,
                MAX(us.accessed_at) as last_accessed,
                COUNT(DISTINCT us.user_id) as unique_users
            FROM documents d
            LEFT JOIN usage_stats us ON d.id = us.document_id
            WHERE us.accessed_at >= NOW() - INTERVAL '{days_back} days'
            GROUP BY d.id, d.title, d.classification, d.ingested_at
            ORDER BY access_count DESC
            LIMIT :limit
        """
        )

        try:
            result = await session.execute(query, {"limit": limit})
            records = result.mappings().all()
            return [HotDocument(**record) for record in records]
        except Exception as e:
            logger.error(f"Error fetching hot documents: {e}", exc_info=True)
            raise

    @staticmethod
    async def get_hot_chunks(
        session: AsyncSession, limit: int = 50, days_back: int = 30
    ) -> list[HotChunk]:
        """Get the most frequently retrieved chunk IDs."""
        query = text(
            f"""
            SELECT
                chunk_id,
                COUNT(*) as access_count,
                COUNT(DISTINCT us.document_id) as document_count,
                COUNT(DISTINCT us.user_id) as unique_users,
                MAX(us.accessed_at) as last_accessed,
                AVG(relevancy_score) as avg_relevancy
            FROM usage_stats us,
                 UNNEST(us.chunk_ids) WITH ORDINALITY AS t(chunk_id, pos)
            LEFT JOIN UNNEST(us.relevancy_scores) WITH ORDINALITY AS r(relevancy_score, pos2)
                 ON t.pos = r.pos2
            WHERE us.accessed_at >= NOW() - INTERVAL '{days_back} days'
            GROUP BY chunk_id
            ORDER BY access_count DESC
            LIMIT :limit
        """
        )

        try:
            result = await session.execute(query, {"limit": limit})
            records = result.mappings().all()
            return [HotChunk(**record) for record in records]
        except Exception as e:
            logger.error(f"Error fetching hot chunks: {e}", exc_info=True)
            raise

    @staticmethod
    async def get_document_stats(
        session: AsyncSession, document_id: uuid.UUID, days_back: int = 30
    ) -> DocumentStats | None:
        """Get access statistics for a specific document."""
        query = text(
            f"""
            SELECT
                COUNT(us.id) as total_accesses,
                COUNT(DISTINCT us.user_id) as unique_users,
                AVG((SELECT AVG(score) FROM UNNEST(us.relevancy_scores) AS score)) as avg_relevancy,
                MIN(us.accessed_at) as first_access,
                MAX(us.accessed_at) as last_access
            FROM usage_stats us
            WHERE us.document_id = :document_id
              AND us.accessed_at >= NOW() - INTERVAL '{days_back} days'
        """
        )

        try:
            result = await session.execute(query, {"document_id": document_id})
            record = result.mappings().first()
            if not record or record["total_accesses"] == 0:
                return None

            return DocumentStats(**record)
        except Exception as e:
            logger.error(f"Error fetching document stats for {document_id}: {e}", exc_info=True)
            raise

    @staticmethod
    async def get_chunk_stats(
        session: AsyncSession, chunk_id: uuid.UUID, days_back: int = 30
    ) -> ChunkStats | None:
        """Get access statistics for a specific chunk ID."""
        query = text(
            f"""
            SELECT
                COUNT(*) as total_accesses,
                COUNT(DISTINCT us.document_id) as unique_documents,
                COUNT(DISTINCT us.user_id) as unique_users,
                AVG(relevancy_score) as avg_relevancy,
                MIN(us.accessed_at) as first_access,
                MAX(us.accessed_at) as last_access
            FROM usage_stats us,
                 UNNEST(us.chunk_ids) WITH ORDINALITY AS t(chunk_id, pos)
            LEFT JOIN UNNEST(us.relevancy_scores) WITH ORDINALITY AS r(relevancy_score, pos2)
                 ON t.pos = r.pos2
            WHERE t.chunk_id = :chunk_id
              AND us.accessed_at >= NOW() - INTERVAL '{days_back} days'
        """
        )

        try:
            result = await session.execute(query, {"chunk_id": chunk_id})
            record = result.mappings().first()
            if not record or record["total_accesses"] == 0:
                return None

            return ChunkStats(**record)
        except Exception as e:
            logger.error(f"Error fetching chunk stats for {chunk_id}: {e}", exc_info=True)
            raise
