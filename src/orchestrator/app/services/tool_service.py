"""
Tool management service.

Provides CRUD operations for platform-level tool configuration.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging, mask_identifier

from ..db.models import Tool
from ..schemas.tool import (
    DataFlowDirection,
    DataSourceType,
    MaxDataSensitivity,
    NetworkAccessLevel,
    ToolCategory,
    ToolCreate,
    ToolListItem,
    ToolUpdate,
)
from .secrets_manager import SecretsManager

logger = configure_logging(service_name="tool_service")


class ToolService:
    """Service for managing platform tools."""

    def __init__(self, db: AsyncSession):
        """Initialize tool service."""
        self.db = db
        self.secrets_manager = SecretsManager(db)

    async def create_tool(
        self,
        tool_data: ToolCreate,
        created_by_user_id: UUID,
    ) -> Tool:
        """
        Create a new tool configuration.

        Args:
            tool_data: Tool configuration data
            created_by_user_id: User creating the tool

        Returns:
            Created Tool record

        Raises:
            ValueError: If tool_id already exists
        """
        # Check for duplicate tool_id
        stmt = select(Tool).where(Tool.tool_id == tool_data.tool_id)
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            raise ValueError(f"Tool with ID '{tool_data.tool_id}' already exists")

        # Convert mcp_command list to JSON string if needed
        mcp_command_str = None
        if tool_data.mcp_command:
            import json

            mcp_command_str = json.dumps(tool_data.mcp_command)

        tool = Tool(
            tool_id=tool_data.tool_id,
            name=tool_data.name,
            description=tool_data.description,
            category=tool_data.category.value,
            provider=tool_data.provider,
            # DEPRECATED: Legacy fields (ADR-001) - kept for backward compatibility
            tool_purpose=tool_data.tool_purpose.value,
            service_location=tool_data.service_location.value,
            # NEW: Security Classification (ADR-057)
            data_source_type=tool_data.data_source_type.value,
            data_flow_direction=tool_data.data_flow_direction.value,
            network_access_level=tool_data.network_access_level.value,
            max_data_sensitivity=tool_data.max_data_sensitivity.value,
            # MCP Configuration
            mcp_server_type=tool_data.mcp_server_type.value,
            mcp_command=mcp_command_str,
            mcp_endpoint=tool_data.mcp_endpoint,
            mcp_protocol_version=tool_data.mcp_protocol_version,
            capabilities=tool_data.capabilities,
            parameters_schema=tool_data.parameters_schema,
            requires_authentication=tool_data.requires_authentication,
            authentication_type=tool_data.authentication_type,
            secret_name=tool_data.secret_name,
            config_options=tool_data.config_options,
            timeout_seconds=tool_data.timeout_seconds,
            rate_limit_per_minute=tool_data.rate_limit_per_minute,
            max_concurrent_calls=tool_data.max_concurrent_calls,
            is_enabled=tool_data.is_enabled,
            health_check_interval_seconds=tool_data.health_check_interval_seconds,
            version=tool_data.version,
            documentation_url=tool_data.documentation_url,
            tags=tool_data.tags,
            created_by=created_by_user_id,
            updated_by=created_by_user_id,
        )

        self.db.add(tool)
        await self.db.commit()
        await self.db.refresh(tool)

        logger.info(
            f"Created tool: {tool.tool_id} (UUID: {tool.id})",
            extra={"tool_id": tool.tool_id, "tool_uuid": str(tool.id)},
        )

        return tool

    async def get_tool(self, tool_id: str) -> Tool | None:
        """Get tool by tool_id."""
        stmt = select(Tool).where(Tool.tool_id == tool_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tool_by_uuid(self, uuid: UUID) -> Tool | None:
        """Get tool by UUID."""
        stmt = select(Tool).where(Tool.id == uuid)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_tools(
        self,
        category: ToolCategory | None = None,
        enabled_only: bool = False,
        healthy_only: bool = False,
    ) -> list[ToolListItem]:
        """
        List tools with optional filters.

        Args:
            category: Filter by category
            enabled_only: Only return enabled tools
            healthy_only: Only return healthy tools

        Returns:
            List of ToolListItem
        """
        stmt = select(Tool)

        if category:
            # Handle both enum and string category values
            category_value = category.value if hasattr(category, "value") else category
            stmt = stmt.where(Tool.category == category_value)

        if enabled_only:
            stmt = stmt.where(Tool.is_enabled == True)  # noqa: E712

        if healthy_only:
            stmt = stmt.where(Tool.is_healthy == True)  # noqa: E712

        result = await self.db.execute(stmt)
        tools = result.scalars().all()

        # Convert to ToolListItem, validating enum values
        # If invalid enum values are found, this indicates a data integrity issue
        # (database constraints should prevent this, so this is a serious problem)
        tool_list_items = []
        for t in tools:
            try:
                tool_item = ToolListItem(
                    id=t.id,
                    tool_id=t.tool_id,
                    name=t.name,
                    description=t.description,
                    category=ToolCategory(t.category),
                    is_enabled=t.is_enabled,
                    is_healthy=t.is_healthy,
                    requires_authentication=t.requires_authentication,
                    # Security classification (ADR-057)
                    data_source_type=DataSourceType(t.data_source_type),
                    data_flow_direction=DataFlowDirection(t.data_flow_direction),
                    network_access_level=NetworkAccessLevel(t.network_access_level),
                    max_data_sensitivity=MaxDataSensitivity(t.max_data_sensitivity),
                )
                tool_list_items.append(tool_item)
            except (ValueError, KeyError) as e:
                # Invalid enum value indicates data integrity issue
                # Database CHECK constraints should prevent this
                logger.error(
                    "Data integrity error: Tool has invalid enum value",
                    exc_info=True,
                    extra={
                        "tool_id": t.tool_id,
                        "tool_uuid": str(t.id),
                        "tool_name": t.name,
                        "invalid_field": str(e),
                        "category_value": t.category,
                        "data_source_type": t.data_source_type,
                        "data_flow_direction": t.data_flow_direction,
                        "network_access_level": t.network_access_level,
                        "max_data_sensitivity": t.max_data_sensitivity,
                    },
                )
                # Re-raise with more context - this is a critical data integrity issue
                raise ValueError(
                    f"Tool '{t.tool_id}' (UUID: {t.id}) has invalid enum value(s). "
                    f"This indicates a data integrity problem. "
                    f"Database CHECK constraints should prevent this. "
                    f"Error: {e}. "
                    f"Please check database constraints and tool data."
                ) from e

        return tool_list_items

    async def update_tool(
        self,
        tool_id: str,
        update_data: ToolUpdate,
        updated_by_user_id: UUID,
    ) -> Tool:
        """
        Update tool configuration.

        Args:
            tool_id: Tool identifier
            update_data: Fields to update
            updated_by_user_id: User updating the tool

        Returns:
            Updated Tool record

        Raises:
            ValueError: If tool not found
        """
        tool = await self.get_tool(tool_id)
        if not tool:
            raise ValueError(f"Tool '{tool_id}' not found")

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            # Handle mcp_command conversion if present (though ToolUpdate doesn't include it)
            if field == "mcp_command" and isinstance(value, list):
                import json

                setattr(tool, field, json.dumps(value))
            else:
                setattr(tool, field, value)

        tool.updated_by = updated_by_user_id
        tool.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(tool)

        logger.info(
            f"Updated tool: {tool_id}",
            extra={"tool_id": tool_id, "updated_fields": list(update_dict.keys())},
        )

        return tool

    async def delete_tool(self, tool_id: str) -> bool:
        """
        Delete a tool configuration.

        Args:
            tool_id: Tool identifier

        Returns:
            True if deleted
        """
        tool = await self.get_tool(tool_id)
        if not tool:
            return False

        # Delete associated secrets
        if tool.secret_name:
            try:
                await self.secrets_manager.delete_secret(tool.secret_name)
            except Exception as e:
                logger.warning(
                    "Failed to delete secret for tool",
                    extra={
                        "tool_id": tool_id,
                        "secret_ref": mask_identifier(tool.secret_name),
                        "error": str(e),
                    },
                )

        await self.db.delete(tool)
        await self.db.commit()

        logger.info(
            f"Deleted tool: {tool_id}",
            extra={"tool_id": tool_id},
        )

        return True

    async def enable_tool(self, tool_id: str) -> Tool:
        """
        Enable a tool.

        Args:
            tool_id: Tool identifier

        Returns:
            Updated Tool record

        Raises:
            ValueError: If tool not found
        """
        tool = await self.get_tool(tool_id)
        if not tool:
            raise ValueError(f"Tool '{tool_id}' not found")

        tool.is_enabled = True
        tool.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(tool)

        logger.info(
            f"Enabled tool: {tool_id}",
            extra={"tool_id": tool_id},
        )

        return tool

    async def disable_tool(self, tool_id: str) -> Tool:
        """
        Disable a tool.

        Args:
            tool_id: Tool identifier

        Returns:
            Updated Tool record

        Raises:
            ValueError: If tool not found
        """
        tool = await self.get_tool(tool_id)
        if not tool:
            raise ValueError(f"Tool '{tool_id}' not found")

        tool.is_enabled = False
        tool.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(tool)

        logger.info(
            f"Disabled tool: {tool_id}",
            extra={"tool_id": tool_id},
        )

        return tool
