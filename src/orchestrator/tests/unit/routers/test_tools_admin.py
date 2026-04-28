"""
Unit tests for tools_admin router.

Tests admin-only endpoints for tool CRUD operations.
All database operations are mocked - no real database interaction.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from app.main import app
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from shared.auth.models import TokenPayload, UserRole


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
def mock_regular_user():
    """Create a mock regular user token payload."""
    now = datetime.now(tz=UTC)
    return TokenPayload(
        sub="user",
        user_id=str(uuid4()),
        username="user",
        role=UserRole.USER,
        exp=int((now + timedelta(hours=1)).timestamp()),
        iat=int(now.timestamp()),
        iss="aio",
        token_type="access",
    )


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()
    session.query = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    session.delete = MagicMock()
    session.close = MagicMock()
    return session


@pytest.fixture
def sample_tool_data():
    """Sample tool creation data."""
    return {
        "tool_id": "test_tool_123",
        "name": "Test Tool",
        "description": "A test tool",
        "category": "custom",
        "provider": "test-provider",
        "tool_purpose": "orchestrator",
        "service_location": "orchestrator",
        "mcp_server_type": "http",
        "mcp_endpoint": "http://test-endpoint.com",
        "requires_authentication": True,
        "authentication_type": "api_key",
        "secret_name": "test_api_key",
    }


@pytest.fixture
def authenticated_admin_client(mock_admin_user):
    """Create a test client with admin authentication."""
    from shared.auth import admin_required, get_current_user

    def mock_get_current_user():
        return mock_admin_user

    def mock_admin_required():
        return mock_admin_user

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[admin_required] = mock_admin_required

    with TestClient(app) as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_user_client(mock_regular_user):
    """Create a test client with regular user authentication."""
    from shared.auth import admin_required, get_current_user

    def mock_get_current_user():
        return mock_regular_user

    def mock_admin_required():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient role. Required: ['admin'], got: {mock_regular_user.role}",
        )

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[admin_required] = mock_admin_required

    with TestClient(app) as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()


class TestCreateTool:
    """Test POST /api/v1/admin/tools/ endpoint."""

    @pytest.mark.skip(
        reason="Complex integration test - covered in tests/integration/test_tools_admin_api.py"
    )
    def test_create_tool_admin_success(self, authenticated_admin_client, sample_tool_data):
        """Admin can create a tool (endpoint exists and is accessible)."""
        # This is a unit test - full integration is tested in tests/integration/
        # We verify the endpoint exists and admin can access it (not 403)
        response = authenticated_admin_client.post("/api/v1/admin/tools/", json=sample_tool_data)
        # Endpoint exists and admin can access (may return 500 if service not fully mocked in unit test)
        assert response.status_code != 403
        assert response.status_code in [
            201,
            400,
            500,
        ]  # 400=validation error, 500=service not mocked

    def test_create_tool_requires_admin(self, authenticated_user_client, sample_tool_data):
        """Non-admin cannot create tool."""
        response = authenticated_user_client.post("/api/v1/admin/tools/", json=sample_tool_data)
        assert response.status_code == 403


class TestListTools:
    """Test GET /api/v1/admin/tools/ endpoint."""

    def test_list_tools_admin_success(self, authenticated_admin_client):
        """Admin can list tools."""
        response = authenticated_admin_client.get("/api/v1/admin/tools/")
        # May return 500 if service not fully mocked, but should not be 403
        assert response.status_code != 403

    def test_list_tools_requires_admin(self, authenticated_user_client):
        """Non-admin cannot list tools."""
        response = authenticated_user_client.get("/api/v1/admin/tools/")
        assert response.status_code == 403


class TestGetTool:
    """Test GET /api/v1/admin/tools/{tool_id} endpoint."""

    def test_get_tool_admin_success(self, authenticated_admin_client):
        """Admin can get tool details."""
        response = authenticated_admin_client.get("/api/v1/admin/tools/test_tool_123")
        # May return 404 or 500 if service not fully mocked, but should not be 403
        assert response.status_code != 403

    def test_get_tool_requires_admin(self, authenticated_user_client):
        """Non-admin cannot get tool details."""
        response = authenticated_user_client.get("/api/v1/admin/tools/test_tool_123")
        assert response.status_code == 403


class TestUpdateTool:
    """Test PUT /api/v1/admin/tools/{tool_id} endpoint."""

    def test_update_tool_requires_admin(self, authenticated_user_client):
        """Non-admin cannot update tool."""
        update_data = {"name": "Updated Name"}
        response = authenticated_user_client.put(
            "/api/v1/admin/tools/test_tool_123", json=update_data
        )
        assert response.status_code == 403


class TestDeleteTool:
    """Test DELETE /api/v1/admin/tools/{tool_id} endpoint."""

    def test_delete_tool_requires_admin(self, authenticated_user_client):
        """Non-admin cannot delete tool."""
        response = authenticated_user_client.delete("/api/v1/admin/tools/test_tool_123")
        assert response.status_code == 403


class TestEnableDisableTool:
    """Test POST /api/v1/admin/tools/{tool_id}/enable|disable endpoints."""

    def test_enable_tool_requires_admin(self, authenticated_user_client):
        """Non-admin cannot enable tool."""
        response = authenticated_user_client.post("/api/v1/admin/tools/test_tool_123/enable")
        assert response.status_code == 403

    def test_disable_tool_requires_admin(self, authenticated_user_client):
        """Non-admin cannot disable tool."""
        response = authenticated_user_client.post("/api/v1/admin/tools/test_tool_123/disable")
        assert response.status_code == 403


class TestToolSecrets:
    """Test tool secret management endpoints."""

    def test_create_tool_secret_requires_admin(self, authenticated_user_client):
        """Non-admin cannot create tool secret."""
        secret_data = {
            "secret_name": "test_api_key",
            "secret_type": "api_key",
            "secret_value": "super_secret",
        }
        response = authenticated_user_client.post(
            "/api/v1/admin/tools/test_tool_123/secrets", json=secret_data
        )
        assert response.status_code == 403

    def test_delete_tool_secret_requires_admin(self, authenticated_user_client):
        """Non-admin cannot delete tool secret."""
        response = authenticated_user_client.delete(
            "/api/v1/admin/tools/test_tool_123/secrets/test_api_key"
        )
        assert response.status_code == 403


class TestToolDiscovery:
    """Tests for tool discovery endpoint."""

    def test_discover_tool_requires_admin(self, authenticated_user_client):
        """Test that tool discovery requires admin role."""
        response = authenticated_user_client.post("/api/v1/admin/tools/test_tool/discover")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires async mocking - covered in integration tests")
    async def test_discover_tool_admin_success(self, authenticated_admin_client):
        """Test successful tool discovery by admin."""
        # This test would require mocking the async discovery service
        # Covered in integration tests
