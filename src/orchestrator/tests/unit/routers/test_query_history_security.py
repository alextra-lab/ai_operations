"""
Unit tests for Query History Security Guards (P5-SEC-01)

Tests that write endpoints are blocked when ENABLE_TRANSCRIPT_STORAGE=false
per ADR-030 Stateless Architecture Enforcement.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status

from shared.auth.models import TokenPayload

# Import the guard function and endpoints
from src.orchestrator.app.routers.query_history import (
    create_query_history,
    create_thread,
    delete_query_history,
    delete_thread,
    fork_query,
    require_transcript_storage,
    update_query_history,
    update_thread,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_db():
    """Mock database session."""
    return MagicMock()


@pytest.fixture
def mock_history_service():
    """Mock history service."""
    return MagicMock()


@pytest.fixture
def admin_user():
    """Mock admin user token payload."""
    now = int(datetime.now(UTC).timestamp())
    return TokenPayload(
        sub="admin",
        user_id="a0000000-0000-0000-0000-000000000001",
        role="admin",
        exp=now + 3600,
        iat=now,
        iss="ai-operations-platform",
        token_type="access",
    )


@pytest.fixture
def test_user():
    """Mock test user token payload."""
    now = int(datetime.now(UTC).timestamp())
    return TokenPayload(
        sub="testuser",
        user_id="004b53ae-0d85-45e3-8e6d-f1806baa2640",
        role="user",
        exp=now + 3600,
        iat=now,
        iss="ai-operations-platform",
        token_type="access",
    )


# ============================================================================
# Guard Function Tests
# ============================================================================


class TestRequireTranscriptStorage:
    """Tests for the require_transcript_storage guard function."""

    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", False)
    def test_guard_blocks_when_disabled(self):
        """Guard raises 501 when transcript storage is disabled."""
        with pytest.raises(HTTPException) as exc_info:
            require_transcript_storage()

        assert exc_info.value.status_code == status.HTTP_501_NOT_IMPLEMENTED
        assert exc_info.value.detail["error"] == "transcript_storage_disabled"
        assert "ADR-030" in exc_info.value.detail["message"]

    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", True)
    def test_guard_allows_when_enabled(self):
        """Guard allows operation when transcript storage is enabled."""
        # Should not raise any exception
        result = require_transcript_storage()
        assert result is None


# ============================================================================
# POST Endpoint Tests (Core Edition - Blocked)
# ============================================================================


class TestCreateQueryHistoryBlocked:
    """Tests that POST /api/v1/query-history is blocked in Core Edition."""

    @pytest.mark.asyncio
    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", False)
    async def test_create_history_returns_501_core_edition(self, mock_history_service, test_user):
        """POST /api/v1/query-history returns 501 in Core Edition."""
        from src.orchestrator.app.schemas.query_history import QueryHistoryCreate

        history_data = QueryHistoryCreate(
            query_text="test query",
            response_status="success",
            run_id="test-run-123",
            user_id=uuid.UUID(test_user.user_id),
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_query_history(
                history_data=history_data,
                history_service=mock_history_service,
                current_user=test_user,
            )

        assert exc_info.value.status_code == status.HTTP_501_NOT_IMPLEMENTED
        assert exc_info.value.detail["error"] == "transcript_storage_disabled"


class TestCreateThreadBlocked:
    """Tests that POST /api/v1/query-history/threads is blocked in Core Edition."""

    @pytest.mark.asyncio
    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", False)
    async def test_create_thread_returns_501_core_edition(self, mock_history_service, test_user):
        """POST /api/v1/query-history/threads returns 501 in Core Edition."""
        from src.orchestrator.app.schemas.query_history import ThreadCreate

        thread_request = ThreadCreate(title="Test Thread")

        with pytest.raises(HTTPException) as exc_info:
            await create_thread(
                request=thread_request,
                history_service=mock_history_service,
                current_user=test_user,
            )

        assert exc_info.value.status_code == status.HTTP_501_NOT_IMPLEMENTED


class TestForkQueryBlocked:
    """Tests that POST /api/v1/query-history/fork is blocked in Core Edition."""

    @pytest.mark.asyncio
    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", False)
    async def test_fork_query_returns_501_core_edition(self, mock_history_service, test_user):
        """POST /api/v1/query-history/fork returns 501 in Core Edition."""
        from src.orchestrator.app.schemas.query_history import ForkQueryRequest

        fork_request = ForkQueryRequest(
            source_query_id=uuid.uuid4(),
        )

        with pytest.raises(HTTPException) as exc_info:
            await fork_query(
                request=fork_request,
                history_service=mock_history_service,
                current_user=test_user,
            )

        assert exc_info.value.status_code == status.HTTP_501_NOT_IMPLEMENTED


# ============================================================================
# PATCH Endpoint Tests (Core Edition - Blocked)
# ============================================================================


class TestUpdateQueryHistoryBlocked:
    """Tests that PATCH /api/v1/query-history/{id} is blocked in Core Edition."""

    @pytest.mark.asyncio
    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", False)
    async def test_update_history_returns_501_core_edition(self, mock_history_service, test_user):
        """PATCH /api/v1/query-history/{id} returns 501 in Core Edition."""
        from src.orchestrator.app.schemas.query_history import QueryHistoryUpdate

        update_data = QueryHistoryUpdate(query_text="updated query")

        with pytest.raises(HTTPException) as exc_info:
            await update_query_history(
                history_id=uuid.uuid4(),
                update_data=update_data,
                history_service=mock_history_service,
                current_user=test_user,
            )

        assert exc_info.value.status_code == status.HTTP_501_NOT_IMPLEMENTED


class TestUpdateThreadBlocked:
    """Tests that PATCH /api/v1/query-history/threads/{id} is blocked."""

    @pytest.mark.asyncio
    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", False)
    async def test_update_thread_returns_501_core_edition(self, mock_history_service, test_user):
        """PATCH /api/v1/query-history/threads/{id} returns 501 in Core Edition."""
        from src.orchestrator.app.schemas.query_history import ThreadUpdate

        update_data = ThreadUpdate(title="Updated Title")

        with pytest.raises(HTTPException) as exc_info:
            await update_thread(
                thread_id=uuid.uuid4(),
                request=update_data,
                history_service=mock_history_service,
                current_user=test_user,
            )

        assert exc_info.value.status_code == status.HTTP_501_NOT_IMPLEMENTED


# ============================================================================
# DELETE Endpoint Tests (Core Edition - Blocked)
# ============================================================================


class TestDeleteQueryHistoryBlocked:
    """Tests that DELETE /api/v1/query-history/{id} is blocked in Core Edition."""

    @pytest.mark.asyncio
    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", False)
    async def test_delete_history_returns_501_core_edition(self, mock_history_service, test_user):
        """DELETE /api/v1/query-history/{id} returns 501 in Core Edition."""
        with pytest.raises(HTTPException) as exc_info:
            await delete_query_history(
                history_id=uuid.uuid4(),
                history_service=mock_history_service,
                current_user=test_user,
            )

        assert exc_info.value.status_code == status.HTTP_501_NOT_IMPLEMENTED


class TestDeleteThreadBlocked:
    """Tests that DELETE /api/v1/query-history/threads/{id} is blocked."""

    @pytest.mark.asyncio
    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", False)
    async def test_delete_thread_returns_501_core_edition(self, mock_history_service, test_user):
        """DELETE /api/v1/query-history/threads/{id} returns 501 in Core Edition."""
        with pytest.raises(HTTPException) as exc_info:
            await delete_thread(
                thread_id=uuid.uuid4(),
                history_service=mock_history_service,
                current_user=test_user,
            )

        assert exc_info.value.status_code == status.HTTP_501_NOT_IMPLEMENTED


# ============================================================================
# Plus Edition Tests (Enabled - Allowed)
# ============================================================================


class TestPlusEditionGuardPasses:
    """
    Tests that the guard passes through when ENABLE_TRANSCRIPT_STORAGE=true.

    Note: Full Plus Edition endpoint tests require integration testing with
    a real database. These tests just verify the guard doesn't block.
    """

    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", True)
    def test_guard_does_not_block_plus_edition(self):
        """Guard allows operations when transcript storage is enabled."""
        # Should not raise any exception
        result = require_transcript_storage()
        assert result is None

    @pytest.mark.asyncio
    @patch("src.orchestrator.app.routers.query_history.ENABLE_TRANSCRIPT_STORAGE", True)
    async def test_create_history_reaches_service_plus_edition(
        self, mock_history_service, test_user
    ):
        """POST /api/v1/query-history calls service in Plus Edition."""
        from src.orchestrator.app.schemas.query_history import QueryHistoryCreate

        # Configure mock to raise a known exception so we can verify
        # the guard passed and the service was reached
        mock_history_service.create_history.side_effect = ValueError("Service was called")

        history_data = QueryHistoryCreate(
            query_text="test query",
            response_status="success",
            run_id="test-run-123",
            user_id=uuid.UUID(test_user.user_id),
        )

        # Should raise 500 (from service error), NOT 501 (from guard)
        with pytest.raises(HTTPException) as exc_info:
            await create_query_history(
                history_data=history_data,
                history_service=mock_history_service,
                current_user=test_user,
            )

        # Guard passed - we got 500 from service error, not 501 from guard
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        mock_history_service.create_history.assert_called_once()
