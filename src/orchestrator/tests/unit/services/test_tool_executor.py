"""
Unit tests for ToolExecutor service.

Tests tool execution with retries, circuit breakers, and rate limiting.
All database operations are mocked - no real database interaction.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.db.models import Tool, ToolPermission
from app.mcp.base_client import MCPClient
from app.schemas.tool import MCPServerType, ServiceLocation, ToolCategory, ToolPurpose
from app.services.tool_executor import CircuitBreaker, ToolExecutor


@pytest.fixture
def mock_db_session():
    """Mock async database session with all necessary methods."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
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
        is_healthy=True,
        timeout_seconds=30,
    )


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client."""
    client = MagicMock(spec=MCPClient)
    client.is_initialized = True
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.initialize = AsyncMock(return_value={"capabilities": {}})
    client.call_tool = AsyncMock(return_value={"result": "success"})
    return client


@pytest.fixture
def tool_executor(mock_db_session):
    """Create ToolExecutor instance with mocked dependencies."""
    return ToolExecutor(mock_db_session)


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_circuit_breaker_init(self):
        """Test circuit breaker initialization."""
        cb = CircuitBreaker(failure_threshold=5, timeout_seconds=60)
        assert cb.failure_threshold == 5
        assert cb.timeout_seconds == 60
        assert cb.failures == {}
        assert cb.open_until == {}

    def test_circuit_breaker_closed_initially(self):
        """Test circuit breaker is closed initially."""
        cb = CircuitBreaker()
        assert not cb.is_open("tool_1")

    def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit breaker opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=60)
        tool_id = "tool_1"

        # Record failures up to threshold
        for _ in range(3):
            cb.record_failure(tool_id)

        assert cb.is_open(tool_id)

    def test_circuit_breaker_resets_on_success(self):
        """Test circuit breaker resets on success."""
        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=60)
        tool_id = "tool_1"

        # Record 2 failures
        cb.record_failure(tool_id)
        cb.record_failure(tool_id)

        # Record success - should reset
        cb.record_success(tool_id)

        # Should not be open
        assert not cb.is_open(tool_id)
        assert len(cb.failures.get(tool_id, [])) == 0

    def test_circuit_breaker_timeout_expires(self):
        """Test circuit breaker closes after timeout."""
        cb = CircuitBreaker(failure_threshold=2, timeout_seconds=1)
        tool_id = "tool_1"

        # Open circuit
        cb.record_failure(tool_id)
        cb.record_failure(tool_id)
        assert cb.is_open(tool_id)

        # Wait for timeout (with small buffer)
        import time

        time.sleep(1.1)

        # Should be closed now
        assert not cb.is_open(tool_id)

    def test_circuit_breaker_removes_old_failures(self):
        """Test circuit breaker removes failures outside window."""
        cb = CircuitBreaker(failure_threshold=10, timeout_seconds=60)
        tool_id = "tool_1"

        # Record old failure (outside 5-minute window)
        old_time = datetime.now(UTC) - timedelta(minutes=6)
        cb.failures[tool_id] = [old_time]

        # Record new failure
        cb.record_failure(tool_id)

        # Old failure should be removed
        assert len(cb.failures[tool_id]) == 1
        assert (datetime.now(UTC) - cb.failures[tool_id][0]).total_seconds() < 60


class TestToolExecutor:
    """Tests for ToolExecutor class."""

    @pytest.mark.asyncio
    async def test_execute_tool_success(
        self, tool_executor, mock_db_session, mock_tool, mock_mcp_client
    ):
        """Test successful tool execution."""
        user_id = uuid4()
        tool_name = "test_tool_function"
        parameters = {"param1": "value1"}

        # Setup mocks for async database queries
        mock_tool_result = MagicMock()
        mock_tool_result.scalar_one_or_none.return_value = mock_tool

        mock_permission_result = MagicMock()
        mock_permission_result.scalar_one_or_none.return_value = (
            None  # No permission = no rate limits
        )

        mock_invocation_result = MagicMock()
        mock_invocation_result.scalar.return_value = 0

        call_count = 0

        def execute_side_effect(stmt):
            nonlocal call_count
            call_count += 1
            # First call is Tool query, second is ToolPermission, third is ToolInvocation
            if call_count == 1:
                return mock_tool_result
            if call_count == 2:
                return mock_permission_result
            return mock_invocation_result

        mock_db_session.execute.side_effect = execute_side_effect

        # Mock permission service and discovery service
        with (
            patch.object(
                tool_executor.permission_service,
                "check_permission",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch.object(
                tool_executor.discovery_service,
                "create_mcp_client",
                return_value=mock_mcp_client,
            ),
        ):
            result = await tool_executor.execute_tool(
                tool_id=mock_tool.id,
                tool_name=tool_name,
                parameters=parameters,
                user_id=user_id,
                user_role="admin",
            )

            assert result == {"result": "success"}
            mock_mcp_client.connect.assert_called_once()
            mock_mcp_client.initialize.assert_called_once()
            mock_mcp_client.call_tool.assert_called_once_with(tool_name, parameters)
            mock_db_session.add.assert_called_once()
            assert mock_db_session.commit.await_count >= 1  # At least one commit

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, tool_executor, mock_db_session):
        """Test tool execution fails when tool not found."""
        tool_id = uuid4()
        user_id = uuid4()

        # Setup mocks - tool not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await tool_executor.execute_tool(
                tool_id=tool_id,
                tool_name="test_tool",
                parameters={},
                user_id=user_id,
                user_role="admin",
            )

    @pytest.mark.asyncio
    async def test_execute_tool_disabled(self, tool_executor, mock_db_session, mock_tool):
        """Test tool execution fails when tool is disabled."""
        user_id = uuid4()
        mock_tool.is_enabled = False

        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tool
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(RuntimeError, match="disabled"):
            await tool_executor.execute_tool(
                tool_id=mock_tool.id,
                tool_name="test_tool",
                parameters={},
                user_id=user_id,
                user_role="admin",
            )

    @pytest.mark.asyncio
    async def test_execute_tool_circuit_breaker_open(
        self, tool_executor, mock_db_session, mock_tool
    ):
        """Test tool execution fails when circuit breaker is open."""
        user_id = uuid4()

        # Open circuit breaker
        tool_executor.circuit_breaker.record_failure(str(mock_tool.id))
        tool_executor.circuit_breaker.record_failure(str(mock_tool.id))
        tool_executor.circuit_breaker.record_failure(str(mock_tool.id))
        tool_executor.circuit_breaker.record_failure(str(mock_tool.id))
        tool_executor.circuit_breaker.record_failure(str(mock_tool.id))

        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tool
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(RuntimeError, match="Circuit breaker open"):
            await tool_executor.execute_tool(
                tool_id=mock_tool.id,
                tool_name="test_tool",
                parameters={},
                user_id=user_id,
                user_role="admin",
            )

    @pytest.mark.asyncio
    async def test_execute_tool_permission_denied(self, tool_executor, mock_db_session, mock_tool):
        """Test tool execution fails without permission."""
        user_id = uuid4()

        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tool
        mock_db_session.execute.return_value = mock_result

        # Mock permission service to deny
        with (
            patch.object(
                tool_executor.permission_service,
                "check_permission",
                new_callable=AsyncMock,
                return_value=False,
            ),
            pytest.raises(PermissionError, match="not permitted"),
        ):
            await tool_executor.execute_tool(
                tool_id=mock_tool.id,
                tool_name="test_tool",
                parameters={},
                user_id=user_id,
                user_role="user",
            )

    @pytest.mark.asyncio
    async def test_execute_tool_rate_limit_exceeded(
        self, tool_executor, mock_db_session, mock_tool
    ):
        """Test tool execution fails when rate limit exceeded."""
        user_id = uuid4()

        # Setup mocks
        mock_tool_result = MagicMock()
        mock_tool_result.scalar_one_or_none.return_value = mock_tool

        # Create permission with rate limit
        permission = ToolPermission(
            id=uuid4(),
            tool_id=mock_tool.id,
            role="admin",
            can_view=True,
            can_use=True,
            can_configure=False,
            max_calls_per_hour=5,
        )

        # Mock permission query result
        mock_permission_result = MagicMock()
        mock_permission_result.scalar_one_or_none.return_value = permission

        # Mock invocation query for rate limit check
        mock_invocation_result = MagicMock()
        mock_invocation_result.scalar.return_value = 5  # Already at limit

        call_count = 0

        def execute_side_effect(stmt):
            nonlocal call_count
            call_count += 1
            # First call is Tool query, second is ToolPermission, third is ToolInvocation
            if call_count == 1:
                return mock_tool_result
            if call_count == 2:
                return mock_permission_result
            return mock_invocation_result

        mock_db_session.execute.side_effect = execute_side_effect

        # Mock permission service
        with (
            patch.object(
                tool_executor.permission_service,
                "check_permission",
                new_callable=AsyncMock,
                return_value=True,
            ),
            pytest.raises(RuntimeError, match="Rate limit exceeded"),
        ):
            await tool_executor.execute_tool(
                tool_id=mock_tool.id,
                tool_name="test_tool",
                parameters={},
                user_id=user_id,
                user_role="admin",
            )

    @pytest.mark.asyncio
    async def test_execute_tool_retry_on_failure(
        self, tool_executor, mock_db_session, mock_tool, mock_mcp_client
    ):
        """Test tool execution retries on failure."""
        user_id = uuid4()
        tool_name = "test_tool_function"
        parameters = {"param1": "value1"}

        # Setup mocks for async database queries
        mock_tool_result = MagicMock()
        mock_tool_result.scalar_one_or_none.return_value = mock_tool

        mock_permission_result = MagicMock()
        mock_permission_result.scalar_one_or_none.return_value = (
            None  # No permission = no rate limits
        )

        mock_invocation_result = MagicMock()
        mock_invocation_result.scalar.return_value = 0

        call_count = 0

        def execute_side_effect(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_tool_result
            if call_count == 2:
                return mock_permission_result
            return mock_invocation_result

        mock_db_session.execute.side_effect = execute_side_effect

        # Mock client to fail first time, succeed second
        mock_mcp_client.call_tool.side_effect = [
            Exception("Temporary failure"),
            {"result": "success"},
        ]

        # Mock permission service and discovery service
        with (
            patch.object(
                tool_executor.permission_service,
                "check_permission",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch.object(
                tool_executor.discovery_service,
                "create_mcp_client",
                return_value=mock_mcp_client,
            ),
        ):
            result = await tool_executor.execute_tool(
                tool_id=mock_tool.id,
                tool_name=tool_name,
                parameters=parameters,
                user_id=user_id,
                user_role="admin",
                max_retries=1,
            )

            assert result == {"result": "success"}
            assert mock_mcp_client.call_tool.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_tool_retry_exhausted(
        self, tool_executor, mock_db_session, mock_tool, mock_mcp_client
    ):
        """Test tool execution fails after retries exhausted."""
        user_id = uuid4()
        tool_name = "test_tool_function"
        parameters = {"param1": "value1"}

        # Setup mocks for async database queries
        mock_tool_result = MagicMock()
        mock_tool_result.scalar_one_or_none.return_value = mock_tool

        mock_permission_result = MagicMock()
        mock_permission_result.scalar_one_or_none.return_value = (
            None  # No permission = no rate limits
        )

        mock_invocation_result = MagicMock()
        mock_invocation_result.scalar.return_value = 0

        call_count = 0

        def execute_side_effect(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_tool_result
            if call_count == 2:
                return mock_permission_result
            return mock_invocation_result

        mock_db_session.execute.side_effect = execute_side_effect

        # Mock client to always fail
        mock_mcp_client.call_tool.side_effect = Exception("Persistent failure")

        # Mock permission service and discovery service
        with (
            patch.object(
                tool_executor.permission_service,
                "check_permission",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch.object(
                tool_executor.discovery_service,
                "create_mcp_client",
                return_value=mock_mcp_client,
            ),
        ):
            with pytest.raises(Exception, match="Persistent failure"):
                await tool_executor.execute_tool(
                    tool_id=mock_tool.id,
                    tool_name=tool_name,
                    parameters=parameters,
                    user_id=user_id,
                    user_role="admin",
                    max_retries=2,
                )

            # Should have tried 3 times (initial + 2 retries)
            assert mock_mcp_client.call_tool.call_count == 3

    @pytest.mark.asyncio
    async def test_get_mcp_client_caches(self, tool_executor, mock_tool, mock_mcp_client):
        """Test MCP client is cached after creation."""
        # Mock discovery service
        with patch.object(
            tool_executor.discovery_service,
            "create_mcp_client",
            return_value=mock_mcp_client,
        ):
            # Get client first time
            client1 = await tool_executor._get_mcp_client(mock_tool)

            # Get client second time - should return cached
            client2 = await tool_executor._get_mcp_client(mock_tool)

            assert client1 is client2
            assert tool_executor.discovery_service.create_mcp_client.call_count == 1

    @pytest.mark.asyncio
    async def test_get_mcp_client_with_secret(self, tool_executor, mock_tool, mock_mcp_client):
        """Test MCP client creation with authentication secret."""
        mock_tool.requires_authentication = True
        mock_tool.secret_name = "test_api_key"

        # Mock secrets manager and discovery service
        with (
            patch.object(
                tool_executor.secrets_manager,
                "retrieve_secret",
                new_callable=AsyncMock,
                return_value="secret_value",
            ),
            patch.object(
                tool_executor.discovery_service,
                "create_mcp_client",
                return_value=mock_mcp_client,
            ),
        ):
            await tool_executor._get_mcp_client(mock_tool)

            tool_executor.secrets_manager.retrieve_secret.assert_called_once_with("test_api_key")

    @pytest.mark.asyncio
    async def test_cleanup_disconnects_clients(self, tool_executor, mock_mcp_client):
        """Test cleanup disconnects all active clients."""
        tool_id = "test_tool_id"
        tool_executor.active_clients[tool_id] = mock_mcp_client

        await tool_executor.cleanup()

        mock_mcp_client.disconnect.assert_called_once()
        assert len(tool_executor.active_clients) == 0
