"""
Integration tests for Tool Permissions API endpoints.

Tests permission CRUD operations, RBAC enforcement, and rate limits.

P5-A20: Migrated to async database patterns (ADR-022).
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.orchestrator.app.db.database import AsyncSessionLocal, init_db
from src.orchestrator.app.main import app
from src.shared.auth import UnifiedAuthManager
from src.shared.auth.models import User, UserRole

auth_manager = UnifiedAuthManager()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a real async database session for testing."""
    await init_db()
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    """Create a real admin user in the database with proper password hashing."""
    # Use timestamp to ensure unique username
    timestamp = int(datetime.now(UTC).timestamp() * 1000000)
    username = f"admin_{timestamp}"
    email = f"admin_{timestamp}@example.com"
    password = "adminpassword"  # Known password for testing

    user = User(
        id=uuid4(),
        username=username,
        full_name="Admin User",
        email=email,
        hashed_password=auth_manager.get_password_hash(password),
        role=UserRole.ADMIN,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Store password for later use in authentication
    user._test_password = password  # type: ignore[attr-defined]

    yield user

    # Cleanup: rollback in fixture handles cleanup automatically


@pytest_asyncio.fixture
async def regular_user(db_session: AsyncSession):
    """Create a real regular user in the database with proper password hashing."""
    # Use timestamp to ensure unique username
    timestamp = int(datetime.now(UTC).timestamp() * 1000000)
    username = f"user_{timestamp}"
    email = f"user_{timestamp}@example.com"
    password = "userpassword"  # Known password for testing

    user = User(
        id=uuid4(),
        username=username,
        full_name="Regular User",
        email=email,
        hashed_password=auth_manager.get_password_hash(password),
        role=UserRole.USER,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Store password for later use in authentication
    user._test_password = password  # type: ignore[attr-defined]

    yield user

    # Cleanup: rollback in fixture handles cleanup automatically


@pytest.fixture
def admin_token(admin_user):
    """Get a real JWT token for admin user by authenticating."""
    client = TestClient(app)
    response = client.post(
        "/auth/token",
        data={
            "username": admin_user.username,
            "password": admin_user._test_password,  # type: ignore[attr-defined]
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def user_token(regular_user):
    """Get a real JWT token for regular user by authenticating."""
    client = TestClient(app)
    response = client.post(
        "/auth/token",
        data={
            "username": regular_user.username,
            "password": regular_user._test_password,  # type: ignore[attr-defined]
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


class AuthenticatedTestClient:
    """Wrapper around TestClient that automatically adds Authorization header."""

    def __init__(self, client: TestClient, token: str):
        self.client = client
        self.headers = {"Authorization": f"Bearer {token}"}

    def get(self, url: str, **kwargs):
        """GET request with auth header."""
        kwargs.setdefault("headers", {}).update(self.headers)
        return self.client.get(url, **kwargs)

    def post(self, url: str, **kwargs):
        """POST request with auth header."""
        kwargs.setdefault("headers", {}).update(self.headers)
        return self.client.post(url, **kwargs)

    def put(self, url: str, **kwargs):
        """PUT request with auth header."""
        kwargs.setdefault("headers", {}).update(self.headers)
        return self.client.put(url, **kwargs)

    def delete(self, url: str, **kwargs):
        """DELETE request with auth header."""
        kwargs.setdefault("headers", {}).update(self.headers)
        return self.client.delete(url, **kwargs)


@pytest.fixture
def authenticated_admin_client(admin_token):
    """Create a test client with real admin authentication."""
    client = TestClient(app)
    return AuthenticatedTestClient(client, admin_token)


@pytest.fixture
def authenticated_user_client(user_token):
    """Create a test client with real user authentication."""
    client = TestClient(app)
    return AuthenticatedTestClient(client, user_token)


@pytest.fixture
def test_tool_data():
    """Sample tool data for testing."""
    return {
        "tool_id": f"test_permission_tool_{uuid4().hex[:8]}",
        "name": "Test Permission Tool",
        "description": "Tool for permission testing",
        "category": "database",
        "provider": "test",
        "tool_purpose": "retrieval",
        "service_location": "retrieval_service",
        "mcp_server_type": "http",
        "mcp_endpoint": "http://test:8080",
        "mcp_protocol_version": "2024-11-05",
        "requires_authentication": False,
        "timeout_seconds": 30,
        "max_concurrent_calls": 5,
        "is_enabled": False,
        "tags": ["test", "permission"],
    }


@pytest.fixture
def test_tool(authenticated_admin_client, test_tool_data):
    """Create a test tool and return it."""
    response = authenticated_admin_client.post(
        "/api/v1/admin/tools/",
        json=test_tool_data,
    )
    assert response.status_code == 201
    return response.json()


class TestToolPermissionsAPI:
    """Integration tests for Tool Permissions API."""

    def test_grant_permission_admin(self, authenticated_admin_client, test_tool):
        """Admin can grant permission to role."""
        tool_id = test_tool["tool_id"]
        permission_data = {
            "role": "user",
            "can_view": True,
            "can_use": True,
            "can_configure": False,
            "max_calls_per_hour": 100,
            "max_calls_per_day": 1000,
        }

        response = authenticated_admin_client.post(
            f"/api/v1/admin/tools/{tool_id}/permissions",
            json=permission_data,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == permission_data["role"]
        assert data["can_view"] is True
        assert data["can_use"] is True
        assert data["can_configure"] is False
        assert data["max_calls_per_hour"] == 100
        assert data["max_calls_per_day"] == 1000
        assert "id" in data
        assert "tool_id" in data

    def test_grant_permission_requires_admin(self, authenticated_user_client, test_tool):
        """Non-admin cannot grant permission."""
        tool_id = test_tool["tool_id"]
        permission_data = {
            "role": "user",
            "can_use": True,
        }

        response = authenticated_user_client.post(
            f"/api/v1/admin/tools/{tool_id}/permissions",
            json=permission_data,
        )
        assert response.status_code == 403

    def test_grant_permission_nonexistent_tool(self, authenticated_admin_client):
        """Granting permission for nonexistent tool returns 404."""
        permission_data = {
            "role": "user",
            "can_use": True,
        }

        response = authenticated_admin_client.post(
            "/api/v1/admin/tools/nonexistent_tool/permissions",
            json=permission_data,
        )
        assert response.status_code == 404

    def test_list_permissions_admin(self, authenticated_admin_client, test_tool):
        """Admin can list all permissions for a tool."""
        tool_id = test_tool["tool_id"]

        # Grant a few permissions
        permissions = [
            {"role": "user", "can_use": True},
            {"role": "corpus_admin", "can_view": True, "can_use": True},
        ]

        for perm_data in permissions:
            response = authenticated_admin_client.post(
                f"/api/v1/admin/tools/{tool_id}/permissions",
                json=perm_data,
            )
            assert response.status_code == 201

        # List permissions
        response = authenticated_admin_client.get(f"/api/v1/admin/tools/{tool_id}/permissions")
        assert response.status_code == 200
        perms = response.json()
        assert isinstance(perms, list)
        assert len(perms) >= 2
        roles = [p["role"] for p in perms]
        assert "user" in roles
        assert "corpus_admin" in roles

    def test_list_permissions_empty(self, authenticated_admin_client, test_tool):
        """Listing permissions for tool with no permissions returns empty list."""
        tool_id = test_tool["tool_id"]

        response = authenticated_admin_client.get(f"/api/v1/admin/tools/{tool_id}/permissions")
        assert response.status_code == 200
        perms = response.json()
        assert isinstance(perms, list)
        assert len(perms) == 0

    def test_get_permission_admin(self, authenticated_admin_client, test_tool):
        """Admin can get specific permission."""
        tool_id = test_tool["tool_id"]
        permission_data = {
            "role": "use_case_publisher",
            "can_view": True,
            "can_use": True,
            "can_configure": True,
            "max_calls_per_hour": 200,
        }

        # Grant permission
        grant_response = authenticated_admin_client.post(
            f"/api/v1/admin/tools/{tool_id}/permissions",
            json=permission_data,
        )
        assert grant_response.status_code == 201

        # Get permission
        response = authenticated_admin_client.get(
            f"/api/v1/admin/tools/{tool_id}/permissions/use_case_publisher"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "use_case_publisher"
        assert data["can_view"] is True
        assert data["can_use"] is True
        assert data["can_configure"] is True
        assert data["max_calls_per_hour"] == 200

    def test_get_permission_not_found(self, authenticated_admin_client, test_tool):
        """Getting nonexistent permission returns 404."""
        tool_id = test_tool["tool_id"]

        response = authenticated_admin_client.get(
            f"/api/v1/admin/tools/{tool_id}/permissions/nonexistent_role"
        )
        assert response.status_code == 404

    def test_update_permission_admin(self, authenticated_admin_client, test_tool):
        """Admin can update permission."""
        tool_id = test_tool["tool_id"]

        # Grant initial permission
        initial_data = {
            "role": "user",
            "can_view": True,
            "can_use": False,
            "max_calls_per_hour": 50,
        }
        grant_response = authenticated_admin_client.post(
            f"/api/v1/admin/tools/{tool_id}/permissions",
            json=initial_data,
        )
        assert grant_response.status_code == 201

        # Update permission
        update_data = {
            "role": "user",
            "can_view": True,
            "can_use": True,  # Changed
            "can_configure": True,  # Added
            "max_calls_per_hour": 100,  # Changed
            "max_calls_per_day": 500,  # Added
        }
        response = authenticated_admin_client.put(
            f"/api/v1/admin/tools/{tool_id}/permissions/user",
            json=update_data,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["can_use"] is True  # Updated
        assert data["can_configure"] is True  # Updated
        assert data["max_calls_per_hour"] == 100  # Updated
        assert data["max_calls_per_day"] == 500  # Updated

    def test_update_permission_role_mismatch(self, authenticated_admin_client, test_tool):
        """Updating permission with mismatched role returns 400."""
        tool_id = test_tool["tool_id"]

        update_data = {
            "role": "different_role",
            "can_use": True,
        }

        response = authenticated_admin_client.put(
            f"/api/v1/admin/tools/{tool_id}/permissions/user",
            json=update_data,
        )
        assert response.status_code == 400
        assert "role in path must match" in response.json()["detail"].lower()

    def test_revoke_permission_admin(self, authenticated_admin_client, test_tool):
        """Admin can revoke permission."""
        tool_id = test_tool["tool_id"]

        # Grant permission
        permission_data = {
            "role": "user",
            "can_use": True,
        }
        grant_response = authenticated_admin_client.post(
            f"/api/v1/admin/tools/{tool_id}/permissions",
            json=permission_data,
        )
        assert grant_response.status_code == 201

        # Verify permission exists
        get_response = authenticated_admin_client.get(
            f"/api/v1/admin/tools/{tool_id}/permissions/user"
        )
        assert get_response.status_code == 200

        # Revoke permission
        response = authenticated_admin_client.delete(
            f"/api/v1/admin/tools/{tool_id}/permissions/user"
        )
        assert response.status_code == 204

        # Verify permission is gone
        get_response = authenticated_admin_client.get(
            f"/api/v1/admin/tools/{tool_id}/permissions/user"
        )
        assert get_response.status_code == 404

    def test_revoke_permission_not_found(self, authenticated_admin_client, test_tool):
        """Revoking nonexistent permission returns 404."""
        tool_id = test_tool["tool_id"]

        response = authenticated_admin_client.delete(
            f"/api/v1/admin/tools/{tool_id}/permissions/nonexistent_role"
        )
        assert response.status_code == 404

    def test_grant_permission_updates_existing(self, authenticated_admin_client, test_tool):
        """Granting permission for existing role updates it."""
        tool_id = test_tool["tool_id"]

        # Grant initial permission
        initial_data = {
            "role": "user",
            "can_view": True,
            "can_use": False,
            "max_calls_per_hour": 50,
        }
        grant_response = authenticated_admin_client.post(
            f"/api/v1/admin/tools/{tool_id}/permissions",
            json=initial_data,
        )
        assert grant_response.status_code == 201
        initial_permission = grant_response.json()
        initial_id = initial_permission["id"]

        # Grant again with different values (should update)
        update_data = {
            "role": "user",
            "can_view": True,
            "can_use": True,  # Changed
            "max_calls_per_hour": 100,  # Changed
        }
        update_response = authenticated_admin_client.post(
            f"/api/v1/admin/tools/{tool_id}/permissions",
            json=update_data,
        )
        assert update_response.status_code == 201
        updated_permission = update_response.json()
        # Same ID (updated, not created)
        assert updated_permission["id"] == initial_id
        assert updated_permission["can_use"] is True
        assert updated_permission["max_calls_per_hour"] == 100

    def test_permission_rate_limits(self, authenticated_admin_client, test_tool):
        """Permission rate limits are stored correctly."""
        tool_id = test_tool["tool_id"]
        permission_data = {
            "role": "user",
            "can_use": True,
            "max_calls_per_hour": 100,
            "max_calls_per_day": 1000,
        }

        response = authenticated_admin_client.post(
            f"/api/v1/admin/tools/{tool_id}/permissions",
            json=permission_data,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["max_calls_per_hour"] == 100
        assert data["max_calls_per_day"] == 1000

    def test_permission_defaults(self, authenticated_admin_client, test_tool):
        """Permission defaults are applied correctly."""
        tool_id = test_tool["tool_id"]
        # Grant with minimal data (should use defaults)
        permission_data = {
            "role": "user",
        }

        response = authenticated_admin_client.post(
            f"/api/v1/admin/tools/{tool_id}/permissions",
            json=permission_data,
        )
        assert response.status_code == 201
        data = response.json()
        # Defaults from ToolPermissionCreate schema
        assert data["can_view"] is True
        assert data["can_use"] is False
        assert data["can_configure"] is False
        assert data["max_calls_per_hour"] is None
        assert data["max_calls_per_day"] is None
