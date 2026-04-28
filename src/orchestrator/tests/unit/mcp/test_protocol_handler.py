"""
Unit tests for MCP protocol handler.
"""

import json

import pytest
from app.mcp.protocol_handler import (
    MCPProtocolHandler,
    MCPRequest,
    MCPResponse,
)


class TestMCPRequest:
    """Tests for MCP request messages."""

    def test_create_request(self):
        """Test creating a basic request."""
        request = MCPRequest.create(method="test/method", params={"key": "value"})
        assert request.jsonrpc == "2.0"
        assert request.method == "test/method"
        assert request.params == {"key": "value"}
        assert request.id is not None

    def test_create_request_with_id(self):
        """Test creating request with explicit ID."""
        request = MCPRequest.create(method="test", request_id="custom-id")
        assert request.id == "custom-id"

    def test_request_serialization(self):
        """Test serializing request to JSON."""
        request = MCPRequest.create(method="test", params={"foo": "bar"})
        json_str = request.to_json()
        data = json.loads(json_str)
        assert data["jsonrpc"] == "2.0"
        assert data["method"] == "test"
        assert data["params"] == {"foo": "bar"}

    def test_request_jsonrpc_validation(self):
        """Test that jsonrpc must be 2.0."""
        with pytest.raises(ValueError, match=r"jsonrpc must be '2\.0'"):
            MCPRequest(jsonrpc="1.0", method="test")


class TestMCPResponse:
    """Tests for MCP response messages."""

    def test_success_response(self):
        """Test creating success response."""
        response = MCPResponse.success({"result": "data"}, request_id="123")
        assert response.jsonrpc == "2.0"
        assert response.id == "123"
        assert response.result == {"result": "data"}
        assert response.error is None

    def test_error_response(self):
        """Test creating error response."""
        response = MCPResponse.error_response(
            code=-32603, message="Internal error", request_id="123"
        )
        assert response.jsonrpc == "2.0"
        assert response.id == "123"
        assert response.result is None
        assert response.error is not None
        assert response.error["code"] == -32603
        assert response.error["message"] == "Internal error"

    def test_error_response_with_data(self):
        """Test error response with additional data."""
        response = MCPResponse.error_response(
            code=-32602, message="Invalid params", data={"param": "value"}, request_id="456"
        )
        assert response.error["data"] == {"param": "value"}

    def test_response_serialization(self):
        """Test serializing response to JSON."""
        response = MCPResponse.success({"test": "data"})
        json_str = response.to_json()
        data = json.loads(json_str)
        assert data["jsonrpc"] == "2.0"
        assert data["result"] == {"test": "data"}

    def test_response_deserialization(self):
        """Test parsing response from JSON."""
        json_str = '{"jsonrpc": "2.0", "id": "123", "result": {"foo": "bar"}}'
        response = MCPResponse.from_json(json_str)
        assert response.jsonrpc == "2.0"
        assert response.id == "123"
        assert response.result == {"foo": "bar"}

    def test_error_validation(self):
        """Test error format validation."""
        with pytest.raises(ValueError, match="Error must have"):
            MCPResponse(jsonrpc="2.0", error={"code": 123})  # Missing message


class TestMCPProtocolHandler:
    """Tests for MCP protocol handler."""

    def test_create_initialize_request(self):
        """Test creating initialize request."""
        handler = MCPProtocolHandler()
        request = handler.create_initialize_request()
        assert request.method == "initialize"
        assert "protocolVersion" in request.params
        assert "capabilities" in request.params

    def test_create_initialize_request_with_info(self):
        """Test initialize request with client info."""
        handler = MCPProtocolHandler()
        request = handler.create_initialize_request(
            client_info={"name": "test-client", "version": "1.0"}
        )
        assert request.params["clientInfo"]["name"] == "test-client"

    def test_create_tools_list_request(self):
        """Test creating tools/list request."""
        handler = MCPProtocolHandler()
        request = handler.create_tools_list_request()
        assert request.method == "tools/list"
        assert request.params == {}

    def test_create_tool_call_request(self):
        """Test creating tools/call request."""
        handler = MCPProtocolHandler()
        request = handler.create_tool_call_request("test_tool", {"arg": "value"})
        assert request.method == "tools/call"
        assert request.params["name"] == "test_tool"
        assert request.params["arguments"] == {"arg": "value"}

    def test_parse_response(self):
        """Test parsing valid response."""
        handler = MCPProtocolHandler()
        json_str = '{"jsonrpc": "2.0", "id": "123", "result": {"data": "test"}}'
        response = handler.parse_response(json_str)
        assert response.id == "123"
        assert response.result == {"data": "test"}

    def test_parse_invalid_response(self):
        """Test parsing invalid JSON raises error."""
        handler = MCPProtocolHandler()
        with pytest.raises(ValueError, match="Invalid MCP response"):
            handler.parse_response("not json")

    def test_validate_response_success(self):
        """Test validating successful response."""
        handler = MCPProtocolHandler()
        response = MCPResponse.success({"data": "test"}, request_id="123")
        assert handler.validate_response(response, expected_id="123") is True

    def test_validate_response_id_mismatch(self):
        """Test validation fails on ID mismatch."""
        handler = MCPProtocolHandler()
        response = MCPResponse.success({"data": "test"}, request_id="123")
        assert handler.validate_response(response, expected_id="456") is False

    def test_validate_response_error(self):
        """Test validation fails on error response."""
        handler = MCPProtocolHandler()
        response = MCPResponse.error_response(code=-1, message="Error", request_id="123")
        assert handler.validate_response(response, expected_id="123") is False
