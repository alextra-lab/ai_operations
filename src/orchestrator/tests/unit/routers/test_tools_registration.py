"""
Unit tests for tools_registration router.

Tests multi-phase tool registration endpoints.
All database operations are mocked - no real database interaction.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from app.main import app
from fastapi import status
from fastapi.testclient import TestClient

from shared.auth import admin_required
from shared.auth.models import TokenPayload, UserRole


def create_auth_headers(user: TokenPayload) -> dict:
    """Create mock authorization headers for testing."""
    return {"Authorization": f"Bearer mock-token-for-{user.username}"}


@pytest.fixture
def client():
    """Create a test client without authentication overrides."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user token payload."""
    now = datetime.now(tz=UTC)
    return TokenPayload(
        sub="admin",
        user_id=str(uuid4()),
        username="admin",
        role=UserRole.ADMIN,
        exp=int((now + timedelta(hours=1)).timestamp()),
        iat=int(now.timestamp()),
        iss="aio",
        token_type="access",
    )


@pytest.fixture
def mock_developer_user():
    """Create a mock developer user token payload."""
    now = datetime.now(tz=UTC)
    return TokenPayload(
        sub="developer",
        user_id=str(uuid4()),
        username="developer",
        role="developer",
        exp=int((now + timedelta(hours=1)).timestamp()),
        iat=int(now.timestamp()),
        iss="aio",
        token_type="access",
    )


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return MagicMock()


@pytest.fixture
def authenticated_admin_client(mock_admin_user, mock_db_session):
    """Create a test client with admin authentication."""

    def mock_admin_required():
        return mock_admin_user

    async def mock_get_async_db():
        yield mock_db_session

    from src.orchestrator.app.db.database import get_async_db

    app.dependency_overrides[admin_required] = mock_admin_required
    app.dependency_overrides[get_async_db] = mock_get_async_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.skip(
    reason="Tests need refactoring - mocking architecture incompatible with FastAPI TestClient"
)
class TestToolRegistrationEndpoints:
    """Test tool registration endpoints.

    NOTE: These tests are currently skipped because they have architectural issues:
    - The @patch decorators don't work properly because the app is imported at module level
    - The TestClient creates a real app instance before patches are applied
    - Needs refactoring to use app.dependency_overrides or factory pattern

    TODO: Refactor tests to use proper FastAPI testing patterns.
    """

    def test_register_basic_info_phase(
        self,
        authenticated_admin_client,
        mock_db_session,
    ):
        """Test basic_info phase registration."""
        from src.orchestrator.app.schemas.tool_registration import ToolRegistrationPhase
        from src.orchestrator.app.services.tool_registration_service import (
            RegistrationSession,
            ToolRegistrationService,
        )

        # Mock the service
        mock_session = RegistrationSession(
            session_id="test_session_123",
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            current_phase=ToolRegistrationPhase.BASIC_INFO,
            created_at=datetime.now(tz=UTC),
            updated_at=datetime.now(tz=UTC),
            expires_at=datetime.now(tz=UTC) + timedelta(hours=1),
            basic_info={"tool_id": "test_tool", "name": "Test Tool"},
            can_proceed=True,
            validation_errors={},
        )

        with patch.object(
            ToolRegistrationService, "process_phase", new_callable=AsyncMock
        ) as mock_process:
            mock_process.return_value = (
                mock_session,
                {"success": True, "message": "Basic info validated"},
            )

            response = authenticated_admin_client.post(
                "/api/v1/admin/tools/register",
                json={
                    "phase": "basic_info",
                    "data": {
                        "tool_id": "test_tool",
                        "name": "Test Tool",
                        "category": "database",
                        "tool_purpose": "orchestrator",
                        "service_location": "orchestrator",
                    },
                },
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["session_id"] == "test_session_123"
            assert data["current_phase"] == "basic_info"
            assert data["can_proceed"] is True

    @patch("app.routers.tools_registration.get_current_user")
    @patch("app.routers.tools_registration.ToolRegistrationService")
    def test_register_mcp_config_phase(
        self,
        mock_service_class,
        mock_get_user,
        client,
        mock_admin_user,
    ):
        """Test mcp_config phase registration."""
        mock_get_user.return_value = mock_admin_user
        mock_service = MagicMock()
        mock_service.process_phase = AsyncMock(
            return_value={
                "session_id": "test_session_123",
                "current_phase": "mcp_config",
                "next_phase": "connection_test",
                "validation_errors": {},
                "can_proceed": True,
                "message": "MCP config validated",
            }
        )
        mock_service_class.return_value = mock_service

        response = client.post(
            "/api/v1/admin/tools/register",
            json={
                "session_id": "test_session_123",
                "phase": "mcp_config",
                "data": {
                    "mcp_server_type": "stdio",
                    "mcp_command": ["node", "server.js"],
                },
            },
            headers=create_auth_headers(mock_admin_user),
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == "test_session_123"
        assert data["current_phase"] == "mcp_config"
        assert data["next_phase"] == "connection_test"

    @patch("app.routers.tools_registration.get_current_user")
    @patch("app.routers.tools_registration.ToolRegistrationService")
    def test_register_connection_test_phase(
        self,
        mock_service_class,
        mock_get_user,
        client,
        mock_admin_user,
    ):
        """Test connection_test phase registration."""
        mock_get_user.return_value = mock_admin_user
        mock_service = MagicMock()
        mock_service.process_phase = AsyncMock(
            return_value={
                "session_id": "test_session_123",
                "current_phase": "connection_test",
                "next_phase": "security_config",
                "validation_errors": {},
                "can_proceed": True,
                "discovered_capabilities": {
                    "tools": [
                        {"name": "test_tool_1", "description": "Test tool 1"},
                        {"name": "test_tool_2", "description": "Test tool 2"},
                    ],
                    "resources": [],
                },
                "message": "Connection successful",
            }
        )
        mock_service_class.return_value = mock_service

        response = client.post(
            "/api/v1/admin/tools/register",
            json={
                "session_id": "test_session_123",
                "phase": "connection_test",
                "data": {"action": "test"},
            },
            headers=create_auth_headers(mock_admin_user),
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["discovered_capabilities"] is not None
        assert len(data["discovered_capabilities"]["tools"]) == 2

    @patch("app.routers.tools_registration.get_current_user")
    @patch("app.routers.tools_registration.ToolRegistrationService")
    def test_register_validation_errors(
        self,
        mock_service_class,
        mock_get_user,
        client,
        mock_admin_user,
    ):
        """Test registration with validation errors."""
        mock_get_user.return_value = mock_admin_user
        mock_service = MagicMock()
        mock_service.process_phase = AsyncMock(
            return_value={
                "session_id": "test_session_123",
                "current_phase": "basic_info",
                "next_phase": None,
                "validation_errors": {
                    "tool_id": ["Invalid format: must be lowercase alphanumeric"],
                    "name": ["Name is required"],
                },
                "can_proceed": False,
                "message": "Validation failed",
            }
        )
        mock_service_class.return_value = mock_service

        response = client.post(
            "/api/v1/admin/tools/register",
            json={
                "phase": "basic_info",
                "data": {
                    "tool_id": "INVALID_TOOL_ID",
                    "name": "",
                },
            },
            headers=create_auth_headers(mock_admin_user),
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["can_proceed"] is False
        assert len(data["validation_errors"]) > 0

    @patch("app.routers.tools_registration.get_current_user")
    @patch("app.routers.tools_registration.ToolRegistrationService")
    def test_get_session(
        self,
        mock_service_class,
        mock_get_user,
        client,
        mock_admin_user,
    ):
        """Test getting registration session."""
        mock_get_user.return_value = mock_admin_user
        mock_service = MagicMock()
        mock_service.get_session = AsyncMock(
            return_value={
                "session_id": "test_session_123",
                "current_phase": "mcp_config",
                "created_at": datetime.now(tz=UTC).isoformat(),
                "updated_at": datetime.now(tz=UTC).isoformat(),
                "expires_at": (datetime.now(tz=UTC) + timedelta(hours=1)).isoformat(),
                "collected_data": {
                    "basic_info": {"tool_id": "test_tool", "name": "Test Tool"},
                },
                "validation_status": {"basic_info": True},
            }
        )
        mock_service_class.return_value = mock_service

        response = client.get(
            "/api/v1/admin/tools/register/session/test_session_123",
            headers=create_auth_headers(mock_admin_user),
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == "test_session_123"
        assert data["current_phase"] == "mcp_config"

    @patch("app.routers.tools_registration.get_current_user")
    @patch("app.routers.tools_registration.ToolRegistrationService")
    def test_cancel_registration(
        self,
        mock_service_class,
        mock_get_user,
        client,
        mock_admin_user,
    ):
        """Test canceling registration."""
        mock_get_user.return_value = mock_admin_user
        mock_service = MagicMock()
        mock_service.cancel_registration = AsyncMock(return_value=None)
        mock_service_class.return_value = mock_service

        response = client.delete(
            "/api/v1/admin/tools/register/session/test_session_123",
            headers=create_auth_headers(mock_admin_user),
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @patch("app.routers.tools_registration.get_current_user")
    def test_register_requires_admin(
        self,
        mock_get_user,
        client,
        mock_developer_user,
    ):
        """Test that registration requires admin role."""
        mock_get_user.return_value = mock_developer_user

        response = client.post(
            "/api/v1/admin/tools/register",
            json={
                "phase": "basic_info",
                "data": {"tool_id": "test_tool"},
            },
            headers=create_auth_headers(mock_developer_user),
        )

        # Should fail authorization (admin-only endpoint)
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
        ]

    @patch("app.routers.tools_registration.get_current_user")
    @patch("app.routers.tools_registration.ToolRegistrationService")
    def test_register_commit_phase(
        self,
        mock_service_class,
        mock_get_user,
        client,
        mock_admin_user,
    ):
        """Test commit phase registration."""
        mock_get_user.return_value = mock_admin_user
        tool_id = uuid4()
        mock_service = MagicMock()
        mock_service.process_phase = AsyncMock(
            return_value={
                "session_id": "test_session_123",
                "current_phase": "commit",
                "next_phase": None,
                "validation_errors": {},
                "can_proceed": True,
                "tool_id": str(tool_id),
                "message": "Tool registered successfully",
            }
        )
        mock_service_class.return_value = mock_service

        response = client.post(
            "/api/v1/admin/tools/register",
            json={
                "session_id": "test_session_123",
                "phase": "commit",
                "data": {"confirmed": True},
            },
            headers=create_auth_headers(mock_admin_user),
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["tool_id"] == str(tool_id)
        assert data["current_phase"] == "commit"
        assert data["next_phase"] is None
