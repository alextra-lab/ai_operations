"""
Admin Router

Administrative endpoints for token usage tracking and system management.

P5-A23 Phase 7: Converted to async database patterns (Nov 2025).
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import admin_required, get_current_user
from shared.auth.models import TokenPayload
from shared.logging_utils.fastapi import get_logger

from ..db.database import get_async_db
from ..schemas.token_usage import (
    AllCentersUsageSummaryResponse,
    CenterUsageSummaryResponse,
    UserUsageResponse,
)
from ..services.token_tracker import TokenTracker

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get(
    "/token-usage/by-center",
    response_model=AllCentersUsageSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get token usage summary for all centers",
    dependencies=[Depends(admin_required)],
)
async def get_all_centers_usage(
    start_date: datetime | None = Query(
        None, description="Start date for usage period (default: 30 days ago)"
    ),
    end_date: datetime | None = Query(None, description="End date for usage period (default: now)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> AllCentersUsageSummaryResponse:
    """
    Get aggregated token usage summary for all centers.

    Admin only. Returns usage statistics aggregated by center for a specified date range.
    """
    # Set defaults if not provided
    if end_date is None:
        end_date = datetime.now(UTC)
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    try:
        tracker = TokenTracker(db)
        summary = await tracker.get_all_centers_usage_summary(start_date, end_date)

        logger.info(
            "Retrieved token usage for all centers",
            extra={
                "user_id": current_user.user_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "center_count": len(summary.centers),
            },
        )

        return summary

    except Exception as e:
        logger.error(
            f"Failed to retrieve all centers usage: {e}",
            extra={"user_id": current_user.user_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve token usage summary",
        ) from e


@router.get(
    "/token-usage/by-center/{center_id}",
    response_model=CenterUsageSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get token usage summary for a specific center",
    dependencies=[Depends(admin_required)],
)
async def get_center_usage(
    center_id: str,
    start_date: datetime | None = Query(
        None, description="Start date for usage period (default: 30 days ago)"
    ),
    end_date: datetime | None = Query(None, description="End date for usage period (default: now)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> CenterUsageSummaryResponse:
    """
    Get aggregated token usage summary for a specific center.

    Admin only. Returns usage statistics for a single center for a specified date range.
    """
    # Set defaults if not provided
    if end_date is None:
        end_date = datetime.now(UTC)
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    try:
        tracker = TokenTracker(db)
        summary = await tracker.get_center_usage_summary(center_id, start_date, end_date)

        logger.info(
            f"Retrieved token usage for center {center_id}",
            extra={
                "user_id": current_user.user_id,
                "center_id": center_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        return CenterUsageSummaryResponse(
            center_id=center_id,
            start_date=start_date,
            end_date=end_date,
            summary=summary,
        )

    except Exception as e:
        logger.error(
            f"Failed to retrieve center usage: {e}",
            extra={
                "user_id": current_user.user_id,
                "center_id": center_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve token usage for center {center_id}",
        ) from e


@router.get(
    "/token-usage/by-user/{user_id}",
    response_model=UserUsageResponse,
    status_code=status.HTTP_200_OK,
    summary="Get token usage summary for a specific user",
    dependencies=[Depends(admin_required)],
)
async def get_user_usage(
    user_id: UUID,
    start_date: datetime | None = Query(
        None, description="Start date for usage period (default: 30 days ago)"
    ),
    end_date: datetime | None = Query(None, description="End date for usage period (default: now)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> UserUsageResponse:
    """
    Get aggregated token usage summary for a specific user.

    Admin only. Returns usage statistics for a single user for a specified date range.
    """
    # Set defaults if not provided
    if end_date is None:
        end_date = datetime.now(UTC)
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    try:
        tracker = TokenTracker(db)
        summary = await tracker.get_user_usage_summary(user_id, start_date, end_date)

        logger.info(
            f"Retrieved token usage for user {user_id}",
            extra={
                "user_id": current_user.user_id,
                "target_user_id": str(user_id),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        return UserUsageResponse(
            user_id=user_id,
            center_id=summary.center_id,
            summary=summary,
        )

    except Exception as e:
        logger.error(
            f"Failed to retrieve user usage: {e}",
            extra={
                "user_id": current_user.user_id,
                "target_user_id": str(user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve token usage for user {user_id}",
        ) from e


@router.get(
    "/token-usage/me",
    response_model=UserUsageResponse,
    status_code=status.HTTP_200_OK,
    summary="Get token usage summary for current user",
)
async def get_my_usage(
    start_date: datetime | None = Query(
        None, description="Start date for usage period (default: 30 days ago)"
    ),
    end_date: datetime | None = Query(None, description="End date for usage period (default: now)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> UserUsageResponse:
    """
    Get aggregated token usage summary for the current authenticated user.

    Any authenticated user can view their own usage statistics.
    """
    # Set defaults if not provided
    if end_date is None:
        end_date = datetime.now(UTC)
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    try:
        user_uuid = UUID(current_user.user_id)
        tracker = TokenTracker(db)
        summary = await tracker.get_user_usage_summary(user_uuid, start_date, end_date)

        logger.info(
            "User retrieved their own token usage",
            extra={
                "user_id": current_user.user_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        return UserUsageResponse(
            user_id=user_uuid,
            center_id=summary.center_id,
            summary=summary,
        )

    except Exception as e:
        logger.error(
            f"Failed to retrieve user's own usage: {e}",
            extra={"user_id": current_user.user_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve your token usage",
        ) from e
