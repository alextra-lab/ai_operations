"""
Admin API for audit log queries.

Provides endpoints for querying and analyzing audit logs with comprehensive
filtering, pagination, and statistics.

P5-A11: Migrated to async database patterns (Nov 2025).

**Authorization:** Admin and Developer roles can read audit logs
**ADR Compliance:** Follows ADR-041 role-based permissions
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import get_current_user
from shared.auth.models import TokenPayload, User
from shared.logging_utils.fastapi import configure_logging

from ..db.database import get_async_db
from ..db.models import AuditLog, UseCase
from ..schemas.audit import (
    AuditLogListResponse,
    AuditLogResponse,
    AuditLogStatsResponse,
)

logger = configure_logging(__name__)
router = APIRouter(prefix="/admin/audit-logs", tags=["admin", "audit"])


# ============================================================================
# Helper Functions
# ============================================================================


def require_admin_or_developer(current_user: TokenPayload) -> None:
    """
    Verify current user is admin or developer.

    Per RLS policies, admin/developer/corpus_admin can read audit logs.

    Raises:
        HTTPException: If user doesn't have permission
    """
    allowed_roles = ["admin", "developer", "corpus_admin"]
    if not current_user.has_any_role(allowed_roles):
        logger.warning(
            "Unauthorized audit log access attempt",
            extra={"user_id": current_user.user_id, "roles": current_user.roles},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin, developer, or corpus_admin can access audit logs",
        )


# ============================================================================
# API Endpoints
# ============================================================================


@router.get(
    "",
    response_model=AuditLogListResponse,
    status_code=status.HTTP_200_OK,
    summary="List audit logs with filters",
)
async def list_audit_logs(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=500, description="Records per page"),
    start_date: datetime | None = Query(None, description="Filter events after this date"),
    end_date: datetime | None = Query(None, description="Filter events before this date"),
    actor_user_id: UUID | None = Query(None, description="Filter by user ID"),
    action: str | None = Query(None, description="Filter by action (partial match)"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    use_case_id: UUID | None = Query(None, description="Filter by use case ID"),
    success: bool | None = Query(None, description="Filter by success status"),
    search: str | None = Query(None, description="Search in action, resource_type, resource_id"),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> AuditLogListResponse:
    """
    Query audit logs with comprehensive filtering and pagination.

    **Filters:**
    - Date range (start_date, end_date)
    - User (actor_user_id)
    - Action (partial match)
    - Resource type
    - Use case
    - Success status
    - Full-text search

    **Pagination:**
    - Returns paginated results with total count
    - Default: page 1, 50 records per page
    - Maximum: 500 records per page

    **Authorization:** Admin, Developer, or Corpus Admin
    """
    require_admin_or_developer(current_user)

    try:
        # Date range filter (default to last 30 days if not specified)
        if end_date is None:
            end_date = datetime.now(UTC)
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        # Build filter conditions
        conditions = [
            AuditLog.event_time >= start_date,
            AuditLog.event_time <= end_date,
        ]

        # User filter
        if actor_user_id:
            conditions.append(AuditLog.actor_user_id == actor_user_id)

        # Action filter (case-insensitive partial match)
        if action:
            conditions.append(AuditLog.action.ilike(f"%{action}%"))

        # Resource type filter
        if resource_type:
            conditions.append(AuditLog.resource_type == resource_type)

        # Use case filter
        if use_case_id:
            conditions.append(AuditLog.use_case_id == use_case_id)

        # Success filter
        if success is not None:
            conditions.append(AuditLog.success == success)

        # Search filter (across multiple fields)
        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    AuditLog.action.ilike(search_pattern),
                    AuditLog.resource_type.ilike(search_pattern),
                    AuditLog.resource_id.ilike(search_pattern),
                )
            )

        # Get total count
        count_stmt = select(func.count()).select_from(AuditLog).where(and_(*conditions))
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Build query with ordering and pagination
        offset = (page - 1) * page_size
        stmt = (
            select(AuditLog)
            .where(and_(*conditions))
            .order_by(AuditLog.event_time.desc())
            .offset(offset)
            .limit(page_size)
        )

        # Execute query
        result = await db.execute(stmt)
        logs = result.scalars().all()

        # Fetch related user and use case data
        log_responses = []
        for log in logs:
            # Get username if actor exists
            actor_username: str | None = None
            if log.actor_user_id:
                user_result = await db.execute(select(User).where(User.id == log.actor_user_id))
                user = user_result.scalar_one_or_none()
                if user:
                    actor_username = str(user.username)

            # Get use case name if exists
            use_case_name: str | None = None
            if log.use_case_id:
                uc_result = await db.execute(select(UseCase).where(UseCase.id == log.use_case_id))
                use_case = uc_result.scalar_one_or_none()
                if use_case:
                    use_case_name = str(use_case.name)

            log_responses.append(
                AuditLogResponse(
                    id=log.id,
                    event_time=log.event_time,
                    actor_user_id=log.actor_user_id,
                    actor_username=actor_username,
                    actor_roles=log.actor_roles,
                    action=log.action,
                    resource_type=log.resource_type,
                    resource_id=log.resource_id,
                    use_case_id=log.use_case_id,
                    use_case_name=use_case_name,
                    request_id=log.request_id,
                    client_ip=str(log.client_ip) if log.client_ip else None,
                    user_agent=log.user_agent,
                    success=log.success,
                    details=log.details,
                    created_at=log.event_time,  # Use event_time as created_at
                )
            )

        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size

        logger.info(
            "Audit logs queried",
            extra={
                "user_id": current_user.user_id,
                "total": total,
                "page": page,
                "filters": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "actor_user_id": str(actor_user_id) if actor_user_id else None,
                    "action": action,
                    "resource_type": resource_type,
                    "success": success,
                },
            },
        )

        return AuditLogListResponse(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            logs=log_responses,
        )

    except Exception as e:
        logger.error(
            "Failed to query audit logs",
            extra={"user_id": current_user.user_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit logs",
        ) from e


@router.get(
    "/stats",
    response_model=AuditLogStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get audit log statistics",
)
async def get_audit_stats(
    start_date: datetime | None = Query(
        None, description="Start date for statistics (default: 30 days ago)"
    ),
    end_date: datetime | None = Query(None, description="End date for statistics (default: now)"),
    actor_user_id: UUID | None = Query(None, description="Filter by user ID"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> AuditLogStatsResponse:
    """
    Get statistical summary of audit logs.

    Returns aggregated statistics including:
    - Total events
    - Success/failure counts
    - Unique users count
    - Top actions
    - Top resource types

    **Authorization:** Admin, Developer, or Corpus Admin
    """
    require_admin_or_developer(current_user)

    try:
        # Date range (default to last 30 days)
        if end_date is None:
            end_date = datetime.now(UTC)
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        # Build base conditions
        conditions = [
            AuditLog.event_time >= start_date,
            AuditLog.event_time <= end_date,
        ]

        # Apply filters
        if actor_user_id:
            conditions.append(AuditLog.actor_user_id == actor_user_id)
        if resource_type:
            conditions.append(AuditLog.resource_type == resource_type)

        # Get total events
        total_stmt = select(func.count()).select_from(AuditLog).where(and_(*conditions))
        total_result = await db.execute(total_stmt)
        total_events = total_result.scalar() or 0

        # Success count
        success_stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(and_(*conditions, AuditLog.success.is_(True)))
        )
        success_result = await db.execute(success_stmt)
        success_count = success_result.scalar() or 0

        # Failure count
        failure_stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(and_(*conditions, AuditLog.success.is_(False)))
        )
        failure_result = await db.execute(failure_stmt)
        failure_count = failure_result.scalar() or 0

        # Unique users count
        unique_users_stmt = (
            select(func.count(func.distinct(AuditLog.actor_user_id)))
            .select_from(AuditLog)
            .where(and_(*conditions, AuditLog.actor_user_id.isnot(None)))
        )
        unique_users_result = await db.execute(unique_users_stmt)
        unique_users = unique_users_result.scalar() or 0

        # Unique resource types
        unique_rt_stmt = (
            select(func.count(func.distinct(AuditLog.resource_type)))
            .select_from(AuditLog)
            .where(and_(*conditions))
        )
        unique_rt_result = await db.execute(unique_rt_stmt)
        unique_resource_types = unique_rt_result.scalar() or 0

        # Top 10 actions
        action_count = func.count(AuditLog.id).label("count")
        top_actions_stmt = (
            select(AuditLog.action, action_count)
            .where(and_(*conditions))
            .group_by(AuditLog.action)
            .order_by(action_count.desc())
            .limit(10)
        )
        top_actions_result = await db.execute(top_actions_stmt)
        top_actions = [{"action": row[0], "count": row[1]} for row in top_actions_result.fetchall()]

        # Top 10 resource types
        resource_count = func.count(AuditLog.id).label("count")
        top_resource_types_stmt = (
            select(AuditLog.resource_type, resource_count)
            .where(and_(*conditions))
            .group_by(AuditLog.resource_type)
            .order_by(resource_count.desc())
            .limit(10)
        )
        top_rt_result = await db.execute(top_resource_types_stmt)
        top_resource_types = [
            {"resource_type": row[0], "count": row[1]} for row in top_rt_result.fetchall()
        ]

        logger.info(
            "Audit log statistics generated",
            extra={
                "user_id": current_user.user_id,
                "total_events": total_events,
                "date_range": f"{start_date.isoformat()} to {end_date.isoformat()}",
            },
        )

        return AuditLogStatsResponse(
            total_events=total_events,
            success_count=success_count,
            failure_count=failure_count,
            unique_users=unique_users,
            unique_resource_types=unique_resource_types,
            date_range_start=start_date,
            date_range_end=end_date,
            top_actions=top_actions,
            top_resource_types=top_resource_types,
        )

    except Exception as e:
        logger.error(
            "Failed to generate audit log statistics",
            extra={"user_id": current_user.user_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit log statistics",
        ) from e


@router.get(
    "/{log_id}",
    response_model=AuditLogResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single audit log entry",
)
async def get_audit_log(
    log_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> AuditLogResponse:
    """
    Get a single audit log entry by ID.

    **Authorization:** Admin, Developer, or Corpus Admin
    """
    require_admin_or_developer(current_user)

    try:
        result = await db.execute(select(AuditLog).where(AuditLog.id == log_id))
        log = result.scalar_one_or_none()

        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audit log {log_id} not found",
            )

        # Get username if actor exists
        actor_username: str | None = None
        if log.actor_user_id:
            user_result = await db.execute(select(User).where(User.id == log.actor_user_id))
            user = user_result.scalar_one_or_none()
            if user:
                actor_username = str(user.username)

        # Get use case name if exists
        use_case_name: str | None = None
        if log.use_case_id:
            uc_result = await db.execute(select(UseCase).where(UseCase.id == log.use_case_id))
            use_case = uc_result.scalar_one_or_none()
            if use_case:
                use_case_name = str(use_case.name)

        logger.info(
            "Audit log retrieved",
            extra={"user_id": current_user.user_id, "log_id": str(log_id)},
        )

        return AuditLogResponse(
            id=log.id,
            event_time=log.event_time,
            actor_user_id=log.actor_user_id,
            actor_username=actor_username,
            actor_roles=log.actor_roles,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            use_case_id=log.use_case_id,
            use_case_name=use_case_name,
            request_id=log.request_id,
            client_ip=str(log.client_ip) if log.client_ip else None,
            user_agent=log.user_agent,
            success=log.success,
            details=log.details,
            created_at=log.event_time,  # Use event_time as created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to retrieve audit log",
            extra={
                "user_id": current_user.user_id,
                "log_id": str(log_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit log",
        ) from e
