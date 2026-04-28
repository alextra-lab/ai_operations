"""
Unit tests for RBAC service (ADR-041) using mocks.

Tests role-based use case access control with three access levels:
1. Admin override (admin always has access)
2. Direct user assignment (user_use_case_assignments)
3. Role-based assignment (role_use_case_assignments)

All async per ADR-022 (P5-A23 - sync patterns removed Nov 2025).
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from app.services.rbac import (
    get_accessible_use_cases,
    get_user_access_source,
    user_can_access_use_case,
)


@pytest.fixture
def mock_async_db():
    """Create a mock async database session."""
    return AsyncMock()


class TestUserCanAccessUseCase:
    """Test user_can_access_use_case function."""

    @pytest.mark.asyncio
    async def test_admin_always_has_access(self, mock_async_db):
        """Admin role bypasses all checks."""
        user_id = uuid4()
        use_case_id = uuid4()

        # Mock admin user query result
        admin_user = Mock(role="admin")
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = admin_user
        mock_async_db.execute.return_value = mock_result

        # Admin should have access even without any assignments
        result = await user_can_access_use_case(user_id, use_case_id, mock_async_db)
        assert result is True

    @pytest.mark.asyncio
    async def test_direct_user_assignment_grants_access(self, mock_async_db):
        """Direct user assignment grants access."""
        user_id = uuid4()
        use_case_id = uuid4()

        # Mock non-admin user
        user = Mock(role="user")
        # Mock direct assignment exists
        assignment = Mock(status="active")

        # Setup execute mock to return different results for different queries
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = user

        mock_assignment_result = Mock()
        mock_assignment_result.scalar_one_or_none.return_value = assignment

        mock_async_db.execute.side_effect = [mock_user_result, mock_assignment_result]

        # User should have access via direct assignment
        result = await user_can_access_use_case(user_id, use_case_id, mock_async_db)
        assert result is True

    @pytest.mark.asyncio
    async def test_no_assignment_denies_access(self, mock_async_db):
        """User without assignments has no access."""
        user_id = uuid4()
        use_case_id = uuid4()

        # Mock non-admin user
        user = Mock(role="user")

        # Mock results for: user query, direct assignment (None), roles query
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = user

        mock_no_direct = Mock()
        mock_no_direct.scalar_one_or_none.return_value = None

        mock_no_roles = Mock()
        mock_no_roles.all.return_value = []

        mock_async_db.execute.side_effect = [
            mock_user_result,
            mock_no_direct,
            mock_no_roles,
        ]

        # User should NOT have access (no assignments)
        result = await user_can_access_use_case(user_id, use_case_id, mock_async_db)
        assert result is False

    @pytest.mark.asyncio
    async def test_nonexistent_user_denies_access(self, mock_async_db):
        """Nonexistent user has no access."""
        user_id = uuid4()
        use_case_id = uuid4()

        # Mock user not found
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_db.execute.return_value = mock_result

        # Nonexistent user should NOT have access
        result = await user_can_access_use_case(user_id, use_case_id, mock_async_db)
        assert result is False

    @pytest.mark.asyncio
    async def test_role_assignment_grants_access(self, mock_async_db):
        """Role-based assignment grants access."""
        user_id = uuid4()
        use_case_id = uuid4()

        # Mock non-admin user
        user = Mock(role="user")
        # Mock role assignment exists
        role_assignment = Mock(is_active=True, expires_at=None)

        # Setup execute mock for: user, no direct, roles list, role assignment
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = user

        mock_no_direct = Mock()
        mock_no_direct.scalar_one_or_none.return_value = None

        mock_roles = Mock()
        mock_roles.all.return_value = [Mock(role="analyst")]

        mock_role_assignment = Mock()
        mock_role_assignment.scalar_one_or_none.return_value = role_assignment

        mock_async_db.execute.side_effect = [
            mock_user_result,
            mock_no_direct,
            mock_roles,
            mock_role_assignment,
        ]

        # User should have access via role assignment
        result = await user_can_access_use_case(user_id, use_case_id, mock_async_db)
        assert result is True


class TestGetAccessibleUseCases:
    """Test get_accessible_use_cases function."""

    @pytest.mark.asyncio
    async def test_admin_sees_all_use_cases(self, mock_async_db):
        """Admin sees all use cases regardless of assignments."""
        user_id = uuid4()

        # Mock admin user
        admin = Mock(role="admin")

        # Mock use cases
        uc1 = Mock(use_case_id="uc1", is_active=True, lifecycle_state="published")
        uc2 = Mock(use_case_id="uc2", is_active=True, lifecycle_state="published")

        # Setup execute mock
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = admin

        mock_use_cases_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [uc1, uc2]
        mock_use_cases_result.scalars.return_value = mock_scalars

        mock_async_db.execute.side_effect = [mock_user_result, mock_use_cases_result]

        # Admin should see all
        use_cases = await get_accessible_use_cases(user_id, mock_async_db)
        assert len(use_cases) == 2

    @pytest.mark.asyncio
    async def test_nonexistent_user_gets_empty_list(self, mock_async_db):
        """Nonexistent user gets empty list."""
        user_id = uuid4()

        # Mock user not found
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_db.execute.return_value = mock_result

        # Nonexistent user should get empty list
        use_cases = await get_accessible_use_cases(user_id, mock_async_db)
        assert use_cases == []

    @pytest.mark.asyncio
    async def test_regular_user_sees_only_assigned(self, mock_async_db):
        """Regular user sees only assigned use cases."""
        user_id = uuid4()

        # Mock non-admin user
        user = Mock(role="user")

        # Mock use case
        uc1 = Mock(use_case_id="uc1", is_active=True, lifecycle_state="published")

        # Setup execute mock for user query and use cases query
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = user

        mock_use_cases_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [uc1]
        mock_use_cases_result.scalars.return_value = mock_scalars

        mock_async_db.execute.side_effect = [mock_user_result, mock_use_cases_result]

        # User should see only assigned use case
        use_cases = await get_accessible_use_cases(user_id, mock_async_db)
        assert len(use_cases) == 1


class TestGetUserAccessSource:
    """Test get_user_access_source function."""

    @pytest.mark.asyncio
    async def test_admin_source_for_admin_users(self, mock_async_db):
        """Returns admin as source for admin users."""
        user_id = uuid4()
        use_case_id = uuid4()

        # Mock admin user
        admin = Mock(role="admin")
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = admin
        mock_async_db.execute.return_value = mock_result

        result = await get_user_access_source(user_id, use_case_id, mock_async_db)
        assert result["has_access"] is True
        assert result["source"] == "admin"

    @pytest.mark.asyncio
    async def test_direct_source_for_direct_assignments(self, mock_async_db):
        """Returns direct as source for direct assignments."""
        user_id = uuid4()
        use_case_id = uuid4()

        # Mock non-admin user
        user = Mock(role="user")
        # Mock direct assignment
        assignment = Mock(
            status="active",
            assigned_role="user",
            granted_by=uuid4(),
            assigned_at=datetime.now(tz=UTC),
            expires_at=None,
        )

        # Setup execute mocks
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = user

        mock_assignment_result = Mock()
        mock_assignment_result.scalar_one_or_none.return_value = assignment

        mock_async_db.execute.side_effect = [mock_user_result, mock_assignment_result]

        result = await get_user_access_source(user_id, use_case_id, mock_async_db)
        assert result["has_access"] is True
        assert result["source"] == "direct"

    @pytest.mark.asyncio
    async def test_none_source_when_no_access(self, mock_async_db):
        """Returns none source when user has no access."""
        user_id = uuid4()
        use_case_id = uuid4()

        # Mock non-admin user
        user = Mock(role="user")

        # Setup execute mocks: user, no direct assignment, no roles
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = user

        mock_no_direct = Mock()
        mock_no_direct.scalar_one_or_none.return_value = None

        mock_no_roles = Mock()
        mock_no_roles.all.return_value = []

        mock_async_db.execute.side_effect = [
            mock_user_result,
            mock_no_direct,
            mock_no_roles,
        ]

        result = await get_user_access_source(user_id, use_case_id, mock_async_db)
        assert result["has_access"] is False
        assert result["source"] == "none"

    @pytest.mark.asyncio
    async def test_role_source_for_role_assignments(self, mock_async_db):
        """Returns role as source for role-based assignments."""
        user_id = uuid4()
        use_case_id = uuid4()

        # Mock non-admin user
        user = Mock(role="user")
        # Mock role assignment
        role_assignment = Mock(
            role_name="analyst",
            granted_at=datetime.now(tz=UTC),
            expires_at=None,
            is_active=True,
        )

        # Setup execute mocks: user, no direct, roles list, role assignment
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = user

        mock_no_direct = Mock()
        mock_no_direct.scalar_one_or_none.return_value = None

        mock_roles = Mock()
        mock_roles.all.return_value = [Mock(role="analyst")]

        mock_role_assignment = Mock()
        mock_role_assignment.scalar_one_or_none.return_value = role_assignment

        mock_async_db.execute.side_effect = [
            mock_user_result,
            mock_no_direct,
            mock_roles,
            mock_role_assignment,
        ]

        result = await get_user_access_source(user_id, use_case_id, mock_async_db)
        assert result["has_access"] is True
        assert result["source"] == "role"
        assert result["details"]["role_name"] == "analyst"
