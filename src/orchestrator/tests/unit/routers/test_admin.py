"""
Unit tests for Admin Router (Token Usage Tracking)

Tests administrative endpoints for token usage tracking.
P5-A11: Created for async admin router (Nov 2025).
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, status

from shared.auth.models import TokenPayload
from src.orchestrator.app.routers.admin import (
    get_all_centers_usage,
    get_center_usage,
    get_my_usage,
    get_user_usage,
)
from src.orchestrator.app.schemas.token_usage import (
    AllCentersUsageSummaryResponse,
    TokenUsageSummary,
)

# ============================================================================
# Fixtures
# ============================================================================


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
def regular_user():
    """Mock regular user token payload."""
    now = int(datetime.now(UTC).timestamp())
    return TokenPayload(
        sub="user",
        user_id="b0000000-0000-0000-0000-000000000002",
        role="user",
        exp=now + 3600,
        iat=now,
        iss="ai-operations-platform",
        token_type="access",
    )


@pytest.fixture
def usage_summary():
    """Sample token usage summary."""
    return TokenUsageSummary(
        center_id="center-001",
        user_id=None,
        total_requests=100,
        unique_users=10,
        total_tokens_in=50000,
        total_tokens_out=25000,
        total_tokens=75000,
        total_cost=None,
        avg_tokens_per_request=750.0,
        top_models={"gpt-4": 50, "gpt-3.5-turbo": 50},
    )


# ============================================================================
# Tests: GET /api/v1/admin/token-usage/by-center
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_centers_usage_success(admin_user, usage_summary):
    """Test successful retrieval of all centers usage."""
    with patch("src.orchestrator.app.routers.admin.SessionLocal") as mock_session_class:
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db

        with patch("src.orchestrator.app.routers.admin.TokenTracker") as mock_tracker_class:
            mock_tracker = MagicMock()
            mock_tracker_class.return_value = mock_tracker

            # Mock the response
            mock_response = AllCentersUsageSummaryResponse(
                start_date=datetime.now(UTC) - timedelta(days=30),
                end_date=datetime.now(UTC),
                centers=[usage_summary],
                grand_total=usage_summary,
            )
            mock_tracker.get_all_centers_usage_summary.return_value = mock_response

            # Execute
            result = await get_all_centers_usage(
                start_date=None,
                end_date=None,
                current_user=admin_user,
            )

            # Verify
            assert result.grand_total.total_requests == 100
            assert len(result.centers) == 1
            mock_tracker.get_all_centers_usage_summary.assert_called_once()
            mock_db.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_centers_usage_with_dates(admin_user, usage_summary):
    """Test with explicit date range."""
    start = datetime.now(UTC) - timedelta(days=7)
    end = datetime.now(UTC)

    with patch("src.orchestrator.app.routers.admin.SessionLocal") as mock_session_class:
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db

        with patch("src.orchestrator.app.routers.admin.TokenTracker") as mock_tracker_class:
            mock_tracker = MagicMock()
            mock_tracker_class.return_value = mock_tracker

            mock_response = AllCentersUsageSummaryResponse(
                start_date=start,
                end_date=end,
                centers=[],
                grand_total=usage_summary,
            )
            mock_tracker.get_all_centers_usage_summary.return_value = mock_response

            await get_all_centers_usage(
                start_date=start,
                end_date=end,
                current_user=admin_user,
            )

            # Verify dates passed correctly
            mock_tracker.get_all_centers_usage_summary.assert_called_once_with(start, end)
            mock_db.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_centers_usage_error(admin_user):
    """Test error handling when tracker fails."""
    with patch("src.orchestrator.app.routers.admin.SessionLocal") as mock_session_class:
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db

        with patch("src.orchestrator.app.routers.admin.TokenTracker") as mock_tracker_class:
            mock_tracker = MagicMock()
            mock_tracker_class.return_value = mock_tracker
            mock_tracker.get_all_centers_usage_summary.side_effect = Exception("DB error")

            with pytest.raises(HTTPException) as exc_info:
                await get_all_centers_usage(
                    start_date=None,
                    end_date=None,
                    current_user=admin_user,
                )

            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            mock_db.close.assert_called_once()


# ============================================================================
# Tests: GET /api/v1/admin/token-usage/by-center/{center_id}
# ============================================================================


@pytest.mark.asyncio
async def test_get_center_usage_success(admin_user, usage_summary):
    """Test successful retrieval of center usage."""
    with patch("src.orchestrator.app.routers.admin.SessionLocal") as mock_session_class:
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db

        with patch("src.orchestrator.app.routers.admin.TokenTracker") as mock_tracker_class:
            mock_tracker = MagicMock()
            mock_tracker_class.return_value = mock_tracker
            mock_tracker.get_center_usage_summary.return_value = usage_summary

            result = await get_center_usage(
                center_id="center-001",
                start_date=None,
                end_date=None,
                current_user=admin_user,
            )

            assert result.center_id == "center-001"
            assert result.summary.total_requests == 100
            mock_db.close.assert_called_once()


# ============================================================================
# Tests: GET /api/v1/admin/token-usage/by-user/{user_id}
# ============================================================================


@pytest.mark.asyncio
async def test_get_user_usage_success(admin_user):
    """Test successful retrieval of user usage."""
    target_user_id = uuid4()
    user_summary = TokenUsageSummary(
        center_id="center-001",
        user_id=target_user_id,
        total_requests=50,
        unique_users=0,
        total_tokens_in=25000,
        total_tokens_out=12500,
        total_tokens=37500,
        total_cost=None,
        avg_tokens_per_request=750.0,
        top_models=None,
    )

    with patch("src.orchestrator.app.routers.admin.SessionLocal") as mock_session_class:
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db

        with patch("src.orchestrator.app.routers.admin.TokenTracker") as mock_tracker_class:
            mock_tracker = MagicMock()
            mock_tracker_class.return_value = mock_tracker
            mock_tracker.get_user_usage_summary.return_value = user_summary

            result = await get_user_usage(
                user_id=target_user_id,
                start_date=None,
                end_date=None,
                current_user=admin_user,
            )

            assert result.user_id == target_user_id
            assert result.summary.total_requests == 50
            mock_db.close.assert_called_once()


# ============================================================================
# Tests: GET /api/v1/admin/token-usage/me
# ============================================================================


@pytest.mark.asyncio
async def test_get_my_usage_success(regular_user):
    """Test user retrieving their own usage."""
    user_summary = TokenUsageSummary(
        center_id="center-001",
        user_id=uuid4(),
        total_requests=25,
        unique_users=0,
        total_tokens_in=12500,
        total_tokens_out=6250,
        total_tokens=18750,
        total_cost=None,
        avg_tokens_per_request=750.0,
        top_models=None,
    )

    with patch("src.orchestrator.app.routers.admin.SessionLocal") as mock_session_class:
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db

        with patch("src.orchestrator.app.routers.admin.TokenTracker") as mock_tracker_class:
            mock_tracker = MagicMock()
            mock_tracker_class.return_value = mock_tracker
            mock_tracker.get_user_usage_summary.return_value = user_summary

            result = await get_my_usage(
                start_date=None,
                end_date=None,
                current_user=regular_user,
            )

            assert result.summary.total_requests == 25
            mock_tracker.get_user_usage_summary.assert_called_once()
            mock_db.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_my_usage_error(regular_user):
    """Test error handling when getting own usage fails."""
    with patch("src.orchestrator.app.routers.admin.SessionLocal") as mock_session_class:
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db

        with patch("src.orchestrator.app.routers.admin.TokenTracker") as mock_tracker_class:
            mock_tracker = MagicMock()
            mock_tracker_class.return_value = mock_tracker
            mock_tracker.get_user_usage_summary.side_effect = Exception("DB error")

            with pytest.raises(HTTPException) as exc_info:
                await get_my_usage(
                    start_date=None,
                    end_date=None,
                    current_user=regular_user,
                )

            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            mock_db.close.assert_called_once()
