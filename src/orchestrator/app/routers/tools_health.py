"""
Tool health monitoring API endpoints.

Provides endpoints for monitoring tool health status, viewing health check history,
and triggering manual health checks.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import admin_required
from shared.auth.models import TokenPayload
from shared.logging_utils.fastapi import get_logger

from ..db.database import get_async_db
from ..db.models import Tool, ToolHealthCheck
from ..schemas.tool import ToolHealthCheck as ToolHealthCheckSchema
from ..schemas.tool import ToolStatus
from ..services.tool_health_monitor import ToolHealthMonitor

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/tools/health", tags=["tools", "monitoring"])


@router.get("/status")
async def get_overall_health_status(
    db: AsyncSession = Depends(get_async_db),
    _current_user: TokenPayload = Depends(admin_required),
) -> dict[str, Any]:
    """
    Get overall health status of all enabled tools.

    Returns summary statistics including total tools, online/offline counts,
    and health percentage.

    **Requires:** admin role

    Returns:
        Dictionary with health status summary:
        - total_tools: Total number of enabled tools
        - online: Number of tools currently online
        - offline: Number of tools currently offline
        - health_percentage: Percentage of tools that are online
        - last_check: Timestamp of most recent health check (if any)
    """
    stmt = select(Tool).where(Tool.is_enabled == True)  # noqa: E712
    result = await db.execute(stmt)
    tools = result.scalars().all()

    if not tools:
        return {
            "total_tools": 0,
            "online": 0,
            "offline": 0,
            "health_percentage": 0.0,
            "last_check": None,
        }

    online = sum(1 for t in tools if t.is_healthy)
    offline = len(tools) - online

    # Find most recent health check timestamp
    last_check_times = [t.last_health_check for t in tools if t.last_health_check is not None]
    last_check = max(last_check_times) if last_check_times else None

    health_percentage = (online / len(tools) * 100) if tools else 0.0

    return {
        "total_tools": len(tools),
        "online": online,
        "offline": offline,
        "health_percentage": round(health_percentage, 2),
        "last_check": last_check.isoformat() if last_check else None,
    }


@router.get("/{tool_id}/history", response_model=list[ToolHealthCheckSchema])
async def get_tool_health_history(
    tool_id: UUID,
    hours: int = Query(default=24, ge=1, le=168, description="Hours of history to retrieve"),
    db: AsyncSession = Depends(get_async_db),
    _current_user: TokenPayload = Depends(admin_required),
) -> list[ToolHealthCheckSchema]:
    """
    Get health check history for a specific tool.

    **Requires:** admin role

    Args:
        tool_id: UUID of the tool
        hours: Number of hours of history to retrieve (1-168, default 24)

    Returns:
        List of ToolHealthCheck records ordered by most recent first

    Raises:
        HTTPException: 404 if tool not found
    """
    # Verify tool exists
    stmt = select(Tool).where(Tool.id == tool_id)
    result = await db.execute(stmt)
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_id}' not found",
        )

    # Calculate time threshold
    since = datetime.now(UTC) - timedelta(hours=hours)

    # Query health checks
    stmt = (
        select(ToolHealthCheck)
        .where(
            ToolHealthCheck.tool_id == tool_id,
            ToolHealthCheck.checked_at >= since,
        )
        .order_by(ToolHealthCheck.checked_at.desc())
    )
    result = await db.execute(stmt)
    checks = result.scalars().all()

    # Convert to schemas
    return [
        ToolHealthCheckSchema(
            id=check.id,
            tool_id=UUID(str(check.tool_id)),
            status=ToolStatus(check.status),
            response_time_ms=check.response_time_ms,
            error_message=check.error_message,
            checked_at=check.checked_at,
            mcp_server_info=check.mcp_server_info,
        )
        for check in checks
    ]


@router.post("/{tool_id}/check", response_model=ToolHealthCheckSchema)
async def trigger_health_check(
    tool_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _current_user: TokenPayload = Depends(admin_required),
) -> ToolHealthCheckSchema:
    """
    Trigger immediate health check for a tool.

    **Requires:** admin role

    Args:
        tool_id: UUID of the tool to check

    Returns:
        ToolHealthCheck record with results

    Raises:
        HTTPException: 404 if tool not found, 400 if health check fails
    """
    # Verify tool exists
    stmt = select(Tool).where(Tool.id == tool_id)
    result = await db.execute(stmt)
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_id}' not found",
        )

    # Perform health check
    monitor = ToolHealthMonitor(db)
    try:
        health_check = await monitor.check_tool_health(tool_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    # Convert to schema
    return ToolHealthCheckSchema(
        id=health_check.id,
        tool_id=health_check.tool_id,
        status=ToolStatus(health_check.status),
        response_time_ms=health_check.response_time_ms,
        error_message=health_check.error_message,
        checked_at=health_check.checked_at,
        mcp_server_info=health_check.mcp_server_info,
    )
