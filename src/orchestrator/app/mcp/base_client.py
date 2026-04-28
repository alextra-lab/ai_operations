"""
Base MCP client interface.

Defines the abstract interface for MCP clients implementing different
transport mechanisms (HTTP, SSE, STDIO).
"""

from abc import ABC, abstractmethod
from typing import Any, cast

from shared.logging_utils.fastapi import configure_logging

from .protocol_handler import MCPProtocolHandler, MCPRequest, MCPResponse

logger = configure_logging(service_name="mcp_base_client")


class MCPClient(ABC):
    """
    Abstract base class for MCP clients.

    All MCP client implementations must inherit from this class
    and implement the required methods.
    """

    def __init__(self, protocol_version: str = "2024-11-05"):
        """
        Initialize MCP client.

        Args:
            protocol_version: MCP protocol version
        """
        self.protocol_version = protocol_version
        self.protocol_handler = MCPProtocolHandler()
        self._initialized = False
        self._server_capabilities: dict[str, Any] | None = None

    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to MCP server.

        Raises:
            ConnectionError: If connection fails
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to MCP server."""

    @abstractmethod
    async def send_request(self, request: MCPRequest) -> MCPResponse:
        """
        Send a request to the MCP server and wait for response.

        Args:
            request: MCP request message

        Returns:
            MCP response message

        Raises:
            ConnectionError: If connection is not established
            TimeoutError: If request times out
            ValueError: If response is invalid
        """

    async def initialize(self) -> dict[str, Any]:
        """
        Initialize MCP session with server.

        Performs the initialize handshake and stores server capabilities.

        Returns:
            Server capabilities and information

        Raises:
            ConnectionError: If connection fails
            ValueError: If initialization fails
        """
        if self._initialized:
            logger.warning("MCP client already initialized")
            if self._server_capabilities:
                return self._server_capabilities
            return {}

        # Create initialize request
        request = self.protocol_handler.create_initialize_request(
            protocol_version=self.protocol_version,
            capabilities=self._get_client_capabilities(),
            client_info=self._get_client_info(),
        )

        # Send initialize request
        response = await self.send_request(request)

        if response.error:
            error_msg = response.error.get("message", "Unknown error")
            raise ValueError(f"MCP initialization failed: {error_msg}")

        if not response.result:
            raise ValueError("MCP initialization returned no result")

        # Store server capabilities
        if not isinstance(response.result, dict):
            raise ValueError("MCP initialization result must be a dictionary")
        self._server_capabilities = response.result
        self._initialized = True

        logger.info("MCP client initialized successfully")
        return self._server_capabilities

    async def list_tools(self) -> list[dict[str, Any]]:
        """
        List available tools from MCP server.

        Returns:
            List of tool definitions

        Raises:
            RuntimeError: If client is not initialized
            ConnectionError: If connection fails
        """
        if not self._initialized:
            raise RuntimeError("MCP client must be initialized before listing tools")

        request = self.protocol_handler.create_tools_list_request()
        response = await self.send_request(request)

        if response.error:
            error_msg = response.error.get("message", "Unknown error")
            raise ValueError(f"Failed to list tools: {error_msg}")

        # MCP tools/list returns { "tools": [...] }
        if isinstance(response.result, dict) and "tools" in response.result:
            return cast("list[dict[str, Any]]", response.result["tools"])
        if isinstance(response.result, list):
            return cast("list[dict[str, Any]]", response.result)
        logger.warning(f"Unexpected tools/list response format: {response.result}")
        return []

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            RuntimeError: If client is not initialized
            ConnectionError: If connection fails
            ValueError: If tool call fails
        """
        if not self._initialized:
            raise RuntimeError("MCP client must be initialized before calling tools")

        request = self.protocol_handler.create_tool_call_request(tool_name, arguments)
        response = await self.send_request(request)

        if response.error:
            error_code = response.error.get("code", -1)
            error_msg = response.error.get("message", "Unknown error")
            error_data = response.error.get("data")

            logger.error(
                f"Tool call failed: {tool_name} (code: {error_code}, message: {error_msg})"
            )

            # Format error for caller
            error_info = f"{error_msg}"
            if error_data:
                error_info += f" (data: {error_data})"

            raise ValueError(f"Tool call failed: {error_info}")

        return response.result

    def _get_client_capabilities(self) -> dict[str, Any]:
        """
        Get client capabilities for initialize handshake.

        Returns:
            Client capabilities dictionary
        """
        return {
            "tools": {},  # Client supports tools
        }

    def _get_client_info(self) -> dict[str, Any]:
        """
        Get client information for initialize handshake.

        Returns:
            Client info dictionary
        """
        return {
            "name": "aio-orchestrator",
            "version": "1.0.0",
        }

    @property
    def is_initialized(self) -> bool:
        """Check if client is initialized."""
        return self._initialized

    @property
    def server_capabilities(self) -> dict[str, Any] | None:
        """Get server capabilities (available after initialization)."""
        return self._server_capabilities
