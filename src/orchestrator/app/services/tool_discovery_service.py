"""
Tool discovery service for MCP integration.

Automatically discovers tool capabilities from MCP servers and updates
tool configurations in the database.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging

from ..db.models import Tool
from ..mcp import HTTPMCPClient, MCPClient, StdioMCPClient
from ..schemas.tool import MCPServerType

logger = configure_logging(service_name="tool_discovery_service")


class ToolDiscoveryService:
    """Service for discovering tool capabilities from MCP servers."""

    def __init__(self, db: AsyncSession):
        """
        Initialize tool discovery service.

        Args:
            db: Database session
        """
        self.db = db

    def create_mcp_client(self, tool: Tool, headers: dict[str, str] | None = None) -> MCPClient:
        """
        Create appropriate MCP client for a tool configuration.

        Args:
            tool: Tool database record
            headers: Optional HTTP headers (for authentication)

        Returns:
            MCP client instance (not connected)

        Raises:
            ValueError: If tool configuration is invalid
        """
        if tool.mcp_server_type == MCPServerType.HTTP:
            if not tool.mcp_endpoint:
                raise ValueError(f"HTTP tool {tool.tool_id} missing endpoint")
            return HTTPMCPClient(
                endpoint=tool.mcp_endpoint,
                protocol_version=tool.mcp_protocol_version,
                timeout_seconds=tool.timeout_seconds,
                headers=headers,
            )

        if tool.mcp_server_type == MCPServerType.SSE:
            if not tool.mcp_endpoint:
                raise ValueError(f"SSE tool {tool.tool_id} missing endpoint")
            # SSE uses same HTTP client (SSE is just a transport mechanism)
            return HTTPMCPClient(
                endpoint=tool.mcp_endpoint,
                protocol_version=tool.mcp_protocol_version,
                timeout_seconds=tool.timeout_seconds,
                headers=headers,
            )

        if tool.mcp_server_type == MCPServerType.STDIO:
            if not tool.mcp_command:
                raise ValueError(f"STDIO tool {tool.tool_id} missing command")
            # Parse command string to list
            if isinstance(tool.mcp_command, str):
                import json

                try:
                    command_list = json.loads(tool.mcp_command)
                except json.JSONDecodeError:
                    # Fallback: split by space (simple case)
                    command_list = tool.mcp_command.split()
            else:
                command_list = tool.mcp_command

            return StdioMCPClient(
                command=command_list,
                protocol_version=tool.mcp_protocol_version,
                timeout_seconds=tool.timeout_seconds,
            )

        raise ValueError(f"Unsupported MCP server type: {tool.mcp_server_type}")

    async def discover_tool_capabilities(self, tool_id: UUID) -> dict[str, Any]:
        """
        Discover tool capabilities from MCP server.

        Connects to MCP server, initializes session, and retrieves available tools.

        Args:
            tool_id: Tool UUID

        Returns:
            Discovered capabilities dictionary

        Raises:
            ValueError: If tool not found or discovery fails
            ConnectionError: If connection to MCP server fails
        """
        stmt = select(Tool).where(Tool.id == tool_id)
        result = await self.db.execute(stmt)
        tool = result.scalar_one_or_none()
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")

        logger.info(f"Discovering capabilities for tool: {tool.tool_id}")

        # Create MCP client
        client = self.create_mcp_client(tool)

        try:
            # Connect and initialize
            await client.connect()
            server_capabilities = await client.initialize()

            # List available tools
            tools_list = await client.list_tools()

            # Build capabilities dictionary
            capabilities: dict[str, Any] = {
                "server_capabilities": server_capabilities,
                "tools": tools_list,
                "protocol_version": tool.mcp_protocol_version,
            }

            logger.info(f"Discovered {len(tools_list)} tools from {tool.tool_id}")

            return capabilities

        except Exception as e:
            logger.error(f"Tool discovery failed for {tool.tool_id}: {e}")
            raise ValueError(f"Tool discovery failed: {e}") from e

        finally:
            await client.disconnect()

    async def update_tool_from_discovery(self, tool_id: UUID) -> Tool:
        """
        Discover capabilities and update tool record in database.

        Args:
            tool_id: Tool UUID

        Returns:
            Updated tool record

        Raises:
            ValueError: If tool not found or discovery fails
        """
        stmt = select(Tool).where(Tool.id == tool_id)
        result = await self.db.execute(stmt)
        tool = result.scalar_one_or_none()
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")

        # Discover capabilities
        capabilities = await self.discover_tool_capabilities(tool_id)

        # Update tool record
        tool.capabilities = capabilities.get("server_capabilities", {})
        tool.updated_at = tool.updated_at  # Trigger update timestamp

        # If tools were discovered, update parameters_schema from first tool
        tools_list = capabilities.get("tools", [])
        if tools_list and len(tools_list) > 0:
            # Use first tool's input schema as example
            first_tool = tools_list[0]
            if "inputSchema" in first_tool:
                tool.parameters_schema = first_tool["inputSchema"]

        await self.db.commit()
        await self.db.refresh(tool)

        logger.info(f"Updated tool {tool.tool_id} from discovery")

        return tool
