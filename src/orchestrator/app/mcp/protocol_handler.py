"""
MCP Protocol Handler for JSON-RPC 2.0 message serialization and validation.

Implements Model Context Protocol (MCP) specification version 2024-11-05.
MCP is based on JSON-RPC 2.0 with specific method names and message formats.
"""

import json
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from shared.logging_utils.fastapi import configure_logging

logger = configure_logging(service_name="mcp_protocol_handler")


class MCPMessage(BaseModel):
    """Base MCP message (JSON-RPC 2.0 format)."""

    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    id: str | int | None = Field(default=None, description="Request ID")

    @field_validator("jsonrpc")
    @classmethod
    def validate_jsonrpc(cls, v: str) -> str:
        """Validate JSON-RPC version."""
        if v != "2.0":
            raise ValueError("jsonrpc must be '2.0'")
        return v


class MCPRequest(MCPMessage):
    """MCP request message."""

    method: str = Field(..., description="MCP method name")
    params: dict[str, Any] | None = Field(default=None, description="Method parameters")

    def to_json(self) -> str:
        """Serialize request to JSON string."""
        return json.dumps(self.model_dump(exclude_none=True), ensure_ascii=False)

    @classmethod
    def create(
        cls,
        method: str,
        params: dict[str, Any] | None = None,
        request_id: str | int | None = None,
    ) -> "MCPRequest":
        """Create a new MCP request."""
        return cls(
            jsonrpc="2.0",
            id=request_id or str(uuid4()),
            method=method,
            params=params or {},
        )


class MCPResponse(MCPMessage):
    """MCP response message."""

    result: Any | None = Field(default=None, description="Method result")
    error: dict[str, Any] | None = Field(default=None, description="Error information")

    @field_validator("error")
    @classmethod
    def validate_error(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        """Validate error format (must have code and message)."""
        if v is not None and ("code" not in v or "message" not in v):
            raise ValueError("Error must have 'code' and 'message' fields")
        return v

    def to_json(self) -> str:
        """Serialize response to JSON string."""
        return json.dumps(self.model_dump(exclude_none=True), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "MCPResponse":
        """Parse response from JSON string."""
        data = json.loads(json_str)
        return cls(**data)

    @classmethod
    def success(cls, result: Any, request_id: str | int | None = None) -> "MCPResponse":
        """Create a successful response."""
        return cls(jsonrpc="2.0", id=request_id, result=result)

    @classmethod
    def error_response(
        cls,
        code: int,
        message: str,
        data: Any | None = None,
        request_id: str | int | None = None,
    ) -> "MCPResponse":
        """Create an error response."""
        error_dict: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            error_dict["data"] = data
        return cls(jsonrpc="2.0", id=request_id, error=error_dict)


class MCPProtocolHandler:
    """
    Handler for MCP protocol messages.

    Provides methods for creating standard MCP requests and parsing responses.
    Implements MCP specification version 2024-11-05.
    """

    PROTOCOL_VERSION = "2024-11-05"

    @staticmethod
    def create_initialize_request(
        protocol_version: str = PROTOCOL_VERSION,
        capabilities: dict[str, Any] | None = None,
        client_info: dict[str, Any] | None = None,
    ) -> MCPRequest:
        """
        Create an initialize request.

        Args:
            protocol_version: MCP protocol version
            capabilities: Client capabilities
            client_info: Client information (name, version)

        Returns:
            Initialize request message
        """
        params: dict[str, Any] = {
            "protocolVersion": protocol_version,
            "capabilities": capabilities or {},
        }
        if client_info:
            params["clientInfo"] = client_info

        return MCPRequest.create(method="initialize", params=params)

    @staticmethod
    def create_tools_list_request() -> MCPRequest:
        """Create a tools/list request to discover available tools."""
        return MCPRequest.create(method="tools/list", params={})

    @staticmethod
    def create_tool_call_request(tool_name: str, arguments: dict[str, Any]) -> MCPRequest:
        """
        Create a tools/call request.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool call request message
        """
        return MCPRequest.create(
            method="tools/call",
            params={"name": tool_name, "arguments": arguments},
        )

    @staticmethod
    def parse_response(json_str: str) -> MCPResponse:
        """
        Parse a JSON-RPC response.

        Args:
            json_str: JSON string response

        Returns:
            Parsed MCP response

        Raises:
            ValueError: If response is invalid
        """
        try:
            return MCPResponse.from_json(json_str)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse MCP response: {e}")
            raise ValueError(f"Invalid MCP response: {e}") from e

    @staticmethod
    def validate_response(response: MCPResponse, expected_id: str | int | None = None) -> bool:
        """
        Validate that a response matches the expected request.

        Args:
            response: MCP response
            expected_id: Expected request ID

        Returns:
            True if valid, False otherwise
        """
        if expected_id is not None and response.id != expected_id:
            logger.warning(f"Response ID mismatch: expected {expected_id}, got {response.id}")
            return False

        if response.error is not None:
            logger.warning(f"MCP error response: {response.error}")
            return False

        return True
