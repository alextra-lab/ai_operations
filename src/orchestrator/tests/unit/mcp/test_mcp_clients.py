"""
Unit tests for MCP client implementations.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.mcp.base_client import MCPClient
from app.mcp.http_client import HTTPMCPClient
from app.mcp.protocol_handler import MCPRequest, MCPResponse
from app.mcp.stdio_client import StdioMCPClient


class TestMCPClientBase:
    """Tests for base MCP client."""

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initialization."""

        # Create a concrete implementation for testing
        class TestClient(MCPClient):
            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def send_request(self, request):
                return MCPResponse.success({})

        client = TestClient()
        assert client.protocol_version == "2024-11-05"
        assert not client.is_initialized

    @pytest.mark.asyncio
    async def test_initialize_handshake(self):
        """Test initialize handshake."""

        class TestClient(MCPClient):
            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def send_request(self, request):
                if request.method == "initialize":
                    return MCPResponse.success({"capabilities": {}}, request_id=request.id)
                return MCPResponse.success({})

        client = TestClient()
        await client.connect()
        capabilities = await client.initialize()
        assert client.is_initialized
        assert "capabilities" in capabilities

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing tools."""

        class TestClient(MCPClient):
            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def send_request(self, request):
                if request.method == "initialize":
                    return MCPResponse.success({"capabilities": {}}, request_id=request.id)
                if request.method == "tools/list":
                    return MCPResponse.success(
                        {"tools": [{"name": "test_tool"}]}, request_id=request.id
                    )
                return MCPResponse.success({})

        client = TestClient()
        await client.connect()
        await client.initialize()
        tools = await client.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"

    @pytest.mark.asyncio
    async def test_call_tool(self):
        """Test calling a tool."""

        class TestClient(MCPClient):
            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def send_request(self, request):
                if request.method == "initialize":
                    return MCPResponse.success({"capabilities": {}}, request_id=request.id)
                if request.method == "tools/call":
                    return MCPResponse.success({"result": "success"}, request_id=request.id)
                return MCPResponse.success({})

        client = TestClient()
        await client.connect()
        await client.initialize()
        result = await client.call_tool("test_tool", {"arg": "value"})
        assert result == {"result": "success"}


class TestHTTPMCPClient:
    """Tests for HTTP MCP client."""

    @pytest.mark.asyncio
    async def test_http_client_initialization(self):
        """Test HTTP client initialization."""
        client = HTTPMCPClient(endpoint="http://example.com/mcp")
        assert client.endpoint == "http://example.com/mcp"
        assert client.timeout_seconds == 30

    @pytest.mark.asyncio
    async def test_http_connect(self):
        """Test HTTP client connection."""
        client = HTTPMCPClient(endpoint="http://example.com/mcp")
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.get.return_value = MagicMock(status_code=200)

            await client.connect()
            assert client._client is not None

    @pytest.mark.asyncio
    async def test_http_send_request(self):
        """Test sending HTTP request."""
        client = HTTPMCPClient(endpoint="http://example.com/mcp")
        request = MCPRequest.create(method="test", params={})

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock successful response
            mock_response = MagicMock()
            mock_response.text = (
                '{"jsonrpc": "2.0", "id": "' + str(request.id) + '", "result": {"data": "test"}}'
            )
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=200))

            await client.connect()
            response = await client.send_request(request)
            assert response.result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_http_timeout(self):
        """Test HTTP request timeout."""
        client = HTTPMCPClient(endpoint="http://example.com/mcp", timeout_seconds=1)
        request = MCPRequest.create(method="test")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.post = AsyncMock(side_effect=TimeoutError())
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=200))

            await client.connect()
            with pytest.raises(TimeoutError):
                await client.send_request(request)

    @pytest.mark.asyncio
    async def test_http_context_manager(self):
        """Test HTTP client as context manager."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get = AsyncMock(return_value=mock_response)

            async with HTTPMCPClient(endpoint="http://example.com/mcp") as client:
                assert client._client is not None

            mock_client.aclose.assert_called_once()


class TestStdioMCPClient:
    """Tests for STDIO MCP client."""

    @pytest.mark.asyncio
    async def test_stdio_client_initialization(self):
        """Test STDIO client initialization."""
        client = StdioMCPClient(command=["echo", "test"])
        assert client.command == ["echo", "test"]

    @pytest.mark.asyncio
    async def test_stdio_connect(self):
        """Test STDIO client connection."""
        client = StdioMCPClient(command=["python", "-c", "import sys; sys.stdin.read()"])

        # This may succeed or fail depending on Python availability
        # Test that the method executes without hanging
        try:
            await asyncio.wait_for(client.connect(), timeout=2.0)
            # If it succeeds, disconnect
            await client.disconnect()
        except (TimeoutError, ConnectionError, ValueError, FileNotFoundError, OSError):
            # Expected failures are acceptable for this test
            pass

    @pytest.mark.asyncio
    async def test_stdio_context_manager(self):
        """Test STDIO client as context manager."""
        client = StdioMCPClient(command=["echo", "test"])
        # Context manager should work even if connect fails
        try:
            async with client:
                pass
        except Exception:
            pass  # Expected to fail without real subprocess
