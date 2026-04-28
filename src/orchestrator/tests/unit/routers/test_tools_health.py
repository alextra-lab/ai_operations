"""
Unit tests for tools_health router.

Tests health monitoring endpoints for tool status, history, and manual checks.
All database operations are mocked - no real database interaction.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from shared.auth.models import TokenPayload, UserRole
from src.orchestrator.app.db.database import get_async_db
from src.orchestrator.app.db.models import Tool, ToolHealthCheck
from src.orchestrator.app.main import app
from src.orchestrator.app.schemas.tool import ToolStatus


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
    return TokenPayload(
        sub="user",
        user_id=str(uuid4()),
        username="user",
        role=UserRole.USER,
        exp=int((now + timedelta(hours=1)).timestamp()),
        iat=int(now.timestamp()),
        iss="aio",
        token_type="access",
    )


@pytest.fixture
def mock_tool():
    """Create a mock tool."""
    tool_id = uuid4()
    tool = MagicMock(spec=Tool)
    tool.id = tool_id
    tool.tool_id = "test_tool_123"
    tool.name = "Test Tool"
    tool.is_enabled = True
    tool.is_healthy = True
    tool.last_health_check = datetime.now(UTC)
    return tool


@pytest.fixture
def mock_health_check():
    """Create a mock health check."""
    check_id = uuid4()
    tool_id = uuid4()
    check = MagicMock(spec=ToolHealthCheck)
    check.id = check_id
    check.tool_id = tool_id
    check.status = ToolStatus.ONLINE.value
    check.response_time_ms = 45.2
    check.error_message = None
    check.error_code = None
    check.checked_at = datetime.now(UTC)
    check.mcp_server_info = {"capabilities": {"tools": []}}
    return check


def create_mock_async_db(scalars_result):
    """Create a mock async database session with proper async patterns."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = scalars_result
    mock_scalars.first.return_value = scalars_result[0] if scalars_result else None
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result
    return mock_db


@pytest.fixture
def authenticated_admin_client(mock_admin_user):
    """Create a test client with admin authentication."""
    from shared.auth import admin_required

    def mock_admin_required():
        return mock_admin_user

    app.dependency_overrides[admin_required] = mock_admin_required

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

    app.dependency_overrides[admin_required] = mock_admin_required

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


class TestGetOverallHealthStatus:
    """Tests for GET /api/v1/tools/health/status endpoint."""

    def test_get_status_success(self, authenticated_admin_client, mock_tool):
        """Test successful retrieval of health status."""
        mock_db = create_mock_async_db([mock_tool])

        async def mock_get_db():
            yield mock_db

        app.dependency_overrides[get_async_db] = mock_get_db

        try:
            response = authenticated_admin_client.get("/api/v1/tools/health/status")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["total_tools"] == 1
            assert data["online"] == 1
            assert data["offline"] == 0
            assert data["health_percentage"] == 100.0
            assert data["last_check"] is not None
        finally:
            app.dependency_overrides.pop(get_async_db, None)

    def test_get_status_no_tools(self, authenticated_admin_client):
        """Test status endpoint when no tools exist."""
        mock_db = create_mock_async_db([])

        async def mock_get_db():
            yield mock_db

        app.dependency_overrides[get_async_db] = mock_get_db

        try:
            response = authenticated_admin_client.get("/api/v1/tools/health/status")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["total_tools"] == 0
            assert data["online"] == 0
            assert data["offline"] == 0
            assert data["health_percentage"] == 0.0
            assert data["last_check"] is None
        finally:
            app.dependency_overrides.pop(get_async_db, None)

    def test_get_status_mixed_health(self, authenticated_admin_client):
        """Test status endpoint with mixed healthy/unhealthy tools."""
        tool1 = MagicMock(spec=Tool)
        tool1.is_healthy = True
        tool1.last_health_check = datetime.now(UTC) - timedelta(minutes=5)

        tool2 = MagicMock(spec=Tool)
        tool2.is_healthy = False
        tool2.last_health_check = datetime.now(UTC) - timedelta(minutes=10)

        tool3 = MagicMock(spec=Tool)
        tool3.is_healthy = True
        tool3.last_health_check = None

        mock_db = create_mock_async_db([tool1, tool2, tool3])

        async def mock_get_db():
            yield mock_db

        app.dependency_overrides[get_async_db] = mock_get_db

        try:
            response = authenticated_admin_client.get("/api/v1/tools/health/status")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["total_tools"] == 3
            assert data["online"] == 2
            assert data["offline"] == 1
            assert data["health_percentage"] == pytest.approx(66.67, abs=0.01)
        finally:
            app.dependency_overrides.pop(get_async_db, None)

    def test_get_status_requires_admin(self, authenticated_user_client):
        """Test that status endpoint requires admin role."""
        mock_db = create_mock_async_db([])

        async def mock_get_db():
            yield mock_db

        app.dependency_overrides[get_async_db] = mock_get_db

        try:
            # Regular user should get 403
            response = authenticated_user_client.get("/api/v1/tools/health/status")
            # Note: admin_required dependency will raise 403 for non-admin
            assert response.status_code == status.HTTP_403_FORBIDDEN
        finally:
            app.dependency_overrides.pop(get_async_db, None)


class TestGetToolHealthHistory:
    """Tests for GET /api/v1/tools/health/{tool_id}/history endpoint."""

    def test_get_history_success(self, authenticated_admin_client, mock_tool, mock_health_check):
        """Test successful retrieval of health check history."""
        tool_id = mock_tool.id

        # Need to mock two different queries - tool lookup and health history
        mock_db = AsyncMock()

        # First call returns tool (uses scalar_one_or_none)
        tool_result = MagicMock()
        tool_result.scalar_one_or_none.return_value = mock_tool

        # Second call returns health checks (uses scalars().all())
        check_result = MagicMock()
        check_scalars = MagicMock()
        check_scalars.all.return_value = [mock_health_check]
        check_result.scalars.return_value = check_scalars

        mock_db.execute.side_effect = [tool_result, check_result]

        async def mock_get_db():
            yield mock_db

        app.dependency_overrides[get_async_db] = mock_get_db

        try:
            response = authenticated_admin_client.get(f"/api/v1/tools/health/{tool_id}/history")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["status"] == ToolStatus.ONLINE.value
            assert data[0]["response_time_ms"] == 45.2
        finally:
            app.dependency_overrides.pop(get_async_db, None)

    def test_get_history_tool_not_found(self, authenticated_admin_client):
        """Test history endpoint when tool doesn't exist."""
        tool_id = uuid4()

        mock_db = AsyncMock()
        tool_result = MagicMock()
        tool_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = tool_result

        async def mock_get_db():
            yield mock_db

        app.dependency_overrides[get_async_db] = mock_get_db

        try:
            response = authenticated_admin_client.get(f"/api/v1/tools/health/{tool_id}/history")

            assert response.status_code == status.HTTP_404_NOT_FOUND
        finally:
            app.dependency_overrides.pop(get_async_db, None)

    def test_get_history_with_hours_parameter(
        self, authenticated_admin_client, mock_tool, mock_health_check
    ):
        """Test history endpoint with custom hours parameter."""
        tool_id = mock_tool.id

        mock_db = AsyncMock()

        # First call returns tool (uses scalar_one_or_none)
        tool_result = MagicMock()
        tool_result.scalar_one_or_none.return_value = mock_tool

        # Second call returns health checks (uses scalars().all())
        check_result = MagicMock()
        check_scalars = MagicMock()
        check_scalars.all.return_value = [mock_health_check]
        check_result.scalars.return_value = check_scalars

        mock_db.execute.side_effect = [tool_result, check_result]

        async def mock_get_db():
            yield mock_db

        app.dependency_overrides[get_async_db] = mock_get_db

        try:
            response = authenticated_admin_client.get(
                f"/api/v1/tools/health/{tool_id}/history?hours=48"
            )

            assert response.status_code == status.HTTP_200_OK
            # Verify execute was called twice (tool lookup + history)
            assert mock_db.execute.call_count == 2
        finally:
            app.dependency_overrides.pop(get_async_db, None)


class TestTriggerHealthCheck:
    """Tests for POST /api/v1/tools/health/{tool_id}/check endpoint."""

    @pytest.mark.asyncio
    async def test_trigger_check_success(
        self, authenticated_admin_client, mock_tool, mock_health_check
    ):
        """Test successful manual health check trigger."""
        tool_id = mock_tool.id

        mock_db = AsyncMock()
        tool_result = MagicMock()
        tool_result.scalar_one_or_none.return_value = mock_tool
        mock_db.execute.return_value = tool_result

        mock_monitor = MagicMock()
        mock_monitor.check_tool_health = AsyncMock(return_value=mock_health_check)

        with patch(
            "src.orchestrator.app.routers.tools_health.ToolHealthMonitor",
            return_value=mock_monitor,
        ):

            async def mock_get_db():
                yield mock_db

            app.dependency_overrides[get_async_db] = mock_get_db

            try:
                response = authenticated_admin_client.post(f"/api/v1/tools/health/{tool_id}/check")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["status"] == ToolStatus.ONLINE.value
                assert data["response_time_ms"] == 45.2
                mock_monitor.check_tool_health.assert_called_once_with(tool_id)
            finally:
                app.dependency_overrides.pop(get_async_db, None)

    @pytest.mark.asyncio
    async def test_trigger_check_tool_not_found(self, authenticated_admin_client):
        """Test health check trigger when tool doesn't exist."""
        tool_id = uuid4()

        mock_db = AsyncMock()
        tool_result = MagicMock()
        tool_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = tool_result

        async def mock_get_db():
            yield mock_db

        app.dependency_overrides[get_async_db] = mock_get_db

        try:
            response = authenticated_admin_client.post(f"/api/v1/tools/health/{tool_id}/check")

            assert response.status_code == status.HTTP_404_NOT_FOUND
        finally:
            app.dependency_overrides.pop(get_async_db, None)

    @pytest.mark.asyncio
    async def test_trigger_check_health_check_fails(self, authenticated_admin_client, mock_tool):
        """Test health check trigger when health check fails."""
        tool_id = mock_tool.id

        mock_db = AsyncMock()
        tool_result = MagicMock()
        tool_result.scalar_one_or_none.return_value = mock_tool
        mock_db.execute.return_value = tool_result

        mock_monitor = MagicMock()
        mock_monitor.check_tool_health = AsyncMock(
            side_effect=ValueError("Tool health check failed")
        )

        with patch(
            "src.orchestrator.app.routers.tools_health.ToolHealthMonitor",
            return_value=mock_monitor,
        ):

            async def mock_get_db():
                yield mock_db

            app.dependency_overrides[get_async_db] = mock_get_db

            try:
                response = authenticated_admin_client.post(f"/api/v1/tools/health/{tool_id}/check")

                assert response.status_code == status.HTTP_400_BAD_REQUEST
                assert "failed" in response.json()["detail"].lower()
            finally:
                app.dependency_overrides.pop(get_async_db, None)
