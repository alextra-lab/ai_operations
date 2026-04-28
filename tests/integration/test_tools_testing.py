"""
Integration tests for Tool Testing API endpoints.

Tests tool testing endpoints with real database interactions.
Tool execution is mocked to avoid requiring actual MCP servers.

P5-A20: Migrated to async database patterns (ADR-022).
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.orchestrator.app.db.database import AsyncSessionLocal, init_db
from src.orchestrator.app.db.models import Tool
from src.orchestrator.app.main import app
from src.shared.auth import UnifiedAuthManager
from src.shared.auth.models import User, UserRole

auth_manager = UnifiedAuthManager()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a real async database session for testing."""
    await init_db()
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture
async def developer_user(db_session: AsyncSession):
    """Create a real developer user in the database."""
    timestamp = int(datetime.now(UTC).timestamp() * 1000000)
    username = f"developer_{timestamp}"
    email = f"developer_{timestamp}@example.com"
    password = "devpassword"

    user = User(
        id=uuid4(),
        username=username,
        full_name="Developer User",
        email=email,
        hashed_password=auth_manager.get_password_hash(password),
        role=UserRole.DEVELOPER,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    user._test_password = password  # type: ignore[attr-defined]

    yield user

    # Cleanup: rollback in fixture handles cleanup automatically


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    """Create a real admin user in the database."""
    timestamp = int(datetime.now(UTC).timestamp() * 1000000)
    username = f"admin_{timestamp}"
    email = f"admin_{timestamp}@example.com"
    password = "adminpassword"

    user = User(
        id=uuid4(),
        username=username,
        full_name="Admin User",
        email=email,
        hashed_password=auth_manager.get_password_hash(password),
        role=UserRole.ADMIN,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    user._test_password = password  # type: ignore[attr-defined]

    yield user

    # Cleanup: rollback in fixture handles cleanup automatically


@pytest_asyncio.fixture
async def regular_user(db_session: AsyncSession):
    """Create a real regular user in the database."""
    timestamp = int(datetime.now(UTC).timestamp() * 1000000)
    username = f"user_{timestamp}"
    email = f"user_{timestamp}@example.com"
    password = "userpassword"

    user = User(
        id=uuid4(),
        username=username,
        full_name="Regular User",
        email=email,
        hashed_password=auth_manager.get_password_hash(password),
        role=UserRole.USER,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    user._test_password = password  # type: ignore[attr-defined]

    yield user

    # Cleanup: rollback in fixture handles cleanup automatically


@pytest.fixture
def developer_token(developer_user):
    """Get a real JWT token for developer user."""
    client = TestClient(app)
    response = client.post(
        "/auth/token",
        data={
            "username": developer_user.username,
            "password": developer_user._test_password,  # type: ignore[attr-defined]
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def admin_token(admin_user):
    """Get a real JWT token for admin user."""
    client = TestClient(app)
    response = client.post(
        "/auth/token",
        data={
            "username": admin_user.username,
            "password": admin_user._test_password,  # type: ignore[attr-defined]
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def user_token(regular_user):
    """Get a real JWT token for regular user."""
    client = TestClient(app)
    response = client.post(
        "/auth/token",
        data={
            "username": regular_user.username,
            "password": regular_user._test_password,  # type: ignore[attr-defined]
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def test_tool(db_session: AsyncSession):
    """Create a test tool in the database."""
    tool = Tool(
        tool_id=f"test_tool_{uuid4().hex[:8]}",
        name="Test Tool",
        description="Test tool for integration testing",
        category="testing",
        provider="test",
        tool_purpose="orchestrator",
        service_location="orchestrator",
        mcp_server_type="http",
        mcp_endpoint="http://test-server:8000",
        mcp_protocol_version="2024-11-05",
        capabilities={"tools": ["test_function"]},
        parameters_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        },
        requires_authentication=False,
        timeout_seconds=30,
        is_enabled=True,
        is_healthy=True,
    )
    db_session.add(tool)
    await db_session.commit()
    await db_session.refresh(tool)

    yield tool

    # Cleanup: rollback in fixture handles cleanup automatically


@pytest_asyncio.fixture
async def disabled_tool(db_session: AsyncSession):
    """Create a disabled test tool in the database."""
    tool = Tool(
        tool_id=f"disabled_tool_{uuid4().hex[:8]}",
        name="Disabled Tool",
        description="Disabled tool for testing",
        category="testing",
        provider="test",
        tool_purpose="orchestrator",
        service_location="orchestrator",
        mcp_server_type="http",
        mcp_endpoint="http://test-server:8000",
        mcp_protocol_version="2024-11-05",
        is_enabled=False,
    )
    db_session.add(tool)
    await db_session.commit()
    await db_session.refresh(tool)

    yield tool

    # Cleanup: rollback in fixture handles cleanup automatically


class TestToolTestingIntegration:
    """Integration tests for tool testing endpoints."""

    def test_execute_tool_success_developer(self, developer_token, test_tool):
        """Test successful tool execution by developer."""
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {developer_token}"}

        mock_executor = AsyncMock()
        mock_executor.execute_tool = AsyncMock(
            return_value={"result": "test success", "data": "test data"}
        )

        with patch("app.routers.tools_testing.ToolExecutor", return_value=mock_executor):
            response = client.post(
                "/api/v1/tools/test/execute",
                json={
                    "tool_id": str(test_tool.id),
                    "tool_name": "test_function",
                    "parameters": {"query": "test query", "limit": 10},
                },
                headers=headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "success"
        assert "result" in data
        assert "duration_ms" in data

    def test_execute_tool_success_admin(self, admin_token, test_tool):
        """Test successful tool execution by admin."""
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {admin_token}"}

        mock_executor = AsyncMock()
        mock_executor.execute_tool = AsyncMock(return_value={"result": "test success"})

        with patch("app.routers.tools_testing.ToolExecutor", return_value=mock_executor):
            response = client.post(
                "/api/v1/tools/test/execute",
                json={
                    "tool_id": str(test_tool.id),
                    "tool_name": "test_function",
                    "parameters": {"query": "test query"},
                },
                headers=headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_execute_tool_unauthorized_user(self, user_token, test_tool):
        """Test that regular users cannot execute tools."""
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {user_token}"}

        response = client.post(
            "/api/v1/tools/test/execute",
            json={
                "tool_id": str(test_tool.id),
                "tool_name": "test_function",
                "parameters": {"query": "test"},
            },
            headers=headers,
        )

        assert response.status_code == 403
        assert "Only admin or developer" in response.json()["detail"]

    def test_execute_tool_not_found(self, developer_token):
        """Test execution with non-existent tool."""
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {developer_token}"}

        response = client.post(
            "/api/v1/tools/test/execute",
            json={
                "tool_id": str(uuid4()),
                "tool_name": "test_function",
                "parameters": {"query": "test"},
            },
            headers=headers,
        )

        assert response.status_code == 404

    def test_execute_tool_disabled(self, developer_token, disabled_tool):
        """Test execution with disabled tool."""
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {developer_token}"}

        response = client.post(
            "/api/v1/tools/test/execute",
            json={
                "tool_id": str(disabled_tool.id),
                "tool_name": "test_function",
                "parameters": {"query": "test"},
            },
            headers=headers,
        )

        assert response.status_code == 400
        assert "disabled" in response.json()["detail"].lower()

    def test_execute_tool_error_handling(self, developer_token, test_tool):
        """Test error handling during tool execution."""
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {developer_token}"}

        mock_executor = AsyncMock()
        mock_executor.execute_tool = AsyncMock(side_effect=ValueError("Tool validation failed"))

        with patch("app.routers.tools_testing.ToolExecutor", return_value=mock_executor):
            response = client.post(
                "/api/v1/tools/test/execute",
                json={
                    "tool_id": str(test_tool.id),
                    "tool_name": "test_function",
                    "parameters": {"query": "test"},
                },
                headers=headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["status"] == "error"
        assert "error" in data

    def test_validate_parameters_success(self, developer_token, test_tool):
        """Test successful parameter validation."""
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {developer_token}"}

        response = client.post(
            "/api/v1/tools/test/validate-parameters",
            json={
                "tool_id": str(test_tool.id),
                "parameters": {"query": "test query", "limit": 10},
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    def test_validate_parameters_invalid(self, developer_token, test_tool):
        """Test parameter validation with invalid parameters."""
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {developer_token}"}

        # Missing required field "query"
        response = client.post(
            "/api/v1/tools/test/validate-parameters",
            json={
                "tool_id": str(test_tool.id),
                "parameters": {"limit": 10},
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "error" in data

    def test_validate_parameters_wrong_type(self, developer_token, test_tool):
        """Test parameter validation with wrong type."""
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {developer_token}"}

        # Wrong type for limit (string instead of integer)
        response = client.post(
            "/api/v1/tools/test/validate-parameters",
            json={
                "tool_id": str(test_tool.id),
                "parameters": {"query": "test", "limit": "not a number"},
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "error" in data

    def test_validate_parameters_no_schema(self, developer_token, disabled_tool):
        """Test parameter validation with no schema defined."""
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {developer_token}"}

        response = client.post(
            "/api/v1/tools/test/validate-parameters",
            json={
                "tool_id": str(disabled_tool.id),
                "parameters": {"query": "test"},
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "message" in data
        assert "No schema defined" in data["message"]

    def test_validate_parameters_tool_not_found(self, developer_token):
        """Test parameter validation with non-existent tool."""
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {developer_token}"}

        response = client.post(
            "/api/v1/tools/test/validate-parameters",
            json={
                "tool_id": str(uuid4()),
                "parameters": {"query": "test"},
            },
            headers=headers,
        )

        assert response.status_code == 404

    def test_validate_parameters_unauthorized_user(self, user_token, test_tool):
        """Test that regular users cannot validate parameters."""
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {user_token}"}

        response = client.post(
            "/api/v1/tools/test/validate-parameters",
            json={
                "tool_id": str(test_tool.id),
                "parameters": {"query": "test"},
            },
            headers=headers,
        )

        assert response.status_code == 403
        assert "Only admin or developer" in response.json()["detail"]

    def test_validate_parameters_admin_access(self, admin_token, test_tool):
        """Test that admins can validate parameters."""
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.post(
            "/api/v1/tools/test/validate-parameters",
            json={
                "tool_id": str(test_tool.id),
                "parameters": {"query": "test query", "limit": 10},
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
