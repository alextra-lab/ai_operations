"""
Unit tests for tools_analytics router.

Tests analytics endpoints for tool usage summary, center-based aggregation,
and audit trail retrieval. All database operations are mocked.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from shared.auth import get_current_user
from shared.auth.models import TokenPayload, UserRole
from src.orchestrator.app.db.database import get_async_db
from src.orchestrator.app.db.models import ToolInvocation
from src.orchestrator.app.main import app
from src.orchestrator.app.schemas.tool import InvocationStatus


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user token payload."""
    now = datetime.now(tz=UTC)
    return TokenPayload(
        sub="admin",
        user_id=str(uuid4()),
        username="admin",
        role=UserRole.ADMIN,
        exp=int((now + timedelta(hours=1)).timestamp()),
        iat=int(now.timestamp()),
        iss="aio",
        token_type="access",
    )


@pytest.fixture
def mock_regular_user():
    """Create a mock regular user token payload."""
    now = datetime.now(tz=UTC)
    user_id = uuid4()
    return TokenPayload(
        sub="user",
        user_id=str(user_id),
        username="user",
        role=UserRole.USER,
        exp=int((now + timedelta(hours=1)).timestamp()),
        iat=int(now.timestamp()),
        iss="aio",
        token_type="access",
    )


@pytest.fixture
def mock_tool_invocation():
    """Create a mock tool invocation."""
    invocation_id = uuid4()
    tool_id = uuid4()
    user_id = uuid4()
    invocation = MagicMock(spec=ToolInvocation)
    invocation.id = invocation_id
    invocation.tool_id = tool_id
    invocation.use_case_id = None
    invocation.run_id = "test_run_123"
    invocation.user_id = user_id
    invocation.center_id = "center_001"
    invocation.tool_name = "test_tool"
    invocation.tool_parameters = {"param1": "value1"}
    invocation.status = InvocationStatus.SUCCESS.value
    invocation.response_data = {"result": "success"}
    invocation.error_message = None
    invocation.started_at = datetime.now(UTC)
    invocation.completed_at = datetime.now(UTC)
    invocation.duration_ms = 45.2
    invocation.cost_estimate = 0.001
    return invocation


@pytest.fixture
def authenticated_admin_client(mock_admin_user):
    """Create a test client with admin authentication."""
    from shared.auth import admin_required

    def mock_admin_required():
        return mock_admin_user

    def mock_get_current_user():
        return mock_admin_user

    app.dependency_overrides[admin_required] = mock_admin_required
    app.dependency_overrides[get_current_user] = mock_get_current_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_user_client(mock_regular_user):
    """Create a test client with regular user authentication."""
    from shared.auth import admin_required

    def mock_admin_required():
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient role. Required: ['admin'], got: {mock_regular_user.role}",
        )

    def mock_get_current_user():
        return mock_regular_user

    app.dependency_overrides[admin_required] = mock_admin_required
    app.dependency_overrides[get_current_user] = mock_get_current_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


class TestGetUsageSummary:
    """Tests for GET /api/v1/tools/analytics/usage/summary endpoint."""

    def test_get_usage_summary_success(self, authenticated_admin_client):
        """Test successful retrieval of usage summary."""
        tool_id = uuid4()

        # Mock aggregated query result (uses result.all())
        mock_row = MagicMock()
        mock_row.tool_id = tool_id
        mock_row.total_calls = 10
        mock_row.successful_calls = 8
        mock_row.avg_duration_ms = 45.5
        mock_row.total_cost = 0.01

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        async def mock_get_db():
            yield mock_db

        app.dependency_overrides[get_async_db] = mock_get_db

        try:
            response = authenticated_admin_client.get("/api/v1/tools/analytics/usage/summary")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["tool_id"] == str(tool_id)
            assert data[0]["total_calls"] == 10
            assert data[0]["successful_calls"] == 8
            assert data[0]["success_rate"] == 80.0
            assert data[0]["avg_duration_ms"] == 45.5
            assert data[0]["total_cost"] == 0.01
        finally:
            app.dependency_overrides.pop(get_async_db, None)

    def test_get_usage_summary_empty(self, authenticated_admin_client):
        """Test usage summary when no invocations exist."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result

        async def mock_get_db():
            yield mock_db

        app.dependency_overrides[get_async_db] = mock_get_db

        try:
            response = authenticated_admin_client.get("/api/v1/tools/analytics/usage/summary")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 0
        finally:
            app.dependency_overrides.pop(get_async_db, None)

    def test_get_usage_summary_with_date_filter(self, authenticated_admin_client):
        """Test usage summary with date filtering."""
        tool_id = uuid4()
        start_date = datetime.now(UTC) - timedelta(days=7)
        end_date = datetime.now(UTC)

        mock_row = MagicMock()
        mock_row.tool_id = tool_id
        mock_row.total_calls = 5
        mock_row.successful_calls = 4
        mock_row.avg_duration_ms = 50.0
        mock_row.total_cost = 0.005

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        async def mock_get_db():
            yield mock_db

        app.dependency_overrides[get_async_db] = mock_get_db

        try:
            from urllib.parse import quote

            start_str = quote(start_date.isoformat())
            end_str = quote(end_date.isoformat())
            response = authenticated_admin_client.get(
                f"/api/v1/tools/analytics/usage/summary?start_date={start_str}&end_date={end_str}"
            )

            assert response.status_code == status.HTTP_200_OK
            mock_db.execute.assert_called_once()
        finally:
            app.dependency_overrides.pop(get_async_db, None)

    def test_get_usage_summary_zero_success_rate(self, authenticated_admin_client):
        """Test usage summary with zero successful calls."""
        tool_id = uuid4()

        mock_row = MagicMock()
        mock_row.tool_id = tool_id
        mock_row.total_calls = 5
        mock_row.successful_calls = 0
        mock_row.avg_duration_ms = None
        mock_row.total_cost = None

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        async def mock_get_db():
            yield mock_db

        app.dependency_overrides[get_async_db] = mock_get_db

        try:
            response = authenticated_admin_client.get("/api/v1/tools/analytics/usage/summary")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data[0]["success_rate"] == 0.0
            assert data[0]["avg_duration_ms"] == 0.0
            assert data[0]["total_cost"] == 0.0
        finally:
            app.dependency_overrides.pop(get_async_db, None)

    def test_get_usage_summary_requires_admin(self, authenticated_user_client):
        """Test that usage summary endpoint requires admin role."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result

        async def mock_get_db():
            yield mock_db

        app.dependency_overrides[get_async_db] = mock_get_db

        try:
            response = authenticated_user_client.get("/api/v1/tools/analytics/usage/summary")
            assert response.status_code == status.HTTP_403_FORBIDDEN
        finally:
            app.dependency_overrides.pop(get_async_db, None)


class TestGetUsageByCenter:
    """Tests for GET /api/v1/tools/analytics/usage/by-center endpoint."""

    def test_get_usage_by_center_success(self, authenticated_admin_client):
        """Test successful retrieval of usage by center."""
        mock_row = MagicMock()
        mock_row.center_id = "center_001"
        mock_row.total_calls = 20
        mock_row.total_cost = 0.02

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        async def mock_get_db():
            yield mock_db

        app.dependency_overrides[get_async_db] = mock_get_db

        try:
            response = authenticated_admin_client.get("/api/v1/tools/analytics/usage/by-center")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["center_id"] == "center_001"
            assert data[0]["total_calls"] == 20
            assert data[0]["total_cost"] == 0.02
        finally:
            app.dependency_overrides.pop(get_async_db, None)

    def test_get_usage_by_center_with_days_parameter(self, authenticated_admin_client):
        """Test usage by center with custom days parameter."""
        mock_row = MagicMock()
        mock_row.center_id = "center_002"
        mock_row.total_calls = 15
        mock_row.total_cost = 0.015

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        async def mock_get_db():
            yield mock_db

        app.dependency_overrides[get_async_db] = mock_get_db

        try:
            response = authenticated_admin_client.get(
                "/api/v1/tools/analytics/usage/by-center?days=60"
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
        finally:
            app.dependency_overrides.pop(get_async_db, None)

    def test_get_usage_by_center_empty(self, authenticated_admin_client):
        """Test usage by center when no data exists."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result

        async def mock_get_db():
            yield mock_db

        app.dependency_overrides[get_async_db] = mock_get_db

        try:
            response = authenticated_admin_client.get("/api/v1/tools/analytics/usage/by-center")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 0
        finally:
            app.dependency_overrides.pop(get_async_db, None)

    def test_get_usage_by_center_requires_admin(self, authenticated_user_client):
        """Test that usage by center endpoint requires admin role."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result

        async def mock_get_db():
            yield mock_db

        app.dependency_overrides[get_async_db] = mock_get_db

        try:
            response = authenticated_user_client.get("/api/v1/tools/analytics/usage/by-center")
            assert response.status_code == status.HTTP_403_FORBIDDEN
        finally:
            app.dependency_overrides.pop(get_async_db, None)


class TestGetToolAuditForRequest:
    """Tests for GET /api/v1/tools/analytics/audit/{run_id} endpoint."""

    def test_get_audit_admin_success(self, authenticated_admin_client, mock_tool_invocation):
        """Test successful audit retrieval by admin."""
        run_id = "test_run_123"

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_tool_invocation]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        async def mock_get_db():
            yield mock_db

        app.dependency_overrides[get_async_db] = mock_get_db

        try:
            response = authenticated_admin_client.get(f"/api/v1/tools/analytics/audit/{run_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["run_id"] == run_id
            assert data[0]["status"] == InvocationStatus.SUCCESS.value
        finally:
            app.dependency_overrides.pop(get_async_db, None)

    def test_get_audit_user_own_request(self, mock_regular_user):
        """Test audit retrieval by user for their own request."""
        run_id = "test_run_123"
        user_id = UUID(mock_regular_user.user_id)

        # Create invocation owned by the user
        invocation = MagicMock(spec=ToolInvocation)
        invocation.id = uuid4()
        invocation.tool_id = uuid4()
        invocation.use_case_id = None
        invocation.run_id = run_id
        invocation.user_id = user_id
        invocation.center_id = "center_001"
        invocation.tool_name = "test_tool"
        invocation.tool_parameters = {}
        invocation.status = InvocationStatus.SUCCESS.value
        invocation.response_data = {}
        invocation.error_message = None
        invocation.started_at = datetime.now(UTC)
        invocation.completed_at = datetime.now(UTC)
        invocation.duration_ms = 50.0
        invocation.cost_estimate = 0.001

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [invocation]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        async def mock_get_db():
            yield mock_db

        def mock_get_current_user():
            return mock_regular_user

        app.dependency_overrides[get_async_db] = mock_get_db
        app.dependency_overrides[get_current_user] = mock_get_current_user

        try:
            with TestClient(app) as client:
                response = client.get(f"/api/v1/tools/analytics/audit/{run_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["run_id"] == run_id
        finally:
            app.dependency_overrides.pop(get_async_db, None)
            app.dependency_overrides.pop(get_current_user, None)

    def test_get_audit_user_other_request(self, mock_regular_user):
        """Test audit retrieval by user for someone else's request (should return 404)."""
        run_id = "test_run_123"

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []  # Filtered out
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        async def mock_get_db():
            yield mock_db

        def mock_get_current_user():
            return mock_regular_user

        app.dependency_overrides[get_async_db] = mock_get_db
        app.dependency_overrides[get_current_user] = mock_get_current_user

        try:
            with TestClient(app) as client:
                response = client.get(f"/api/v1/tools/analytics/audit/{run_id}")

            # Should return 404 when no invocations found
            assert response.status_code == status.HTTP_404_NOT_FOUND
        finally:
            app.dependency_overrides.pop(get_async_db, None)
            app.dependency_overrides.pop(get_current_user, None)

    def test_get_audit_not_found(self, authenticated_admin_client):
        """Test audit retrieval when run_id doesn't exist."""
        run_id = "nonexistent_run"

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        async def mock_get_db():
            yield mock_db

        app.dependency_overrides[get_async_db] = mock_get_db

        try:
            response = authenticated_admin_client.get(f"/api/v1/tools/analytics/audit/{run_id}")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            detail = response.json()["detail"].lower()
            assert "not found" in detail or "no tool invocations" in detail
        finally:
            app.dependency_overrides.pop(get_async_db, None)

    def test_get_audit_user_no_user_id(self):
        """Test audit retrieval when user has no user_id."""
        run_id = "test_run_123"

        # Create user with empty string user_id
        user_no_id = TokenPayload(
            sub="user",
            user_id="",
            username="user",
            role=UserRole.USER,
            exp=int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
            iat=int(datetime.now(UTC).timestamp()),
            iss="aio",
            token_type="access",
        )

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        async def mock_get_db():
            yield mock_db

        def mock_get_current_user():
            return user_no_id

        app.dependency_overrides[get_async_db] = mock_get_db
        app.dependency_overrides[get_current_user] = mock_get_current_user

        try:
            with TestClient(app) as client:
                response = client.get(f"/api/v1/tools/analytics/audit/{run_id}")

            # Should return 404 when user_id is empty/invalid
            assert response.status_code == status.HTTP_404_NOT_FOUND
        finally:
            app.dependency_overrides.pop(get_async_db, None)
            app.dependency_overrides.pop(get_current_user, None)
