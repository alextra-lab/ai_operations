"""
Developer API endpoints for tool discovery.

Provides tool listing and details for use case configuration.
Requires authentication and respects RBAC permissions.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import get_current_user
from shared.auth.models import TokenPayload
from shared.logging_utils.fastapi import get_logger

from ..db.database import get_async_db
from ..schemas.tool import Tool, ToolCategory, ToolListItem
from ..services.tool_permission_service import ToolPermissionService
from ..services.tool_service import ToolService

router = APIRouter(prefix="/api/v1/tools", tags=["tools", "developer"])
logger = get_logger(__name__)


@router.get("/available", response_model=list[ToolListItem])
async def list_available_tools(
    category: ToolCategory | None = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> list[ToolListItem]:
    """
    List tools available to current user based on role.

    Returns enabled tools that the user's role has permission to use.
    Supports optional category filtering.

    **Permissions:** All authenticated users (filtered by RBAC)
    """
    try:
        permission_service = ToolPermissionService(db)

        # Get all user roles for multi-role support (ADR-060)
        user_roles = current_user.roles if current_user.roles else ["user"]

        # Get tool IDs user's roles are allowed to use (enabled only)
        # This checks all roles and returns union of allowed tools
        allowed_tool_ids = await permission_service.get_allowed_tools_for_roles(
            roles=user_roles,
            enabled_only=True,
        )

        if not allowed_tool_ids:
            # No allowed tools for these roles - return empty list (not an error)
            logger.debug(
                "No allowed tools found for roles %s",
                user_roles,
                extra={"user_roles": user_roles},
            )
            return []

        tool_service = ToolService(db)

        # Get all enabled tools matching category filter
        # (permission filtering happens via allowed_tool_ids)
        all_tools = await tool_service.list_tools(
            category=category,
            enabled_only=True,
            healthy_only=False,
        )

        # Filter to allowed tools (convert to set for O(1) lookup)
        allowed_ids_set = set(allowed_tool_ids)
        filtered_tools = [tool for tool in all_tools if tool.id in allowed_ids_set]

        logger.debug(
            "Returning %d tools for roles %s",
            len(filtered_tools),
            user_roles,
            extra={
                "user_roles": user_roles,
                "tool_count": len(filtered_tools),
            },
        )
        return filtered_tools

    except Exception as e:
        logger.error(
            "Error listing available tools",
            exc_info=True,
            extra={
                "user_roles": current_user.roles,
                "category": category,
                "user_id": current_user.user_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available tools. Please try again later.",
        ) from e


@router.get("/{tool_id}/details", response_model=Tool)
async def get_tool_details(
    tool_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> Tool:
    """
    Get detailed tool information for configuration.

    Includes parameters schema, usage examples, capabilities, etc.
    Requires permission check based on user's role.

    **Permissions:** All authenticated users (requires can_use or can_view permission)
    """
    tool_service = ToolService(db)
    tool = await tool_service.get_tool(tool_id)

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_id}' not found",
        )

    # Admin role bypasses permission checks
    if current_user.is_admin():
        return Tool.model_validate(tool)

    # Check if user's roles have permission to view or use this tool
    permission_service = ToolPermissionService(db)

    # Get all user roles for multi-role support (ADR-060)
    user_roles = current_user.roles if current_user.roles else ["user"]

    # Check if any role has view or use permission
    has_view = await permission_service.check_permission_for_roles(
        tool_id=tool.id, roles=user_roles, permission_type="view"
    )
    has_use = await permission_service.check_permission_for_roles(
        tool_id=tool.id, roles=user_roles, permission_type="use"
    )

    if not (has_view or has_use):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Roles {user_roles} do not have permission to view this tool",
        )

    return Tool.model_validate(tool)
