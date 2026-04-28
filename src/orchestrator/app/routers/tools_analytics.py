"""
Tool usage analytics and audit API endpoints.

Provides endpoints for viewing tool usage statistics, cost tracking,
center-based aggregation, and audit trails for tool invocations.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import admin_required
from shared.auth.models import TokenPayload
from shared.logging_utils.fastapi import configure_logging

from ..db.database import get_async_db
from ..db.models import ToolInvocation
from ..schemas.tool import InvocationStatus
from ..schemas.tool import ToolInvocation as ToolInvocationSchema
from ..utils.auth import get_current_user

logger = configure_logging(service_name="tools_analytics", log_level="INFO", log_format="json")

router = APIRouter(prefix="/api/v1/tools/analytics", tags=["tools", "analytics"])


@router.get("/usage/summary")
async def get_usage_summary(
    start_date: datetime | None = Query(
        default=None, description="Start date for filtering (ISO 8601 format)"
    ),
    end_date: datetime | None = Query(
        default=None, description="End date for filtering (ISO 8601 format)"
    ),
    db: AsyncSession = Depends(get_async_db),
    _current_user: TokenPayload = Depends(admin_required),
) -> list[dict[str, Any]]:
    """
    Get aggregated tool usage summary.

    Returns aggregated statistics per tool including total calls, successful calls,
    success rate, average duration, and total cost.

    **Requires:** admin role

    Args:
        start_date: Optional start date for filtering (ISO 8601 format)
        end_date: Optional end date for filtering (ISO 8601 format)
        db: Database session
        _current_user: Current authenticated user (admin required)

    Returns:
        List of dictionaries with usage statistics per tool:
        - tool_id: UUID of the tool
        - total_calls: Total number of invocations
        - successful_calls: Number of successful invocations
        - success_rate: Percentage of successful calls (0-100)
        - avg_duration_ms: Average duration in milliseconds
        - total_cost: Total estimated cost
    """
    stmt = (
        select(
            ToolInvocation.tool_id,
            func.count(ToolInvocation.id).label("total_calls"),  # type: ignore
            func.sum(
                case(
                    (ToolInvocation.status == InvocationStatus.SUCCESS.value, 1),
                    else_=0,
                )
            ).label("successful_calls"),
            func.avg(ToolInvocation.duration_ms).label("avg_duration_ms"),
            func.sum(ToolInvocation.cost_estimate).label("total_cost"),
        )
        .group_by(ToolInvocation.tool_id)
        .where(ToolInvocation.tool_id.isnot(None))
    )

    if start_date:
        stmt = stmt.where(ToolInvocation.started_at >= start_date)
    if end_date:
        stmt = stmt.where(ToolInvocation.started_at <= end_date)

    result = await db.execute(stmt)
    results = result.all()

    return [
        {
            "tool_id": str(r.tool_id),
            "total_calls": r.total_calls,
            "successful_calls": r.successful_calls or 0,
            "success_rate": (
                round((r.successful_calls or 0) / r.total_calls * 100, 2)
                if r.total_calls > 0
                else 0.0
            ),
            "avg_duration_ms": round(float(r.avg_duration_ms or 0), 2),
            "total_cost": round(float(r.total_cost or 0), 4),
        }
        for r in results
    ]


@router.get("/usage/by-center")
async def get_usage_by_center(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to look back"),
    db: AsyncSession = Depends(get_async_db),
    _current_user: TokenPayload = Depends(admin_required),
) -> list[dict[str, Any]]:
    """
    Get tool usage aggregated by center.

    Returns aggregated statistics per center including total calls and total cost
    for the specified time period.

    **Requires:** admin role

    Args:
        days: Number of days to look back (1-365, default 30)
        db: Database session
        _current_user: Current authenticated user (admin required)

    Returns:
        List of dictionaries with usage statistics per center:
        - center_id: Center identifier
        - total_calls: Total number of invocations
        - total_cost: Total estimated cost
    """
    since = datetime.now(UTC) - timedelta(days=days)

    stmt = (
        select(
            ToolInvocation.center_id,
            func.count(ToolInvocation.id).label("total_calls"),  # type: ignore
            func.sum(ToolInvocation.cost_estimate).label("total_cost"),
        )
        .where(
            ToolInvocation.started_at >= since,
            ToolInvocation.center_id.isnot(None),
        )
        .group_by(ToolInvocation.center_id)
    )
    result = await db.execute(stmt)
    results = result.all()

    return [
        {
            "center_id": r.center_id,
            "total_calls": r.total_calls,
            "total_cost": round(float(r.total_cost or 0), 4),
        }
        for r in results
    ]


@router.get("/audit/{run_id}", response_model=list[ToolInvocationSchema])
async def get_tool_audit_for_request(
    run_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> list[ToolInvocationSchema]:
    """
    Get tool invocation audit trail for a specific run.

    Returns all tool invocations associated with a given run_id.
    Non-admin users can only view their own requests, while admins can view all.

    Args:
        run_id: Run identifier to retrieve audit trail for
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of ToolInvocation records for the specified run

    Raises:
        HTTPException: 404 if run_id not found or user doesn't have access
    """
    stmt = select(ToolInvocation).where(ToolInvocation.run_id == run_id)

    # Non-admin users can only see their own requests
    if not current_user.is_admin():
        if not current_user.user_id:
            # If user_id is not available, return 404
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No tool invocations found for run_id '{run_id}'",
            )
        try:
            user_uuid = UUID(current_user.user_id)
            stmt = stmt.where(ToolInvocation.user_id == user_uuid)
        except (ValueError, TypeError):
            # Invalid user_id format, return 404
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No tool invocations found for run_id '{run_id}'",
            )

    stmt = stmt.order_by(ToolInvocation.started_at.desc())
    result = await db.execute(stmt)
    invocations = result.scalars().all()

    if not invocations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No tool invocations found for run_id '{run_id}'",
        )

    return [
        ToolInvocationSchema(
            id=inv.id,
            tool_id=inv.tool_id,
            use_case_id=inv.use_case_id,
            run_id=inv.run_id,
            user_id=inv.user_id,
            center_id=inv.center_id,
            tool_name=inv.tool_name,
            tool_parameters=inv.tool_parameters,
            status=InvocationStatus(inv.status),
            response_data=inv.response_data,
            error_message=inv.error_message,
            started_at=inv.started_at,
            completed_at=inv.completed_at,
            duration_ms=inv.duration_ms,
            cost_estimate=inv.cost_estimate,
        )
        for inv in invocations
    ]
