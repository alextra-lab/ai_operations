"""
Unit tests for RBAC V2 service (ADR-060) using mocks.

Tests two-tier role system with team isolation:
1. System roles (admin, corpus_admin, use_case_admin, etc.)
2. Grouping roles (threat_hunting, incident_response, etc.)
3. Team memberships (team:csirt_security, etc.)

All async per ADR-022 (P5-A23 - sync patterns removed Nov 2025).
"""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from app.services.rbac_v2 import (
    can_edit_use_case,
    can_transition_state,
    get_accessible_collections,
    get_accessible_use_cases,
    get_user_grouping_roles,
    get_user_roles,
    get_user_system_roles,
    get_user_teams,
    has_any_role,
    has_role,
)


@pytest.fixture
def mock_async_db():
    """Create a mock async database session."""
    return AsyncMock()


@pytest.fixture
def sample_user_id():
    """Sample user UUID for testing."""
    return uuid4()


@pytest.fixture
def sample_use_case():
    """Sample use case object for testing."""
    uc = Mock()
    uc.id = uuid4()
    uc.lifecycle_state = "draft"
    uc.created_by_user_id = uuid4()
    uc.team_id = "team:csirt_security"
    return uc


class TestGetUserRoles:
    """Test get_user_roles function."""

    @pytest.mark.asyncio
    async def test_get_user_roles_returns_all_roles(self, mock_async_db, sample_user_id):
        """Get all roles assigned to user."""
        # Mock role memberships
        role1 = Mock(role="admin")
        role2 = Mock(role="threat_hunting")
        role3 = Mock(role="team:csirt_security")

        mock_result = Mock()
        mock_result.all.return_value = [role1, role2, role3]
        mock_async_db.execute.return_value = mock_result

        roles = await get_user_roles(sample_user_id, mock_async_db)
        assert len(roles) == 3
        assert "admin" in roles
        assert "threat_hunting" in roles
        assert "team:csirt_security" in roles

    @pytest.mark.asyncio
    async def test_get_user_roles_empty_when_no_roles(self, mock_async_db, sample_user_id):
        """Returns empty list when user has no roles."""
        mock_result = Mock()
        mock_result.all.return_value = []
        mock_async_db.execute.return_value = mock_result

        roles = await get_user_roles(sample_user_id, mock_async_db)
        assert roles == []


class TestGetUserSystemRoles:
    """Test get_user_system_roles function."""

    @pytest.mark.asyncio
    async def test_get_user_system_roles_filters_system_roles(self, mock_async_db, sample_user_id):
        """Returns only system roles."""
        # Mock mixed roles
        role1 = Mock(role="admin")
        role2 = Mock(role="threat_hunting")  # Grouping role
        role3 = Mock(role="team:csirt_security")  # Team

        mock_result = Mock()
        mock_result.all.return_value = [role1, role2, role3]
        mock_async_db.execute.return_value = mock_result

        system_roles = await get_user_system_roles(sample_user_id, mock_async_db)
        assert len(system_roles) == 1
        assert "admin" in system_roles
        assert "threat_hunting" not in system_roles
        assert "team:csirt_security" not in system_roles


class TestGetUserGroupingRoles:
    """Test get_user_grouping_roles function."""

    @pytest.mark.asyncio
    async def test_get_user_grouping_roles_filters_correctly(self, mock_async_db, sample_user_id):
        """Returns only grouping roles (not system, not teams)."""
        # Mock mixed roles
        role1 = Mock(role="admin")  # System
        role2 = Mock(role="threat_hunting")  # Grouping
        role3 = Mock(role="incident_response")  # Grouping
        role4 = Mock(role="team:csirt_security")  # Team

        mock_result = Mock()
        mock_result.all.return_value = [role1, role2, role3, role4]
        mock_async_db.execute.return_value = mock_result

        grouping_roles = await get_user_grouping_roles(sample_user_id, mock_async_db)
        assert len(grouping_roles) == 2
        assert "threat_hunting" in grouping_roles
        assert "incident_response" in grouping_roles
        assert "admin" not in grouping_roles
        assert "team:csirt_security" not in grouping_roles


class TestGetUserTeams:
    """Test get_user_teams function."""

    @pytest.mark.asyncio
    async def test_get_user_teams_filters_teams(self, mock_async_db, sample_user_id):
        """Returns only team memberships."""
        # Mock mixed roles
        role1 = Mock(role="admin")
        role2 = Mock(role="threat_hunting")
        role3 = Mock(role="team:csirt_security")
        role4 = Mock(role="team:soc_governance")

        mock_result = Mock()
        mock_result.all.return_value = [role1, role2, role3, role4]
        mock_async_db.execute.return_value = mock_result

        teams = await get_user_teams(sample_user_id, mock_async_db)
        assert len(teams) == 2
        assert "team:csirt_security" in teams
        assert "team:soc_governance" in teams
        assert "admin" not in teams
        assert "threat_hunting" not in teams


class TestHasRole:
    """Test has_role function."""

    @pytest.mark.asyncio
    async def test_has_role_returns_true_when_user_has_role(self, mock_async_db, sample_user_id):
        """Returns True when user has the role."""
        membership = Mock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = membership
        mock_async_db.execute.return_value = mock_result

        result = await has_role(sample_user_id, "admin", mock_async_db)
        assert result is True

    @pytest.mark.asyncio
    async def test_has_role_returns_false_when_user_lacks_role(self, mock_async_db, sample_user_id):
        """Returns False when user doesn't have the role."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_db.execute.return_value = mock_result

        result = await has_role(sample_user_id, "admin", mock_async_db)
        assert result is False


class TestHasAnyRole:
    """Test has_any_role function."""

    @pytest.mark.asyncio
    async def test_has_any_role_returns_true_when_user_has_one(self, mock_async_db, sample_user_id):
        """Returns True when user has any of the required roles."""
        role1 = Mock(role="admin")
        mock_result = Mock()
        mock_result.all.return_value = [role1]
        mock_async_db.execute.return_value = mock_result

        result = await has_any_role(sample_user_id, ["admin", "corpus_admin"], mock_async_db)
        assert result is True

    @pytest.mark.asyncio
    async def test_has_any_role_returns_false_when_user_has_none(
        self, mock_async_db, sample_user_id
    ):
        """Returns False when user has none of the required roles."""
        role1 = Mock(role="threat_hunting")
        mock_result = Mock()
        mock_result.all.return_value = [role1]
        mock_async_db.execute.return_value = mock_result

        result = await has_any_role(sample_user_id, ["admin", "corpus_admin"], mock_async_db)
        assert result is False


class TestGetAccessibleUseCases:
    """Test get_accessible_use_cases function."""

    @pytest.mark.asyncio
    async def test_admin_sees_all_use_cases(self, mock_async_db, sample_user_id):
        """Admin sees all use cases regardless of state."""
        # Mock admin role
        role1 = Mock(role="admin")
        mock_roles_result = Mock()
        mock_roles_result.all.return_value = [role1]

        # Mock use cases
        uc1 = Mock()
        uc1.id = uuid4()
        uc1.lifecycle_state = "published"
        uc2 = Mock()
        uc2.id = uuid4()
        uc2.lifecycle_state = "draft"

        mock_ucs_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [uc1, uc2]
        mock_ucs_result.scalars.return_value = mock_scalars

        mock_async_db.execute.side_effect = [mock_roles_result, mock_ucs_result]

        use_cases = await get_accessible_use_cases(sample_user_id, mock_async_db)
        assert len(use_cases) == 2

    @pytest.mark.asyncio
    async def test_admin_sees_filtered_use_cases_by_lifecycle(self, mock_async_db, sample_user_id):
        """Admin can filter use cases by lifecycle_state."""
        # Mock admin role
        role1 = Mock(role="admin")
        mock_roles_result = Mock()
        mock_roles_result.all.return_value = [role1]

        # Mock published use case only
        uc1 = Mock()
        uc1.id = uuid4()
        uc1.lifecycle_state = "published"

        mock_ucs_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [uc1]
        mock_ucs_result.scalars.return_value = mock_scalars

        mock_async_db.execute.side_effect = [mock_roles_result, mock_ucs_result]

        use_cases = await get_accessible_use_cases(
            sample_user_id, mock_async_db, lifecycle_state="published"
        )
        assert len(use_cases) == 1
        assert use_cases[0].lifecycle_state == "published"

    @pytest.mark.asyncio
    async def test_use_case_admin_sees_published_and_team_drafts(
        self, mock_async_db, sample_user_id
    ):
        """use_case_admin sees published + team drafts."""
        # Mock use_case_admin role and team
        role1 = Mock(role="use_case_admin")
        role2 = Mock(role="team:csirt_security")
        mock_roles_result = Mock()
        mock_roles_result.all.return_value = [role1, role2]

        # Mock published use case
        published_uc = Mock()
        published_uc.id = uuid4()
        published_uc.lifecycle_state = "published"

        # Mock team draft use case
        draft_uc = Mock()
        draft_uc.id = uuid4()
        draft_uc.lifecycle_state = "draft"
        draft_uc.team_id = "team:csirt_security"

        # The function flow:
        # 1. get_user_roles() - calls execute once
        # 2. get_user_teams() - calls get_user_roles() again, so execute once more
        # 3. Builds union subquery (no execute - it's part of SQL)
        # 4. Executes final select(UseCase).where(UseCase.id.in_(union)) - one execute

        mock_ucs_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [published_uc, draft_uc]
        mock_ucs_result.scalars.return_value = mock_scalars

        # Mock execute calls: 2 for get_user_roles/get_user_teams, 1 for final query
        mock_async_db.execute.side_effect = [
            mock_roles_result,  # get_user_roles (first call)
            mock_roles_result,  # get_user_teams -> get_user_roles (second call)
            mock_ucs_result,  # final select(UseCase).where(id.in_(union))
        ]

        use_cases = await get_accessible_use_cases(sample_user_id, mock_async_db)
        assert len(use_cases) == 2

    @pytest.mark.asyncio
    async def test_use_case_admin_without_teams_sees_only_published(
        self, mock_async_db, sample_user_id
    ):
        """use_case_admin without teams sees only published use cases."""
        # Mock use_case_admin role but no teams
        role1 = Mock(role="use_case_admin")
        mock_roles_result = Mock()
        mock_roles_result.all.return_value = [role1]

        # Mock published use case
        published_uc = Mock()
        published_uc.id = uuid4()
        published_uc.lifecycle_state = "published"

        mock_ucs_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [published_uc]
        mock_ucs_result.scalars.return_value = mock_scalars

        mock_async_db.execute.side_effect = [
            mock_roles_result,  # get_user_roles
            mock_roles_result,  # get_user_teams (returns empty)
            mock_ucs_result,  # final query
        ]

        use_cases = await get_accessible_use_cases(sample_user_id, mock_async_db)
        assert len(use_cases) == 1

    @pytest.mark.asyncio
    async def test_use_case_admin_with_lifecycle_filter(self, mock_async_db, sample_user_id):
        """use_case_admin can filter by lifecycle_state."""
        # Mock use_case_admin role and team
        role1 = Mock(role="use_case_admin")
        role2 = Mock(role="team:csirt_security")
        mock_roles_result = Mock()
        mock_roles_result.all.return_value = [role1, role2]

        # Mock draft use case
        draft_uc = Mock()
        draft_uc.id = uuid4()
        draft_uc.lifecycle_state = "draft"
        draft_uc.team_id = "team:csirt_security"

        mock_ucs_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [draft_uc]
        mock_ucs_result.scalars.return_value = mock_scalars

        mock_async_db.execute.side_effect = [
            mock_roles_result,  # get_user_roles
            mock_roles_result,  # get_user_teams
            mock_ucs_result,  # final query with lifecycle filter
        ]

        use_cases = await get_accessible_use_cases(
            sample_user_id, mock_async_db, lifecycle_state="draft"
        )
        assert len(use_cases) == 1
        assert use_cases[0].lifecycle_state == "draft"

    @pytest.mark.asyncio
    async def test_corpus_admin_sees_all_published(self, mock_async_db, sample_user_id):
        """corpus_admin sees all published use cases."""
        # Mock corpus_admin role
        role1 = Mock(role="corpus_admin")
        mock_roles_result = Mock()
        mock_roles_result.all.return_value = [role1]

        # Mock published use cases
        uc1 = Mock()
        uc1.id = uuid4()
        uc1.lifecycle_state = "published"
        uc2 = Mock()
        uc2.id = uuid4()
        uc2.lifecycle_state = "published"

        mock_ucs_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [uc1, uc2]
        mock_ucs_result.scalars.return_value = mock_scalars

        mock_async_db.execute.side_effect = [mock_roles_result, mock_ucs_result]

        use_cases = await get_accessible_use_cases(sample_user_id, mock_async_db)
        assert len(use_cases) == 2
        assert all(uc.lifecycle_state == "published" for uc in use_cases)

    @pytest.mark.asyncio
    async def test_corpus_admin_with_lifecycle_filter(self, mock_async_db, sample_user_id):
        """corpus_admin can filter by lifecycle_state."""
        # Mock corpus_admin role
        role1 = Mock(role="corpus_admin")
        mock_roles_result = Mock()
        mock_roles_result.all.return_value = [role1]

        # Mock published use case
        uc1 = Mock()
        uc1.id = uuid4()
        uc1.lifecycle_state = "published"

        mock_ucs_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [uc1]
        mock_ucs_result.scalars.return_value = mock_scalars

        mock_async_db.execute.side_effect = [mock_roles_result, mock_ucs_result]

        use_cases = await get_accessible_use_cases(
            sample_user_id, mock_async_db, lifecycle_state="published"
        )
        assert len(use_cases) == 1

    @pytest.mark.asyncio
    async def test_grouping_role_sees_only_assigned_published(self, mock_async_db, sample_user_id):
        """Grouping role sees only assigned published use cases."""
        # Mock grouping role
        role1 = Mock(role="threat_hunting")
        mock_roles_result = Mock()
        mock_roles_result.all.return_value = [role1]

        # Mock use case
        uc = Mock()
        uc.id = uuid4()
        uc.lifecycle_state = "published"

        # Mock role assignment
        assignment = Mock()
        assignment.use_case_id = uc.id
        assignment.role_name = "threat_hunting"
        assignment.is_active = True
        assignment.expires_at = None

        mock_ucs_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [uc]
        mock_ucs_result.scalars.return_value = mock_scalars

        mock_async_db.execute.side_effect = [
            mock_roles_result,  # get_user_roles
            mock_roles_result,  # get_user_grouping_roles
            mock_ucs_result,  # get_accessible_use_cases
        ]

        use_cases = await get_accessible_use_cases(sample_user_id, mock_async_db)
        assert len(use_cases) == 1

    @pytest.mark.asyncio
    async def test_grouping_role_with_lifecycle_filter(self, mock_async_db, sample_user_id):
        """Grouping role can filter by lifecycle_state."""
        # Mock grouping role
        role1 = Mock(role="threat_hunting")
        mock_roles_result = Mock()
        mock_roles_result.all.return_value = [role1]

        # Mock use case
        uc = Mock()
        uc.id = uuid4()
        uc.lifecycle_state = "published"

        # Mock role assignment
        assignment = Mock()
        assignment.use_case_id = uc.id
        assignment.role_name = "threat_hunting"
        assignment.is_active = True
        assignment.expires_at = None

        mock_ucs_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [uc]
        mock_ucs_result.scalars.return_value = mock_scalars

        mock_async_db.execute.side_effect = [
            mock_roles_result,  # get_user_roles
            mock_roles_result,  # get_user_grouping_roles
            mock_ucs_result,  # get_accessible_use_cases with filter
        ]

        use_cases = await get_accessible_use_cases(
            sample_user_id, mock_async_db, lifecycle_state="published"
        )
        assert len(use_cases) == 1

    @pytest.mark.asyncio
    async def test_no_roles_returns_empty_list(self, mock_async_db, sample_user_id):
        """User with no roles sees nothing (default-deny)."""
        mock_result = Mock()
        mock_result.all.return_value = []
        mock_async_db.execute.return_value = mock_result

        use_cases = await get_accessible_use_cases(sample_user_id, mock_async_db)
        assert use_cases == []


class TestCanEditUseCase:
    """Test can_edit_use_case function."""

    @pytest.mark.asyncio
    async def test_admin_can_edit_anything(self, mock_async_db, sample_user_id, sample_use_case):
        """Admin can edit any use case."""
        role1 = Mock(role="admin")
        mock_result = Mock()
        mock_result.all.return_value = [role1]
        mock_async_db.execute.return_value = mock_result

        result = await can_edit_use_case(sample_user_id, sample_use_case, mock_async_db)
        assert result is True

    @pytest.mark.asyncio
    async def test_cannot_edit_non_draft(self, mock_async_db, sample_user_id, sample_use_case):
        """Cannot edit non-draft use cases."""
        sample_use_case.lifecycle_state = "published"
        role1 = Mock(role="use_case_admin")
        mock_result = Mock()
        mock_result.all.return_value = [role1]
        mock_async_db.execute.return_value = mock_result

        result = await can_edit_use_case(sample_user_id, sample_use_case, mock_async_db)
        assert result is False

    @pytest.mark.asyncio
    async def test_creator_can_edit_own_draft(self, mock_async_db, sample_user_id, sample_use_case):
        """Creator can edit own draft use cases."""
        sample_use_case.created_by_user_id = sample_user_id
        sample_use_case.lifecycle_state = "draft"
        mock_result = Mock()
        mock_result.all.return_value = []
        mock_async_db.execute.return_value = mock_result

        result = await can_edit_use_case(sample_user_id, sample_use_case, mock_async_db)
        assert result is True

    @pytest.mark.asyncio
    async def test_cannot_edit_others_drafts(self, mock_async_db, sample_user_id, sample_use_case):
        """Cannot edit other users' drafts."""
        sample_use_case.created_by_user_id = uuid4()  # Different user
        sample_use_case.lifecycle_state = "draft"
        mock_result = Mock()
        mock_result.all.return_value = []
        mock_async_db.execute.return_value = mock_result

        result = await can_edit_use_case(sample_user_id, sample_use_case, mock_async_db)
        assert result is False


class TestGetAccessibleCollections:
    """Test get_accessible_collections function."""

    @pytest.mark.asyncio
    async def test_admin_sees_all_collections(self, mock_async_db, sample_user_id):
        """Admin sees all active collections."""
        role1 = Mock(role="admin")
        mock_roles_result = Mock()
        mock_roles_result.all.return_value = [role1]

        # Mock collection query result
        mock_row1 = Mock()
        mock_row1 = Mock()
        mock_row1._mapping = {"id": uuid4(), "name": "collection1", "is_active": True}
        mock_row2 = Mock()
        mock_row2._mapping = {"id": uuid4(), "name": "collection2", "is_active": True}

        mock_collections_result = Mock()
        mock_collections_result.all.return_value = [mock_row1, mock_row2]

        mock_async_db.execute.side_effect = [mock_roles_result, mock_collections_result]

        collections = await get_accessible_collections(sample_user_id, mock_async_db)
        assert len(collections) == 2

    @pytest.mark.asyncio
    async def test_corpus_admin_sees_all_collections(self, mock_async_db, sample_user_id):
        """corpus_admin sees all active collections."""
        role1 = Mock(role="corpus_admin")
        mock_roles_result = Mock()
        mock_roles_result.all.return_value = [role1]

        mock_row = Mock()
        mock_row._mapping = {"id": uuid4(), "name": "collection1", "is_active": True}
        mock_collections_result = Mock()
        mock_collections_result.all.return_value = [mock_row]

        mock_async_db.execute.side_effect = [mock_roles_result, mock_collections_result]

        collections = await get_accessible_collections(sample_user_id, mock_async_db)
        assert len(collections) == 1

    @pytest.mark.asyncio
    async def test_grouping_role_sees_only_assigned_collections(
        self, mock_async_db, sample_user_id
    ):
        """Grouping role sees only assigned collections."""
        role1 = Mock(role="threat_hunting")
        mock_roles_result = Mock()
        mock_roles_result.all.return_value = [role1]

        # Mock role collection assignment
        collection_id = uuid4()
        mock_assignment_result = Mock()
        mock_assignment_result.all.return_value = [(collection_id,)]

        # Mock collection query
        mock_row = Mock()
        mock_row._mapping = {"id": collection_id, "name": "collection1", "is_active": True}
        mock_collections_result = Mock()
        mock_collections_result.all.return_value = [mock_row]

        mock_async_db.execute.side_effect = [
            mock_roles_result,  # get_user_roles
            mock_roles_result,  # get_user_grouping_roles
            mock_assignment_result,  # role collection assignments
            mock_collections_result,  # collection details
        ]

        collections = await get_accessible_collections(sample_user_id, mock_async_db)
        assert len(collections) == 1

    @pytest.mark.asyncio
    async def test_grouping_role_with_no_assigned_collections(self, mock_async_db, sample_user_id):
        """Grouping role with no assigned collections returns empty list."""
        role1 = Mock(role="threat_hunting")
        mock_roles_result = Mock()
        mock_roles_result.all.return_value = [role1]

        # Mock role collection assignment query returns empty
        mock_assignment_result = Mock()
        mock_assignment_result.all.return_value = []

        mock_async_db.execute.side_effect = [
            mock_roles_result,  # get_user_roles
            mock_roles_result,  # get_user_grouping_roles
            mock_assignment_result,  # role collection assignments (empty)
        ]

        collections = await get_accessible_collections(sample_user_id, mock_async_db)
        assert collections == []

    @pytest.mark.asyncio
    async def test_no_roles_returns_empty_collections(self, mock_async_db, sample_user_id):
        """User with no roles sees no collections (default-deny)."""
        mock_result = Mock()
        mock_result.all.return_value = []
        mock_async_db.execute.return_value = mock_result

        collections = await get_accessible_collections(sample_user_id, mock_async_db)
        assert collections == []


class TestCanTransitionState:
    """Test can_transition_state function (ADR-060 lifecycle permissions)."""

    @pytest.mark.asyncio
    async def test_admin_can_transition_anything(
        self, mock_async_db, sample_user_id, sample_use_case
    ):
        """Admin can transition to any state."""
        role1 = Mock(role="admin")
        mock_result = Mock()
        mock_result.all.return_value = [role1]
        mock_async_db.execute.return_value = mock_result

        result = await can_transition_state(
            sample_user_id, sample_use_case, "published", mock_async_db
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_creator_can_submit_draft_to_review(
        self, mock_async_db, sample_user_id, sample_use_case
    ):
        """Creator can submit own draft to review."""
        sample_use_case.created_by_user_id = sample_user_id
        sample_use_case.lifecycle_state = "draft"
        mock_result = Mock()
        mock_result.all.return_value = []
        mock_async_db.execute.return_value = mock_result

        result = await can_transition_state(
            sample_user_id, sample_use_case, "review", mock_async_db
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_developer_can_submit_own_draft_to_review(
        self, mock_async_db, sample_user_id, sample_use_case
    ):
        """Developer can submit own draft to review."""
        sample_use_case.created_by_user_id = sample_user_id
        sample_use_case.lifecycle_state = "draft"
        role1 = Mock(role="developer")
        mock_result = Mock()
        mock_result.all.return_value = [role1]
        mock_async_db.execute.return_value = mock_result

        result = await can_transition_state(
            sample_user_id, sample_use_case, "review", mock_async_db
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_developer_cannot_submit_others_draft(
        self, mock_async_db, sample_user_id, sample_use_case
    ):
        """Developer cannot submit other users' drafts."""
        sample_use_case.created_by_user_id = uuid4()
        sample_use_case.lifecycle_state = "draft"
        role1 = Mock(role="developer")
        mock_result = Mock()
        mock_result.all.return_value = [role1]
        mock_async_db.execute.return_value = mock_result

        result = await can_transition_state(
            sample_user_id, sample_use_case, "review", mock_async_db
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_use_case_admin_can_submit_any_draft(
        self, mock_async_db, sample_user_id, sample_use_case
    ):
        """use_case_admin can submit any draft to review."""
        sample_use_case.created_by_user_id = uuid4()
        sample_use_case.lifecycle_state = "draft"
        role1 = Mock(role="use_case_admin")
        mock_result = Mock()
        mock_result.all.return_value = [role1]
        mock_async_db.execute.return_value = mock_result

        result = await can_transition_state(
            sample_user_id, sample_use_case, "review", mock_async_db
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_use_case_publisher_can_publish(
        self, mock_async_db, sample_user_id, sample_use_case
    ):
        """use_case_publisher can publish use cases."""
        sample_use_case.lifecycle_state = "review"
        role1 = Mock(role="use_case_publisher")
        mock_result = Mock()
        mock_result.all.return_value = [role1]
        mock_async_db.execute.return_value = mock_result

        result = await can_transition_state(
            sample_user_id, sample_use_case, "published", mock_async_db
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_use_case_admin_can_publish(self, mock_async_db, sample_user_id, sample_use_case):
        """use_case_admin can publish use cases."""
        sample_use_case.lifecycle_state = "review"
        role1 = Mock(role="use_case_admin")
        mock_result = Mock()
        mock_result.all.return_value = [role1]
        mock_async_db.execute.return_value = mock_result

        result = await can_transition_state(
            sample_user_id, sample_use_case, "published", mock_async_db
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_developer_cannot_publish(self, mock_async_db, sample_user_id, sample_use_case):
        """Developer cannot publish use cases."""
        sample_use_case.lifecycle_state = "review"
        role1 = Mock(role="developer")
        mock_result = Mock()
        mock_result.all.return_value = [role1]
        mock_async_db.execute.return_value = mock_result

        result = await can_transition_state(
            sample_user_id, sample_use_case, "published", mock_async_db
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_use_case_publisher_can_reject(
        self, mock_async_db, sample_user_id, sample_use_case
    ):
        """use_case_publisher can reject (review → draft)."""
        sample_use_case.lifecycle_state = "review"
        role1 = Mock(role="use_case_publisher")
        mock_result = Mock()
        mock_result.all.return_value = [role1]
        mock_async_db.execute.return_value = mock_result

        result = await can_transition_state(sample_user_id, sample_use_case, "draft", mock_async_db)
        assert result is True

    @pytest.mark.asyncio
    async def test_use_case_publisher_can_archive(
        self, mock_async_db, sample_user_id, sample_use_case
    ):
        """use_case_publisher can archive published use cases."""
        sample_use_case.lifecycle_state = "published"
        role1 = Mock(role="use_case_publisher")
        mock_result = Mock()
        mock_result.all.return_value = [role1]
        mock_async_db.execute.return_value = mock_result

        result = await can_transition_state(
            sample_user_id, sample_use_case, "archived", mock_async_db
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_developer_cannot_archive(self, mock_async_db, sample_user_id, sample_use_case):
        """Developer cannot archive use cases."""
        sample_use_case.lifecycle_state = "published"
        role1 = Mock(role="developer")
        mock_result = Mock()
        mock_result.all.return_value = [role1]
        mock_async_db.execute.return_value = mock_result

        result = await can_transition_state(
            sample_user_id, sample_use_case, "archived", mock_async_db
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_invalid_transition_returns_false(
        self, mock_async_db, sample_user_id, sample_use_case
    ):
        """Invalid transitions return False."""
        sample_use_case.lifecycle_state = "draft"
        role1 = Mock(role="developer")
        mock_result = Mock()
        mock_result.all.return_value = [role1]
        mock_async_db.execute.return_value = mock_result

        result = await can_transition_state(
            sample_user_id, sample_use_case, "published", mock_async_db
        )
        assert result is False
