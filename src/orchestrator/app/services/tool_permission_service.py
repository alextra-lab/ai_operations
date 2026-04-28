"""
Tool permission management service.

Manages role-based access control for tools.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging

from ..db.models import Tool, ToolPermission

logger = configure_logging(service_name="tool_permission_service")


class ToolPermissionService:
    """Service for managing tool permissions."""

    def __init__(self, db: AsyncSession):
        """Initialize permission service."""
        self.db = db

    async def grant_permission(
        self,
        tool_id: UUID,
        role: str,
        can_view: bool = True,
        can_use: bool = False,
        can_configure: bool = False,
        max_calls_per_hour: int | None = None,
        max_calls_per_day: int | None = None,
        created_by_user_id: UUID | None = None,
    ) -> ToolPermission:
        """
        Grant permissions for a tool to a role.

        Args:
            tool_id: Tool UUID
            role: Role name
            can_view: View permission (default: True)
            can_use: Use permission (default: False)
            can_configure: Configure permission (default: False)
            max_calls_per_hour: Hourly rate limit (optional)
            max_calls_per_day: Daily rate limit (optional)
            created_by_user_id: User creating the permission

        Returns:
            Created or updated ToolPermission record

        Raises:
            ValueError: If tool_id does not exist
        """
        # Verify tool exists
        stmt = select(Tool).where(Tool.id == tool_id)
        result = await self.db.execute(stmt)
        tool = result.scalar_one_or_none()
        if not tool:
            raise ValueError(f"Tool with ID '{tool_id}' not found")

        # Check if permission already exists
        stmt = select(ToolPermission).where(
            ToolPermission.tool_id == tool_id, ToolPermission.role == role
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing
            existing.can_view = can_view
            existing.can_use = can_use
            existing.can_configure = can_configure
            existing.max_calls_per_hour = max_calls_per_hour
            existing.max_calls_per_day = max_calls_per_day
            await self.db.commit()
            await self.db.refresh(existing)
            logger.info("Updated permission for tool %s, role %s", tool_id, role)
            return existing

        # Create new
        permission = ToolPermission(
            tool_id=tool_id,
            role=role,
            can_view=can_view,
            can_use=can_use,
            can_configure=can_configure,
            max_calls_per_hour=max_calls_per_hour,
            max_calls_per_day=max_calls_per_day,
            created_by=created_by_user_id,
        )

        self.db.add(permission)
        await self.db.commit()
        await self.db.refresh(permission)

        logger.info("Granted permission for tool %s, role %s", tool_id, role)
        return permission

    async def check_permission(
        self,
        tool_id: UUID,
        role: str,
        permission_type: str = "use",
    ) -> bool:
        """
        Check if a role has specific permission for a tool.

        Args:
            tool_id: Tool UUID
            role: Role name
            permission_type: 'view', 'use', or 'configure'

        Returns:
            True if permitted, False otherwise

        Note:
            Admin role bypasses all permission checks and returns True.
        """
        # Admin role bypasses all permission checks
        if role == "admin":
            return True

        stmt = select(ToolPermission).where(
            ToolPermission.tool_id == tool_id, ToolPermission.role == role
        )
        result = await self.db.execute(stmt)
        permission = result.scalar_one_or_none()

        if not permission:
            return False

        permission_map = {
            "view": permission.can_view,
            "use": permission.can_use,
            "configure": permission.can_configure,
        }

        return permission_map.get(permission_type, False)

    async def check_permission_for_roles(
        self,
        tool_id: UUID,
        roles: list[str],
        permission_type: str = "use",
    ) -> bool:
        """
        Check if any of the provided roles has specific permission for a tool.

        This method supports multi-role users (ADR-060) by checking all roles.
        If any role has the required permission, returns True.
        Admin role always bypasses permission checks.

        Args:
            tool_id: Tool UUID
            roles: List of role names to check
            permission_type: 'view', 'use', or 'configure'

        Returns:
            True if any role has permission, False otherwise

        Note:
            If "admin" is in the roles list, returns True immediately (bypass).
        """
        # Admin role bypasses all permission checks
        if "admin" in roles:
            return True

        # Check if any role has the required permission
        if not roles:
            return False

        stmt = select(ToolPermission).where(
            and_(
                ToolPermission.tool_id == tool_id,
                ToolPermission.role.in_(roles),
            )
        )
        result = await self.db.execute(stmt)
        permissions = result.scalars().all()

        if not permissions:
            return False

        # Check if any permission grants the required access
        permission_map = {
            "view": lambda p: p.can_view,
            "use": lambda p: p.can_use,
            "configure": lambda p: p.can_configure,
        }

        check_func = permission_map.get(permission_type, lambda _: False)
        return any(check_func(permission) for permission in permissions)

    async def list_permissions(
        self,
        tool_id: UUID,
    ) -> Sequence[ToolPermission]:
        """
        List all permissions for a tool.

        Args:
            tool_id: Tool UUID

        Returns:
            List of ToolPermission records
        """
        stmt = (
            select(ToolPermission)
            .where(ToolPermission.tool_id == tool_id)
            .order_by(ToolPermission.role)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_permission(
        self,
        tool_id: UUID,
        role: str,
    ) -> ToolPermission | None:
        """
        Get specific permission for a tool and role.

        Args:
            tool_id: Tool UUID
            role: Role name

        Returns:
            ToolPermission record if found, None otherwise
        """
        stmt = select(ToolPermission).where(
            ToolPermission.tool_id == tool_id, ToolPermission.role == role
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_permission(
        self,
        tool_id: UUID,
        role: str,
    ) -> bool:
        """
        Revoke permission for a tool and role.

        Args:
            tool_id: Tool UUID
            role: Role name

        Returns:
            True if permission was deleted, False if not found
        """
        stmt = select(ToolPermission).where(
            ToolPermission.tool_id == tool_id, ToolPermission.role == role
        )
        result = await self.db.execute(stmt)
        permission = result.scalar_one_or_none()

        if not permission:
            return False

        await self.db.delete(permission)
        await self.db.commit()
        logger.info("Revoked permission for tool %s, role %s", tool_id, role)
        return True

    async def get_allowed_tools_for_role(
        self,
        role: str,
        enabled_only: bool = True,
    ) -> list[UUID]:
        """
        Get list of tool UUIDs that a role is allowed to use.

        Args:
            role: Role name
            enabled_only: Only return enabled tools (default: True)

        Returns:
            List of tool UUIDs where role has can_use=True permission

        Note:
            Admin role bypasses permissions and returns all tools.
        """
        # Admin role bypasses all permission checks
        if role == "admin":
            stmt = select(Tool.id)
            if enabled_only:
                stmt = stmt.where(Tool.is_enabled == True)  # noqa: E712
            result = await self.db.execute(stmt)
            tool_ids = list(result.scalars().all())
            logger.debug("Admin role: returning all tools (%d)", len(tool_ids))
            return tool_ids

        # For non-admin roles, filter by permission
        # Get tool IDs where role has can_use permission
        stmt = select(ToolPermission.tool_id).where(
            and_(
                ToolPermission.role == role,
                ToolPermission.can_use == True,  # noqa: E712
            )
        )
        result = await self.db.execute(stmt)
        allowed_tool_ids = list(result.scalars().all())

        if not allowed_tool_ids:
            logger.debug("Role %s: no allowed tools found", role)
            return []

        # Query tools with additional filters
        stmt = select(Tool.id).where(Tool.id.in_(allowed_tool_ids))

        if enabled_only:
            stmt = stmt.where(Tool.is_enabled == True)  # noqa: E712

        result = await self.db.execute(stmt)
        tool_ids = list(result.scalars().all())
        logger.debug("Role %s: returning %d allowed tools", role, len(tool_ids))
        return tool_ids

    async def get_allowed_tools_for_roles(
        self,
        roles: list[str],
        enabled_only: bool = True,
    ) -> list[UUID]:
        """
        Get list of tool UUIDs that any of the provided roles is allowed to use.

        This method supports multi-role users (ADR-060) by checking all roles.
        Returns the union of tools allowed for any of the roles.
        Admin role always bypasses permissions and returns all tools.

        Args:
            roles: List of role names to check
            enabled_only: Only return enabled tools (default: True)

        Returns:
            List of tool UUIDs where any role has can_use=True permission

        Note:
            If "admin" is in the roles list, returns all tools immediately (bypass).
        """
        # Admin role bypasses all permission checks
        if "admin" in roles:
            stmt = select(Tool.id)
            if enabled_only:
                stmt = stmt.where(Tool.is_enabled == True)  # noqa: E712
            result = await self.db.execute(stmt)
            tool_ids = list(result.scalars().all())
            logger.debug("Admin role in roles list: returning all tools (%d)", len(tool_ids))
            return tool_ids

        # Check if any role has the required permission
        if not roles:
            return []

        # Get tool IDs where any role has can_use permission
        stmt = select(ToolPermission.tool_id).where(
            and_(
                ToolPermission.role.in_(roles),
                ToolPermission.can_use == True,  # noqa: E712
            )
        )
        result = await self.db.execute(stmt)
        allowed_tool_ids = list(result.scalars().all())

        if not allowed_tool_ids:
            logger.debug("Roles %s: no allowed tools found", roles)
            return []

        # Query tools with additional filters
        stmt = select(Tool.id).where(Tool.id.in_(allowed_tool_ids))

        if enabled_only:
            stmt = stmt.where(Tool.is_enabled == True)  # noqa: E712

        result = await self.db.execute(stmt)
        tool_ids = list(result.scalars().all())
        logger.debug("Roles %s: returning %d allowed tools", roles, len(tool_ids))
        return tool_ids
