"""
Unit tests for admin user roles router (RBAC V2) using mocks.

Tests admin-only endpoints for managing user role memberships.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from shared.auth.models import TokenPayload
from src.orchestrator.app.routers.admin_user_roles import (
    UpdateUserRolesRequest,
    add_user_role,
    get_user,
    get_user_roles,
    remove_user_role,
    require_admin_or_role_admin,
    update_user_roles,
)


@pytest.fixture
def admin_token():
    """Create a valid admin token payload."""
    now = datetime.now(tz=UTC)
    return TokenPayload(
        sub="admin",
        user_id=str(uuid4()),
        roles=["admin"],  # Multi-role support per ADR-060
        exp=int((now + timedelta(hours=1)).timestamp()),
        iat=int(now.timestamp()),
        iss="aio",
        token_type="access",
    )


@pytest.fixture
def role_admin_token():
    """Create a valid role_admin token payload."""
    now = datetime.now(tz=UTC)
    return TokenPayload(
        sub="role_admin",
        user_id=str(uuid4()),
        roles=["user", "role_admin"],  # Multi-role support per ADR-060
        scopes=[],
        exp=int((now + timedelta(hours=1)).timestamp()),
        iat=int(now.timestamp()),
        iss="aio",
        token_type="access",
    )


@pytest.fixture
def user_token():
    """Create a valid user token payload."""
    now = datetime.now(tz=UTC)
    return TokenPayload(
        sub="user",
        user_id=str(uuid4()),
        roles=["user"],  # Multi-role support per ADR-060
        exp=int((now + timedelta(hours=1)).timestamp()),
        iat=int(now.timestamp()),
        iss="aio",
        token_type="access",
    )


@pytest.fixture
def mock_async_db():
    """Create a mock async database session."""
    return AsyncMock()


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return uuid4()


@pytest.fixture
def mock_user():
    """Create a mock user object."""
    user = Mock()
    user.id = uuid4()
    user.role = "user"
    return user


class TestRequireAdminOrRoleAdmin:
    """Test require_admin_or_role_admin helper function."""

    def test_admin_user_passes(self, admin_token):
        """Admin user passes the check."""
        # Should not raise
        require_admin_or_role_admin(admin_token)

    def test_role_admin_user_passes(self, role_admin_token):
        """Role admin user passes the check."""
        # Should not raise
        require_admin_or_role_admin(role_admin_token)

    def test_non_admin_user_raises(self, user_token):
        """Non-admin user raises 403."""
        with pytest.raises(HTTPException) as exc_info:
            require_admin_or_role_admin(user_token)
        assert exc_info.value.status_code == 403


class TestGetUser:
    """Test get_user endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_returns_user_details(
        self, admin_token, mock_async_db, sample_user_id, mock_user
    ):
        """Get user details by ID."""
        from datetime import UTC, datetime

        mock_user.id = sample_user_id
        mock_user.username = "testuser"
        mock_user.full_name = "Test User"
        mock_user.email = "test@example.com"
        mock_user.role = "user"
        mock_user.is_active = True
        mock_user.user_metadata = {}
        mock_user.created_at = datetime.now(UTC)
        mock_user.updated_at = datetime.now(UTC)
        mock_user.last_login = datetime.now(UTC)

        # Mock user query
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = mock_user
        mock_async_db.execute.return_value = mock_user_result

        response = await get_user(
            user_id=sample_user_id, db=mock_async_db, current_user=admin_token
        )

        assert response["id"] == str(sample_user_id)
        assert response["username"] == "testuser"
        assert response["full_name"] == "Test User"
        assert response["email"] == "test@example.com"
        assert response["role"] == "user"
        assert response["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, admin_token, mock_async_db, sample_user_id):
        """User not found raises 404."""
        # Mock user query to return None
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = None
        mock_async_db.execute.return_value = mock_user_result

        with pytest.raises(HTTPException) as exc_info:
            await get_user(user_id=sample_user_id, db=mock_async_db, current_user=admin_token)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_user_requires_admin(self, user_token, mock_async_db, sample_user_id):
        """Non-admin user cannot access."""
        with pytest.raises(HTTPException) as exc_info:
            await get_user(user_id=sample_user_id, db=mock_async_db, current_user=user_token)
        assert exc_info.value.status_code == 403


class TestGetUserRoles:
    """Test get_user_roles endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_roles_returns_all_roles(
        self, admin_token, mock_async_db, sample_user_id, mock_user
    ):
        """Get all roles assigned to user."""
        mock_user.role = "admin"

        # Mock user query (first execute call for user lookup)
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = mock_user

        # Mock role memberships query (second execute call)
        membership1 = Mock(
            role="admin", granted_by=None, created_at=datetime.now(UTC), metadata_json={}
        )
        membership2 = Mock(
            role="threat_hunting",
            granted_by=uuid4(),
            created_at=datetime.now(UTC),
            metadata_json={},
        )
        membership3 = Mock(
            role="team:csirt", granted_by=uuid4(), created_at=datetime.now(UTC), metadata_json={}
        )

        mock_membership_result = Mock()
        mock_membership_result.scalars.return_value.all.return_value = [
            membership1,
            membership2,
            membership3,
        ]

        # Mock execute to return user on first call, memberships on second
        mock_async_db.execute.side_effect = [mock_user_result, mock_membership_result]

        response = await get_user_roles(
            user_id=sample_user_id, db=mock_async_db, current_user=admin_token
        )

        assert response.user_id == sample_user_id
        assert "admin" in response.system_roles
        assert "threat_hunting" in response.grouping_roles
        assert "team:csirt" in response.teams
        assert len(response.all_roles) == 3

    @pytest.mark.asyncio
    async def test_get_user_roles_user_not_found(self, admin_token, mock_async_db, sample_user_id):
        """User not found raises 404."""
        # Mock user query to return None
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = None
        mock_async_db.execute.return_value = mock_user_result

        with pytest.raises(HTTPException) as exc_info:
            await get_user_roles(user_id=sample_user_id, db=mock_async_db, current_user=admin_token)
        assert exc_info.value.status_code == 404


class TestUpdateUserRoles:
    """Test update_user_roles endpoint."""

    @pytest.mark.asyncio
    async def test_update_user_roles_success(
        self, admin_token, mock_async_db, sample_user_id, mock_user
    ):
        """Successfully update user roles."""
        mock_user.role = "user"

        # Mock user query (first execute call)
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = mock_user

        # Mock existing memberships query (second execute call)
        existing_membership = Mock(role="old_role")
        mock_membership_result = Mock()
        mock_membership_result.scalars.return_value.all.return_value = [existing_membership]

        # Mock execute to return user on first call, memberships on second
        mock_async_db.execute.side_effect = [mock_user_result, mock_membership_result]

        request = UpdateUserRolesRequest(
            system_roles=["admin"],
            grouping_roles=["threat_hunting"],
            teams=["team:csirt"],
        )

        # Mock get_user_roles call at end
        async def mock_get_user_roles(*args, **kwargs):
            from src.orchestrator.app.routers.admin_user_roles import UserRolesResponse

            return UserRolesResponse(
                user_id=sample_user_id,
                system_roles=["admin"],
                grouping_roles=["threat_hunting"],
                teams=["team:csirt"],
                all_roles=[],
            )

        # Patch get_user_roles
        import src.orchestrator.app.routers.admin_user_roles as admin_user_roles_module

        original_get = admin_user_roles_module.get_user_roles
        admin_user_roles_module.get_user_roles = mock_get_user_roles

        try:
            response = await update_user_roles(
                user_id=sample_user_id,
                request=request,
                db=mock_async_db,
                current_user=admin_token,
            )

            assert response.user_id == sample_user_id
            assert "admin" in response.system_roles
            assert "threat_hunting" in response.grouping_roles
            assert "team:csirt" in response.teams

            # Verify user.role was updated
            assert mock_user.role == "admin"
            # Verify commit was called
            mock_async_db.commit.assert_called_once()
        finally:
            admin_user_roles_module.get_user_roles = original_get

    @pytest.mark.asyncio
    async def test_update_user_roles_multiple_system_roles_raises(
        self, admin_token, mock_async_db, sample_user_id, mock_user
    ):
        """Multiple system roles raises 400."""
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = mock_user
        mock_async_db.execute.return_value = mock_user_result

        request = UpdateUserRolesRequest(
            system_roles=["admin", "corpus_admin"],
            grouping_roles=[],
            teams=[],
        )

        with pytest.raises(HTTPException) as exc_info:
            await update_user_roles(
                user_id=sample_user_id,
                request=request,
                db=mock_async_db,
                current_user=admin_token,
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_update_user_roles_invalid_system_role_raises(
        self, admin_token, mock_async_db, sample_user_id, mock_user
    ):
        """Invalid system role raises 400."""
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = mock_user
        mock_async_db.execute.return_value = mock_user_result

        request = UpdateUserRolesRequest(
            system_roles=["invalid_role"],
            grouping_roles=[],
            teams=[],
        )

        with pytest.raises(HTTPException) as exc_info:
            await update_user_roles(
                user_id=sample_user_id,
                request=request,
                db=mock_async_db,
                current_user=admin_token,
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_update_user_roles_invalid_team_format_raises(
        self, admin_token, mock_async_db, sample_user_id, mock_user
    ):
        """Invalid team format raises 400."""
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = mock_user
        mock_async_db.execute.return_value = mock_user_result

        request = UpdateUserRolesRequest(
            system_roles=["user"],
            grouping_roles=[],
            teams=["invalid_team"],
        )

        with pytest.raises(HTTPException) as exc_info:
            await update_user_roles(
                user_id=sample_user_id,
                request=request,
                db=mock_async_db,
                current_user=admin_token,
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_update_user_roles_preserves_admin_role_in_audit_log(
        self, admin_token, mock_async_db, sample_user_id, mock_user
    ):
        """Verify admin user's role is preserved in audit logs (variable shadowing fix)."""
        from unittest.mock import patch

        mock_user.role = "user"

        # Mock user query (first execute call)
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = mock_user

        # Mock existing memberships query (second execute call)
        mock_membership_result = Mock()
        mock_membership_result.scalars.return_value.all.return_value = []

        mock_async_db.execute.side_effect = [mock_user_result, mock_membership_result]

        request = UpdateUserRolesRequest(
            system_roles=["corpus_admin"],  # Different from admin_token.role
            grouping_roles=["threat_hunting"],
            teams=[],
        )

        # Mock get_user_roles call at end
        async def mock_get_user_roles(*args, **kwargs):
            from src.orchestrator.app.routers.admin_user_roles import UserRolesResponse

            return UserRolesResponse(
                user_id=sample_user_id,
                system_roles=["corpus_admin"],
                grouping_roles=["threat_hunting"],
                teams=[],
                all_roles=[],
            )

        # Patch get_user_roles
        import src.orchestrator.app.routers.admin_user_roles as admin_user_roles_module

        original_get = admin_user_roles_module.get_user_roles
        admin_user_roles_module.get_user_roles = mock_get_user_roles

        # Capture logger.info calls
        with patch("src.orchestrator.app.routers.admin_user_roles.logger") as mock_logger:
            try:
                await update_user_roles(
                    user_id=sample_user_id,
                    request=request,
                    db=mock_async_db,
                    current_user=admin_token,
                )

                # Verify logger.info was called
                assert mock_logger.info.called

                # Get the call arguments
                call_args = mock_logger.info.call_args
                assert call_args is not None

                # Extract the extra dict from the call
                extra_dict = call_args.kwargs.get("extra", {})

                # Verify the 'role' field contains the admin's role, not the system role from request
                assert extra_dict.get("role") == "admin"  # admin_token.role
                assert extra_dict.get("role") != "corpus_admin"  # Not the system role from request
                assert extra_dict.get("system_roles") == ["corpus_admin"]  # Request system roles
            finally:
                admin_user_roles_module.get_user_roles = original_get


class TestAddUserRole:
    """Test add_user_role endpoint."""

    @pytest.mark.asyncio
    async def test_add_user_role_success(self, admin_token, mock_async_db, sample_user_id):
        """Successfully add role to user."""
        # Mock user exists check (first execute call)
        mock_user = Mock()
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = mock_user

        # Mock no existing membership (second execute call)
        mock_membership_result = Mock()
        mock_membership_result.scalar_one_or_none.return_value = None

        mock_async_db.execute.side_effect = [mock_user_result, mock_membership_result]

        response = await add_user_role(
            user_id=sample_user_id,
            role_name="threat_hunting",
            db=mock_async_db,
            current_user=admin_token,
        )

        assert response["role"] == "threat_hunting"
        assert response["user_id"] == str(sample_user_id)
        mock_async_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_user_role_already_exists(self, admin_token, mock_async_db, sample_user_id):
        """Adding existing role returns success without creating duplicate."""
        # Mock user exists check
        mock_user = Mock()
        mock_async_db.get.return_value = mock_user

        # Mock existing membership
        existing = Mock(role="threat_hunting", created_at=datetime.now(UTC))
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_async_db.execute.return_value = mock_result

        response = await add_user_role(
            user_id=sample_user_id,
            role_name="threat_hunting",
            db=mock_async_db,
            current_user=admin_token,
        )

        assert response["role"] == "threat_hunting"
        # Should not commit if already exists
        mock_async_db.commit.assert_not_called()


class TestRemoveUserRole:
    """Test remove_user_role endpoint."""

    @pytest.mark.asyncio
    async def test_remove_user_role_success(self, admin_token, mock_async_db, sample_user_id):
        """Successfully remove role from user."""
        # Mock user exists check
        mock_user = Mock()
        mock_user.role = "user"
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = mock_user
        mock_async_db.execute.return_value = mock_user_result

        # Mock execute for delete
        mock_result = Mock()
        mock_async_db.execute.return_value = mock_result

        await remove_user_role(
            user_id=sample_user_id,
            role_name="threat_hunting",
            db=mock_async_db,
            current_user=admin_token,
        )

        mock_async_db.execute.assert_called()
        mock_async_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_primary_system_role_raises(
        self, admin_token, mock_async_db, sample_user_id
    ):
        """Removing primary system role raises 400."""
        # Mock user exists check
        mock_user = Mock()
        mock_user.role = "admin"
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = mock_user
        mock_async_db.execute.return_value = mock_user_result

        with pytest.raises(HTTPException) as exc_info:
            await remove_user_role(
                user_id=sample_user_id,
                role_name="admin",
                db=mock_async_db,
                current_user=admin_token,
            )
        assert exc_info.value.status_code == 400
