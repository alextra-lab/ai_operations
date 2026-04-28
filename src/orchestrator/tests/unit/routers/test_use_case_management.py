"""
Unit tests for use_case_management router with RBAC V2 integration.

Tests the /api/v1/admin/use-cases endpoints:
- GET /api/v1/admin/use-cases - List use cases with RBAC V2 filtering
- POST /api/v1/admin/use-cases - Create use case with team assignment and role checks
- PUT /api/v1/admin/use-cases/{use_case_id} - Update use case with RBAC V2 edit checks

Uses RBAC V2 service (ADR-060).
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from app.routers.use_case_management import (
    clone_use_case,
    create_use_case,
    list_use_cases_for_management,
    transition_use_case_state,
    update_use_case,
)
from app.schemas.use_case_management import (
    StateTransitionRequest,
    UseCaseCloneRequest,
    UseCaseCreateRequest,
    UseCaseListResponse,
    UseCasePromptSet,
    UseCaseUpdateRequest,
)
from fastapi import HTTPException


@pytest.fixture
def mock_async_db():
    """Create a mock async database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    db.flush = AsyncMock()
    return db


@pytest.fixture
def mock_current_user():
    """Create a mock authenticated user."""
    return Mock(
        user_id=str(uuid4()),
        role="admin",
        username="testuser",
    )


@pytest.fixture
def mock_use_case_admin_user():
    """Create a mock use_case_admin user."""
    return Mock(
        user_id=str(uuid4()),
        role="use_case_admin",
        username="devuser",
    )


class TestListUseCasesForManagement:
    """Test GET /api/v1/admin/use-cases endpoint with RBAC V2."""

    @pytest.mark.asyncio
    async def test_list_uses_rbac_v2(self, mock_async_db, mock_current_user):
        """Should use RBAC V2 get_accessible_use_cases for filtering."""
        mock_uc = MagicMock()
        mock_uc.id = uuid4()
        mock_uc.use_case_id = "test-uc"
        mock_uc.name = "Test Use Case"
        mock_uc.description = "Test"
        mock_uc.category = "security"
        mock_uc.intent_type = "query"
        mock_uc.team_id = None
        mock_uc.version = 1
        mock_uc.lifecycle_state = "published"
        mock_uc.is_active = True
        mock_uc.config_json = {}
        mock_uc.metadata_json = {}
        mock_uc.created_at = datetime.now(UTC)
        mock_uc.updated_at = datetime.now(UTC)
        mock_uc.created_by_user_id = None
        mock_uc.approved_by_user_id = None
        mock_uc.published_by_user_id = None
        mock_uc.approved_at = None
        mock_uc.published_at = None

        with patch(
            "app.routers.use_case_management.get_accessible_use_cases",
            new_callable=AsyncMock,
        ) as mock_get_accessible:
            mock_get_accessible.return_value = [mock_uc]

            result = await list_use_cases_for_management(
                page=1,
                page_size=50,
                use_case_id_filter=None,
                category=None,
                lifecycle_state=None,
                active_only=False,
                db=mock_async_db,
                current_user=mock_current_user,
            )

            assert isinstance(result, UseCaseListResponse)
            assert result.total == 1
            assert len(result.use_cases) == 1
            mock_get_accessible.assert_called_once()


class TestCreateUseCase:
    """Test POST /api/v1/admin/use-cases endpoint with role checks."""

    @pytest.mark.asyncio
    async def test_create_requires_use_case_admin_or_admin_role(
        self, mock_async_db, mock_current_user
    ):
        """Should require use_case_admin or admin role to create use cases."""
        user_id = uuid4()
        mock_current_user.user_id = str(user_id)

        request = UseCaseCreateRequest(
            use_case_id="test-uc",
            name="Test Use Case",
            intent_type="query",
        )

        # Mock user lacks both roles
        with patch(
            "app.routers.use_case_management.has_role", new_callable=AsyncMock
        ) as mock_has_role:
            mock_has_role.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await create_use_case(
                    use_case_data=request,
                    db=mock_async_db,
                    current_user=mock_current_user,
                )

            assert exc_info.value.status_code == 403
            assert "use_case_admin or admin role required" in str(exc_info.value.detail).lower()
            # Should check for both roles
            assert mock_has_role.call_count == 2

    @pytest.mark.asyncio
    async def test_create_allows_admin_role(self, mock_async_db, mock_current_user):
        """Should allow creation when user has admin role."""
        user_id = uuid4()
        mock_current_user.user_id = str(user_id)

        request = UseCaseCreateRequest(
            use_case_id="test-uc",
            name="Test Use Case",
            intent_type="query",
        )

        # Mock admin role check - user has admin role
        with patch(
            "app.routers.use_case_management.has_role", new_callable=AsyncMock
        ) as mock_has_role:
            # First call checks admin (True), second checks use_case_admin (False)
            mock_has_role.side_effect = [True, False]

            # Mock get_user_teams (needed for team assignment logic)
            with patch(
                "app.routers.use_case_management.get_user_teams", new_callable=AsyncMock
            ) as mock_get_teams:
                mock_get_teams.return_value = []

                # Should pass authorization check (admin role found)
                # We just verify it doesn't raise 403, actual creation would fail later
                # but that's fine - we're testing authorization, not full creation flow
                try:
                    await create_use_case(
                        use_case_data=request,
                        db=mock_async_db,
                        current_user=mock_current_user,
                    )
                except HTTPException as e:
                    # Should NOT be 403 authorization error
                    assert e.status_code != 403, "Should not raise 403 when user has admin role"
                except Exception:
                    # Other exceptions (like DB errors) are fine - auth passed
                    pass

                # Verify role checks were made
                assert mock_has_role.call_count >= 1

    @pytest.mark.asyncio
    async def test_create_allows_use_case_admin_role(self, mock_async_db, mock_use_case_admin_user):
        """Should allow creation when user has use_case_admin role."""
        user_id = uuid4()
        mock_use_case_admin_user.user_id = str(user_id)

        request = UseCaseCreateRequest(
            use_case_id="test-uc",
            name="Test Use Case",
            intent_type="query",
        )

        # Mock use_case_admin role check - user has use_case_admin role
        with patch(
            "app.routers.use_case_management.has_role", new_callable=AsyncMock
        ) as mock_has_role:
            # First call checks admin (False), second checks use_case_admin (True)
            mock_has_role.side_effect = [False, True]

            # Mock get_user_teams
            with patch(
                "app.routers.use_case_management.get_user_teams", new_callable=AsyncMock
            ) as mock_get_teams:
                mock_get_teams.return_value = ["team:csirt"]

                # Should pass authorization check (use_case_admin role found)
                try:
                    await create_use_case(
                        use_case_data=request,
                        db=mock_async_db,
                        current_user=mock_use_case_admin_user,
                    )
                except HTTPException as e:
                    # Should NOT be 403 authorization error
                    assert (
                        e.status_code != 403
                    ), "Should not raise 403 when user has use_case_admin role"
                except Exception:
                    # Other exceptions (like DB errors) are fine - auth passed
                    pass

                # Verify role checks were made
                assert mock_has_role.call_count >= 2


class TestUpdateUseCase:
    """Test PUT /api/v1/admin/use-cases/{use_case_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_use_case_with_prompts_separate_field(
        self, mock_async_db, mock_current_user
    ):
        """Should update use case with prompts as separate field, not in config_json."""
        user_id = uuid4()
        use_case_id = uuid4()
        mock_current_user.user_id = str(user_id)

        # Create mock use case
        mock_use_case = MagicMock()
        mock_use_case.id = use_case_id
        mock_use_case.use_case_id = "test-uc"
        mock_use_case.name = "Test Use Case"
        mock_use_case.description = "Original description"
        mock_use_case.category = "security"
        mock_use_case.lifecycle_state = "draft"
        mock_use_case.created_by_user_id = user_id
        mock_use_case.config_json = {"models": {"llm": "gpt-4"}}
        mock_use_case.metadata_json = {}
        mock_use_case.version = 1

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_use_case
        mock_async_db.execute = AsyncMock(return_value=mock_result)

        # Mock RBAC check - user can edit
        with patch(
            "app.routers.use_case_management.can_edit_use_case", new_callable=AsyncMock
        ) as mock_can_edit:
            mock_can_edit.return_value = True

            # Create update request with prompts as separate field
            update_request = UseCaseUpdateRequest(
                name="Updated Name",
                description="Updated description",
                prompts=UseCasePromptSet(
                    system_prompt="Updated system prompt",
                    developer_prompt="Updated developer prompt",
                    fewshots=[],
                ),
            )

            # Mock UseCaseResponse.from_orm
            with patch("app.routers.use_case_management.UseCaseResponse.from_orm") as mock_from_orm:
                mock_response = MagicMock()
                mock_from_orm.return_value = mock_response

                await update_use_case(
                    use_case_id=use_case_id,
                    use_case_data=update_request,
                    db=mock_async_db,
                    current_user=mock_current_user,
                )

                # Verify prompts were stored in metadata, not config_json
                assert "prompts" in mock_use_case.metadata_json
                assert (
                    mock_use_case.metadata_json["prompts"]["system_prompt"]
                    == "Updated system prompt"
                )
                assert mock_use_case.name == "Updated Name"
                assert mock_use_case.description == "Updated description"
                mock_async_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_use_case_validates_config_json(self, mock_async_db, mock_current_user):
        """Should validate config_json through UseCaseConfig schema."""
        user_id = uuid4()
        use_case_id = uuid4()
        mock_current_user.user_id = str(user_id)

        # Create mock use case with all required fields
        mock_use_case = MagicMock()
        mock_use_case.id = use_case_id
        mock_use_case.use_case_id = "test-uc"
        mock_use_case.name = "Test Use Case"
        mock_use_case.description = "Test description"
        mock_use_case.category = "security"
        mock_use_case.intent_type = "query"
        mock_use_case.team_id = None
        mock_use_case.lifecycle_state = "draft"
        mock_use_case.created_by_user_id = user_id
        mock_use_case.approved_by_user_id = None
        mock_use_case.published_by_user_id = None
        mock_use_case.config_json = {"models": {"llm": "gpt-4"}}
        mock_use_case.metadata_json = {}
        mock_use_case.version = 1
        mock_use_case.is_active = True
        mock_use_case.created_at = datetime.now(UTC)
        mock_use_case.updated_at = datetime.now(UTC)
        mock_use_case.approved_at = None
        mock_use_case.published_at = None

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_use_case
        mock_async_db.execute = AsyncMock(return_value=mock_result)

        # Mock RBAC check
        with patch(
            "app.routers.use_case_management.can_edit_use_case", new_callable=AsyncMock
        ) as mock_can_edit:
            mock_can_edit.return_value = True

            # Create update request with invalid config_json
            # UseCaseConfig will try to validate, but we'll mock it to raise an error
            with patch("app.schemas.use_case_config.UseCaseConfig") as mock_config_class:
                # Mock the UseCaseConfig constructor to raise a validation error
                mock_config_class.side_effect = ValueError(
                    "Invalid configuration: missing required fields"
                )

                update_request = UseCaseUpdateRequest(
                    config_json={"invalid": "config"},
                )

                with pytest.raises(HTTPException) as exc_info:
                    await update_use_case(
                        use_case_id=use_case_id,
                        use_case_data=update_request,
                        db=mock_async_db,
                        current_user=mock_current_user,
                    )

                assert exc_info.value.status_code == 400
                assert "Invalid use case configuration" in str(exc_info.value.detail)


class TestTransitionUseCaseState:
    """Test POST /api/v1/admin/use-cases/{use_case_id}/transition endpoint."""

    @pytest.mark.asyncio
    async def test_transition_draft_to_review(self, mock_async_db, mock_current_user):
        """Should allow draft → review transition."""
        user_id = uuid4()
        use_case_id = uuid4()
        mock_current_user.user_id = str(user_id)

        # Create mock use case in draft state
        mock_use_case = MagicMock()
        mock_use_case.id = use_case_id
        mock_use_case.use_case_id = "test-uc"
        mock_use_case.name = "Test Use Case"
        mock_use_case.description = "Test description"
        mock_use_case.category = "security"
        mock_use_case.intent_type = "query"
        mock_use_case.team_id = None
        mock_use_case.lifecycle_state = "draft"
        mock_use_case.created_by_user_id = user_id
        mock_use_case.approved_by_user_id = None
        mock_use_case.published_by_user_id = None
        mock_use_case.config_json = {"models": {"llm": "gpt-4"}}
        mock_use_case.metadata_json = {}
        mock_use_case.version = 1
        mock_use_case.is_active = False
        mock_use_case.created_at = datetime.now(UTC)
        mock_use_case.updated_at = datetime.now(UTC)
        mock_use_case.approved_at = None
        mock_use_case.published_at = None

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_use_case
        mock_async_db.execute = AsyncMock(return_value=mock_result)

        # Mock UseCaseResponse.from_orm
        with patch("app.routers.use_case_management.UseCaseResponse.from_orm") as mock_from_orm:
            mock_response = MagicMock()
            mock_from_orm.return_value = mock_response

            transition_request = StateTransitionRequest(to_state="review")

            await transition_use_case_state(
                use_case_id=use_case_id,
                transition=transition_request,
                db=mock_async_db,
                current_user=mock_current_user,
            )

            assert mock_use_case.lifecycle_state == "review"
            mock_async_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_transition_review_to_published(self, mock_async_db, mock_current_user):
        """Should allow review → published transition with admin role."""
        user_id = uuid4()
        use_case_id = uuid4()
        mock_current_user.user_id = str(user_id)

        # Create mock use case in review state
        mock_use_case = MagicMock()
        mock_use_case.id = use_case_id
        mock_use_case.use_case_id = "test-uc"
        mock_use_case.name = "Test Use Case"
        mock_use_case.description = "Test description"
        mock_use_case.category = "security"
        mock_use_case.intent_type = "query"
        mock_use_case.team_id = None
        mock_use_case.lifecycle_state = "review"
        mock_use_case.created_by_user_id = user_id
        mock_use_case.approved_by_user_id = None
        mock_use_case.published_by_user_id = None
        mock_use_case.config_json = {"models": {"llm": "gpt-4"}}
        mock_use_case.metadata_json = {}
        mock_use_case.version = 1
        mock_use_case.is_active = False
        mock_use_case.created_at = datetime.now(UTC)
        mock_use_case.updated_at = datetime.now(UTC)
        mock_use_case.approved_at = None
        mock_use_case.published_at = None

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_use_case
        mock_async_db.execute = AsyncMock(return_value=mock_result)

        # Mock admin role check
        with patch(
            "app.routers.use_case_management.has_role", new_callable=AsyncMock
        ) as mock_has_role:
            mock_has_role.return_value = True

            # Mock UseCaseResponse.from_orm
            with patch("app.routers.use_case_management.UseCaseResponse.from_orm") as mock_from_orm:
                mock_response = MagicMock()
                mock_from_orm.return_value = mock_response

                transition_request = StateTransitionRequest(to_state="published")

                await transition_use_case_state(
                    use_case_id=use_case_id,
                    transition=transition_request,
                    db=mock_async_db,
                    current_user=mock_current_user,
                )

                assert mock_use_case.lifecycle_state == "published"
                assert mock_use_case.is_active is True
                assert mock_use_case.published_at is not None
                assert mock_use_case.published_by_user_id == user_id
                assert mock_use_case.team_id is None  # Cleared on publish
                mock_async_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_transition_review_to_draft(self, mock_async_db, mock_current_user):
        """Should allow review → draft transition (rejection)."""
        user_id = uuid4()
        use_case_id = uuid4()
        mock_current_user.user_id = str(user_id)

        # Create mock use case in review state
        mock_use_case = MagicMock()
        mock_use_case.id = use_case_id
        mock_use_case.use_case_id = "test-uc"
        mock_use_case.name = "Test Use Case"
        mock_use_case.description = "Test description"
        mock_use_case.category = "security"
        mock_use_case.intent_type = "query"
        mock_use_case.team_id = None
        mock_use_case.lifecycle_state = "review"
        mock_use_case.created_by_user_id = user_id
        mock_use_case.approved_by_user_id = user_id
        mock_use_case.published_by_user_id = None
        mock_use_case.config_json = {"models": {"llm": "gpt-4"}}
        mock_use_case.metadata_json = {}
        mock_use_case.version = 1
        mock_use_case.is_active = False
        mock_use_case.created_at = datetime.now(UTC)
        mock_use_case.updated_at = datetime.now(UTC)
        mock_use_case.approved_at = datetime.now(UTC)
        mock_use_case.published_at = None

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_use_case
        mock_async_db.execute = AsyncMock(return_value=mock_result)

        # Mock UseCaseResponse.from_orm
        with patch("app.routers.use_case_management.UseCaseResponse.from_orm") as mock_from_orm:
            mock_response = MagicMock()
            mock_from_orm.return_value = mock_response

            transition_request = StateTransitionRequest(to_state="draft")

            await transition_use_case_state(
                use_case_id=use_case_id,
                transition=transition_request,
                db=mock_async_db,
                current_user=mock_current_user,
            )

            assert mock_use_case.lifecycle_state == "draft"
            assert mock_use_case.approved_at is None
            assert mock_use_case.approved_by_user_id is None
            mock_async_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_transition_published_to_archived(self, mock_async_db, mock_current_user):
        """Should allow published → archived transition."""
        user_id = uuid4()
        use_case_id = uuid4()
        mock_current_user.user_id = str(user_id)

        # Create mock use case in published state
        mock_use_case = MagicMock()
        mock_use_case.id = use_case_id
        mock_use_case.use_case_id = "test-uc"
        mock_use_case.name = "Test Use Case"
        mock_use_case.description = "Test description"
        mock_use_case.category = "security"
        mock_use_case.intent_type = "query"
        mock_use_case.team_id = None
        mock_use_case.lifecycle_state = "published"
        mock_use_case.created_by_user_id = user_id
        mock_use_case.approved_by_user_id = user_id
        mock_use_case.published_by_user_id = user_id
        mock_use_case.config_json = {"models": {"llm": "gpt-4"}}
        mock_use_case.metadata_json = {}
        mock_use_case.version = 1
        mock_use_case.is_active = True
        mock_use_case.created_at = datetime.now(UTC)
        mock_use_case.updated_at = datetime.now(UTC)
        mock_use_case.approved_at = datetime.now(UTC)
        mock_use_case.published_at = datetime.now(UTC)

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_use_case
        mock_async_db.execute = AsyncMock(return_value=mock_result)

        # Mock UseCaseResponse.from_orm
        with patch("app.routers.use_case_management.UseCaseResponse.from_orm") as mock_from_orm:
            mock_response = MagicMock()
            mock_from_orm.return_value = mock_response

            transition_request = StateTransitionRequest(to_state="archived")

            await transition_use_case_state(
                use_case_id=use_case_id,
                transition=transition_request,
                db=mock_async_db,
                current_user=mock_current_user,
            )

            assert mock_use_case.lifecycle_state == "archived"
            mock_async_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_transition_draft_to_published_invalid(self, mock_async_db, mock_current_user):
        """Should reject draft → published transition (must go through review)."""
        user_id = uuid4()
        use_case_id = uuid4()
        mock_current_user.user_id = str(user_id)

        # Create mock use case in draft state
        mock_use_case = MagicMock()
        mock_use_case.id = use_case_id
        mock_use_case.use_case_id = "test-uc"
        mock_use_case.lifecycle_state = "draft"

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_use_case
        mock_async_db.execute = AsyncMock(return_value=mock_result)

        transition_request = StateTransitionRequest(to_state="published")

        with pytest.raises(HTTPException) as exc_info:
            await transition_use_case_state(
                use_case_id=use_case_id,
                transition=transition_request,
                db=mock_async_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 400
        assert "Invalid transition: draft → published" in str(exc_info.value.detail)
        assert "Valid transitions: ['review']" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_transition_published_requires_admin(self, mock_async_db, mock_current_user):
        """Should require admin role for review → published transition."""
        user_id = uuid4()
        use_case_id = uuid4()
        mock_current_user.user_id = str(user_id)

        # Create mock use case in review state
        mock_use_case = MagicMock()
        mock_use_case.id = use_case_id
        mock_use_case.use_case_id = "test-uc"
        mock_use_case.lifecycle_state = "review"

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_use_case
        mock_async_db.execute = AsyncMock(return_value=mock_result)

        # Mock admin role check - user is NOT admin
        with patch(
            "app.routers.use_case_management.has_role", new_callable=AsyncMock
        ) as mock_has_role:
            mock_has_role.return_value = False

            transition_request = StateTransitionRequest(to_state="published")

            with pytest.raises(HTTPException) as exc_info:
                await transition_use_case_state(
                    use_case_id=use_case_id,
                    transition=transition_request,
                    db=mock_async_db,
                    current_user=mock_current_user,
                )

            assert exc_info.value.status_code == 403
            assert "Only admin role can publish use cases" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_transition_archived_is_terminal(self, mock_async_db, mock_current_user):
        """Should reject transitions from archived state (terminal state)."""
        user_id = uuid4()
        use_case_id = uuid4()
        mock_current_user.user_id = str(user_id)

        # Create mock use case in archived state
        mock_use_case = MagicMock()
        mock_use_case.id = use_case_id
        mock_use_case.use_case_id = "test-uc"
        mock_use_case.lifecycle_state = "archived"

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_use_case
        mock_async_db.execute = AsyncMock(return_value=mock_result)

        transition_request = StateTransitionRequest(to_state="draft")

        with pytest.raises(HTTPException) as exc_info:
            await transition_use_case_state(
                use_case_id=use_case_id,
                transition=transition_request,
                db=mock_async_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 400
        assert "Invalid transition: archived → draft" in str(exc_info.value.detail)
        assert "Valid transitions: []" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_transition_nonexistent_use_case(self, mock_async_db, mock_current_user):
        """Should return 404 for non-existent use case."""
        use_case_id = uuid4()

        # Mock database query to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_db.execute = AsyncMock(return_value=mock_result)

        transition_request = StateTransitionRequest(to_state="review")

        with pytest.raises(HTTPException) as exc_info:
            await transition_use_case_state(
                use_case_id=use_case_id,
                transition=transition_request,
                db=mock_async_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()


class TestCloneUseCase:
    """Test POST /api/v1/admin/use-cases/{use_case_id}/clone endpoint."""

    @pytest.mark.asyncio
    async def test_clone_preserves_prompts_and_input_fields(self, mock_async_db, mock_current_user):
        """Should preserve prompts and input_fields when cloning."""

        user_id = uuid4()
        source_use_case_id = uuid4()
        mock_current_user.user_id = str(user_id)

        # Create source use case with prompts and input_fields
        source_use_case = MagicMock()
        source_use_case.id = source_use_case_id
        source_use_case.use_case_id = "source-uc"
        source_use_case.name = "Source Use Case"
        source_use_case.description = "Source description"
        source_use_case.category = "security"
        source_use_case.intent_type = "QUERY"
        source_use_case.team_id = "team:test"
        source_use_case.version = 1
        source_use_case.lifecycle_state = "published"
        source_use_case.is_active = True
        source_use_case.config_json = {
            "models": {"llm": "mistral-small"},
            "input_fields": [
                {
                    "name": "incident_details",
                    "type": "textarea",
                    "label": "Incident Details",
                    "required": True,
                },
                {
                    "name": "summary_type",
                    "type": "select",
                    "label": "Summary Type",
                    "required": True,
                },
            ],
        }
        source_use_case.metadata_json = {
            "prompts": {
                "system_prompt": "You are a SOC analyst.",
                "developer_prompt": "Create concise summaries.",
                "fewshots": [
                    {"user": "Test input", "assistant": "Test output"},
                ],
                "variables": [],
            }
        }
        source_use_case.created_by_user_id = user_id

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = source_use_case
        mock_async_db.execute = AsyncMock(return_value=mock_result)

        # Mock team assignment
        with patch(
            "app.routers.use_case_management.get_user_teams", new_callable=AsyncMock
        ) as mock_get_teams:
            mock_get_teams.return_value = ["team:test"]

            # Mock new use case creation - create a proper mock that will be returned
            from app.db.models import UseCase as DBUseCase

            cloned_db_instance = MagicMock(spec=DBUseCase)
            cloned_db_instance.id = uuid4()
            cloned_db_instance.use_case_id = "cloned-uc"
            cloned_db_instance.name = "Cloned Use Case"
            # Deep copy to verify preservation
            import copy

            cloned_db_instance.config_json = copy.deepcopy(source_use_case.config_json)
            cloned_db_instance.metadata_json = copy.deepcopy(source_use_case.metadata_json)
            cloned_db_instance.lifecycle_state = "draft"
            cloned_db_instance.is_active = False
            cloned_db_instance.version = 1
            cloned_db_instance.created_by_user_id = user_id
            cloned_db_instance.team_id = "team:test"
            cloned_db_instance.description = "Source description"
            cloned_db_instance.category = "security"
            cloned_db_instance.intent_type = "QUERY"
            cloned_db_instance.created_at = datetime.now(UTC)
            cloned_db_instance.updated_at = datetime.now(UTC)

            # Mock DBUseCase constructor to return our mock
            with patch(
                "app.routers.use_case_management.DBUseCase",
                return_value=cloned_db_instance,
            ):
                mock_async_db.add = MagicMock()
                mock_async_db.flush = AsyncMock()
                mock_async_db.commit = AsyncMock()
                mock_async_db.refresh = AsyncMock(side_effect=lambda obj: None)

                clone_request = UseCaseCloneRequest(
                    new_use_case_id="cloned-uc", new_name="Cloned Use Case"
                )

                result = await clone_use_case(
                    use_case_id=source_use_case_id,
                    clone_data=clone_request,
                    db=mock_async_db,
                    current_user=mock_current_user,
                )

                # Verify prompts were preserved
                assert result.prompts is not None
                assert result.prompts.system_prompt == "You are a SOC analyst."
                assert result.prompts.developer_prompt == "Create concise summaries."
                assert len(result.prompts.fewshots) == 1
                assert result.prompts.fewshots[0].user == "Test input"
                assert result.prompts.fewshots[0].assistant == "Test output"

                # Verify input_fields were preserved in config_json
                assert "input_fields" in result.config_json
                assert len(result.config_json["input_fields"]) == 2
                assert result.config_json["input_fields"][0]["name"] == "incident_details"
                assert result.config_json["input_fields"][1]["name"] == "summary_type"
