"""
Unit tests for ToolHealthMonitor service.

Tests health monitoring, periodic checks, and error handling.
All database operations are mocked - no real database interaction.
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.db.models import Tool, ToolHealthCheck
from app.schemas.tool import (
    MCPServerType,
    ServiceLocation,
    ToolCategory,
    ToolPurpose,
    ToolStatus,
)
from app.services.tool_health_monitor import ToolHealthMonitor


@pytest.fixture
def mock_db_session():
    """Mock async database session with all necessary methods."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_tool():
    """Create a mock Tool model."""
    tool_id = uuid4()
    return Tool(
        id=tool_id,
        tool_id="test_tool",
        name="Test Tool",
        description="Test tool for unit testing",
        category=ToolCategory.CUSTOM.value,
        provider="test-provider",
        tool_purpose=ToolPurpose.ORCHESTRATOR.value,
        service_location=ServiceLocation.ORCHESTRATOR.value,
        mcp_server_type=MCPServerType.HTTP.value,
        mcp_endpoint="http://test-endpoint.com",
        mcp_protocol_version="2024-11-05",
        requires_authentication=False,
        secret_name=None,
        is_enabled=True,
        is_healthy=False,
        last_health_check=None,
        timeout_seconds=30,
    )


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client."""
    client = MagicMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.initialize = AsyncMock(return_value={"capabilities": {"tools": []}})
    return client


@pytest.fixture
def health_monitor(mock_db_session):
    """Create ToolHealthMonitor instance with mocked dependencies."""
    return ToolHealthMonitor(mock_db_session)


class TestToolHealthMonitor:
    """Tests for ToolHealthMonitor class."""

    def test_init(self, health_monitor, mock_db_session):
        """Test health monitor initialization."""
        assert health_monitor.db == mock_db_session
        assert health_monitor.discovery_service is not None
        assert health_monitor.secrets_manager is not None
        assert not health_monitor._running
        assert health_monitor._task is None

    @pytest.mark.asyncio
    async def test_check_tool_health_success(
        self, health_monitor, mock_db_session, mock_tool, mock_mcp_client
    ):
        """Test successful health check."""
        # Setup mocks for async database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tool
        mock_db_session.execute.return_value = mock_result

        # Mock discovery service
        with patch.object(
            health_monitor.discovery_service,
            "create_mcp_client",
            return_value=mock_mcp_client,
        ):
            # Execute health check
            health_check = await health_monitor.check_tool_health(mock_tool.id)

            # Verify results
            assert health_check.status == ToolStatus.ONLINE.value
            assert health_check.response_time_ms is not None
            assert health_check.response_time_ms >= 0
            assert health_check.mcp_server_info == {"capabilities": {"tools": []}}
            assert mock_tool.is_healthy is True
            assert mock_tool.last_health_check is not None

            # Verify database operations
            mock_db_session.add.assert_called_once()
            # Commit may be called multiple times due to SQLAlchemy behavior
            assert mock_db_session.commit.await_count >= 1
            assert mock_db_session.refresh.await_count >= 1

            # Verify MCP client operations
            mock_mcp_client.connect.assert_called_once()
            mock_mcp_client.initialize.assert_called_once()
            mock_mcp_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_tool_health_timeout(self, health_monitor, mock_db_session, mock_tool):
        """Test health check with timeout."""
        # Setup mocks for async database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tool
        mock_db_session.execute.return_value = mock_result

        # Mock discovery service to raise timeout
        mock_client = MagicMock()
        mock_client.connect = AsyncMock(side_effect=TimeoutError("Connection timeout"))

        with patch.object(
            health_monitor.discovery_service,
            "create_mcp_client",
            return_value=mock_client,
        ):
            # Execute health check
            health_check = await health_monitor.check_tool_health(mock_tool.id)

            # Verify results
            assert health_check.status == ToolStatus.OFFLINE.value
            assert health_check.error_message == "Connection timeout"
            assert health_check.error_code == "TIMEOUT"
            assert mock_tool.is_healthy is False
            assert mock_tool.last_health_check is not None

    @pytest.mark.asyncio
    async def test_check_tool_health_connection_error(
        self, health_monitor, mock_db_session, mock_tool
    ):
        """Test health check with connection error."""
        # Setup mocks for async database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tool
        mock_db_session.execute.return_value = mock_result

        # Mock discovery service to raise connection error
        mock_client = MagicMock()
        mock_client.connect = AsyncMock(side_effect=ConnectionError("Connection failed"))

        with patch.object(
            health_monitor.discovery_service,
            "create_mcp_client",
            return_value=mock_client,
        ):
            # Execute health check
            health_check = await health_monitor.check_tool_health(mock_tool.id)

            # Verify results
            assert health_check.status == ToolStatus.OFFLINE.value
            assert "Connection failed" in health_check.error_message
            assert health_check.error_code == "ConnectionError"
            assert mock_tool.is_healthy is False

    @pytest.mark.asyncio
    async def test_check_tool_health_tool_not_found(self, health_monitor, mock_db_session):
        """Test health check with tool not found."""
        # Setup mocks for async database query - tool not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Execute health check - should raise ValueError
        with pytest.raises(ValueError, match=r"Tool .* not found"):
            await health_monitor.check_tool_health(uuid4())

    @pytest.mark.asyncio
    async def test_check_tool_health_with_authentication(
        self, health_monitor, mock_db_session, mock_tool, mock_mcp_client
    ):
        """Test health check with authentication."""
        # Setup tool with authentication
        mock_tool.requires_authentication = True
        mock_tool.secret_name = "test_secret"

        # Setup mocks for async database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tool
        mock_db_session.execute.return_value = mock_result

        # Mock secrets manager
        with (
            patch.object(
                health_monitor.secrets_manager,
                "retrieve_secret",
                new_callable=AsyncMock,
                return_value="secret_value",
            ),
            patch.object(
                health_monitor.discovery_service,
                "create_mcp_client",
                return_value=mock_mcp_client,
            ),
        ):
            # Mock client with auth token support
            mock_mcp_client.set_auth_token = MagicMock()

            # Execute health check
            health_check = await health_monitor.check_tool_health(mock_tool.id)

            # Verify auth token was set
            mock_mcp_client.set_auth_token.assert_called_once_with("secret_value")
            assert health_check.status == ToolStatus.ONLINE.value

    @pytest.mark.asyncio
    async def test_check_all_enabled_tools(self, health_monitor, mock_db_session, mock_tool):
        """Test checking all enabled tools."""
        # Setup multiple tools
        tool1 = mock_tool
        tool2 = Tool(
            id=uuid4(),
            tool_id="test_tool_2",
            name="Test Tool 2",
            category=ToolCategory.CUSTOM.value,
            tool_purpose=ToolPurpose.ORCHESTRATOR.value,
            service_location=ServiceLocation.ORCHESTRATOR.value,
            mcp_server_type=MCPServerType.HTTP.value,
            mcp_endpoint="http://test-endpoint-2.com",
            mcp_protocol_version="2024-11-05",
            is_enabled=True,
            timeout_seconds=30,
        )

        # Setup mocks for async database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [tool1, tool2]
        mock_db_session.execute.return_value = mock_result

        # Mock check_tool_health to return health checks directly
        health_check1 = ToolHealthCheck(
            tool_id=tool1.id,
            status=ToolStatus.ONLINE.value,
            checked_at=datetime.now(UTC),
            response_time_ms=10.0,
        )
        health_check2 = ToolHealthCheck(
            tool_id=tool2.id,
            status=ToolStatus.ONLINE.value,
            checked_at=datetime.now(UTC),
            response_time_ms=15.0,
        )

        call_count = 0

        async def mock_check_tool_health(_tool_id):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return health_check1
            return health_check2

        with patch.object(health_monitor, "check_tool_health", side_effect=mock_check_tool_health):
            # Execute check all
            results = await health_monitor.check_all_enabled_tools()

            # Verify results
            assert len(results) == 2
            assert tool1.id in results
            assert tool2.id in results
            assert results[tool1.id].status == ToolStatus.ONLINE.value
            assert results[tool2.id].status == ToolStatus.ONLINE.value

    @pytest.mark.asyncio
    async def test_check_all_enabled_tools_with_failure(
        self, health_monitor, mock_db_session, mock_tool
    ):
        """Test checking all enabled tools with some failures."""
        # Setup mocks for async database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_tool]
        mock_db_session.execute.return_value = mock_result

        # Mock health check to raise exception
        with patch.object(
            health_monitor,
            "check_tool_health",
            side_effect=Exception("Health check failed"),
        ):
            # Execute check all - should handle errors gracefully
            results = await health_monitor.check_all_enabled_tools()

            # Verify no results (error was logged but not raised)
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_periodic_health_checks(
        self, health_monitor, mock_db_session, mock_tool, mock_mcp_client
    ):
        """Test periodic health checks."""
        # Setup mocks for async database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_tool]
        mock_result.scalar_one_or_none.return_value = mock_tool
        mock_db_session.execute.return_value = mock_result

        with patch.object(
            health_monitor.discovery_service,
            "create_mcp_client",
            return_value=mock_mcp_client,
        ):
            # Start periodic checks with short interval
            task = asyncio.create_task(health_monitor.periodic_health_checks(interval_seconds=0.1))

            # Wait a bit
            await asyncio.sleep(0.15)

            # Stop periodic checks
            health_monitor.stop_periodic_checks()
            task.cancel()

            # Verify health checks were called
            assert mock_db_session.add.called

    def test_start_stop_periodic_checks(self, health_monitor):
        """Test starting and stopping periodic checks."""
        # Initially not running
        assert not health_monitor._running
        assert health_monitor._task is None

        # Start periodic checks
        mock_task = MagicMock()
        with patch("asyncio.create_task", return_value=mock_task) as mock_create_task:
            health_monitor.start_periodic_checks(interval_seconds=300)
            # _running is set inside periodic_health_checks, not immediately
            # But task should be created
            assert health_monitor._task is not None
            mock_create_task.assert_called_once()

        # Try to start again - should warn
        with patch("asyncio.create_task") as mock_create_task:
            health_monitor.start_periodic_checks()
            # Should not create new task
            assert mock_create_task.call_count == 0

        # Stop periodic checks
        health_monitor.stop_periodic_checks()
        assert not health_monitor._running

        # Try to stop again - should warn
        health_monitor.stop_periodic_checks()

    @pytest.mark.asyncio
    async def test_periodic_health_checks_handles_exceptions(self, health_monitor):
        """Test periodic health checks handle exceptions gracefully."""
        # Mock check_all_enabled_tools to raise exception
        with patch.object(
            health_monitor,
            "check_all_enabled_tools",
            side_effect=Exception("Check failed"),
        ):
            # Start periodic checks
            task = asyncio.create_task(health_monitor.periodic_health_checks(interval_seconds=0.1))

            # Wait a bit
            await asyncio.sleep(0.15)

            # Stop periodic checks
            health_monitor.stop_periodic_checks()
            task.cancel()

            # Should not raise exception (handled gracefully)
