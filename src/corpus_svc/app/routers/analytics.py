"""
Working analytics API endpoints for the refactored retrieval service.

This module provides endpoints for reporting on hot documents and hot chunks
using direct database queries to avoid connection pool issues.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging

from ..db.connection import get_db_session

logger = configure_logging(service_name="analytics_router")

router = APIRouter()


# Response models
class HotDocumentResponse(BaseModel):
    """Response model for hot document data."""

    id: str
    title: str
    classification: str | None
    ingested_at: datetime
    access_count: int
    last_accessed: datetime | None
    unique_users: int


class HotChunkResponse(BaseModel):
    """Response model for hot chunk data."""

    chunk_id: str
    access_count: int
    document_count: int
    unique_users: int
    last_accessed: datetime | None
    avg_relevancy: float | None


@router.get("/hot-documents", response_model=list[HotDocumentResponse])
async def get_hot_documents(
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of documents to return"),
    days_back: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    session: AsyncSession = Depends(get_db_session),
) -> list[HotDocumentResponse]:
    """
    Get the most frequently accessed documents.

    This endpoint identifies "hot" documents by aggregating access frequency
    for maintenance and optimization purposes.
    """
    try:
        # Use DatabaseConnection.fetch() which handles connection pooling internally
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

        result = await session.execute(query, {"limit": limit})
        records = result.mappings().all()

        return [
            HotDocumentResponse(
                id=str(record["id"]),
                title=record["title"] or "Untitled",
                classification=record["classification"],
                ingested_at=record["ingested_at"],
                access_count=record["access_count"],
                last_accessed=record["last_accessed"],
                unique_users=record["unique_users"],
            )
            for record in records
        ]

    except Exception as e:
        logger.error(f"Error fetching hot documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch hot documents")


@router.get("/hot-chunks", response_model=list[HotChunkResponse])
async def get_hot_chunks(
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of chunks to return"),
    days_back: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    session: AsyncSession = Depends(get_db_session),
) -> list[HotChunkResponse]:
    """
    Get the most frequently retrieved chunk IDs.

    This endpoint identifies "hot" chunks by aggregating retrieval frequency
    for maintenance and optimization purposes.
    """
    try:
        # Use DatabaseConnection.fetch() which handles connection pooling internally
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

        result = await session.execute(query, {"limit": limit})
        records = result.mappings().all()

        return [
            HotChunkResponse(
                chunk_id=str(record["chunk_id"]),
                access_count=record["access_count"],
                document_count=record["document_count"],
                unique_users=record["unique_users"],
                last_accessed=record["last_accessed"],
                avg_relevancy=(float(record["avg_relevancy"]) if record["avg_relevancy"] else None),
            )
            for record in records
        ]

    except Exception as e:
        logger.error(f"Error fetching hot chunks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch hot chunks")


@router.get("/performance-metrics")
async def get_performance_metrics(
    days_back: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """
    Get performance metrics for the retrieval system.

    This endpoint provides comprehensive analytics about system
    performance, usage trends, and content effectiveness.
    """
    try:
        # Basic metrics query
        basic_query = text(
            f"""
            SELECT
                COUNT(*) as total_retrievals,
                COUNT(DISTINCT document_id) as unique_documents_accessed,
                COUNT(DISTINCT user_id) as unique_users,
                AVG(array_length(chunk_ids, 1)) as avg_chunks_per_retrieval
            FROM usage_stats
            WHERE accessed_at >= NOW() - INTERVAL '{days_back} days'
        """
        )

        result = await session.execute(basic_query)
        basic_record = result.mappings().first()

        # Calculate average relevancy score from all searches
        relevancy_query = text(
            f"""
            SELECT
                AVG(score) as avg_relevancy,
                COUNT(*) as total_scores
            FROM (
                SELECT unnest(relevancy_scores) as score
                FROM usage_stats
                WHERE accessed_at >= NOW() - INTERVAL '{days_back} days'
                AND relevancy_scores IS NOT NULL
                AND array_length(relevancy_scores, 1) > 0
            ) scores
            WHERE score IS NOT NULL AND score > 0
        """
        )

        relevancy_result = await session.execute(relevancy_query)
        relevancy_record = relevancy_result.mappings().first()

        # Get top relevancy documents
        top_docs_query = text(
            f"""
            SELECT
                d.id,
                d.title,
                AVG(score) as avg_score,
                COUNT(*) as access_count
            FROM (
                SELECT
                    document_id,
                    unnest(relevancy_scores) as score
                FROM usage_stats
                WHERE accessed_at >= NOW() - INTERVAL '{days_back} days'
                AND relevancy_scores IS NOT NULL
                AND array_length(relevancy_scores, 1) > 0
            ) scores
            JOIN documents d ON d.id = scores.document_id
            WHERE score IS NOT NULL AND score > 0
            GROUP BY d.id, d.title
            ORDER BY avg_score DESC
            LIMIT 5
        """
        )

        top_docs_result = await session.execute(top_docs_query)
        top_docs_records = top_docs_result.mappings().all()

        # Get daily trends (basic implementation)
        daily_trends_query = text(
            f"""
            SELECT
                DATE(accessed_at) as date,
                COUNT(*) as queries,
                AVG(
                    CASE
                        WHEN relevancy_scores IS NOT NULL AND array_length(relevancy_scores, 1) > 0
                        THEN (SELECT AVG(unnest) FROM unnest(relevancy_scores) WHERE unnest > 0)
                        ELSE NULL
                    END
                ) as avg_relevancy
            FROM usage_stats
            WHERE accessed_at >= NOW() - INTERVAL '{days_back} days'
            GROUP BY DATE(accessed_at)
            ORDER BY date DESC
            LIMIT 7
        """
        )

        daily_trends_result = await session.execute(daily_trends_query)
        daily_trends_records = daily_trends_result.mappings().all()

        return {
            "total_retrievals": basic_record["total_retrievals"] if basic_record else 0,
            "unique_documents_accessed": (
                basic_record["unique_documents_accessed"] if basic_record else 0
            ),
            "unique_users": basic_record["unique_users"] if basic_record else 0,
            "avg_chunks_per_retrieval": (
                float(basic_record["avg_chunks_per_retrieval"])
                if basic_record and basic_record["avg_chunks_per_retrieval"]
                else 0.0
            ),
            "avg_relevancy_score": (
                float(relevancy_record["avg_relevancy"])
                if relevancy_record and relevancy_record["avg_relevancy"]
                else 0.0
            ),
            "daily_trends": [
                {
                    "date": str(record["date"]),
                    "queries": record["queries"],
                    "avg_relevancy": (
                        float(record["avg_relevancy"]) if record["avg_relevancy"] else 0.0
                    ),
                }
                for record in daily_trends_records
            ],
            "top_relevancy_documents": [
                {
                    "document_id": str(record["id"]),
                    "title": record["title"],
                    "avg_relevancy_score": float(record["avg_score"]),
                    "access_count": record["access_count"],
                }
                for record in top_docs_records
            ],
        }

    except Exception as e:
        logger.error(f"Error fetching performance metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch performance metrics")


@router.get("/document-statistics")
async def get_overall_document_statistics(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """
    Get overall document collection statistics.

    This endpoint provides high-level metrics about the document
    collection including ingestion status and content breakdown.
    """
    try:
        # Basic document counts
        total_query = text("SELECT COUNT(*) as total FROM documents")
        total_result = await session.execute(total_query)
        total_docs = total_result.scalar_one_or_none() or 0

        # Status breakdown
        status_query = text(
            """
            SELECT status, COUNT(*) as count
            FROM documents
            GROUP BY status
        """
        )
        status_result = await session.execute(status_query)
        status_records = status_result.mappings().all()
        status_counts = {record["status"]: record["count"] for record in status_records}

        return {
            "collection_overview": {
                "total_documents": total_docs,
                "created_documents": status_counts.get("created", 0),
                "processing_documents": status_counts.get("processing", 0),
                "completed_documents": status_counts.get("completed", 0),
                "failed_documents": status_counts.get("failed", 0),
                "deleted_documents": status_counts.get("deleted", 0),
            },
            "content_metrics": {
                "unique_classifications": 0,  # Placeholder
                "unique_embedding_models": 0,  # Placeholder
                "total_chunks": 0,  # Placeholder
                "avg_file_size_bytes": 0,  # Placeholder
                "total_file_size_bytes": 0,  # Placeholder
            },
            "classification_breakdown": status_counts,  # Use status as a proxy for now
            "embedding_model_breakdown": {},
        }

    except Exception as e:
        logger.error(f"Error fetching document statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch document statistics")


@router.get("/health")
async def analytics_health(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Simple health check for analytics endpoints."""
    try:
        # Test database connection
        result = await session.execute(text("SELECT 1 as test"))
        return {
            "status": "healthy",
            "database": ("connected" if result.scalar_one_or_none() == 1 else "disconnected"),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"Analytics health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(UTC).isoformat(),
        }
