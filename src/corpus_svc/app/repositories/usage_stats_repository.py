"""
Usage statistics repository for the refactored retrieval service.

This repository handles tracking of document and chunk access patterns
without storing chunk content. Only minimal identifiers are tracked
for analytics and optimization purposes.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging

from ..db.models import AnalyticsQueries, ChunkStats, HotChunk, HotDocument, UsageStats

logger = configure_logging(service_name="usage_stats_repository")


class UsageStatsRepository:
    """
    Repository for usage statistics operations.

    This repository tracks retrieval events and provides analytics
    for hot documents and hot chunks without storing chunk content.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_retrieval(
        self,
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
    ) -> UsageStats:
        """
        Record a retrieval event.

        This is the main method for tracking when documents and chunks
        are accessed through search or retrieval operations.
        """
        try:
            return await UsageStats.record_retrieval(
                session=self.session,
                document_id=document_id,
                chunk_ids=chunk_ids,
                user_id=user_id,
                query_text=query_text,
                relevancy_scores=relevancy_scores,
                metadata=metadata,
                average_relevancy=average_relevancy,
                rag_confidence=rag_confidence,
                total_results_found=total_results_found,
                source_document_count=source_document_count,
                run_id=run_id,
            )
        except Exception as e:
            logger.error(
                f"Error recording retrieval for document {document_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_usage_stats_by_document(
        self, document_id: uuid.UUID, limit: int = 100, days_back: int = 30
    ) -> list[UsageStats]:
        """Get usage statistics for a specific document."""
        try:
            return await UsageStats.get_by_document_id(self.session, document_id, limit, days_back)
        except Exception as e:
            logger.error(
                f"Error fetching usage stats for document {document_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_usage_stats_by_user(
        self, user_id: str, limit: int = 100, days_back: int = 30
    ) -> list[UsageStats]:
        """Get usage statistics for a specific user."""
        try:
            return await UsageStats.get_by_user_id(self.session, user_id, limit, days_back)
        except Exception as e:
            logger.error(f"Error fetching usage stats for user {user_id}: {e}", exc_info=True)
            raise

    async def get_hot_documents(self, limit: int = 50, days_back: int = 30) -> list[HotDocument]:
        """
        Get the most frequently accessed documents.

        Returns documents ranked by access frequency for maintenance
        and optimization purposes.
        """
        try:
            return await AnalyticsQueries.get_hot_documents(self.session, limit, days_back)
        except Exception as e:
            logger.error(f"Error fetching hot documents: {e}", exc_info=True)
            raise

    async def get_hot_chunks(self, limit: int = 50, days_back: int = 30) -> list[HotChunk]:
        """
        Get the most frequently retrieved chunk IDs.

        Returns chunk IDs ranked by retrieval frequency for maintenance
        and optimization purposes.
        """
        try:
            return await AnalyticsQueries.get_hot_chunks(self.session, limit, days_back)
        except Exception as e:
            logger.error(f"Error fetching hot chunks: {e}", exc_info=True)
            raise

    async def get_chunk_access_stats(
        self, chunk_id: uuid.UUID, days_back: int = 30
    ) -> ChunkStats | None:
        """Get access statistics for a specific chunk ID."""
        try:
            return await AnalyticsQueries.get_chunk_stats(self.session, chunk_id, days_back)
        except Exception as e:
            logger.error(f"Error fetching chunk stats for {chunk_id}: {e}", exc_info=True)
            raise

    async def get_user_activity_summary(self, user_id: str, days_back: int = 30) -> dict[str, Any]:
        """Get activity summary for a specific user."""
        try:
            query = text(
                f"""
                SELECT
                    COUNT(*) as total_queries,
                    COUNT(DISTINCT document_id) as unique_documents_accessed,
                    COUNT(DISTINCT DATE(accessed_at)) as active_days,
                    AVG(array_length(chunk_ids, 1)) as avg_chunks_per_query,
                    MIN(accessed_at) as first_access,
                    MAX(accessed_at) as last_access
                FROM usage_stats
                WHERE user_id = :user_id
                  AND accessed_at >= NOW() - INTERVAL '{days_back} days'
            """
            )

            result = await self.session.execute(query, {"user_id": user_id})
            summary = dict(result.mappings().first() or {})

            doc_query = text(
                f"""
                SELECT d.id, d.title, COUNT(*) as access_count
                FROM usage_stats us
                JOIN documents d ON us.document_id = d.id
                WHERE us.user_id = :user_id
                  AND us.accessed_at >= NOW() - INTERVAL '{days_back} days'
                GROUP BY d.id, d.title
                ORDER BY access_count DESC
                LIMIT 10
            """
            )

            doc_result = await self.session.execute(doc_query, {"user_id": user_id})
            summary["top_documents"] = [
                {
                    "document_id": str(record["id"]),
                    "title": record["title"],
                    "access_count": record["access_count"],
                }
                for record in doc_result.mappings()
            ]

            return summary

        except Exception as e:
            logger.error(
                f"Error fetching user activity summary for {user_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_query_patterns(
        self, limit: int = 100, days_back: int = 30
    ) -> list[dict[str, Any]]:
        """Get common query patterns for analysis."""
        try:
            query = text(
                f"""
                SELECT
                    query_text,
                    COUNT(*) as frequency,
                    COUNT(DISTINCT user_id) as unique_users,
                    AVG(array_length(chunk_ids, 1)) as avg_chunks_returned,
                    AVG((SELECT AVG(score) FROM UNNEST(relevancy_scores) AS score)) as avg_relevancy
                FROM usage_stats
                WHERE query_text IS NOT NULL
                  AND query_text != ''
                  AND accessed_at >= NOW() - INTERVAL '{days_back} days'
                GROUP BY query_text
                ORDER BY frequency DESC
                LIMIT :limit
            """
            )

            result = await self.session.execute(query, {"limit": limit})
            return [dict(record) for record in result.mappings()]

        except Exception as e:
            logger.error(f"Error fetching query patterns: {e}", exc_info=True)
            raise

    async def get_retrieval_performance_metrics(self, days_back: int = 30) -> dict[str, Any]:
        """Get performance metrics for the retrieval system."""
        try:
            basic_query = text(
                f"""
                SELECT
                    COUNT(*) as total_retrievals,
                    COUNT(DISTINCT document_id) as unique_documents_accessed,
                    COUNT(DISTINCT user_id) as unique_users,
                    AVG(array_length(chunk_ids, 1)) as avg_chunks_per_retrieval,
                    AVG((SELECT AVG(score) FROM UNNEST(relevancy_scores) AS score)) as avg_relevancy_score
                FROM usage_stats
                WHERE accessed_at >= NOW() - INTERVAL '{days_back} days'
            """
            )

            basic_result = await self.session.execute(basic_query)
            metrics = dict(basic_result.mappings().first() or {})

            trend_query = text(
                f"""
                SELECT
                    DATE(accessed_at) as date,
                    COUNT(*) as daily_retrievals,
                    COUNT(DISTINCT user_id) as daily_unique_users,
                    COUNT(DISTINCT document_id) as daily_unique_documents
                FROM usage_stats
                WHERE accessed_at >= NOW() - INTERVAL '{days_back} days'
                GROUP BY DATE(accessed_at)
                ORDER BY date DESC
            """
            )

            trend_result = await self.session.execute(trend_query)
            metrics["daily_trends"] = [dict(record) for record in trend_result.mappings()]

            relevancy_query = text(
                f"""
                SELECT
                    d.id,
                    d.title,
                    AVG((SELECT AVG(score) FROM UNNEST(us.relevancy_scores) AS score)) as avg_relevancy,
                    COUNT(*) as access_count
                FROM usage_stats us
                JOIN documents d ON us.document_id = d.id
                WHERE us.accessed_at >= NOW() - INTERVAL '{days_back} days'
                  AND array_length(us.relevancy_scores, 1) > 0
                GROUP BY d.id, d.title
                HAVING COUNT(*) >= 5
                ORDER BY avg_relevancy DESC
                LIMIT 20
            """
            )

            relevancy_result = await self.session.execute(relevancy_query)
            metrics["top_relevancy_documents"] = [
                {
                    "document_id": str(record["id"]),
                    "title": record["title"],
                    "avg_relevancy": (
                        float(record["avg_relevancy"]) if record["avg_relevancy"] else None
                    ),
                    "access_count": record["access_count"],
                }
                for record in relevancy_result.mappings()
            ]

            return metrics

        except Exception as e:
            logger.error(f"Error fetching retrieval performance metrics: {e}", exc_info=True)
            raise

    async def cleanup_old_stats(self, days_to_keep: int = 90) -> int:
        """
        Clean up old usage statistics to manage database size.

        Returns the number of records deleted.
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            query = text(
                """
                DELETE FROM usage_stats
                WHERE accessed_at < :cutoff_date
            """
            )

            await self.session.execute(query, {"cutoff_date": cutoff_date})
            await self.session.commit()
            logger.info("Cleaned up old usage stats records")
            return 0

        except Exception as e:
            logger.error(f"Error cleaning up old usage stats: {e}", exc_info=True)
            raise

    async def get_chunk_usage_distribution(
        self, document_id: uuid.UUID | None = None, days_back: int = 30
    ) -> list[dict[str, Any]]:
        """
        Get distribution of chunk usage to identify hot spots.

        This helps identify which parts of documents are most valuable.
        """
        try:
            params = {"days_back": f"{days_back} days"}
            where_clauses = ["us.accessed_at >= NOW() - INTERVAL :days_back"]

            if document_id:
                where_clauses.append("us.document_id = :document_id")
                params["document_id"] = str(document_id)

            query = text(
                f"""
                SELECT
                    chunk_id,
                    COUNT(*) as access_count,
                    COUNT(DISTINCT us.user_id) as unique_users,
                    COUNT(DISTINCT us.document_id) as document_count,
                    AVG(relevancy_score) as avg_relevancy,
                    MIN(us.accessed_at) as first_access,
                    MAX(us.accessed_at) as last_access
                FROM usage_stats us,
                     UNNEST(us.chunk_ids) WITH ORDINALITY AS t(chunk_id, pos)
                LEFT JOIN UNNEST(us.relevancy_scores) WITH ORDINALITY AS r(relevancy_score, pos2)
                     ON t.pos = r.pos2
                WHERE {" AND ".join(where_clauses)}
                GROUP BY chunk_id
                ORDER BY access_count DESC
                LIMIT 1000
            """
            )

            result = await self.session.execute(query, params)
            return [
                {
                    "chunk_id": str(record["chunk_id"]),
                    "access_count": record["access_count"],
                    "unique_users": record["unique_users"],
                    "document_count": record["document_count"],
                    "avg_relevancy": (
                        float(record["avg_relevancy"]) if record["avg_relevancy"] else None
                    ),
                    "first_access": record["first_access"],
                    "last_access": record["last_access"],
                }
                for record in result.mappings()
            ]

        except Exception as e:
            logger.error(f"Error fetching chunk usage distribution: {e}", exc_info=True)
            raise
