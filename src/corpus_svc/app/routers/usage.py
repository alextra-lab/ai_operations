"""
API router for usage statistics operations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging

from ..db.connection import get_db_session
from ..repositories.usage_stats_repository import UsageStatsRepository
from ..schemas.usage import UsageStatsCreateRequest, UsageStatsResponse

logger = configure_logging(service_name="usage_router")

router = APIRouter()


async def get_usage_stats_repository(
    session: AsyncSession = Depends(get_db_session),
) -> UsageStatsRepository:
    """Get usage stats repository with dependencies."""
    return UsageStatsRepository(session)


@router.post(
    "/",
    response_model=UsageStatsResponse,
    summary="Record a retrieval event",
    status_code=status.HTTP_201_CREATED,
)
async def record_retrieval(
    usage_data: UsageStatsCreateRequest,
    usage_stats_repo: UsageStatsRepository = Depends(get_usage_stats_repository),
) -> UsageStatsResponse:
    """
    Record a retrieval event.
    """
    try:
        usage_stat = await usage_stats_repo.record_retrieval(
            document_id=usage_data.document_id,
            chunk_ids=usage_data.chunk_ids,
            user_id=usage_data.user_id,
            query_text=usage_data.query_text,
            relevancy_scores=usage_data.relevancy_scores,
            metadata=usage_data.metadata,
            run_id=usage_data.run_id,
            rag_confidence=usage_data.rag_confidence,
            total_results_found=usage_data.total_results_found,
            source_document_count=usage_data.source_document_count,
            average_relevancy=usage_data.average_relevancy,
        )
        return UsageStatsResponse.model_validate(usage_stat)
    except Exception as e:
        logger.error(f"Error recording retrieval: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while recording retrieval: {e!s}",
        )
