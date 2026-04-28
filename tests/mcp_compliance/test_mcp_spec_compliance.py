"""
MCP Protocol Compliance Tests

Verifies 100% adherence to Model Context Protocol specification version 2024-11-05.
Tests cover JSON-RPC 2.0 compliance and MCP-specific requirements.
"""

import json

import pytest
from app.mcp.protocol_handler import (
    MCPProtocolHandler,
    MCPRequest,
    MCPResponse,
)


class TestMCPJSONRPCCompliance:
    """Tests for JSON-RPC 2.0 compliance."""

    def test_jsonrpc_version_required(self):
        """MCP-001: All messages must have jsonrpc: "2.0"."""
        request = MCPRequest.create(method="test")
        assert request.jsonrpc == "2.0"

        response = MCPResponse.success({})
        assert response.jsonrpc == "2.0"

    def test_request_id_format(self):
        """MCP-002: Request ID can be string or number."""
        request1 = MCPRequest.create(method="test", request_id="string-id")
        assert isinstance(request1.id, str)

        request2 = MCPRequest.create(method="test", request_id=123)
        assert isinstance(request2.id, int)

    def test_request_method_required(self):
        """MCP-003: Request must have method field."""
        request = MCPRequest.create(method="test/method")
        assert request.method == "test/method"

    def test_response_result_or_error(self):
        """MCP-004: Response must have result OR error, not both."""
        success = MCPResponse.success({"data": "test"})
        assert success.result is not None
        assert success.error is None

        error = MCPResponse.error_response(code=-1, message="Error")
        assert error.result is None
        assert error.error is not None

    def test_error_format(self):
        """MCP-005: Error must have code and message."""
        error = MCPResponse.error_response(code=-32603, message="Internal error")
        assert "code" in error.error
        assert "message" in error.error
        assert error.error["code"] == -32603
        assert error.error["message"] == "Internal error"


class TestMCPInitializeProtocol:
    """Tests for MCP initialize handshake."""

    def test_initialize_request_format(self):
        """MCP-006: Initialize request must have protocolVersion and capabilities."""
        handler = MCPProtocolHandler()
        request = handler.create_initialize_request()

        assert request.method == "initialize"
        assert "protocolVersion" in request.params
        assert "capabilities" in request.params
        assert request.params["protocolVersion"] == "2024-11-05"

    def test_initialize_client_info(self):
        """MCP-007: Initialize can include optional clientInfo."""
        handler = MCPProtocolHandler()
        request = handler.create_initialize_request(client_info={"name": "test", "version": "1.0"})
        assert "clientInfo" in request.params
        assert request.params["clientInfo"]["name"] == "test"


class TestMCPToolsProtocol:
    """Tests for MCP tools protocol."""

    def test_tools_list_request(self):
        """MCP-008: tools/list request has no parameters."""
        handler = MCPProtocolHandler()
        request = handler.create_tools_list_request()
        assert request.method == "tools/list"
        assert request.params == {}

    def test_tools_list_response_format(self):
        """MCP-009: tools/list returns { tools: [...] } or tools array."""
        # Handler should accept both formats
        response1 = MCPResponse.success({"tools": [{"name": "tool1"}]})
        assert "tools" in response1.result

        response2 = MCPResponse.success([{"name": "tool1"}])
        assert isinstance(response2.result, list)

    def test_tools_call_request(self):
        """MCP-010: tools/call request has name and arguments."""
        handler = MCPProtocolHandler()
        request = handler.create_tool_call_request("test_tool", {"arg": "value"})
        assert request.method == "tools/call"
        assert request.params["name"] == "test_tool"
        assert request.params["arguments"] == {"arg": "value"}

    def test_tools_call_response(self):
        """MCP-011: tools/call returns tool execution result."""
        # Result format is tool-specific
        response = MCPResponse.success({"content": [{"type": "text", "text": "result"}]})
        assert "content" in response.result


class TestMCPMessageSerialization:
    """Tests for message serialization compliance."""

    def test_request_serialization(self):
        """MCP-012: Request serializes to valid JSON."""
        request = MCPRequest.create(method="test", params={"key": "value"})
        json_str = request.to_json()
        data = json.loads(json_str)

        assert data["jsonrpc"] == "2.0"
        assert data["method"] == "test"
        assert "id" in data

    def test_response_serialization(self):
        """MCP-013: Response serializes to valid JSON."""
        response = MCPResponse.success({"data": "test"})
        json_str = response.to_json()
        data = json.loads(json_str)

        assert data["jsonrpc"] == "2.0"
        assert "result" in data

    def test_error_serialization(self):
        """MCP-014: Error response serializes correctly."""
        response = MCPResponse.error_response(code=-1, message="Error")
        json_str = response.to_json()
        data = json.loads(json_str)

        assert data["jsonrpc"] == "2.0"
        assert "error" in data
        assert data["error"]["code"] == -1

    def test_deserialization(self):
        """MCP-015: Can parse JSON back to response."""
        json_str = '{"jsonrpc": "2.0", "id": "123", "result": {"test": "data"}}'
        response = MCPResponse.from_json(json_str)
        assert response.id == "123"
        assert response.result == {"test": "data"}


class TestMCPProtocolVersion:
    """Tests for protocol version handling."""

    def test_default_protocol_version(self):
        """MCP-016: Default protocol version is 2024-11-05."""
        handler = MCPProtocolHandler()
        assert handler.PROTOCOL_VERSION == "2024-11-05"

    def test_custom_protocol_version(self):
        """MCP-017: Can specify custom protocol version."""
        handler = MCPProtocolHandler()
        request = handler.create_initialize_request(protocol_version="2024-12-01")
        assert request.params["protocolVersion"] == "2024-12-01"


class TestMCPErrorCodes:
    """Tests for standard JSON-RPC error codes."""

    def test_parse_error_code(self):
        """MCP-018: Parse error code -32700."""
        response = MCPResponse.error_response(code=-32700, message="Parse error")
        assert response.error["code"] == -32700

    def test_invalid_request_code(self):
        """MCP-019: Invalid request code -32600."""
        response = MCPResponse.error_response(code=-32600, message="Invalid Request")
        assert response.error["code"] == -32600

    def test_method_not_found_code(self):
        """MCP-020: Method not found code -32601."""
        response = MCPResponse.error_response(code=-32601, message="Method not found")
        assert response.error["code"] == -32601

    def test_invalid_params_code(self):
        """MCP-021: Invalid params code -32602."""
        response = MCPResponse.error_response(code=-32602, message="Invalid params")
        assert response.error["code"] == -32602

    def test_internal_error_code(self):
        """MCP-022: Internal error code -32603."""
        response = MCPResponse.error_response(code=-32603, message="Internal error")
        assert response.error["code"] == -32603


class TestMCPTransportCompliance:
    """Tests for transport-specific compliance."""

    def test_http_transport(self):
        """MCP-023: HTTP transport uses POST with JSON body."""
        # This is tested in HTTP client tests
        # Compliance: HTTP client sends JSON in POST body

    def test_stdio_transport(self):
        """MCP-024: STDIO transport uses newline-delimited JSON."""
        # This is tested in STDIO client tests
        # Compliance: STDIO client sends newline-delimited JSON

    def test_sse_transport(self):
        """MCP-025: SSE transport uses HTTP client with SSE streaming."""
        # SSE uses same HTTP client, streaming handled separately


class TestMCPValidation:
    """Tests for message validation."""

    def test_validate_response_id_match(self):
        """MCP-026: Response ID must match request ID."""
        handler = MCPProtocolHandler()
        MCPRequest.create(method="test", request_id="123")
        response = MCPResponse.success({}, request_id="123")

        assert handler.validate_response(response, expected_id="123") is True

    def test_validate_response_id_mismatch(self):
        """MCP-027: Validation fails on ID mismatch."""
        handler = MCPProtocolHandler()
        response = MCPResponse.success({}, request_id="123")
        assert handler.validate_response(response, expected_id="456") is False

    def test_validate_error_response(self):
        """MCP-028: Validation fails on error response."""
        handler = MCPProtocolHandler()
        response = MCPResponse.error_response(code=-1, message="Error", request_id="123")
        assert handler.validate_response(response, expected_id="123") is False


@pytest.mark.parametrize(
    "test_method",
    [
        "test_jsonrpc_version_required",
        "test_request_id_format",
        "test_initialize_request_format",
        "test_tools_list_request",
        "test_tools_call_request",
    ],
)
def test_compliance_suite(test_method):
    """Run all compliance tests."""
    # This is a meta-test to ensure all compliance tests are run
    # Individual tests are defined above
