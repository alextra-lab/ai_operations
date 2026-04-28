"""
Unit tests for ToolService.

Tests CRUD operations for tool management.
All database operations are mocked - no real database interaction.
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.db.models import Tool
from app.schemas.tool import (
    DataFlowDirection,
    DataSourceType,
    MaxDataSensitivity,
    MCPServerType,
    NetworkAccessLevel,
    ServiceLocation,
    ToolCategory,
    ToolCreate,
    ToolPurpose,
    ToolUpdate,
)
from app.services.tool_service import ToolService


@pytest.fixture
def mock_db_session():
    """Mock async database session with all necessary methods."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def mock_secrets_manager():
    """Mock SecretsManager."""
    manager = MagicMock()
    manager.delete_secret = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def tool_service(mock_db_session, mock_secrets_manager):
    """Create ToolService instance with mocked dependencies."""
    with patch(
        "app.services.tool_service.SecretsManager",
        return_value=mock_secrets_manager,
    ):
        return ToolService(mock_db_session)


@pytest.fixture
def sample_tool_data():
    """Sample tool creation data."""
    return ToolCreate(
        tool_id="test_tool_123",
        name="Test Tool",
        description="A test tool for unit testing",
        category=ToolCategory.CUSTOM,
        provider="test-provider",
        tool_purpose=ToolPurpose.ORCHESTRATOR,
        service_location=ServiceLocation.ORCHESTRATOR,
        mcp_server_type=MCPServerType.HTTP,
        mcp_endpoint="http://test-endpoint.com",
        requires_authentication=True,
        authentication_type="api_key",
        secret_name="test_api_key",
    )


@pytest.fixture
def sample_tool_model(sample_tool_data):
    """Sample Tool model instance."""
    tool_id = uuid4()
    now = datetime.now(UTC)
    return Tool(
        id=tool_id,
        tool_id=sample_tool_data.tool_id,
        name=sample_tool_data.name,
        description=sample_tool_data.description,
        category=sample_tool_data.category.value,
        provider=sample_tool_data.provider,
        tool_purpose=sample_tool_data.tool_purpose.value,
        service_location=sample_tool_data.service_location.value,
        mcp_server_type=sample_tool_data.mcp_server_type.value,
        mcp_command=None,
        mcp_endpoint=sample_tool_data.mcp_endpoint,
        mcp_protocol_version="2024-11-05",
        capabilities=None,
        parameters_schema=None,
        requires_authentication=sample_tool_data.requires_authentication,
        authentication_type=sample_tool_data.authentication_type,
        secret_name=sample_tool_data.secret_name,
        config_options=None,
        timeout_seconds=30,
        rate_limit_per_minute=None,
        max_concurrent_calls=5,
        is_enabled=False,
        is_healthy=True,
        health_check_interval_seconds=300,
        version=None,
        documentation_url=None,
        tags=[],
        last_health_check=None,
        # Security classification (ADR-057)
        data_source_type=DataSourceType.INTERNAL.value,
        data_flow_direction=DataFlowDirection.INGRESS.value,
        network_access_level=NetworkAccessLevel.INTERNAL.value,
        max_data_sensitivity=MaxDataSensitivity.INTERNAL.value,
        created_at=now,
        updated_at=now,
        created_by=uuid4(),
        updated_by=uuid4(),
    )


class TestToolServiceCreate:
    """Test ToolService.create_tool method."""

    @pytest.mark.asyncio
    async def test_create_tool_success(self, tool_service, mock_db_session, sample_tool_data):
        """Successfully create a new tool."""
        user_id = uuid4()

        # Mock no existing tool (scalar_one_or_none returns None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Mock tool creation
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        # Create tool
        created_tool = await tool_service.create_tool(sample_tool_data, user_id)

        # Verify database operations
        assert mock_db_session.execute.called
        assert mock_db_session.add.called
        assert mock_db_session.commit.called
        assert mock_db_session.refresh.called

        # Verify tool attributes
        assert created_tool.tool_id == sample_tool_data.tool_id
        assert created_tool.name == sample_tool_data.name

    @pytest.mark.asyncio
    async def test_create_tool_duplicate_id_raises_error(
        self, tool_service, mock_db_session, sample_tool_data, sample_tool_model
    ):
        """Creating tool with duplicate tool_id raises ValueError."""
        user_id = uuid4()

        # Mock existing tool
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_tool_model
        mock_db_session.execute.return_value = mock_result

        # Attempt to create duplicate
        with pytest.raises(ValueError, match="already exists"):
            await tool_service.create_tool(sample_tool_data, user_id)

    @pytest.mark.asyncio
    async def test_create_tool_with_mcp_command(
        self, tool_service, mock_db_session, sample_tool_data
    ):
        """Create tool with mcp_command list is converted to JSON."""
        user_id = uuid4()
        sample_tool_data.mcp_command = [
            "python",
            "mcp_server.py",
            "--config",
            "config.json",
        ]
        sample_tool_data.mcp_server_type = MCPServerType.STDIO

        # Mock no existing tool
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Capture the tool object passed to add()
        added_tool = None

        def capture_add(obj):
            nonlocal added_tool
            added_tool = obj

        mock_db_session.add.side_effect = capture_add

        await tool_service.create_tool(sample_tool_data, user_id)

        # Verify mcp_command was converted to JSON string
        assert added_tool is not None
        assert isinstance(added_tool.mcp_command, str)
        assert json.loads(added_tool.mcp_command) == sample_tool_data.mcp_command


class TestToolServiceGet:
    """Test ToolService get methods."""

    @pytest.mark.asyncio
    async def test_get_tool_by_id(self, tool_service, mock_db_session, sample_tool_model):
        """Get tool by tool_id."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_tool_model
        mock_db_session.execute.return_value = mock_result

        result = await tool_service.get_tool("test_tool_123")

        assert result == sample_tool_model
        assert mock_db_session.execute.called

    @pytest.mark.asyncio
    async def test_get_tool_not_found(self, tool_service, mock_db_session):
        """Get nonexistent tool returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await tool_service.get_tool("nonexistent_tool")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_tool_by_uuid(self, tool_service, mock_db_session, sample_tool_model):
        """Get tool by UUID."""
        tool_uuid = sample_tool_model.id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_tool_model
        mock_db_session.execute.return_value = mock_result

        result = await tool_service.get_tool_by_uuid(tool_uuid)

        assert result == sample_tool_model


class TestToolServiceList:
    """Test ToolService.list_tools method."""

    @pytest.mark.asyncio
    async def test_list_tools_all(self, tool_service, mock_db_session, sample_tool_model):
        """List all tools."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_tool_model]
        mock_db_session.execute.return_value = mock_result

        tools = await tool_service.list_tools()

        assert len(tools) == 1
        assert tools[0].tool_id == sample_tool_model.tool_id

    @pytest.mark.asyncio
    async def test_list_tools_filter_category(
        self, tool_service, mock_db_session, sample_tool_model
    ):
        """List tools filtered by category."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_tool_model]
        mock_db_session.execute.return_value = mock_result

        tools = await tool_service.list_tools(category="custom")

        assert len(tools) == 1
        assert mock_db_session.execute.called

    @pytest.mark.asyncio
    async def test_list_tools_enabled_only(self, tool_service, mock_db_session, sample_tool_model):
        """List only enabled tools."""
        sample_tool_model.is_enabled = True
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_tool_model]
        mock_db_session.execute.return_value = mock_result

        tools = await tool_service.list_tools(enabled_only=True)

        assert len(tools) == 1
        assert mock_db_session.execute.called

    @pytest.mark.asyncio
    async def test_list_tools_healthy_only(self, tool_service, mock_db_session, sample_tool_model):
        """List only healthy tools."""
        sample_tool_model.is_healthy = True
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_tool_model]
        mock_db_session.execute.return_value = mock_result

        tools = await tool_service.list_tools(healthy_only=True)

        assert len(tools) == 1
        assert mock_db_session.execute.called


class TestToolServiceUpdate:
    """Test ToolService.update_tool method."""

    @pytest.mark.asyncio
    async def test_update_tool_success(self, tool_service, mock_db_session, sample_tool_model):
        """Successfully update a tool."""
        user_id = uuid4()
        update_data = ToolUpdate(name="Updated Tool Name", is_enabled=True)

        # Mock tool exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_tool_model
        mock_db_session.execute.return_value = mock_result

        result = await tool_service.update_tool("test_tool_123", update_data, user_id)

        assert result == sample_tool_model
        assert result.name == "Updated Tool Name"
        assert result.is_enabled is True
        assert mock_db_session.commit.called
        assert mock_db_session.refresh.called

    @pytest.mark.asyncio
    async def test_update_tool_not_found_raises_error(self, tool_service, mock_db_session):
        """Updating nonexistent tool raises ValueError."""
        user_id = uuid4()
        update_data = ToolUpdate(name="Updated Name")

        # Mock tool not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await tool_service.update_tool("nonexistent_tool", update_data, user_id)


class TestToolServiceDelete:
    """Test ToolService.delete_tool method."""

    @pytest.mark.asyncio
    async def test_delete_tool_success(
        self, tool_service, mock_db_session, mock_secrets_manager, sample_tool_model
    ):
        """Successfully delete a tool."""
        # Mock tool exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_tool_model
        mock_db_session.execute.return_value = mock_result

        result = await tool_service.delete_tool("test_tool_123")

        assert result is True
        assert mock_db_session.delete.called
        assert mock_db_session.commit.called
        # Verify secret deletion was attempted
        assert mock_secrets_manager.delete_secret.called

    @pytest.mark.asyncio
    async def test_delete_tool_not_found_returns_false(self, tool_service, mock_db_session):
        """Deleting nonexistent tool returns False."""
        # Mock tool not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await tool_service.delete_tool("nonexistent_tool")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_tool_without_secret(
        self, tool_service, mock_db_session, mock_secrets_manager, sample_tool_model
    ):
        """Delete tool without secret_name doesn't call secrets_manager."""
        sample_tool_model.secret_name = None

        # Mock tool exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_tool_model
        mock_db_session.execute.return_value = mock_result

        result = await tool_service.delete_tool("test_tool_123")

        assert result is True
        # Verify secret deletion was NOT called
        assert not mock_secrets_manager.delete_secret.called


class TestToolServiceEnableDisable:
    """Test ToolService enable/disable methods."""

    @pytest.mark.asyncio
    async def test_enable_tool(self, tool_service, mock_db_session, sample_tool_model):
        """Successfully enable a tool."""
        # Mock tool exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_tool_model
        mock_db_session.execute.return_value = mock_result

        result = await tool_service.enable_tool("test_tool_123")

        assert result.is_enabled is True
        assert mock_db_session.commit.called
        assert mock_db_session.refresh.called

    @pytest.mark.asyncio
    async def test_disable_tool(self, tool_service, mock_db_session, sample_tool_model):
        """Successfully disable a tool."""
        sample_tool_model.is_enabled = True

        # Mock tool exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_tool_model
        mock_db_session.execute.return_value = mock_result

        result = await tool_service.disable_tool("test_tool_123")

        assert result.is_enabled is False
        assert mock_db_session.commit.called

    @pytest.mark.asyncio
    async def test_enable_tool_not_found_raises_error(self, tool_service, mock_db_session):
        """Enabling nonexistent tool raises ValueError."""
        # Mock tool not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await tool_service.enable_tool("nonexistent_tool")

    @pytest.mark.asyncio
    async def test_disable_tool_not_found_raises_error(self, tool_service, mock_db_session):
        """Disabling nonexistent tool raises ValueError."""
        # Mock tool not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await tool_service.disable_tool("nonexistent_tool")
