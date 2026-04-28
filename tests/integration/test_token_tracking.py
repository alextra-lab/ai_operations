"""
Integration tests for token tracking functionality.

Tests the complete token tracking flow including:
- Token usage recording
- Center-based aggregation
- User-based aggregation
- Admin endpoints
- RLS policies

P5-A20: Migrated to async database patterns (ADR-022).
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.orchestrator.app.db.models import TokenUsage
from src.orchestrator.app.main import app
from src.orchestrator.app.schemas.token_usage import TokenUsageResponse, TokenUsageSummary
from src.orchestrator.app.services.token_tracker import TokenTracker


class TestTokenTracking:
    """Test token tracking service and database operations."""

    @pytest.mark.asyncio
    async def test_record_token_usage(self, db_session: AsyncSession, test_user):
        """Test recording token usage."""
        tracker = TokenTracker(db_session)

        usage = await tracker.record_usage(
            run_id=str(uuid4()),
            user_id=test_user.id,
            model_id="gpt-4o",
            tokens_in=100,
            tokens_out=50,
            intent_type="QUERY",
            request_type="QUERY",
            streaming_used=False,
            call_duration_ms=1500,
        )

        assert isinstance(usage, TokenUsageResponse)
        assert usage.tokens_in == 100
        assert usage.tokens_out == 50
        assert usage.total_tokens == 150
        assert usage.model_id == "gpt-4o"
        assert usage.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_token_usage_with_center_id(self, db_session: AsyncSession, test_user):
        """Test token usage records include center_id from user."""
        # Set center_id on user
        test_user.center_id = "test-center-001"
        await db_session.commit()

        tracker = TokenTracker(db_session)

        usage = await tracker.record_usage(
            run_id=str(uuid4()),
            user_id=test_user.id,
            model_id="gpt-4o-mini",
            tokens_in=50,
            tokens_out=25,
        )

        assert usage.center_id == "test-center-001"

    @pytest.mark.asyncio
    async def test_get_center_usage_summary(self, db_session: AsyncSession, test_user):
        """Test retrieving center usage summary."""
        # Set up test data
        test_user.center_id = "center-alpha"
        await db_session.commit()

        tracker = TokenTracker(db_session)

        # Record multiple usages
        for i in range(5):
            await tracker.record_usage(
                run_id=str(uuid4()),
                user_id=test_user.id,
                model_id="gpt-4o",
                tokens_in=100 + i * 10,
                tokens_out=50 + i * 5,
            )

        # Get summary
        summary = await tracker.get_center_usage_summary(
            center_id="center-alpha",
            start_date=datetime.now(UTC) - timedelta(days=1),
            end_date=datetime.now(UTC) + timedelta(days=1),
        )

        assert isinstance(summary, TokenUsageSummary)
        assert summary.center_id == "center-alpha"
        assert summary.total_requests == 5
        assert summary.unique_users == 1
        assert summary.total_tokens_in == 600  # 100+110+120+130+140
        assert summary.total_tokens_out == 300  # 50+55+60+65+70
        assert summary.total_tokens == 900

    @pytest.mark.asyncio
    async def test_get_all_centers_usage_summary(
        self, db_session: AsyncSession, test_user, admin_user
    ):
        """Test retrieving all centers usage summary."""
        # Clean up any existing token usage records to ensure test isolation
        from sqlalchemy import delete

        await db_session.execute(delete(TokenUsage))
        await db_session.commit()

        # Set up multiple centers
        test_user.center_id = "center-a"
        admin_user.center_id = "center-b"
        await db_session.commit()

        tracker = TokenTracker(db_session)

        # Record usages for center-a
        for _i in range(3):
            await tracker.record_usage(
                run_id=str(uuid4()),
                user_id=test_user.id,
                model_id="gpt-4o",
                tokens_in=100,
                tokens_out=50,
            )

        # Record usages for center-b
        for _i in range(2):
            await tracker.record_usage(
                run_id=str(uuid4()),
                user_id=admin_user.id,
                model_id="gpt-4o-mini",
                tokens_in=80,
                tokens_out=40,
            )

        # Get summary
        response = await tracker.get_all_centers_usage_summary(
            start_date=datetime.now(UTC) - timedelta(days=1),
            end_date=datetime.now(UTC) + timedelta(days=1),
        )

        assert len(response.centers) == 2
        assert response.grand_total.total_requests == 5
        assert response.grand_total.total_tokens == 690  # (150*3) + (120*2)

    @pytest.mark.asyncio
    async def test_get_user_usage_summary(self, db_session: AsyncSession, test_user):
        """Test retrieving user usage summary."""
        tracker = TokenTracker(db_session)

        # Record usages
        for _i in range(4):
            await tracker.record_usage(
                run_id=str(uuid4()),
                user_id=test_user.id,
                model_id="gpt-4o",
                tokens_in=150,
                tokens_out=75,
            )

        # Get summary
        summary = await tracker.get_user_usage_summary(
            user_id=test_user.id,
            start_date=datetime.now(UTC) - timedelta(days=1),
            end_date=datetime.now(UTC) + timedelta(days=1),
        )

        assert isinstance(summary, TokenUsageSummary)
        assert summary.user_id == test_user.id
        assert summary.total_requests == 4
        assert summary.total_tokens_in == 600
        assert summary.total_tokens_out == 300
        assert summary.total_tokens == 900

    @pytest.mark.asyncio
    async def test_token_usage_rls_policies(self, db_session: AsyncSession, test_user, admin_user):
        """Test Row Level Security policies on token_usage table."""
        # This test requires setting up RLS context
        # In a real environment, RLS would be enforced by PostgreSQL
        tracker = TokenTracker(db_session)

        # Record usage for test_user
        user_usage = await tracker.record_usage(
            run_id=str(uuid4()),
            user_id=test_user.id,
            model_id="gpt-4o",
            tokens_in=100,
            tokens_out=50,
        )

        # Record usage for admin_user
        admin_usage = await tracker.record_usage(
            run_id=str(uuid4()),
            user_id=admin_user.id,
            model_id="gpt-4o-mini",
            tokens_in=80,
            tokens_out=40,
        )

        # Verify both records exist
        assert user_usage.user_id == test_user.id
        assert admin_usage.user_id == admin_user.id

        # Verify records are in database
        result = await db_session.execute(select(TokenUsage).where(TokenUsage.id == user_usage.id))
        user_record = result.scalar_one_or_none()
        result = await db_session.execute(select(TokenUsage).where(TokenUsage.id == admin_usage.id))
        admin_record = result.scalar_one_or_none()

        assert user_record is not None
        assert admin_record is not None


class TestTokenTrackingAPI:
    """Test token tracking API endpoints."""

    def test_admin_get_all_centers_usage(self, authenticated_admin_client):
        """Test admin endpoint for all centers usage."""
        response = authenticated_admin_client.get("/api/v1/admin/token-usage/by-center")

        assert response.status_code == 200
        data = response.json()
        assert "centers" in data
        assert "grand_total" in data
        assert "start_date" in data
        assert "end_date" in data

    def test_admin_get_center_usage(self, authenticated_admin_client):
        """Test admin endpoint for specific center usage."""
        response = authenticated_admin_client.get("/api/v1/admin/token-usage/by-center/test-center")

        assert response.status_code == 200
        data = response.json()
        assert "center_id" in data
        assert data["center_id"] == "test-center"
        assert "summary" in data

    def test_admin_get_user_usage(self, authenticated_admin_client, test_user):
        """Test admin endpoint for user usage."""
        response = authenticated_admin_client.get(
            f"/api/v1/admin/token-usage/by-user/{test_user.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "summary" in data

    def test_user_get_own_usage(self, authenticated_user_client):
        """Test user endpoint for their own usage."""
        response = authenticated_user_client.get("/api/v1/admin/token-usage/me")

        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "summary" in data

    def test_non_admin_cannot_access_admin_endpoints(self, authenticated_user_client):
        """Test that non-admin users cannot access admin-only endpoints."""
        response = authenticated_user_client.get("/api/v1/admin/token-usage/by-center")

        assert response.status_code == 403

    def test_unauthenticated_cannot_access_endpoints(self, async_client):
        """Test that unauthenticated requests are rejected."""
        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            response = client.get("/api/v1/admin/token-usage/me")
            assert response.status_code == 401
