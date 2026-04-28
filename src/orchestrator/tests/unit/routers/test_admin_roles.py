"""
Unit tests for admin roles router (ADR-041) using mocks.

Tests admin-only endpoints for managing role-based use case assignments.
P5-A11: Updated for async database patterns (Nov 2025).
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from shared.auth.models import TokenPayload
from src.orchestrator.app.routers.admin_roles import (
    RoleUseCaseAssignRequest,
    assign_use_case_to_role,
    get_role_use_cases,
    get_use_case_roles,
    require_admin,
    revoke_use_case_from_role,
)


@pytest.fixture
def admin_token():
    """Create a valid admin token payload."""
    now = datetime.now(tz=UTC)
    return TokenPayload(
        sub="admin",
        user_id=str(uuid4()),
        role="admin",
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
        role="user",
        exp=int((now + timedelta(hours=1)).timestamp()),
        iat=int(now.timestamp()),
        iss="aio",
        token_type="access",
    )


@pytest.fixture
def mock_async_db():
    """Create a mock async database session."""
    return AsyncMock()


class TestRequireAdmin:
    """Test require_admin helper function."""

    def test_admin_user_passes(self, admin_token):
        """Admin user passes the check."""
        # Should not raise
        require_admin(admin_token)

    def test_non_admin_user_raises(self, user_token):
        """Non-admin user raises 403."""
        with pytest.raises(HTTPException) as exc_info:
            require_admin(user_token)
        assert exc_info.value.status_code == 403


class TestAssignUseCaseToRole:
    """Test assign_use_case_to_role endpoint."""

    @pytest.mark.asyncio
    async def test_create_new_assignment(self, admin_token, mock_async_db):
        """Successfully creates a new role-use case assignment."""
        use_case_id = uuid4()

        # Mock use case exists (first query)
        mock_use_case = Mock(id=use_case_id)
        mock_use_case.name = "Test Use Case"  # Set name as attribute, not param
        mock_uc_result = MagicMock()
        mock_uc_result.scalar_one_or_none.return_value = mock_use_case

        # Mock no existing assignment (second query)
        mock_existing_result = MagicMock()
        mock_existing_result.scalar_one_or_none.return_value = None

        # Setup execute to return different results for different queries
        mock_async_db.execute.side_effect = [mock_uc_result, mock_existing_result]

        # Mock the assignment after add/commit/refresh
        mock_assignment = Mock(
            id=uuid4(),
            role_name="analyst",
            use_case_id=use_case_id,
            granted_by=uuid4(),
            granted_at=datetime.now(tz=UTC),
            expires_at=None,
            is_active=True,
            metadata_json={},
        )
        mock_async_db.refresh = AsyncMock(
            side_effect=lambda obj: setattr(obj, "id", mock_assignment.id)
            or setattr(obj, "granted_at", mock_assignment.granted_at)
            or setattr(obj, "is_active", True)
        )

        request = RoleUseCaseAssignRequest(use_case_id=use_case_id, expires_at=None, metadata={})

        response = await assign_use_case_to_role(
            role_name="analyst",
            request=request,
            db=mock_async_db,
            current_user=admin_token,
        )

        # Verify response
        assert response.role_name == "analyst"
        assert response.use_case_id == use_case_id
        assert response.use_case_name == "Test Use Case"
        assert response.is_active is True
        mock_async_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_invalid_role_name_raises_400(self, admin_token, mock_async_db):
        """Invalid role name raises 400."""
        request = RoleUseCaseAssignRequest(use_case_id=uuid4(), expires_at=None, metadata={})

        # Invalid role name (uppercase, special chars)
        with pytest.raises(HTTPException) as exc_info:
            await assign_use_case_to_role(
                role_name="INVALID-ROLE!",
                request=request,
                db=mock_async_db,
                current_user=admin_token,
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_nonexistent_use_case_raises_404(self, admin_token, mock_async_db):
        """Nonexistent use case raises 404."""
        # Mock use case not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_db.execute.return_value = mock_result

        request = RoleUseCaseAssignRequest(use_case_id=uuid4(), expires_at=None, metadata={})

        with pytest.raises(HTTPException) as exc_info:
            await assign_use_case_to_role(
                role_name="analyst",
                request=request,
                db=mock_async_db,
                current_user=admin_token,
            )
        assert exc_info.value.status_code == 404


class TestRevokeUseCaseFromRole:
    """Test revoke_use_case_from_role endpoint."""

    @pytest.mark.asyncio
    async def test_deactivate_assignment(self, admin_token, mock_async_db):
        """Soft delete (deactivate) an assignment."""
        use_case_id = uuid4()

        # Mock assignment exists
        mock_assignment = Mock(is_active=True)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_assignment
        mock_async_db.execute.return_value = mock_result

        # Revoke (soft delete)
        await revoke_use_case_from_role(
            role_name="analyst",
            use_case_id=use_case_id,
            permanent=False,
            db=mock_async_db,
            current_user=admin_token,
        )

        # Verify deactivated
        assert mock_assignment.is_active is False
        mock_async_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_permanent_delete_assignment(self, admin_token, mock_async_db):
        """Permanently delete an assignment."""
        use_case_id = uuid4()

        # Mock assignment exists
        mock_assignment = Mock(is_active=True)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_assignment
        mock_async_db.execute.return_value = mock_result

        # Revoke (permanent delete)
        await revoke_use_case_from_role(
            role_name="analyst",
            use_case_id=use_case_id,
            permanent=True,
            db=mock_async_db,
            current_user=admin_token,
        )

        # Verify delete was called
        mock_async_db.delete.assert_awaited_with(mock_assignment)
        mock_async_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_nonexistent_assignment_raises_404(self, admin_token, mock_async_db):
        """Nonexistent assignment raises 404."""
        # Mock assignment not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await revoke_use_case_from_role(
                role_name="analyst",
                use_case_id=uuid4(),
                permanent=False,
                db=mock_async_db,
                current_user=admin_token,
            )
        assert exc_info.value.status_code == 404


class TestGetRoleUseCases:
    """Test get_role_use_cases endpoint."""

    @pytest.mark.asyncio
    async def test_list_active_assignments(self, admin_token, mock_async_db):
        """Lists only active assignments by default."""
        uc1_id = uuid4()

        # Mock active assignment
        mock_assignment = Mock(
            id=uuid4(),
            role_name="analyst",
            use_case_id=uc1_id,
            granted_by=uuid4(),
            granted_at=datetime.now(tz=UTC),
            expires_at=None,
            is_active=True,
            metadata_json={},
        )

        # Mock assignments query result
        mock_assignments_result = MagicMock()
        mock_assignments_result.scalars.return_value.all.return_value = [mock_assignment]

        # Mock use cases query result
        mock_use_case = Mock(id=uc1_id)
        mock_use_case.name = "UC 1"  # Set name as attribute, not param
        mock_uc_result = MagicMock()
        mock_uc_result.scalars.return_value.all.return_value = [mock_use_case]

        # Set up execute to return different results
        mock_async_db.execute.side_effect = [mock_assignments_result, mock_uc_result]

        # Get assignments (default: active only)
        response = await get_role_use_cases(
            role_name="analyst",
            include_inactive=False,
            db=mock_async_db,
            current_user=admin_token,
        )

        assert response.role_name == "analyst"
        assert response.total == 1
        assert response.active == 1
        assert len(response.assignments) == 1
        assert response.assignments[0].use_case_name == "UC 1"

    @pytest.mark.asyncio
    async def test_list_empty_assignments(self, admin_token, mock_async_db):
        """Returns empty list when no assignments exist."""
        # Mock empty assignments
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_async_db.execute.return_value = mock_result

        response = await get_role_use_cases(
            role_name="analyst",
            include_inactive=False,
            db=mock_async_db,
            current_user=admin_token,
        )

        assert response.role_name == "analyst"
        assert response.total == 0
        assert response.active == 0
        assert len(response.assignments) == 0


class TestGetUseCaseRoles:
    """Test get_use_case_roles endpoint."""

    @pytest.mark.asyncio
    async def test_list_roles_with_access(self, admin_token, mock_async_db):
        """Lists all roles with access to a use case."""
        use_case_id = uuid4()

        # Mock use case exists
        mock_use_case = Mock(id=use_case_id)
        mock_uc_result = MagicMock()
        mock_uc_result.scalar_one_or_none.return_value = mock_use_case

        # Mock role assignments
        mock_assignment1 = Mock(role_name="analyst")
        mock_assignment2 = Mock(role_name="developer")
        mock_assignments_result = MagicMock()
        mock_assignments_result.scalars.return_value.all.return_value = [
            mock_assignment1,
            mock_assignment2,
        ]

        # Set up execute to return different results
        mock_async_db.execute.side_effect = [mock_uc_result, mock_assignments_result]

        # Get roles
        roles = await get_use_case_roles(
            use_case_id=use_case_id, db=mock_async_db, current_user=admin_token
        )

        # Should include admin (implicit), analyst, developer - sorted
        assert "admin" in roles
        assert "analyst" in roles
        assert "developer" in roles
        assert roles == sorted(roles)  # Verify sorted

    @pytest.mark.asyncio
    async def test_nonexistent_use_case_raises_404(self, admin_token, mock_async_db):
        """Nonexistent use case raises 404."""
        # Mock use case not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_use_case_roles(
                use_case_id=uuid4(), db=mock_async_db, current_user=admin_token
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_admin_always_included(self, admin_token, mock_async_db):
        """Admin role is always included even if not explicitly assigned."""
        use_case_id = uuid4()

        # Mock use case exists
        mock_use_case = Mock(id=use_case_id)
        mock_uc_result = MagicMock()
        mock_uc_result.scalar_one_or_none.return_value = mock_use_case

        # Mock no explicit assignments
        mock_assignments_result = MagicMock()
        mock_assignments_result.scalars.return_value.all.return_value = []

        mock_async_db.execute.side_effect = [mock_uc_result, mock_assignments_result]

        # Get roles
        roles = await get_use_case_roles(
            use_case_id=use_case_id, db=mock_async_db, current_user=admin_token
        )

        # Admin should still be included
        assert "admin" in roles
        assert len(roles) == 1
