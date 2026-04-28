"""
Unit tests for ToolRegistrationService.

Tests multi-phase registration workflow, session management, and validation.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.orchestrator.app.schemas.tool import (
    MCPServerType,
    ServiceLocation,
    ToolCategory,
    ToolPurpose,
)
from src.orchestrator.app.schemas.tool_registration import ToolRegistrationPhase
from src.orchestrator.app.services.tool_registration_service import (
    ToolRegistrationService,
)


@pytest.fixture
def mock_db():
    """Mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def registration_service(mock_db):
    """Create registration service with mocked dependencies."""
    with (
        patch("src.orchestrator.app.services.tool_registration_service.ToolService"),
        patch("src.orchestrator.app.services.tool_registration_service.ToolDiscoveryService"),
        patch("src.orchestrator.app.services.tool_registration_service.SecretsManager"),
        patch("src.orchestrator.app.services.tool_registration_service.ToolPermissionService"),
    ):
        service = ToolRegistrationService(mock_db)
        service.tool_service = MagicMock()
        service.discovery_service = MagicMock()
        service.secrets_manager = MagicMock()
        service.permission_service = MagicMock()
        # Make service methods async
        service.tool_service.get_tool = AsyncMock(return_value=None)
        service.tool_service.create_tool = AsyncMock()
        service.secrets_manager.store_secret = AsyncMock()
        service.permission_service.grant_permission = AsyncMock()
        return service


@pytest.fixture
def user_id():
    """Test user ID."""
    return uuid.uuid4()


class TestSessionManagement:
    """Test session creation and management."""

    def test_create_session(self, registration_service, user_id):
        """Test session creation."""
        session = registration_service._create_session(user_id)

        assert session.session_id is not None
        assert session.user_id == user_id
        assert session.current_phase == ToolRegistrationPhase.BASIC_INFO
        assert session.created_at is not None
        assert session.expires_at > session.created_at

    def test_get_session(self, registration_service, user_id):
        """Test session retrieval."""
        session = registration_service._create_session(user_id)
        retrieved = registration_service._get_session(session.session_id)

        assert retrieved.session_id == session.session_id

    def test_get_session_not_found(self, registration_service):
        """Test session not found error."""
        with pytest.raises(ValueError, match="not found"):
            registration_service._get_session("invalid_session_id")

    def test_get_session_expired(self, registration_service, user_id):
        """Test expired session handling."""
        session = registration_service._create_session(user_id)
        # Manually expire the session
        session.expires_at = datetime.now(UTC) - timedelta(hours=1)

        with pytest.raises(ValueError, match="expired"):
            registration_service._get_session(session.session_id)


class TestBasicInfoPhase:
    """Test Phase 1: Basic Information."""

    @pytest.mark.asyncio
    async def test_handle_basic_info_success(self, registration_service, user_id):
        """Test successful basic info validation."""
        session = registration_service._create_session(user_id)
        registration_service.tool_service.get_tool.return_value = None

        data = {
            "tool_id": "test_tool",
            "name": "Test Tool",
            "category": ToolCategory.DATABASE.value,
            "tool_purpose": ToolPurpose.ORCHESTRATOR.value,
            "service_location": ServiceLocation.ORCHESTRATOR.value,
        }

        result = await registration_service._handle_basic_info(session, data)

        assert result["success"] is True
        assert session.basic_info is not None
        assert session.can_proceed is True

    @pytest.mark.asyncio
    async def test_handle_basic_info_duplicate_tool_id(self, registration_service, user_id):
        """Test duplicate tool ID validation."""
        session = registration_service._create_session(user_id)
        registration_service.tool_service.get_tool.return_value = MagicMock()

        data = {
            "tool_id": "existing_tool",
            "name": "Test Tool",
            "category": ToolCategory.DATABASE.value,
            "tool_purpose": ToolPurpose.ORCHESTRATOR.value,
            "service_location": ServiceLocation.ORCHESTRATOR.value,
        }

        result = await registration_service._handle_basic_info(session, data)

        assert result["success"] is False
        assert "already exists" in result["error"]
        assert session.can_proceed is False

    @pytest.mark.asyncio
    async def test_handle_basic_info_invalid_data(self, registration_service, user_id):
        """Test invalid data validation."""
        session = registration_service._create_session(user_id)

        data = {
            "tool_id": "INVALID_TOOL_ID",  # Invalid format
            "name": "",
        }

        result = await registration_service._handle_basic_info(session, data)

        assert result["success"] is False
        assert session.can_proceed is False


class TestMcpConfigPhase:
    """Test Phase 2: MCP Configuration."""

    @pytest.mark.asyncio
    async def test_handle_mcp_config_stdio(self, registration_service, user_id):
        """Test STDIO server configuration."""
        session = registration_service._create_session(user_id)
        session.basic_info = {"tool_id": "test_tool"}

        data = {
            "mcp_server_type": MCPServerType.STDIO.value,
            "mcp_command": ["python", "-m", "mcp_server"],
            "mcp_protocol_version": "2024-11-05",
            "timeout_seconds": 30,
        }

        result = await registration_service._handle_mcp_config(session, data)

        assert result["success"] is True
        assert session.mcp_config is not None
        assert session.can_proceed is True

    @pytest.mark.asyncio
    async def test_handle_mcp_config_http(self, registration_service, user_id):
        """Test HTTP server configuration."""
        session = registration_service._create_session(user_id)
        session.basic_info = {"tool_id": "test_tool"}

        data = {
            "mcp_server_type": MCPServerType.HTTP.value,
            "mcp_endpoint": "http://localhost:8080",
            "mcp_protocol_version": "2024-11-05",
            "timeout_seconds": 30,
        }

        result = await registration_service._handle_mcp_config(session, data)

        assert result["success"] is True
        assert session.can_proceed is True

    @pytest.mark.asyncio
    async def test_handle_mcp_config_stdio_missing_command(self, registration_service, user_id):
        """Test STDIO without command fails."""
        session = registration_service._create_session(user_id)

        data = {
            "mcp_server_type": MCPServerType.STDIO.value,
            "mcp_protocol_version": "2024-11-05",
            "timeout_seconds": 30,
        }

        result = await registration_service._handle_mcp_config(session, data)

        assert result["success"] is False
        assert "mcp_command" in result["error"].lower()
        assert session.can_proceed is False


@pytest.mark.asyncio
class TestConnectionTestPhase:
    """Test Phase 3: Connection Testing."""

    async def test_handle_connection_test_skip(self, registration_service, user_id):
        """Test skipping connection test."""
        session = registration_service._create_session(user_id)
        session.basic_info = {"tool_id": "test_tool"}
        session.mcp_config = {"mcp_server_type": "stdio"}

        data = {"action": "skip"}

        result = await registration_service._handle_connection_test(session, data)

        assert result["success"] is True
        assert result["skipped"] is True
        assert session.can_proceed is True

    async def test_handle_connection_test_success(self, registration_service, user_id):
        """Test successful connection test."""
        session = registration_service._create_session(user_id)
        session.basic_info = {
            "tool_id": "test_tool",
            "name": "Test Tool",
            "category": "database",
            "tool_purpose": "orchestrator",
            "service_location": "orchestrator",
        }
        session.mcp_config = {
            "mcp_server_type": "stdio",
            "mcp_command": ["python", "-m", "mcp_server"],
            "mcp_protocol_version": "2024-11-05",
            "timeout_seconds": 30,
        }

        # Mock MCP client
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.initialize = AsyncMock(return_value={"version": "2024-11-05"})
        mock_client.list_tools = AsyncMock(return_value=[{"name": "test_tool"}])
        mock_client.disconnect = AsyncMock()

        registration_service.discovery_service.create_mcp_client.return_value = mock_client

        data = {"action": "test"}

        result = await registration_service._handle_connection_test(session, data)

        assert result["success"] is True
        assert "response_time_ms" in result
        assert session.connection_result["success"] is True


class TestSecurityConfigPhase:
    """Test Phase 4: Security Configuration."""

    @pytest.mark.asyncio
    async def test_handle_security_config_no_auth(self, registration_service, user_id):
        """Test security config without authentication."""
        session = registration_service._create_session(user_id)

        data = {
            "requires_authentication": False,
        }

        result = await registration_service._handle_security_config(session, data)

        assert result["success"] is True
        assert session.can_proceed is True

    @pytest.mark.asyncio
    async def test_handle_security_config_with_auth(self, registration_service, user_id):
        """Test security config with authentication."""
        session = registration_service._create_session(user_id)

        data = {
            "requires_authentication": True,
            "authentication_type": "api_key",
            "secret_name": "test_secret",
            "secret_value": "secret_value_123",
        }

        result = await registration_service._handle_security_config(session, data)

        assert result["success"] is True
        assert session.can_proceed is True

    @pytest.mark.asyncio
    async def test_handle_security_config_missing_secret(self, registration_service, user_id):
        """Test security config with auth but missing secret."""
        session = registration_service._create_session(user_id)

        data = {
            "requires_authentication": True,
            "authentication_type": "api_key",
            # Missing secret_name and secret_value
        }

        result = await registration_service._handle_security_config(session, data)

        assert result["success"] is False
        assert "secret" in result["error"].lower()
        assert session.can_proceed is False


class TestPermissionsPhase:
    """Test Phase 5: Permissions."""

    @pytest.mark.asyncio
    async def test_handle_permissions_success(self, registration_service, user_id):
        """Test successful permissions configuration."""
        session = registration_service._create_session(user_id)

        data = {
            "rate_limit_per_minute": 60,
            "max_concurrent_calls": 5,
            "health_check_interval_seconds": 300,
            "role_permissions": [],
        }

        result = await registration_service._handle_permissions(session, data)

        assert result["success"] is True
        assert session.can_proceed is True


class TestReviewPhase:
    """Test Phase 6: Review."""

    @pytest.mark.asyncio
    async def test_handle_review_confirm(self, registration_service, user_id):
        """Test review confirmation."""
        session = registration_service._create_session(user_id)

        data = {"action": "confirm"}

        result = await registration_service._handle_review(session, data)

        assert result["success"] is True
        assert result["action"] == "confirm"
        assert session.can_proceed is True

    @pytest.mark.asyncio
    async def test_handle_review_edit(self, registration_service, user_id):
        """Test review edit action."""
        session = registration_service._create_session(user_id)

        data = {"action": "edit"}

        result = await registration_service._handle_review(session, data)

        assert result["success"] is True
        assert result["action"] == "edit"
        assert session.can_proceed is False


class TestCommitPhase:
    """Test Phase 7: Commit."""

    @pytest.mark.asyncio
    async def test_handle_commit_success(self, registration_service, user_id):
        """Test successful commit."""
        session = registration_service._create_session(user_id)
        session.basic_info = {
            "tool_id": "test_tool",
            "name": "Test Tool",
            "category": ToolCategory.DATABASE.value,
            "tool_purpose": ToolPurpose.ORCHESTRATOR.value,
            "service_location": ServiceLocation.ORCHESTRATOR.value,
        }
        session.mcp_config = {
            "mcp_server_type": MCPServerType.STDIO.value,
            "mcp_command": ["python", "-m", "mcp_server"],
            "mcp_protocol_version": "2024-11-05",
            "timeout_seconds": 30,
        }
        session.security_config = {"requires_authentication": False}
        session.permissions_config = {
            "rate_limit_per_minute": 60,
            "max_concurrent_calls": 5,
            "health_check_interval_seconds": 300,
            "role_permissions": [],
        }

        # Mock tool creation
        mock_tool = MagicMock()
        mock_tool.id = uuid.uuid4()
        mock_tool.tool_id = "test_tool"
        mock_tool.name = "Test Tool"
        registration_service.tool_service.create_tool.return_value = mock_tool

        data = {"confirmed": True}

        result = await registration_service._handle_commit(session, data, user_id)

        assert result["success"] is True
        assert result["tool_id"] == mock_tool.id
        assert "registered successfully" in result["message"]

    @pytest.mark.asyncio
    async def test_handle_commit_not_confirmed(self, registration_service, user_id):
        """Test commit without confirmation."""
        session = registration_service._create_session(user_id)

        data = {"confirmed": False}

        result = await registration_service._handle_commit(session, data, user_id)

        assert result["success"] is False
        assert "Confirmation required" in result["error"]


@pytest.mark.asyncio
class TestProcessPhase:
    """Test main process_phase method."""

    async def test_process_phase_basic_info(self, registration_service, user_id):
        """Test processing basic info phase."""
        registration_service.tool_service.get_tool = AsyncMock(return_value=None)

        data = {
            "tool_id": "test_tool",
            "name": "Test Tool",
            "category": ToolCategory.DATABASE.value,
            "tool_purpose": ToolPurpose.ORCHESTRATOR.value,
            "service_location": ServiceLocation.ORCHESTRATOR.value,
        }

        session, result = await registration_service.process_phase(
            session_id=None,
            phase=ToolRegistrationPhase.BASIC_INFO,
            data=data,
            user_id=user_id,
        )

        assert session is not None
        assert result["success"] is True
        assert session.current_phase == ToolRegistrationPhase.MCP_CONFIG

    async def test_process_phase_invalid_first_phase(self, registration_service, user_id):
        """Test invalid first phase."""
        with pytest.raises(ValueError, match="First phase must be BASIC_INFO"):
            await registration_service.process_phase(
                session_id=None,
                phase=ToolRegistrationPhase.MCP_CONFIG,
                data={},
                user_id=user_id,
            )
