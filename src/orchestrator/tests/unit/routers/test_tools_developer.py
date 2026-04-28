"""
Unit tests for tools_developer router.

Tests developer-facing endpoints for tool discovery and listing.
All database operations are mocked - no real database interaction.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.main import app
from app.schemas.tool import (
    MCPServerType,
    ServiceLocation,
    ToolCategory,
    ToolPurpose,
)
from app.schemas.tool import (
    Tool as ToolSchema,
)
from fastapi import status
from fastapi.testclient import TestClient

from shared.auth.models import TokenPayload, UserRole


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user token payload."""
    now = datetime.now(tz=UTC)
    return TokenPayload(
        sub="admin",
        user_id=str(uuid4()),
        roles=[UserRole.ADMIN.value],
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
        roles=[UserRole.USER.value],
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
        roles=[UserRole.USE_CASE_PUBLISHER.value],  # Developer role
        exp=int((now + timedelta(hours=1)).timestamp()),
        iat=int(now.timestamp()),
        iss="aio",
        token_type="access",
    )


@pytest.fixture
def authenticated_admin_client(mock_admin_user):
    """Create a test client with admin authentication."""
    from shared.auth import get_current_user

    def mock_get_current_user():
        return mock_admin_user

    app.dependency_overrides[get_current_user] = mock_get_current_user

    with TestClient(app) as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_user_client(mock_regular_user):
    """Create a test client with regular user authentication."""
    from shared.auth import get_current_user

    def mock_get_current_user():
        return mock_regular_user

    app.dependency_overrides[get_current_user] = mock_get_current_user

    with TestClient(app) as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_developer_client(mock_developer_user):
    """Create a test client with developer authentication."""
    from shared.auth import get_current_user

    def mock_get_current_user():
        return mock_developer_user

    app.dependency_overrides[get_current_user] = mock_get_current_user

    with TestClient(app) as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()


class TestListAvailableTools:
    """Test GET /api/v1/tools/available endpoint."""

    @patch("app.routers.tools_developer.ToolPermissionService")
    @patch("app.routers.tools_developer.ToolService")
    def test_list_available_tools_admin_sees_all(
        self,
        mock_tool_service_class,
        mock_permission_service_class,
        authenticated_admin_client,
    ):
        """Admin role sees all enabled tools."""
        # Setup mocks
        mock_permission_service = MagicMock()
        mock_permission_service_class.return_value = mock_permission_service

        mock_tool_service = MagicMock()
        mock_tool_service_class.return_value = mock_tool_service

        tool_id_1 = uuid4()
        tool_id_2 = uuid4()

        # Admin bypasses permissions - returns all tool IDs
        mock_permission_service.get_allowed_tools_for_roles = AsyncMock(
            return_value=[tool_id_1, tool_id_2]
        )

        from app.schemas.tool import ToolListItem

        mock_tool_service.list_tools = AsyncMock(
            return_value=[
                ToolListItem(
                    id=tool_id_1,
                    tool_id="tool_1",
                    name="Tool 1",
                    description="Test tool 1",
                    category=ToolCategory.DATABASE,
                    is_enabled=True,
                    is_healthy=True,
                    requires_authentication=False,
                ),
                ToolListItem(
                    id=tool_id_2,
                    tool_id="tool_2",
                    name="Tool 2",
                    description="Test tool 2",
                    category=ToolCategory.CUSTOM,
                    is_enabled=True,
                    is_healthy=True,
                    requires_authentication=True,
                ),
            ]
        )

        response = authenticated_admin_client.get("/api/v1/tools/available")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

        # Verify permission service was called with admin roles
        mock_permission_service.get_allowed_tools_for_roles.assert_called_once_with(
            roles=[UserRole.ADMIN.value], enabled_only=True
        )

        # Verify tool service was called
        mock_tool_service.list_tools.assert_called_once_with(
            category=None, enabled_only=True, healthy_only=False
        )

    @patch("app.routers.tools_developer.ToolPermissionService")
    @patch("app.routers.tools_developer.ToolService")
    def test_list_available_tools_user_sees_permitted_only(
        self,
        mock_tool_service_class,
        mock_permission_service_class,
        authenticated_user_client,
    ):
        """Regular user sees only tools they have permission to use."""
        # Setup mocks
        mock_permission_service = MagicMock()
        mock_permission_service_class.return_value = mock_permission_service

        mock_tool_service = MagicMock()
        mock_tool_service_class.return_value = mock_tool_service

        tool_id_1 = uuid4()
        tool_id_2 = uuid4()
        tool_id_3 = uuid4()

        # User only has permission for tool_1
        mock_permission_service.get_allowed_tools_for_roles = AsyncMock(return_value=[tool_id_1])

        from app.schemas.tool import ToolListItem

        # Service returns 3 tools, but user only has permission for 1
        mock_tool_service.list_tools = AsyncMock(
            return_value=[
                ToolListItem(
                    id=tool_id_1,
                    tool_id="tool_1",
                    name="Tool 1",
                    description="Test tool 1",
                    category=ToolCategory.DATABASE,
                    is_enabled=True,
                    is_healthy=True,
                    requires_authentication=False,
                ),
                ToolListItem(
                    id=tool_id_2,
                    tool_id="tool_2",
                    name="Tool 2",
                    description="Test tool 2",
                    category=ToolCategory.CUSTOM,
                    is_enabled=True,
                    is_healthy=True,
                    requires_authentication=True,
                ),
                ToolListItem(
                    id=tool_id_3,
                    tool_id="tool_3",
                    name="Tool 3",
                    description="Test tool 3",
                    category=ToolCategory.VECTOR_DB,
                    is_enabled=True,
                    is_healthy=True,
                    requires_authentication=False,
                ),
            ]
        )

        response = authenticated_user_client.get("/api/v1/tools/available")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["tool_id"] == "tool_1"

        # Verify permission service was called with user role
        mock_permission_service.get_allowed_tools_for_roles.assert_called_once_with(
            roles=[UserRole.USER.value], enabled_only=True
        )

    @patch("app.routers.tools_developer.ToolPermissionService")
    @patch("app.routers.tools_developer.ToolService")
    def test_list_available_tools_category_filter(
        self,
        mock_tool_service_class,
        mock_permission_service_class,
        authenticated_user_client,
    ):
        """Category filter works correctly."""
        # Setup mocks
        mock_permission_service = MagicMock()
        mock_permission_service_class.return_value = mock_permission_service

        mock_tool_service = MagicMock()
        mock_tool_service_class.return_value = mock_tool_service

        tool_id_1 = uuid4()

        mock_permission_service.get_allowed_tools_for_roles = AsyncMock(return_value=[tool_id_1])

        from app.schemas.tool import ToolListItem

        mock_tool_service.list_tools = AsyncMock(
            return_value=[
                ToolListItem(
                    id=tool_id_1,
                    tool_id="tool_1",
                    name="Tool 1",
                    description="Test tool 1",
                    category=ToolCategory.DATABASE,
                    is_enabled=True,
                    is_healthy=True,
                    requires_authentication=False,
                ),
            ]
        )

        response = authenticated_user_client.get("/api/v1/tools/available?category=database")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1

        # Verify category filter was passed to tool service
        mock_tool_service.list_tools.assert_called_once_with(
            category=ToolCategory.DATABASE, enabled_only=True, healthy_only=False
        )

    @patch("app.routers.tools_developer.ToolPermissionService")
    def test_list_available_tools_no_permissions(
        self, mock_permission_service_class, authenticated_user_client
    ):
        """User with no tool permissions gets empty list."""
        # Setup mocks
        mock_permission_service = MagicMock()
        mock_permission_service_class.return_value = mock_permission_service

        # User has no allowed tools
        mock_permission_service.get_allowed_tools_for_roles = AsyncMock(return_value=[])

        response = authenticated_user_client.get("/api/v1/tools/available")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


class TestGetToolDetails:
    """Test GET /api/v1/tools/{tool_id}/details endpoint."""

    @patch("app.routers.tools_developer.ToolPermissionService")
    @patch("app.routers.tools_developer.ToolService")
    @patch("app.routers.tools_developer.Tool.model_validate")
    def test_get_tool_details_admin_success(
        self,
        mock_model_validate,
        mock_tool_service_class,
        mock_permission_service_class,
        authenticated_admin_client,
    ):
        """Admin can view any tool details."""
        # Setup mocks
        mock_tool_service = MagicMock()
        mock_tool_service_class.return_value = mock_tool_service

        tool_uuid = uuid4()

        # Create a mock Tool instance
        mock_tool = MagicMock()
        mock_tool.id = tool_uuid
        mock_tool.tool_id = "test_tool"
        mock_tool.name = "Test Tool"
        mock_tool.description = "A test tool"

        mock_tool_service.get_tool = AsyncMock(return_value=mock_tool)

        # Mock Tool.model_validate to return a Pydantic model-like object
        mock_model_validate.return_value = ToolSchema(
            id=tool_uuid,
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            category=ToolCategory.DATABASE,
            tool_purpose=ToolPurpose.RETRIEVAL,
            service_location=ServiceLocation.RETRIEVAL_SERVICE,
            mcp_server_type=MCPServerType.HTTP,
            mcp_protocol_version="2024-11-05",
            is_enabled=True,
            is_healthy=True,
            last_health_check=None,
            requires_authentication=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            created_by=None,
            updated_by=None,
        )

        response = authenticated_admin_client.get("/api/v1/tools/test_tool/details")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["tool_id"] == "test_tool"
        assert data["name"] == "Test Tool"

        # Admin bypasses permission checks - permission service should not be instantiated
        mock_permission_service_class.assert_not_called()

    @patch("app.routers.tools_developer.ToolPermissionService")
    @patch("app.routers.tools_developer.ToolService")
    @patch("app.routers.tools_developer.Tool.model_validate")
    def test_get_tool_details_user_with_permission(
        self,
        mock_model_validate,
        mock_tool_service_class,
        mock_permission_service_class,
        authenticated_user_client,
    ):
        """User with view or use permission can view tool details."""
        # Setup mocks
        mock_tool_service = MagicMock()
        mock_tool_service_class.return_value = mock_tool_service

        mock_permission_service = MagicMock()
        mock_permission_service_class.return_value = mock_permission_service

        tool_uuid = uuid4()

        # Create a mock Tool instance
        mock_tool = MagicMock()
        mock_tool.id = tool_uuid
        mock_tool.tool_id = "test_tool"
        mock_tool.name = "Test Tool"
        mock_tool.description = "A test tool"

        mock_tool_service.get_tool = AsyncMock(return_value=mock_tool)

        # User has view permission
        async def check_permission_for_roles_side_effect(tool_id, roles, permission_type):
            """Mock permission check - returns True for view, False for others."""
            return permission_type == "view"

        mock_permission_service.check_permission_for_roles = AsyncMock(
            side_effect=check_permission_for_roles_side_effect
        )

        # Mock Tool.model_validate to return a Pydantic model-like object
        mock_model_validate.return_value = ToolSchema(
            id=tool_uuid,
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            category=ToolCategory.DATABASE,
            tool_purpose=ToolPurpose.RETRIEVAL,
            service_location=ServiceLocation.RETRIEVAL_SERVICE,
            mcp_server_type=MCPServerType.HTTP,
            mcp_protocol_version="2024-11-05",
            is_enabled=True,
            is_healthy=True,
            last_health_check=None,
            requires_authentication=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            created_by=None,
            updated_by=None,
        )

        response = authenticated_user_client.get("/api/v1/tools/test_tool/details")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["tool_id"] == "test_tool"

        # Verify permission checks were made
        assert mock_permission_service.check_permission_for_roles.call_count == 2

    @patch("app.routers.tools_developer.ToolPermissionService")
    @patch("app.routers.tools_developer.ToolService")
    def test_get_tool_details_user_no_permission(
        self,
        mock_tool_service_class,
        mock_permission_service_class,
        authenticated_user_client,
    ):
        """User without permission gets 403."""
        # Setup mocks
        mock_tool_service = MagicMock()
        mock_tool_service_class.return_value = mock_tool_service

        mock_permission_service = MagicMock()
        mock_permission_service_class.return_value = mock_permission_service

        tool_uuid = uuid4()

        # Create a mock Tool instance
        mock_tool = MagicMock()
        mock_tool.id = tool_uuid
        mock_tool.tool_id = "test_tool"

        mock_tool_service.get_tool = AsyncMock(return_value=mock_tool)

        # User has no permissions
        mock_permission_service.check_permission_for_roles = AsyncMock(return_value=False)

        response = authenticated_user_client.get("/api/v1/tools/test_tool/details")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Access denied" in response.json()["detail"]

    @patch("app.routers.tools_developer.ToolService")
    def test_get_tool_details_tool_not_found(
        self, mock_tool_service_class, authenticated_user_client
    ):
        """Tool not found returns 404."""
        # Setup mocks
        mock_tool_service = MagicMock()
        mock_tool_service_class.return_value = mock_tool_service

        mock_tool_service.get_tool = AsyncMock(return_value=None)

        response = authenticated_user_client.get("/api/v1/tools/nonexistent/details")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()
