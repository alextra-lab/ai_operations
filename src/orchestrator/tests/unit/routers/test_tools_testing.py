"""
Unit tests for tools_testing router.

Tests tool testing endpoints for execution and parameter validation.
All database operations are mocked - no real database interaction.

Fully async per ADR-022 (P5-A23 - converted Nov 2025).
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from shared.auth import get_current_user
from shared.auth.models import TokenPayload, UserRole
from src.orchestrator.app.db.database import get_async_db
from src.orchestrator.app.db.models import Tool
from src.orchestrator.app.main import app


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
def mock_developer_user():
    """Create a mock developer user token payload."""
    now = datetime.now(tz=UTC)
    return TokenPayload(
        sub="developer",
        user_id=str(uuid4()),
        username="developer",
        role="developer",
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
    tool.parameters_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer"},
        },
        "required": ["query"],
    }
    return tool


@pytest.fixture
def mock_disabled_tool():
    """Create a mock disabled tool."""
    tool_id = uuid4()
    tool = MagicMock(spec=Tool)
    tool.id = tool_id
    tool.tool_id = "disabled_tool"
    tool.name = "Disabled Tool"
    tool.is_enabled = False
    tool.parameters_schema = None
    return tool


def create_mock_async_db(tool_to_return=None):
    """Create a mock async database session."""
    mock_db = AsyncMock()
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = tool_to_return
    mock_db.execute.return_value = mock_result
    return mock_db


@pytest.fixture
def authenticated_admin_client(mock_admin_user):
    """Create a test client with admin authentication."""

    def mock_get_current_user():
        return mock_admin_user

    async def mock_get_async_db():
        yield AsyncMock()

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_async_db] = mock_get_async_db

    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_developer_client(mock_developer_user):
    """Create a test client with developer authentication."""

    def mock_get_current_user():
        return mock_developer_user

    async def mock_get_async_db():
        yield AsyncMock()

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_async_db] = mock_get_async_db

    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_user_client(mock_regular_user):
    """Create a test client with regular user authentication."""

    def mock_get_current_user():
        return mock_regular_user

    async def mock_get_async_db():
        yield AsyncMock()

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_async_db] = mock_get_async_db

    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


class TestTestToolExecution:
    """Tests for test_tool_execution endpoint."""

    def test_execute_tool_success_admin(self, mock_admin_user, mock_tool):
        """Test successful tool execution by admin."""
        mock_db = create_mock_async_db(mock_tool)

        def mock_get_current_user():
            return mock_admin_user

        async def mock_get_async_db():
            yield mock_db

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_async_db] = mock_get_async_db

        mock_executor = AsyncMock()
        mock_executor.execute_tool = AsyncMock(
            return_value={"result": "test success", "data": "test data"}
        )

        with (
            TestClient(app) as client,
            patch(
                "src.orchestrator.app.routers.tools_testing.ToolExecutor",
                return_value=mock_executor,
            ),
        ):
            response = client.post(
                "/api/v1/tools/test/execute",
                json={
                    "tool_id": str(mock_tool.id),
                    "tool_name": "test_tool_function",
                    "parameters": {"query": "test query", "limit": 10},
                },
            )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "success"
        assert data["result"] == {"result": "test success", "data": "test data"}
        assert "duration_ms" in data
        assert data["duration_ms"] >= 0

    def test_execute_tool_success_developer(self, mock_developer_user, mock_tool):
        """Test successful tool execution by developer."""
        mock_db = create_mock_async_db(mock_tool)

        def mock_get_current_user():
            return mock_developer_user

        async def mock_get_async_db():
            yield mock_db

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_async_db] = mock_get_async_db

        mock_executor = AsyncMock()
        mock_executor.execute_tool = AsyncMock(return_value={"result": "test success"})

        with (
            TestClient(app) as client,
            patch(
                "src.orchestrator.app.routers.tools_testing.ToolExecutor",
                return_value=mock_executor,
            ),
        ):
            response = client.post(
                "/api/v1/tools/test/execute",
                json={
                    "tool_id": str(mock_tool.id),
                    "tool_name": "test_tool_function",
                    "parameters": {"query": "test"},
                },
            )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "success"

    def test_execute_tool_unauthorized_user(self, mock_regular_user, mock_tool):
        """Test that regular users cannot execute tools."""
        mock_db = create_mock_async_db(mock_tool)

        def mock_get_current_user():
            return mock_regular_user

        async def mock_get_async_db():
            yield mock_db

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_async_db] = mock_get_async_db

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/tools/test/execute",
                json={
                    "tool_id": str(mock_tool.id),
                    "tool_name": "test_tool_function",
                    "parameters": {"query": "test"},
                },
            )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Only admin or developer" in response.json()["detail"]

    def test_execute_tool_not_found(self, mock_admin_user):
        """Test execution with non-existent tool."""
        mock_db = create_mock_async_db(None)

        def mock_get_current_user():
            return mock_admin_user

        async def mock_get_async_db():
            yield mock_db

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_async_db] = mock_get_async_db

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/tools/test/execute",
                json={
                    "tool_id": str(uuid4()),
                    "tool_name": "test_tool_function",
                    "parameters": {"query": "test"},
                },
            )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_execute_tool_disabled(self, mock_admin_user, mock_disabled_tool):
        """Test execution with disabled tool."""
        mock_db = create_mock_async_db(mock_disabled_tool)

        def mock_get_current_user():
            return mock_admin_user

        async def mock_get_async_db():
            yield mock_db

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_async_db] = mock_get_async_db

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/tools/test/execute",
                json={
                    "tool_id": str(mock_disabled_tool.id),
                    "tool_name": "test_tool_function",
                    "parameters": {"query": "test"},
                },
            )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "disabled" in response.json()["detail"].lower()

    def test_execute_tool_value_error(self, mock_admin_user, mock_tool):
        """Test execution with ValueError from executor."""
        mock_db = create_mock_async_db(mock_tool)

        def mock_get_current_user():
            return mock_admin_user

        async def mock_get_async_db():
            yield mock_db

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_async_db] = mock_get_async_db

        mock_executor = AsyncMock()
        mock_executor.execute_tool = AsyncMock(side_effect=ValueError("Tool validation failed"))

        with (
            TestClient(app) as client,
            patch(
                "src.orchestrator.app.routers.tools_testing.ToolExecutor",
                return_value=mock_executor,
            ),
        ):
            response = client.post(
                "/api/v1/tools/test/execute",
                json={
                    "tool_id": str(mock_tool.id),
                    "tool_name": "test_tool_function",
                    "parameters": {"query": "test"},
                },
            )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert data["status"] == "error"
        assert "error" in data
        assert "duration_ms" in data

    def test_execute_tool_runtime_error(self, mock_admin_user, mock_tool):
        """Test execution with RuntimeError from executor."""
        mock_db = create_mock_async_db(mock_tool)

        def mock_get_current_user():
            return mock_admin_user

        async def mock_get_async_db():
            yield mock_db

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_async_db] = mock_get_async_db

        mock_executor = AsyncMock()
        mock_executor.execute_tool = AsyncMock(side_effect=RuntimeError("Circuit breaker open"))

        with (
            TestClient(app) as client,
            patch(
                "src.orchestrator.app.routers.tools_testing.ToolExecutor",
                return_value=mock_executor,
            ),
        ):
            response = client.post(
                "/api/v1/tools/test/execute",
                json={
                    "tool_id": str(mock_tool.id),
                    "tool_name": "test_tool_function",
                    "parameters": {"query": "test"},
                },
            )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert data["status"] == "error"
        assert "error" in data

    def test_execute_tool_permission_error(self, mock_admin_user, mock_tool):
        """Test execution with PermissionError from executor."""
        mock_db = create_mock_async_db(mock_tool)

        def mock_get_current_user():
            return mock_admin_user

        async def mock_get_async_db():
            yield mock_db

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_async_db] = mock_get_async_db

        mock_executor = AsyncMock()
        mock_executor.execute_tool = AsyncMock(side_effect=PermissionError("User lacks permission"))

        with (
            TestClient(app) as client,
            patch(
                "src.orchestrator.app.routers.tools_testing.ToolExecutor",
                return_value=mock_executor,
            ),
        ):
            response = client.post(
                "/api/v1/tools/test/execute",
                json={
                    "tool_id": str(mock_tool.id),
                    "tool_name": "test_tool_function",
                    "parameters": {"query": "test"},
                },
            )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permission" in response.json()["detail"].lower()

    def test_execute_tool_unexpected_error(self, mock_admin_user, mock_tool):
        """Test execution with unexpected exception."""
        mock_db = create_mock_async_db(mock_tool)

        def mock_get_current_user():
            return mock_admin_user

        async def mock_get_async_db():
            yield mock_db

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_async_db] = mock_get_async_db

        mock_executor = AsyncMock()
        mock_executor.execute_tool = AsyncMock(side_effect=Exception("Unexpected error"))

        with (
            TestClient(app) as client,
            patch(
                "src.orchestrator.app.routers.tools_testing.ToolExecutor",
                return_value=mock_executor,
            ),
        ):
            response = client.post(
                "/api/v1/tools/test/execute",
                json={
                    "tool_id": str(mock_tool.id),
                    "tool_name": "test_tool_function",
                    "parameters": {"query": "test"},
                },
            )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert data["status"] == "error"
        assert "error" in data


class TestValidateToolParameters:
    """Tests for validate_tool_parameters endpoint."""

    def test_validate_parameters_success(self, mock_admin_user, mock_tool):
        """Test successful parameter validation."""
        mock_db = create_mock_async_db(mock_tool)

        def mock_get_current_user():
            return mock_admin_user

        async def mock_get_async_db():
            yield mock_db

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_async_db] = mock_get_async_db

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/tools/test/validate-parameters",
                json={
                    "tool_id": str(mock_tool.id),
                    "parameters": {"query": "test query", "limit": 10},
                },
            )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is True

    def test_validate_parameters_invalid(self, mock_admin_user, mock_tool):
        """Test parameter validation with invalid parameters."""
        mock_db = create_mock_async_db(mock_tool)

        def mock_get_current_user():
            return mock_admin_user

        async def mock_get_async_db():
            yield mock_db

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_async_db] = mock_get_async_db

        with TestClient(app) as client:
            # Missing required field "query"
            response = client.post(
                "/api/v1/tools/test/validate-parameters",
                json={
                    "tool_id": str(mock_tool.id),
                    "parameters": {"limit": 10},
                },
            )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is False
        assert "error" in data

    def test_validate_parameters_wrong_type(self, mock_admin_user, mock_tool):
        """Test parameter validation with wrong type."""
        mock_db = create_mock_async_db(mock_tool)

        def mock_get_current_user():
            return mock_admin_user

        async def mock_get_async_db():
            yield mock_db

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_async_db] = mock_get_async_db

        with TestClient(app) as client:
            # Wrong type for limit (string instead of integer)
            response = client.post(
                "/api/v1/tools/test/validate-parameters",
                json={
                    "tool_id": str(mock_tool.id),
                    "parameters": {"query": "test", "limit": "not a number"},
                },
            )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is False
        assert "error" in data

    def test_validate_parameters_no_schema(self, mock_admin_user, mock_disabled_tool):
        """Test parameter validation with no schema defined."""
        mock_db = create_mock_async_db(mock_disabled_tool)

        def mock_get_current_user():
            return mock_admin_user

        async def mock_get_async_db():
            yield mock_db

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_async_db] = mock_get_async_db

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/tools/test/validate-parameters",
                json={
                    "tool_id": str(mock_disabled_tool.id),
                    "parameters": {"query": "test"},
                },
            )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is True
        assert "message" in data
        assert "No schema defined" in data["message"]

    def test_validate_parameters_tool_not_found(self, mock_admin_user):
        """Test parameter validation with non-existent tool."""
        mock_db = create_mock_async_db(None)

        def mock_get_current_user():
            return mock_admin_user

        async def mock_get_async_db():
            yield mock_db

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_async_db] = mock_get_async_db

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/tools/test/validate-parameters",
                json={
                    "tool_id": str(uuid4()),
                    "parameters": {"query": "test"},
                },
            )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_validate_parameters_unauthorized_user(self, mock_regular_user, mock_tool):
        """Test that regular users cannot validate parameters."""
        mock_db = create_mock_async_db(mock_tool)

        def mock_get_current_user():
            return mock_regular_user

        async def mock_get_async_db():
            yield mock_db

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_async_db] = mock_get_async_db

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/tools/test/validate-parameters",
                json={
                    "tool_id": str(mock_tool.id),
                    "parameters": {"query": "test"},
                },
            )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Only admin or developer" in response.json()["detail"]

    def test_validate_parameters_developer_access(self, mock_developer_user, mock_tool):
        """Test that developers can validate parameters."""
        mock_db = create_mock_async_db(mock_tool)

        def mock_get_current_user():
            return mock_developer_user

        async def mock_get_async_db():
            yield mock_db

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_async_db] = mock_get_async_db

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/tools/test/validate-parameters",
                json={
                    "tool_id": str(mock_tool.id),
                    "parameters": {"query": "test query", "limit": 10},
                },
            )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is True
