"""
Unit tests for use_cases router (P5-A10: Async migration).

Tests the /api/v1/use-cases endpoints:
- GET /available - List available use cases for current user
- GET /{use_case_id} - Get use case details
- GET /{use_case_id}/config - Get use case configuration
- POST /{use_case_id}/execute - Execute a use case

Uses async patterns per ADR-022.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from app.routers.use_cases import (
    get_available_use_cases,
    get_db,
    get_use_case_config,
    get_use_case_details,
)
from app.schemas.use_case import UseCaseListResponse
from app.schemas.use_case_management import UseCaseResponse
from fastapi import HTTPException


@pytest.fixture
def mock_async_db():
    """Create a mock async database session."""
    return AsyncMock()


@pytest.fixture
def mock_current_user():
    """Create a mock authenticated user."""
    return Mock(
        user_id=str(uuid4()),
        role="user",
        username="testuser",
    )


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user."""
    return Mock(
        user_id=str(uuid4()),
        role="admin",
        username="admin",
    )


class TestGetDb:
    """Test the async get_db dependency."""

    @pytest.mark.asyncio
    async def test_get_db_yields_async_session(self):
        """get_db should yield an async session and close it."""
        with patch("app.routers.use_cases.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session

            async for session in get_db():
                assert session == mock_session

            # Verify session was closed
            mock_session.close.assert_called_once()


class TestGetAvailableUseCases:
    """Test GET /api/v1/use-cases/available endpoint."""

    @pytest.mark.asyncio
    async def test_returns_use_cases_for_user(self, mock_async_db, mock_current_user):
        """Should return available use cases for authenticated user."""
        # Create a mock that behaves like a UseCase model
        # Use MagicMock with configured return values for each attribute
        mock_uc = MagicMock()
        mock_uc.id = uuid4()
        mock_uc.name = "Test Use Case"
        mock_uc.description = "A test use case"
        mock_uc.category = "security"
        mock_uc.intent_type = "query"  # Valid RequestType value
        mock_uc.team_id = None
        mock_uc.is_active = True
        mock_uc.lifecycle_state = "published"
        mock_uc.version = "1.0"
        mock_uc.updated_at = None

        with patch("app.routers.use_cases.get_accessible_use_cases") as mock_get_accessible:
            mock_get_accessible.return_value = [mock_uc]

            result = await get_available_use_cases(
                category=None,
                intent_type=None,
                db=mock_async_db,
                current_user=mock_current_user,
            )

            assert isinstance(result, UseCaseListResponse)
            assert result.total == 1
            assert len(result.use_cases) == 1
            assert result.use_cases[0].name == "Test Use Case"

    @pytest.mark.asyncio
    async def test_filters_inactive_use_cases(self, mock_async_db, mock_current_user):
        """Should filter out inactive use cases."""
        # Create mocks with direct attribute values
        mock_uc_active = MagicMock()
        mock_uc_active.id = uuid4()
        mock_uc_active.name = "Active UC"
        mock_uc_active.description = "Active"
        mock_uc_active.category = "security"
        mock_uc_active.intent_type = "query"
        mock_uc_active.team_id = None
        mock_uc_active.is_active = True
        mock_uc_active.lifecycle_state = "published"
        mock_uc_active.version = "1.0"
        mock_uc_active.updated_at = None

        mock_uc_inactive = MagicMock()
        mock_uc_inactive.id = uuid4()
        mock_uc_inactive.name = "Inactive UC"
        mock_uc_inactive.description = "Inactive"
        mock_uc_inactive.category = "security"
        mock_uc_inactive.intent_type = "query"
        mock_uc_inactive.team_id = None
        mock_uc_inactive.is_active = False
        mock_uc_inactive.lifecycle_state = "published"
        mock_uc_inactive.version = "1.0"
        mock_uc_inactive.updated_at = None

        with patch("app.routers.use_cases.get_accessible_use_cases") as mock_get_accessible:
            # RBAC returns both (filtering happens in endpoint)
            mock_get_accessible.return_value = [mock_uc_active, mock_uc_inactive]

            result = await get_available_use_cases(
                category=None,
                intent_type=None,
                db=mock_async_db,
                current_user=mock_current_user,
            )

            # Should only include active, published use cases
            assert result.total == 1
            assert result.use_cases[0].name == "Active UC"

    @pytest.mark.asyncio
    async def test_filters_by_category(self, mock_async_db, mock_current_user):
        """Should filter use cases by category."""
        mock_uc_security = MagicMock()
        mock_uc_security.id = uuid4()
        mock_uc_security.name = "Security UC"
        mock_uc_security.description = "Security use case"
        mock_uc_security.category = "security"
        mock_uc_security.intent_type = "query"
        mock_uc_security.team_id = None
        mock_uc_security.is_active = True
        mock_uc_security.lifecycle_state = "published"
        mock_uc_security.version = "1.0"
        mock_uc_security.updated_at = None

        mock_uc_other = MagicMock()
        mock_uc_other.id = uuid4()
        mock_uc_other.name = "Other UC"
        mock_uc_other.description = "Other use case"
        mock_uc_other.category = "other"
        mock_uc_other.intent_type = "query"
        mock_uc_other.team_id = None
        mock_uc_other.is_active = True
        mock_uc_other.lifecycle_state = "published"
        mock_uc_other.version = "1.0"
        mock_uc_other.updated_at = None

        with patch("app.routers.use_cases.get_accessible_use_cases") as mock_get_accessible:
            mock_get_accessible.return_value = [mock_uc_security, mock_uc_other]

            result = await get_available_use_cases(
                category="security",
                intent_type=None,
                db=mock_async_db,
                current_user=mock_current_user,
            )

            assert result.total == 1
            assert result.use_cases[0].category == "security"

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_no_access(self, mock_async_db, mock_current_user):
        """Should return empty list when user has no accessible use cases."""
        with patch("app.routers.use_cases.get_accessible_use_cases") as mock_get_accessible:
            mock_get_accessible.return_value = []

            result = await get_available_use_cases(
                category=None,
                intent_type=None,
                db=mock_async_db,
                current_user=mock_current_user,
            )

            assert result.total == 0
            assert result.use_cases == []

    @pytest.mark.asyncio
    async def test_handles_database_error(self, mock_async_db, mock_current_user):
        """Should raise HTTPException on database error."""
        with patch("app.routers.use_cases.get_accessible_use_cases") as mock_get_accessible:
            mock_get_accessible.side_effect = Exception("Database error")

            with pytest.raises(HTTPException) as exc_info:
                await get_available_use_cases(
                    category=None,
                    intent_type=None,
                    db=mock_async_db,
                    current_user=mock_current_user,
                )

            assert exc_info.value.status_code == 500
            assert "Failed to fetch use cases" in str(exc_info.value.detail)


class TestExecuteUseCase:
    """Test POST /api/v1/use-cases/{use_case_id}/execute endpoint."""

    @pytest.mark.asyncio
    async def test_returns_404_for_nonexistent_use_case(self, mock_async_db, mock_current_user):
        """Should return 404 for non-existent use case."""
        from app.routers.use_cases import execute_use_case
        from app.schemas.use_case import UseCaseExecution

        use_case_id = uuid4()
        execution = UseCaseExecution(inputs={"query": "test"})

        # Mock DB query to return None (use case not found)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_db.execute.return_value = mock_result

        # Mock JWT validator
        mock_token_creds = Mock(credentials="fake_token")

        with pytest.raises(HTTPException) as exc_info:
            await execute_use_case(
                use_case_id=use_case_id,
                execution=execution,
                db=mock_async_db,
                current_user=mock_current_user,
                raw_token_creds=mock_token_creds,
            )

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_returns_403_for_unauthorized_access(self, mock_async_db, mock_current_user):
        """Should return 403 when user lacks access to use case."""
        from app.routers.use_cases import execute_use_case
        from app.schemas.use_case import UseCaseExecution

        use_case_id = uuid4()
        execution = UseCaseExecution(inputs={"query": "test"})

        # Mock use case exists
        mock_use_case = Mock(
            id=use_case_id,
            name="Test UC",
            is_active=True,
            lifecycle_state="published",
            config_json={},
        )
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_use_case
        mock_async_db.execute.return_value = mock_result

        # Mock JWT validator
        mock_token_creds = Mock(credentials="fake_token")

        with patch("app.routers.use_cases.user_can_access_use_case") as mock_access:
            mock_access.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await execute_use_case(
                    use_case_id=use_case_id,
                    execution=execution,
                    db=mock_async_db,
                    current_user=mock_current_user,
                    raw_token_creds=mock_token_creds,
                )

            assert exc_info.value.status_code == 403
            assert "access denied" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_returns_401_for_missing_token(self, mock_async_db, mock_current_user):
        """Should return 401 when JWT token is missing."""
        from app.routers.use_cases import execute_use_case
        from app.schemas.use_case import UseCaseExecution

        use_case_id = uuid4()
        execution = UseCaseExecution(inputs={"query": "test"})

        # Mock use case exists
        mock_use_case = Mock(
            id=use_case_id,
            name="Test UC",
            is_active=True,
            lifecycle_state="published",
            config_json={"input_fields": []},
        )
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_use_case
        mock_async_db.execute.return_value = mock_result

        with patch(
            "app.routers.use_cases.user_can_access_use_case", new_callable=AsyncMock
        ) as mock_access:
            mock_access.return_value = True

            with pytest.raises(HTTPException) as exc_info:
                await execute_use_case(
                    use_case_id=use_case_id,
                    execution=execution,
                    db=mock_async_db,
                    current_user=mock_current_user,
                    raw_token_creds=None,
                )

            assert exc_info.value.status_code == 401
            assert "missing jwt token" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_returns_400_for_missing_required_input(self, mock_async_db, mock_current_user):
        """Should return 400 when required input field is missing."""
        from app.routers.use_cases import execute_use_case
        from app.schemas.use_case import UseCaseExecution

        use_case_id = uuid4()
        execution = UseCaseExecution(inputs={})  # Missing required field

        # Mock use case with required field
        mock_use_case = Mock(
            id=use_case_id,
            name="Test UC",
            is_active=True,
            lifecycle_state="published",
            config_json={"input_fields": [{"name": "query", "required": True}]},
        )
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_use_case
        mock_async_db.execute.return_value = mock_result

        # Mock JWT validator
        mock_token_creds = Mock(credentials="fake_token")

        with patch(
            "app.routers.use_cases.user_can_access_use_case", new_callable=AsyncMock
        ) as mock_access:
            mock_access.return_value = True

            with pytest.raises(HTTPException) as exc_info:
                await execute_use_case(
                    use_case_id=use_case_id,
                    execution=execution,
                    db=mock_async_db,
                    current_user=mock_current_user,
                    raw_token_creds=mock_token_creds,
                )

            assert exc_info.value.status_code == 400
            assert "missing required input" in str(exc_info.value.detail).lower()


class TestGetUseCaseDetails:
    """Test GET /api/v1/use-cases/{use_case_id} endpoint."""

    @pytest.mark.asyncio
    async def test_returns_use_case_details(self, mock_async_db, mock_current_user):
        """Should return use case details for accessible use case."""
        use_case_id = uuid4()
        uuid4()

        # Create mock use case
        mock_use_case = MagicMock()
        mock_use_case.id = use_case_id
        mock_use_case.use_case_id = "test-use-case"
        mock_use_case.name = "Test Use Case"
        mock_use_case.description = "Test description"
        mock_use_case.category = "security"
        mock_use_case.intent_type = "query"
        mock_use_case.team_id = None
        mock_use_case.version = 1
        mock_use_case.lifecycle_state = "published"
        mock_use_case.is_active = True
        mock_use_case.config_json = {"test": "config"}
        mock_use_case.metadata_json = {}
        mock_use_case.created_at = datetime.now(UTC)
        mock_use_case.updated_at = datetime.now(UTC)
        mock_use_case.created_by_user_id = None
        mock_use_case.approved_by_user_id = None
        mock_use_case.published_by_user_id = None
        mock_use_case.approved_at = None
        mock_use_case.published_at = None

        # Mock DB query
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_use_case
        mock_async_db.execute.return_value = mock_result

        # Mock RBAC access check
        with patch(
            "app.routers.use_cases.user_can_access_use_case", new_callable=AsyncMock
        ) as mock_access:
            mock_access.return_value = True

            result = await get_use_case_details(
                use_case_id=use_case_id,
                db=mock_async_db,
                current_user=mock_current_user,
            )

            assert isinstance(result, UseCaseResponse)
            assert result.id == use_case_id
            assert result.name == "Test Use Case"
            assert result.use_case_id == "test-use-case"

    @pytest.mark.asyncio
    async def test_returns_404_for_nonexistent_use_case(self, mock_async_db, mock_current_user):
        """Should return 404 for non-existent use case."""
        use_case_id = uuid4()

        # Mock DB query to return None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_use_case_details(
                use_case_id=use_case_id,
                db=mock_async_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_returns_404_for_inactive_use_case(self, mock_async_db, mock_current_user):
        """Should return 404 for inactive use case."""
        use_case_id = uuid4()

        # Mock inactive use case
        mock_use_case = MagicMock()
        mock_use_case.id = use_case_id
        mock_use_case.is_active = False
        mock_use_case.lifecycle_state = "published"

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None  # Query filters out inactive
        mock_async_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_use_case_details(
                use_case_id=use_case_id,
                db=mock_async_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_403_for_unauthorized_access(self, mock_async_db, mock_current_user):
        """Should return 403 when user lacks access to use case."""
        use_case_id = uuid4()

        # Mock use case exists
        mock_use_case = MagicMock()
        mock_use_case.id = use_case_id
        mock_use_case.is_active = True
        mock_use_case.lifecycle_state = "published"

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_use_case
        mock_async_db.execute.return_value = mock_result

        # Mock RBAC access check returns False
        with patch("app.routers.use_cases.user_can_access_use_case") as mock_access:
            mock_access.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await get_use_case_details(
                    use_case_id=use_case_id,
                    db=mock_async_db,
                    current_user=mock_current_user,
                )

            assert exc_info.value.status_code == 403
            assert "access denied" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_handles_database_error(self, mock_async_db, mock_current_user):
        """Should raise HTTPException on database error."""
        use_case_id = uuid4()

        mock_async_db.execute.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await get_use_case_details(
                use_case_id=use_case_id,
                db=mock_async_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 500
        assert "Failed to retrieve use case" in str(exc_info.value.detail)


class TestGetUseCaseConfig:
    """Test GET /api/v1/use-cases/{use_case_id}/config endpoint."""

    @pytest.mark.asyncio
    async def test_returns_use_case_config(self, mock_async_db, mock_current_user):
        """Should return use case configuration for accessible use case."""
        use_case_id = uuid4()

        # Create mock use case with config
        mock_use_case = MagicMock()
        mock_use_case.id = use_case_id
        mock_use_case.use_case_id = "test-use-case"
        mock_use_case.name = "Test Use Case"
        mock_use_case.description = "Test description"
        mock_use_case.category = "test_category"
        mock_use_case.intent_type = "query"
        mock_use_case.is_active = True
        mock_use_case.lifecycle_state = "published"
        mock_use_case.config_json = {
            "models": {"llm": "mistral-large"},
            "rag": {"enabled": True},
            "ui_config": {"input_sections": []},
        }

        # Mock DB query
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_use_case
        mock_async_db.execute.return_value = mock_result

        # Mock RBAC access check
        with patch(
            "app.routers.use_cases.user_can_access_use_case", new_callable=AsyncMock
        ) as mock_access:
            mock_access.return_value = True

            result = await get_use_case_config(
                use_case_id=use_case_id,
                db=mock_async_db,
                current_user=mock_current_user,
            )

            assert isinstance(result, dict)
            assert result["use_case_id"] == "test-use-case"
            assert result["name"] == "Test Use Case"
            assert result["description"] == "Test description"
            assert result["category"] == "test_category"
            assert result["intent_type"] == "query"
            assert "config" in result
            assert result["config"]["models"]["llm"] == "mistral-large"

    @pytest.mark.asyncio
    async def test_returns_404_for_nonexistent_use_case(self, mock_async_db, mock_current_user):
        """Should return 404 for non-existent use case."""
        use_case_id = uuid4()

        # Mock DB query to return None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_use_case_config(
                use_case_id=use_case_id,
                db=mock_async_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_returns_403_for_unauthorized_access(self, mock_async_db, mock_current_user):
        """Should return 403 when user lacks access to use case."""
        use_case_id = uuid4()

        # Mock use case exists
        mock_use_case = MagicMock()
        mock_use_case.id = use_case_id
        mock_use_case.is_active = True
        mock_use_case.lifecycle_state = "published"

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_use_case
        mock_async_db.execute.return_value = mock_result

        # Mock RBAC access check returns False
        with patch("app.routers.use_cases.user_can_access_use_case") as mock_access:
            mock_access.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await get_use_case_config(
                    use_case_id=use_case_id,
                    db=mock_async_db,
                    current_user=mock_current_user,
                )

            assert exc_info.value.status_code == 403
            assert "access denied" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_handles_database_error(self, mock_async_db, mock_current_user):
        """Should raise HTTPException on database error."""
        use_case_id = uuid4()

        mock_async_db.execute.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await get_use_case_config(
                use_case_id=use_case_id,
                db=mock_async_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 500
        assert "Failed to retrieve use case configuration" in str(exc_info.value.detail)
