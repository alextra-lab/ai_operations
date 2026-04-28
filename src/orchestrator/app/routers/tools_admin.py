"""
Admin API endpoints for tool management.

Requires 'admin' role for all operations.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import admin_required
from shared.auth.models import TokenPayload
from shared.logging_utils.fastapi import get_logger

logger = get_logger(__name__)

from ..db.database import get_async_db
from ..schemas.tool import (
    Tool,
    ToolCategory,
    ToolCreate,
    ToolListItem,
    ToolPermission,
    ToolPermissionCreate,
    ToolSecret,
    ToolSecretCreate,
    ToolUpdate,
)
from ..services.secrets_manager import SecretsManager
from ..services.tool_discovery_service import ToolDiscoveryService
from ..services.tool_permission_service import ToolPermissionService
from ..services.tool_service import ToolService

router = APIRouter(prefix="/api/v1/admin/tools", tags=["admin", "tools"])


def require_admin(current_user: TokenPayload) -> None:
    """Ensure current user has admin role."""
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )


@router.post("/", response_model=Tool, status_code=status.HTTP_201_CREATED)
async def create_tool(
    tool_data: ToolCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(admin_required),
) -> Tool:
    """
    Create a new tool configuration.

    **Requires:** admin role
    """
    tool_service = ToolService(db)

    try:
        return await tool_service.create_tool(tool_data, UUID(current_user.user_id))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/", response_model=list[ToolListItem])
async def list_tools(
    category: ToolCategory | None = None,
    enabled_only: bool = False,
    healthy_only: bool = False,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(admin_required),
) -> list[ToolListItem]:
    """
    List all tools with optional filters.

    **Requires:** admin role
    """
    tool_service = ToolService(db)
    return await tool_service.list_tools(category, enabled_only, healthy_only)


@router.get("/{tool_id}", response_model=Tool)
async def get_tool(
    tool_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(admin_required),
) -> Tool:
    """
    Get detailed tool configuration.

    **Requires:** admin role

    Accepts either UUID (primary key) or tool_id (string identifier).
    """
    tool_service = ToolService(db)

    # Try UUID first (primary key)
    try:
        tool = await tool_service.get_tool_by_uuid(UUID(tool_id))
        if tool:
            return tool
    except (ValueError, TypeError):
        pass

    # Fall back to tool_id string
    tool = await tool_service.get_tool(tool_id)

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_id}' not found",
        )

    return tool


@router.put("/{tool_id}", response_model=Tool)
async def update_tool(
    tool_id: str,
    update_data: ToolUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(admin_required),
) -> Tool:
    """
    Update tool configuration.

    **Requires:** admin role

    Accepts either UUID (primary key) or tool_id (string identifier).
    """
    tool_service = ToolService(db)

    # Try UUID first (primary key)
    try:
        tool_uuid = UUID(tool_id)
        tool = await tool_service.get_tool_by_uuid(tool_uuid)
        if tool:
            # Update using tool_id string (service expects tool_id)
            try:
                return await tool_service.update_tool(
                    tool.tool_id,
                    update_data,
                    UUID(current_user.user_id),
                )
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(e),
                ) from e
    except (ValueError, TypeError):
        pass

    # Fall back to tool_id string
    try:
        return await tool_service.update_tool(
            tool_id,
            update_data,
            UUID(current_user.user_id),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool(
    tool_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(admin_required),
) -> None:
    """
    Delete a tool configuration.

    **Requires:** admin role

    Accepts either UUID (primary key) or tool_id (string identifier).
    """
    tool_service = ToolService(db)

    # Try UUID first (primary key)
    try:
        tool_uuid = UUID(tool_id)
        tool = await tool_service.get_tool_by_uuid(tool_uuid)
        if tool:
            deleted = await tool_service.delete_tool(tool.tool_id)
            if deleted:
                return
    except (ValueError, TypeError):
        pass

    # Fall back to tool_id string
    deleted = await tool_service.delete_tool(tool_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_id}' not found",
        )


@router.post("/{tool_id}/enable", response_model=Tool)
async def enable_tool(
    tool_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(admin_required),
) -> Tool:
    """
    Enable a tool.

    **Requires:** admin role

    Accepts either UUID (primary key) or tool_id (string identifier).
    """
    tool_service = ToolService(db)

    # Try UUID first (primary key)
    try:
        tool_uuid = UUID(tool_id)
        tool = await tool_service.get_tool_by_uuid(tool_uuid)
        if tool:
            try:
                return await tool_service.enable_tool(tool.tool_id)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(e),
                ) from e
    except (ValueError, TypeError):
        pass

    # Fall back to tool_id string
    try:
        return await tool_service.enable_tool(tool_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post("/{tool_id}/disable", response_model=Tool)
async def disable_tool(
    tool_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(admin_required),
) -> Tool:
    """
    Disable a tool.

    **Requires:** admin role

    Accepts either UUID (primary key) or tool_id (string identifier).
    """
    tool_service = ToolService(db)

    # Try UUID first (primary key)
    try:
        tool_uuid = UUID(tool_id)
        tool = await tool_service.get_tool_by_uuid(tool_uuid)
        if tool:
            try:
                return await tool_service.disable_tool(tool.tool_id)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(e),
                ) from e
    except (ValueError, TypeError):
        pass

    # Fall back to tool_id string
    try:
        return await tool_service.disable_tool(tool_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


# Secret Management Endpoints


@router.post(
    "/{tool_id}/secrets",
    response_model=ToolSecret,
    status_code=status.HTTP_201_CREATED,
)
async def create_tool_secret(
    tool_id: str,
    secret_data: ToolSecretCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(admin_required),
) -> ToolSecret:
    """
    Store an encrypted secret for a tool.

    **Requires:** admin role
    **Security:** Secret value encrypted before storage
    """
    tool_service = ToolService(db)
    tool = await tool_service.get_tool(tool_id)

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_id}' not found",
        )

    secrets_mgr = SecretsManager(db)

    try:
        secret_model = await secrets_mgr.store_secret(
            tool_id=tool.id,
            secret_name=secret_data.secret_name,
            secret_type=secret_data.secret_type,
            secret_value=secret_data.secret_value,
            expires_at=secret_data.expires_at,
        )
        # Convert SQLAlchemy model to Pydantic schema
        from ..db.models import ToolSecret as ToolSecretModel

        # Query the database to get the actual instance for proper conversion
        stmt = select(ToolSecretModel).where(ToolSecretModel.id == secret_model.id)
        result = await db.execute(stmt)
        secret_db = result.scalar_one_or_none()

        if not secret_db:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created secret",
            )

        return ToolSecret.model_validate(secret_db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to store secret: {e!s}",
        ) from e


@router.delete(
    "/{tool_id}/secrets/{secret_name}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_tool_secret(
    tool_id: str,
    secret_name: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(admin_required),
) -> None:
    """
    Delete a tool secret.

    **Requires:** admin role
    """
    secrets_mgr = SecretsManager(db)
    deleted = await secrets_mgr.delete_secret(secret_name)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Secret '{secret_name}' not found",
        )


# Permission Management Endpoints


@router.post(
    "/{tool_id}/permissions",
    response_model=ToolPermission,
    status_code=status.HTTP_201_CREATED,
)
async def grant_tool_permission(
    tool_id: str,
    permission_data: ToolPermissionCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(admin_required),
) -> ToolPermission:
    """
    Grant permissions for a tool to a role.

    **Requires:** admin role
    """
    tool_service = ToolService(db)
    tool = await tool_service.get_tool(tool_id)

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_id}' not found",
        )

    permission_service = ToolPermissionService(db)

    try:
        permission = await permission_service.grant_permission(
            tool_id=tool.id,
            role=permission_data.role,
            can_view=permission_data.can_view,
            can_use=permission_data.can_use,
            can_configure=permission_data.can_configure,
            max_calls_per_hour=permission_data.max_calls_per_hour,
            max_calls_per_day=permission_data.max_calls_per_day,
            created_by_user_id=UUID(current_user.user_id),
        )
        return ToolPermission.model_validate(permission)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{tool_id}/permissions",
    response_model=list[ToolPermission],
)
async def list_tool_permissions(
    tool_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(admin_required),
) -> list[ToolPermission]:
    """
    List all permissions for a tool.

    **Requires:** admin role
    """
    tool_service = ToolService(db)
    tool = await tool_service.get_tool(tool_id)

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_id}' not found",
        )

    permission_service = ToolPermissionService(db)
    permissions = await permission_service.list_permissions(tool.id)

    return [ToolPermission.model_validate(p) for p in permissions]


@router.get(
    "/{tool_id}/permissions/{role}",
    response_model=ToolPermission,
)
async def get_tool_permission(
    tool_id: str,
    role: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(admin_required),
) -> ToolPermission:
    """
    Get specific permission for a tool and role.

    **Requires:** admin role
    """
    tool_service = ToolService(db)
    tool = await tool_service.get_tool(tool_id)

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_id}' not found",
        )

    permission_service = ToolPermissionService(db)
    permission = await permission_service.get_permission(tool.id, role)

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permission for tool '{tool_id}' and role '{role}' not found",
        )

    return ToolPermission.model_validate(permission)


@router.put(
    "/{tool_id}/permissions/{role}",
    response_model=ToolPermission,
)
async def update_tool_permission(
    tool_id: str,
    role: str,
    permission_data: ToolPermissionCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(admin_required),
) -> ToolPermission:
    """
    Update permission for a tool and role.

    **Requires:** admin role
    **Note:** Role in path must match role in body
    """
    if permission_data.role != role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role in path must match role in body",
        )

    tool_service = ToolService(db)
    tool = await tool_service.get_tool(tool_id)

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_id}' not found",
        )

    permission_service = ToolPermissionService(db)

    try:
        permission = await permission_service.grant_permission(
            tool_id=tool.id,
            role=permission_data.role,
            can_view=permission_data.can_view,
            can_use=permission_data.can_use,
            can_configure=permission_data.can_configure,
            max_calls_per_hour=permission_data.max_calls_per_hour,
            max_calls_per_day=permission_data.max_calls_per_day,
            created_by_user_id=UUID(current_user.user_id),
        )
        return ToolPermission.model_validate(permission)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete(
    "/{tool_id}/permissions/{role}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_tool_permission(
    tool_id: str,
    role: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(admin_required),
) -> None:
    """
    Revoke permission for a tool and role.

    **Requires:** admin role
    """
    tool_service = ToolService(db)
    tool = await tool_service.get_tool(tool_id)

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_id}' not found",
        )

    permission_service = ToolPermissionService(db)
    deleted = await permission_service.revoke_permission(tool.id, role)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permission for tool '{tool_id}' and role '{role}' not found",
        )


@router.post("/{tool_id}/discover", response_model=Tool)
async def discover_tool_capabilities(
    tool_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(admin_required),
) -> Tool:
    """
    Discover tool capabilities from MCP server and update tool configuration.

    Connects to the MCP server, initializes session, retrieves available tools,
    and updates the tool record with discovered capabilities.

    **Requires:** admin role

    **Note:** This operation may take several seconds depending on MCP server response time.
    """
    tool_service = ToolService(db)
    tool = await tool_service.get_tool(tool_id)

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_id}' not found",
        )

    discovery_service = ToolDiscoveryService(db)

    try:
        return await discovery_service.update_tool_from_discovery(tool.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tool discovery failed: {e!s}",
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error during tool discovery: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool discovery error: {e!s}",
        ) from e
