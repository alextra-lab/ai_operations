"""
Unit tests for tool discovery service.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.db.models import Tool
from app.schemas.tool import MCPServerType
from app.services.tool_discovery_service import ToolDiscoveryService


@pytest.fixture
def mock_tool_http():
    """Create a mock HTTP tool."""
    tool = MagicMock(spec=Tool)
    tool.id = uuid4()
    tool.tool_id = "test_http_tool"
    tool.mcp_server_type = MCPServerType.HTTP
    tool.mcp_endpoint = "http://example.com/mcp"
    tool.mcp_protocol_version = "2024-11-05"
    tool.timeout_seconds = 30
    tool.mcp_command = None
    return tool


@pytest.fixture
def mock_tool_stdio():
    """Create a mock STDIO tool."""
    tool = MagicMock(spec=Tool)
    tool.id = uuid4()
    tool.tool_id = "test_stdio_tool"
    tool.mcp_server_type = MCPServerType.STDIO
    tool.mcp_endpoint = None
    tool.mcp_protocol_version = "2024-11-05"
    tool.timeout_seconds = 30
    tool.mcp_command = ["python", "-m", "mcp_server"]
    return tool


@pytest.fixture
def db_session():
    """Create a mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    return session


class TestToolDiscoveryService:
    """Tests for tool discovery service."""

    def test_create_http_client(self, db_session, mock_tool_http):
        """Test creating HTTP MCP client."""
        service = ToolDiscoveryService(db_session)
        client = service.create_mcp_client(mock_tool_http)
        assert client.endpoint == "http://example.com/mcp"

    def test_create_stdio_client(self, db_session, mock_tool_stdio):
        """Test creating STDIO MCP client."""
        service = ToolDiscoveryService(db_session)
        client = service.create_mcp_client(mock_tool_stdio)
        assert client.command == ["python", "-m", "mcp_server"]

    def test_create_client_missing_endpoint(self, db_session):
        """Test error when HTTP tool missing endpoint."""
        tool = MagicMock(spec=Tool)
        tool.mcp_server_type = MCPServerType.HTTP
        tool.mcp_endpoint = None
        tool.tool_id = "test"

        service = ToolDiscoveryService(db_session)
        with pytest.raises(ValueError, match="missing endpoint"):
            service.create_mcp_client(tool)

    def test_create_client_missing_command(self, db_session):
        """Test error when STDIO tool missing command."""
        tool = MagicMock(spec=Tool)
        tool.mcp_server_type = MCPServerType.STDIO
        tool.mcp_command = None
        tool.tool_id = "test"

        service = ToolDiscoveryService(db_session)
        with pytest.raises(ValueError, match="missing command"):
            service.create_mcp_client(tool)

    @pytest.mark.asyncio
    async def test_discover_capabilities(self, db_session, mock_tool_http):
        """Test discovering tool capabilities."""
        service = ToolDiscoveryService(db_session)

        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tool_http
        db_session.execute.return_value = mock_result

        # Mock MCP client
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.initialize = AsyncMock(return_value={"capabilities": {"tools": {}}})
        mock_client.list_tools = AsyncMock(return_value=[{"name": "test_tool", "inputSchema": {}}])

        with patch.object(service, "create_mcp_client", return_value=mock_client):
            capabilities = await service.discover_tool_capabilities(mock_tool_http.id)

        assert "server_capabilities" in capabilities
        assert "tools" in capabilities
        assert len(capabilities["tools"]) == 1

    @pytest.mark.asyncio
    async def test_update_tool_from_discovery(self, db_session, mock_tool_http):
        """Test updating tool from discovery."""
        service = ToolDiscoveryService(db_session)

        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tool_http
        db_session.execute.return_value = mock_result
        db_session.commit = AsyncMock()
        db_session.refresh = AsyncMock()

        # Mock MCP client
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.initialize = AsyncMock(return_value={"capabilities": {"tools": {}}})
        mock_client.list_tools = AsyncMock(
            return_value=[{"name": "test_tool", "inputSchema": {"type": "object"}}]
        )

        with patch.object(service, "create_mcp_client", return_value=mock_client):
            updated_tool = await service.update_tool_from_discovery(mock_tool_http.id)

        assert updated_tool is not None
        db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_discover_tool_not_found(self, db_session):
        """Test error when tool not found."""
        service = ToolDiscoveryService(db_session)
        # Mock database query result - tool not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await service.discover_tool_capabilities(uuid4())
