"""
Integration tests for Tools Admin API endpoints.

Tests CRUD operations, RBAC enforcement, and secret management.

P5-A20: Removed unused Session import (no direct DB operations in this file).
All tests use TestClient which is sync and doesn't require async migration.
"""

import os
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.orchestrator.app.main import app
from src.shared.auth import admin_required, get_current_user
from src.shared.auth.models import TokenPayload, UserRole


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user token payload."""
    user_id = str(uuid4())
    return TokenPayload(
        sub=user_id,
        user_id=user_id,
        username="admin",
        role=UserRole.ADMIN,
        exp=9999999999,
        iat=1000000000,
        token_type="access",
        iss="aio",
    )


@pytest.fixture
def mock_regular_user():
    """Create a mock regular user token payload."""
    user_id = str(uuid4())
    return TokenPayload(
        sub=user_id,
        user_id=user_id,
        username="user",
        role=UserRole.USER,
        exp=9999999999,
        iat=1000000000,
        token_type="access",
        iss="aio",
    )


@pytest.fixture
def authenticated_admin_client(mock_admin_user):
    """Create a test client with admin authentication."""

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
    from fastapi import HTTPException, status

    def mock_get_current_user():
        return mock_regular_user

    def mock_admin_required():
        # This should raise 403 for non-admin users
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[admin_required] = mock_admin_required

    with TestClient(app) as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def test_tool_data():
    """Sample tool data for testing."""
    return {
        "tool_id": f"test_elasticsearch_{uuid4().hex[:8]}",
        "name": "Test Elasticsearch",
        "description": "Test Elasticsearch search tool",
        "category": "database",
        "provider": "elastic",
        "tool_purpose": "retrieval",
        "service_location": "retrieval_service",
        "mcp_server_type": "http",
        "mcp_endpoint": "http://elasticsearch:9200",
        "mcp_protocol_version": "2024-11-05",
        "requires_authentication": True,
        "authentication_type": "api_key",
        "timeout_seconds": 30,
        "max_concurrent_calls": 5,
        "is_enabled": False,
        "tags": ["test", "elasticsearch"],
    }


class TestToolsAdminAPI:
    """Integration tests for Tools Admin API."""

    def test_create_tool_admin(self, authenticated_admin_client, test_tool_data):
        """Admin can create tool."""
        response = authenticated_admin_client.post(
            "/api/v1/admin/tools/",
            json=test_tool_data,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["tool_id"] == test_tool_data["tool_id"]
        assert data["name"] == test_tool_data["name"]
        assert data["is_enabled"] is False  # Default
        assert data["category"] == test_tool_data["category"]

    def test_create_tool_requires_admin(self, authenticated_user_client, test_tool_data):
        """Non-admin cannot create tool."""
        response = authenticated_user_client.post(
            "/api/v1/admin/tools/",
            json=test_tool_data,
        )
        assert response.status_code == 403

    def test_create_tool_duplicate_id(self, authenticated_admin_client, test_tool_data):
        """Creating tool with duplicate tool_id fails."""
        # Create first tool
        response1 = authenticated_admin_client.post(
            "/api/v1/admin/tools/",
            json=test_tool_data,
        )
        assert response1.status_code == 201

        # Try to create duplicate
        response2 = authenticated_admin_client.post(
            "/api/v1/admin/tools/",
            json=test_tool_data,
        )
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"].lower()

    def test_list_tools_admin(self, authenticated_admin_client, test_tool_data):
        """Admin can list all tools."""
        # Create a tool first
        create_response = authenticated_admin_client.post(
            "/api/v1/admin/tools/",
            json=test_tool_data,
        )
        assert create_response.status_code == 201

        # List tools
        response = authenticated_admin_client.get("/api/v1/admin/tools/")
        assert response.status_code == 200
        tools = response.json()
        assert isinstance(tools, list)
        assert len(tools) >= 1
        # Find our tool
        tool_ids = [t["tool_id"] for t in tools]
        assert test_tool_data["tool_id"] in tool_ids

    def test_list_tools_with_filters(self, authenticated_admin_client, test_tool_data):
        """Admin can filter tools by category and status."""
        # Create a tool
        create_response = authenticated_admin_client.post(
            "/api/v1/admin/tools/",
            json=test_tool_data,
        )
        assert create_response.status_code == 201

        # List with category filter
        response = authenticated_admin_client.get(
            "/api/v1/admin/tools/",
            params={"category": "database"},
        )
        assert response.status_code == 200
        tools = response.json()
        assert all(t["category"] == "database" for t in tools)

        # List enabled only
        response = authenticated_admin_client.get(
            "/api/v1/admin/tools/",
            params={"enabled_only": True},
        )
        assert response.status_code == 200
        tools = response.json()
        # Our test tool is disabled, so it shouldn't appear
        tool_ids = [t["tool_id"] for t in tools]
        assert test_tool_data["tool_id"] not in tool_ids

    def test_get_tool_admin(self, authenticated_admin_client, test_tool_data):
        """Admin can get tool details."""
        # Create a tool
        create_response = authenticated_admin_client.post(
            "/api/v1/admin/tools/",
            json=test_tool_data,
        )
        assert create_response.status_code == 201
        created_tool = create_response.json()

        # Get tool
        response = authenticated_admin_client.get(
            f"/api/v1/admin/tools/{test_tool_data['tool_id']}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tool_id"] == test_tool_data["tool_id"]
        assert data["id"] == created_tool["id"]

    def test_get_tool_not_found(self, authenticated_admin_client):
        """Getting nonexistent tool returns 404."""
        response = authenticated_admin_client.get("/api/v1/admin/tools/nonexistent_tool")
        assert response.status_code == 404

    def test_update_tool_admin(self, authenticated_admin_client, test_tool_data):
        """Admin can update tool."""
        # Create a tool
        create_response = authenticated_admin_client.post(
            "/api/v1/admin/tools/",
            json=test_tool_data,
        )
        assert create_response.status_code == 201

        # Update tool
        update_data = {
            "name": "Updated Tool Name",
            "description": "Updated description",
            "is_enabled": True,
        }
        response = authenticated_admin_client.put(
            f"/api/v1/admin/tools/{test_tool_data['tool_id']}",
            json=update_data,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Tool Name"
        assert data["description"] == "Updated description"
        assert data["is_enabled"] is True

    def test_delete_tool_admin(self, authenticated_admin_client, test_tool_data):
        """Admin can delete tool."""
        # Create a tool
        create_response = authenticated_admin_client.post(
            "/api/v1/admin/tools/",
            json=test_tool_data,
        )
        assert create_response.status_code == 201

        # Delete tool
        response = authenticated_admin_client.delete(
            f"/api/v1/admin/tools/{test_tool_data['tool_id']}"
        )
        assert response.status_code == 204

        # Verify deleted
        get_response = authenticated_admin_client.get(
            f"/api/v1/admin/tools/{test_tool_data['tool_id']}"
        )
        assert get_response.status_code == 404

    def test_enable_disable_tool(self, authenticated_admin_client, test_tool_data):
        """Admin can enable/disable tool."""
        # Create a tool
        create_response = authenticated_admin_client.post(
            "/api/v1/admin/tools/",
            json=test_tool_data,
        )
        assert create_response.status_code == 201
        assert create_response.json()["is_enabled"] is False

        # Enable tool
        enable_response = authenticated_admin_client.post(
            f"/api/v1/admin/tools/{test_tool_data['tool_id']}/enable"
        )
        assert enable_response.status_code == 200
        assert enable_response.json()["is_enabled"] is True

        # Disable tool
        disable_response = authenticated_admin_client.post(
            f"/api/v1/admin/tools/{test_tool_data['tool_id']}/disable"
        )
        assert disable_response.status_code == 200
        assert disable_response.json()["is_enabled"] is False

    def test_create_tool_secret(self, authenticated_admin_client, test_tool_data):
        """Admin can create tool secret."""
        # Set encryption key for tests
        test_key = "test_key_minimum_32_characters_for_aes256_encryption"
        with patch.dict(os.environ, {"TOOL_SECRETS_KEY": test_key}):
            # Create a tool
            create_response = authenticated_admin_client.post(
                "/api/v1/admin/tools/",
                json=test_tool_data,
            )
            assert create_response.status_code == 201
            tool_id = test_tool_data["tool_id"]

            # Create secret
            secret_data = {
                "secret_name": f"test_secret_{uuid4().hex[:8]}",
                "secret_type": "api_key",
                "secret_value": "super_secret_key_12345",
            }
            response = authenticated_admin_client.post(
                f"/api/v1/admin/tools/{tool_id}/secrets",
                json=secret_data,
            )
            assert response.status_code == 201
            data = response.json()
            assert data["secret_name"] == secret_data["secret_name"]
            assert data["secret_type"] == secret_data["secret_type"]
            # Encrypted value should never be exposed
            assert "encrypted_value" not in data or data.get("encrypted_value") == ""

    def test_delete_tool_secret(self, authenticated_admin_client, test_tool_data):
        """Admin can delete tool secret."""
        # Set encryption key for tests
        test_key = "test_key_minimum_32_characters_for_aes256_encryption"
        with patch.dict(os.environ, {"TOOL_SECRETS_KEY": test_key}):
            # Create a tool
            create_response = authenticated_admin_client.post(
                "/api/v1/admin/tools/",
                json=test_tool_data,
            )
            assert create_response.status_code == 201
            tool_id = test_tool_data["tool_id"]

            # Create secret
            secret_name = f"test_secret_{uuid4().hex[:8]}"
            secret_data = {
                "secret_name": secret_name,
                "secret_type": "api_key",
                "secret_value": "super_secret_key_12345",
            }
            create_secret_response = authenticated_admin_client.post(
                f"/api/v1/admin/tools/{tool_id}/secrets",
                json=secret_data,
            )
            assert create_secret_response.status_code == 201

            # Delete secret
            response = authenticated_admin_client.delete(
                f"/api/v1/admin/tools/{tool_id}/secrets/{secret_name}"
            )
            assert response.status_code == 204

    def test_create_tool_with_mcp_command(self, authenticated_admin_client, test_tool_data):
        """Tool with mcp_command list is stored and retrieved correctly."""
        tool_data = test_tool_data.copy()
        tool_data["mcp_server_type"] = "stdio"
        tool_data["mcp_command"] = ["python", "-m", "mcp_server", "--port", "8080"]
        tool_data.pop("mcp_endpoint", None)  # Remove endpoint for stdio

        # Create tool
        create_response = authenticated_admin_client.post(
            "/api/v1/admin/tools/",
            json=tool_data,
        )
        assert create_response.status_code == 201
        data = create_response.json()
        assert data["mcp_command"] == tool_data["mcp_command"]

        # Get tool and verify mcp_command
        get_response = authenticated_admin_client.get(f"/api/v1/admin/tools/{tool_data['tool_id']}")
        assert get_response.status_code == 200
        retrieved_data = get_response.json()
        assert retrieved_data["mcp_command"] == tool_data["mcp_command"]
