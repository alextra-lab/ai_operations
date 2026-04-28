"""
Unit tests for ToolPermissionService.

Tests permission CRUD operations and permission checking.
All database operations are mocked - no real database interaction.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.db.models import Tool, ToolPermission
from app.services.tool_permission_service import ToolPermissionService


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
def permission_service(mock_db_session):
    """Create ToolPermissionService instance with mocked dependencies."""
    return ToolPermissionService(mock_db_session)


@pytest.fixture
def sample_tool_model():
    """Sample tool model for testing."""
    return Tool(
        id=uuid4(),
        tool_id="test_tool_123",
        name="Test Tool",
        description="Test tool description",
        category="database",
        tool_purpose="retrieval",
        service_location="retrieval_service",
        mcp_server_type="http",
        mcp_protocol_version="2024-11-05",
        is_enabled=False,
    )


@pytest.fixture
def sample_permission_model(sample_tool_model):
    """Sample permission model for testing."""
    return ToolPermission(
        id=uuid4(),
        tool_id=sample_tool_model.id,
        role="user",
        can_view=True,
        can_use=True,
        can_configure=False,
        max_calls_per_hour=100,
        max_calls_per_day=1000,
        created_by=uuid4(),
    )


class TestToolPermissionServiceGrant:
    """Test ToolPermissionService.grant_permission method."""

    @pytest.mark.asyncio
    async def test_grant_permission_success(
        self, permission_service, mock_db_session, sample_tool_model
    ):
        """Successfully grant permission to a role."""
        tool_id = sample_tool_model.id
        user_id = uuid4()

        # Mock tool exists
        mock_tool_result = MagicMock()
        mock_tool_result.scalar_one_or_none.return_value = sample_tool_model

        # Mock permission doesn't exist
        mock_perm_result = MagicMock()
        mock_perm_result.scalar_one_or_none.return_value = None

        # Setup execute mock to return different results
        mock_db_session.execute.side_effect = [mock_tool_result, mock_perm_result]

        # Mock permission creation
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        # Grant permission
        permission = await permission_service.grant_permission(
            tool_id=tool_id,
            role="user",
            can_view=True,
            can_use=True,
            max_calls_per_hour=100,
            created_by_user_id=user_id,
        )

        # Verify database operations
        assert mock_db_session.execute.call_count == 2  # Tool query + Permission query
        assert mock_db_session.add.called
        assert mock_db_session.commit.called
        assert mock_db_session.refresh.called

        # Verify permission is a ToolPermission instance
        assert isinstance(permission, ToolPermission)

    @pytest.mark.asyncio
    async def test_grant_permission_updates_existing(
        self,
        permission_service,
        mock_db_session,
        sample_tool_model,
        sample_permission_model,
    ):
        """Granting permission for existing role updates it."""
        tool_id = sample_tool_model.id
        user_id = uuid4()

        # Mock tool exists
        mock_tool_result = MagicMock()
        mock_tool_result.scalar_one_or_none.return_value = sample_tool_model

        # Mock permission exists
        mock_perm_result = MagicMock()
        mock_perm_result.scalar_one_or_none.return_value = sample_permission_model

        # Setup execute mock
        mock_db_session.execute.side_effect = [mock_tool_result, mock_perm_result]

        # Grant permission with updated values
        permission = await permission_service.grant_permission(
            tool_id=tool_id,
            role="user",
            can_view=True,
            can_use=True,  # Changed from original
            can_configure=True,  # Changed from original
            max_calls_per_hour=200,  # Changed from original
            created_by_user_id=user_id,
        )

        # Verify permission was updated
        assert permission.can_use is True
        assert permission.can_configure is True
        assert permission.max_calls_per_hour == 200
        assert mock_db_session.commit.called
        assert mock_db_session.refresh.called
        # Should NOT add new permission
        assert not mock_db_session.add.called

    @pytest.mark.asyncio
    async def test_grant_permission_tool_not_found(self, permission_service, mock_db_session):
        """Granting permission for nonexistent tool raises ValueError."""
        tool_id = uuid4()

        # Mock tool doesn't exist
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Attempt to grant permission
        with pytest.raises(ValueError, match="not found"):
            await permission_service.grant_permission(
                tool_id=tool_id,
                role="user",
            )


class TestToolPermissionServiceCheck:
    """Test ToolPermissionService.check_permission method."""

    @pytest.mark.asyncio
    async def test_check_permission_use_allowed(
        self,
        permission_service,
        mock_db_session,
        sample_permission_model,
    ):
        """Check permission returns True when role has use permission."""
        tool_id = sample_permission_model.tool_id
        role = sample_permission_model.role

        # Mock permission exists with can_use=True
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_permission_model
        mock_db_session.execute.return_value = mock_result

        # Check permission
        result = await permission_service.check_permission(
            tool_id=tool_id, role=role, permission_type="use"
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_check_permission_use_denied(
        self, permission_service, mock_db_session, sample_permission_model
    ):
        """Check permission returns False when role doesn't have use permission."""
        tool_id = sample_permission_model.tool_id
        role = sample_permission_model.role
        # Update permission to deny use
        sample_permission_model.can_use = False

        # Mock permission exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_permission_model
        mock_db_session.execute.return_value = mock_result

        # Check permission
        result = await permission_service.check_permission(
            tool_id=tool_id, role=role, permission_type="use"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_check_permission_not_found(self, permission_service, mock_db_session):
        """Check permission returns False when permission doesn't exist."""
        tool_id = uuid4()
        role = "user"

        # Mock permission doesn't exist
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Check permission
        result = await permission_service.check_permission(
            tool_id=tool_id, role=role, permission_type="use"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_check_permission_view(
        self, permission_service, mock_db_session, sample_permission_model
    ):
        """Check permission returns correct value for view permission."""
        tool_id = sample_permission_model.tool_id
        role = sample_permission_model.role

        # Mock permission exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_permission_model
        mock_db_session.execute.return_value = mock_result

        # Check view permission
        result = await permission_service.check_permission(
            tool_id=tool_id, role=role, permission_type="view"
        )

        assert result is True  # can_view is True in fixture

    @pytest.mark.asyncio
    async def test_check_permission_configure(
        self, permission_service, mock_db_session, sample_permission_model
    ):
        """Check permission returns correct value for configure permission."""
        tool_id = sample_permission_model.tool_id
        role = sample_permission_model.role

        # Mock permission exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_permission_model
        mock_db_session.execute.return_value = mock_result

        # Check configure permission
        result = await permission_service.check_permission(
            tool_id=tool_id, role=role, permission_type="configure"
        )

        assert result is False  # can_configure is False in fixture

    @pytest.mark.asyncio
    async def test_check_permission_invalid_type(
        self, permission_service, mock_db_session, sample_permission_model
    ):
        """Check permission returns False for invalid permission type."""
        tool_id = sample_permission_model.tool_id
        role = sample_permission_model.role

        # Mock permission exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_permission_model
        mock_db_session.execute.return_value = mock_result

        # Check invalid permission type
        result = await permission_service.check_permission(
            tool_id=tool_id, role=role, permission_type="invalid"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_check_permission_admin_bypass(self, permission_service, mock_db_session):
        """Admin role bypasses permission checks and returns True."""
        tool_id = uuid4()
        role = "admin"

        # Admin bypass should return True without database query
        result = await permission_service.check_permission(
            tool_id=tool_id, role=role, permission_type="use"
        )

        assert result is True
        # Should not query database for admin
        assert not mock_db_session.execute.called


class TestToolPermissionServiceCheckForRoles:
    """Test ToolPermissionService.check_permission_for_roles method."""

    @pytest.mark.asyncio
    async def test_check_permission_for_roles_admin_bypass(
        self, permission_service, mock_db_session
    ):
        """Admin role in roles list bypasses permission checks."""
        tool_id = uuid4()
        roles = ["analyst", "admin", "user"]

        # Admin bypass should return True without database query
        result = await permission_service.check_permission_for_roles(
            tool_id=tool_id, roles=roles, permission_type="use"
        )

        assert result is True
        # Should not query database for admin
        assert not mock_db_session.execute.called

    @pytest.mark.asyncio
    async def test_check_permission_for_roles_one_role_has_permission(
        self, permission_service, mock_db_session, sample_permission_model
    ):
        """Check permission returns True if any role has permission."""
        tool_id = sample_permission_model.tool_id
        roles = ["analyst", "user", "viewer"]

        # Mock permission exists for "user" role
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_permission_model]
        mock_db_session.execute.return_value = mock_result

        # Check permission
        result = await permission_service.check_permission_for_roles(
            tool_id=tool_id, roles=roles, permission_type="use"
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_check_permission_for_roles_no_permissions(
        self, permission_service, mock_db_session
    ):
        """Check permission returns False when no roles have permission."""
        tool_id = uuid4()
        roles = ["analyst", "viewer"]

        # Mock no permissions found
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        # Check permission
        result = await permission_service.check_permission_for_roles(
            tool_id=tool_id, roles=roles, permission_type="use"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_check_permission_for_roles_empty_list(self, permission_service, mock_db_session):
        """Check permission returns False for empty roles list."""
        tool_id = uuid4()
        roles = []

        # Should return False without querying
        result = await permission_service.check_permission_for_roles(
            tool_id=tool_id, roles=roles, permission_type="use"
        )

        assert result is False
        assert not mock_db_session.execute.called

    @pytest.mark.asyncio
    async def test_check_permission_for_roles_multiple_permissions(
        self, permission_service, mock_db_session, sample_tool_model
    ):
        """Check permission works with multiple roles having permissions."""
        tool_id = sample_tool_model.id

        # Create permissions for multiple roles
        perm1 = ToolPermission(
            id=uuid4(),
            tool_id=tool_id,
            role="analyst",
            can_view=True,
            can_use=False,  # Analyst can view but not use
            can_configure=False,
        )
        perm2 = ToolPermission(
            id=uuid4(),
            tool_id=tool_id,
            role="user",
            can_view=True,
            can_use=True,  # User can use
            can_configure=False,
        )

        # Mock query returns both permissions
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [perm1, perm2]
        mock_db_session.execute.return_value = mock_result

        # Check use permission - should return True because user role has it
        result = await permission_service.check_permission_for_roles(
            tool_id=tool_id, roles=["analyst", "user"], permission_type="use"
        )

        assert result is True

        # Check configure permission - should return False (neither has it)
        result = await permission_service.check_permission_for_roles(
            tool_id=tool_id, roles=["analyst", "user"], permission_type="configure"
        )

        assert result is False


class TestToolPermissionServiceList:
    """Test ToolPermissionService.list_permissions method."""

    @pytest.mark.asyncio
    async def test_list_permissions_success(
        self, permission_service, mock_db_session, sample_tool_model
    ):
        """Successfully list permissions for a tool."""
        tool_id = sample_tool_model.id

        # Create multiple permissions
        perm1 = ToolPermission(
            id=uuid4(),
            tool_id=tool_id,
            role="user",
            can_view=True,
            can_use=True,
        )
        perm2 = ToolPermission(
            id=uuid4(),
            tool_id=tool_id,
            role="admin",
            can_view=True,
            can_use=True,
            can_configure=True,
        )

        # Mock query returns multiple permissions
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [perm1, perm2]
        mock_db_session.execute.return_value = mock_result

        # List permissions
        permissions = await permission_service.list_permissions(tool_id)

        # Verify results
        assert len(permissions) == 2
        assert permissions[0] == perm1
        assert permissions[1] == perm2
        assert mock_db_session.execute.called

    @pytest.mark.asyncio
    async def test_list_permissions_empty(
        self, permission_service, mock_db_session, sample_tool_model
    ):
        """List permissions returns empty list when no permissions exist."""
        tool_id = sample_tool_model.id

        # Mock query returns empty list
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        # List permissions
        permissions = await permission_service.list_permissions(tool_id)

        # Verify results
        assert len(permissions) == 0
        assert isinstance(permissions, list)


class TestToolPermissionServiceGet:
    """Test ToolPermissionService.get_permission method."""

    @pytest.mark.asyncio
    async def test_get_permission_success(
        self,
        permission_service,
        mock_db_session,
        sample_permission_model,
    ):
        """Successfully get specific permission."""
        tool_id = sample_permission_model.tool_id
        role = sample_permission_model.role

        # Mock permission exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_permission_model
        mock_db_session.execute.return_value = mock_result

        # Get permission
        permission = await permission_service.get_permission(tool_id, role)

        # Verify results
        assert permission == sample_permission_model
        assert permission.role == role

    @pytest.mark.asyncio
    async def test_get_permission_not_found(self, permission_service, mock_db_session):
        """Get nonexistent permission returns None."""
        tool_id = uuid4()
        role = "user"

        # Mock permission doesn't exist
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Get permission
        permission = await permission_service.get_permission(tool_id, role)

        # Verify results
        assert permission is None


class TestToolPermissionServiceRevoke:
    """Test ToolPermissionService.revoke_permission method."""

    @pytest.mark.asyncio
    async def test_revoke_permission_success(
        self,
        permission_service,
        mock_db_session,
        sample_permission_model,
    ):
        """Successfully revoke permission."""
        tool_id = sample_permission_model.tool_id
        role = sample_permission_model.role

        # Mock permission exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_permission_model
        mock_db_session.execute.return_value = mock_result

        # Revoke permission
        result = await permission_service.revoke_permission(tool_id, role)

        # Verify results
        assert result is True
        assert mock_db_session.delete.called
        assert mock_db_session.commit.called

    @pytest.mark.asyncio
    async def test_revoke_permission_not_found(self, permission_service, mock_db_session):
        """Revoking nonexistent permission returns False."""
        tool_id = uuid4()
        role = "user"

        # Mock permission doesn't exist
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Revoke permission
        result = await permission_service.revoke_permission(tool_id, role)

        # Verify results
        assert result is False
        assert not mock_db_session.delete.called


class TestToolPermissionServiceGetAllowedTools:
    """Test ToolPermissionService.get_allowed_tools_for_role method."""

    @pytest.mark.asyncio
    async def test_get_allowed_tools_admin_sees_all(
        self, permission_service, mock_db_session, sample_tool_model
    ):
        """Admin role sees all enabled tools."""
        tool_id_1 = uuid4()
        tool_id_2 = uuid4()

        # Create enabled tools
        Tool(
            id=tool_id_1,
            tool_id="tool_1",
            name="Tool 1",
            category="database",
            tool_purpose="retrieval",
            service_location="retrieval_service",
            mcp_server_type="http",
            mcp_protocol_version="2024-11-05",
            is_enabled=True,
        )
        Tool(
            id=tool_id_2,
            tool_id="tool_2",
            name="Tool 2",
            category="custom",
            tool_purpose="orchestrator",
            service_location="orchestrator",
            mcp_server_type="http",
            mcp_protocol_version="2024-11-05",
            is_enabled=True,
        )

        # Mock query returns all enabled tools
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [tool_id_1, tool_id_2]
        mock_db_session.execute.return_value = mock_result

        # Get allowed tools for admin
        tool_ids = await permission_service.get_allowed_tools_for_role(
            role="admin", enabled_only=True
        )

        # Verify results - admin sees all enabled tools
        assert len(tool_ids) == 2
        assert tool_id_1 in tool_ids
        assert tool_id_2 in tool_ids

    @pytest.mark.asyncio
    async def test_get_allowed_tools_user_sees_permitted_only(
        self, permission_service, mock_db_session
    ):
        """Non-admin role sees only tools they have permission to use."""
        tool_id_1 = uuid4()
        tool_id_2 = uuid4()

        # Create permission for tool_1 only
        ToolPermission(
            id=uuid4(),
            tool_id=tool_id_1,
            role="user",
            can_view=True,
            can_use=True,  # User can use tool_1
            can_configure=False,
        )

        # Mock permission query returns tool_1
        mock_perm_result = MagicMock()
        mock_perm_result.scalars.return_value.all.return_value = [tool_id_1]

        # Mock tool query returns enabled tool_1
        mock_tool_result = MagicMock()
        mock_tool_result.scalars.return_value.all.return_value = [tool_id_1]

        # Setup execute mock to return different results
        mock_db_session.execute.side_effect = [mock_perm_result, mock_tool_result]

        # Get allowed tools for user
        tool_ids = await permission_service.get_allowed_tools_for_role(
            role="user", enabled_only=True
        )

        # Verify results - user sees only tool_1
        assert len(tool_ids) == 1
        assert tool_id_1 in tool_ids
        assert tool_id_2 not in tool_ids

    @pytest.mark.asyncio
    async def test_get_allowed_tools_user_no_permissions(self, permission_service, mock_db_session):
        """User with no tool permissions gets empty list."""
        # Mock permission query returns empty
        mock_perm_result = MagicMock()
        mock_perm_result.scalars.return_value.all.return_value = []

        mock_db_session.execute.return_value = mock_perm_result

        # Get allowed tools for user
        tool_ids = await permission_service.get_allowed_tools_for_role(
            role="user", enabled_only=True
        )

        # Verify results - empty list
        assert len(tool_ids) == 0
        assert isinstance(tool_ids, list)

    @pytest.mark.asyncio
    async def test_get_allowed_tools_admin_disabled_only(self, permission_service, mock_db_session):
        """Admin with enabled_only=False sees all tools."""
        tool_id_1 = uuid4()
        tool_id_2 = uuid4()

        # Mock query returns all tools (no enabled filter)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [tool_id_1, tool_id_2]
        mock_db_session.execute.return_value = mock_result

        # Get allowed tools for admin (all tools)
        tool_ids = await permission_service.get_allowed_tools_for_role(
            role="admin", enabled_only=False
        )

        # Verify results
        assert len(tool_ids) == 2
        assert tool_id_1 in tool_ids
        assert tool_id_2 in tool_ids

    @pytest.mark.asyncio
    async def test_get_allowed_tools_user_enabled_filter(self, permission_service, mock_db_session):
        """User with permissions sees only enabled tools."""
        tool_id_1 = uuid4()
        tool_id_2 = uuid4()

        # Mock permission query returns both tool IDs
        mock_perm_result = MagicMock()
        mock_perm_result.scalars.return_value.all.return_value = [tool_id_1, tool_id_2]

        # Mock tool query returns only enabled tool_1
        mock_tool_result = MagicMock()
        mock_tool_result.scalars.return_value.all.return_value = [tool_id_1]

        # Setup execute mock
        mock_db_session.execute.side_effect = [mock_perm_result, mock_tool_result]

        # Get allowed tools for user (enabled only)
        tool_ids = await permission_service.get_allowed_tools_for_role(
            role="user", enabled_only=True
        )

        # Verify results - only enabled tool_1
        assert len(tool_ids) == 1
        assert tool_id_1 in tool_ids
        assert tool_id_2 not in tool_ids


class TestToolPermissionServiceGetAllowedToolsForRoles:
    """Test ToolPermissionService.get_allowed_tools_for_roles method."""

    @pytest.mark.asyncio
    async def test_get_allowed_tools_for_roles_admin_bypass(
        self, permission_service, mock_db_session
    ):
        """Admin role in roles list bypasses and returns all tools."""
        tool_id_1 = uuid4()
        tool_id_2 = uuid4()

        # Mock query returns all enabled tools
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [tool_id_1, tool_id_2]
        mock_db_session.execute.return_value = mock_result

        # Get allowed tools with admin in roles
        tool_ids = await permission_service.get_allowed_tools_for_roles(
            roles=["analyst", "admin", "user"], enabled_only=True
        )

        # Verify results - admin sees all enabled tools
        assert len(tool_ids) == 2
        assert tool_id_1 in tool_ids
        assert tool_id_2 in tool_ids

    @pytest.mark.asyncio
    async def test_get_allowed_tools_for_roles_multiple_roles_union(
        self, permission_service, mock_db_session
    ):
        """Multiple roles return union of allowed tools."""
        tool_id_1 = uuid4()
        tool_id_2 = uuid4()
        tool_id_3 = uuid4()

        # Create permissions: analyst has tool_1, user has tool_2
        ToolPermission(
            id=uuid4(),
            tool_id=tool_id_1,
            role="analyst",
            can_view=True,
            can_use=True,
        )
        ToolPermission(
            id=uuid4(),
            tool_id=tool_id_2,
            role="user",
            can_view=True,
            can_use=True,
        )

        # Mock permission query returns both tool IDs
        mock_perm_result = MagicMock()
        mock_perm_result.scalars.return_value.all.return_value = [tool_id_1, tool_id_2]

        # Mock tool query returns enabled tools
        mock_tool_result = MagicMock()
        mock_tool_result.scalars.return_value.all.return_value = [tool_id_1, tool_id_2]

        # Setup execute mock
        mock_db_session.execute.side_effect = [mock_perm_result, mock_tool_result]

        # Get allowed tools for multiple roles
        tool_ids = await permission_service.get_allowed_tools_for_roles(
            roles=["analyst", "user"], enabled_only=True
        )

        # Verify results - union of both roles' permissions
        assert len(tool_ids) == 2
        assert tool_id_1 in tool_ids
        assert tool_id_2 in tool_ids
        assert tool_id_3 not in tool_ids

    @pytest.mark.asyncio
    async def test_get_allowed_tools_for_roles_empty_list(
        self, permission_service, mock_db_session
    ):
        """Empty roles list returns empty tool list."""
        tool_ids = await permission_service.get_allowed_tools_for_roles(roles=[], enabled_only=True)

        assert len(tool_ids) == 0
        assert isinstance(tool_ids, list)
        assert not mock_db_session.execute.called

    @pytest.mark.asyncio
    async def test_get_allowed_tools_for_roles_no_permissions(
        self, permission_service, mock_db_session
    ):
        """Roles with no permissions return empty list."""
        # Mock permission query returns empty
        mock_perm_result = MagicMock()
        mock_perm_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_perm_result

        # Get allowed tools
        tool_ids = await permission_service.get_allowed_tools_for_roles(
            roles=["analyst", "viewer"], enabled_only=True
        )

        # Verify results - empty list
        assert len(tool_ids) == 0
        assert isinstance(tool_ids, list)
