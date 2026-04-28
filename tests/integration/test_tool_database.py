"""
Integration tests for tool database models.

Tests database operations, relationships, and constraints.

P5-A20: Migrated to async database patterns (ADR-022).
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.orchestrator.app.db.models import (
    Tool,
    ToolHealthCheck,
    ToolInvocation,
    ToolPermission,
    ToolSecret,
)


class TestToolDatabase:
    """Test tool database operations."""

    @pytest.mark.asyncio
    async def test_create_tool(self, db_session: AsyncSession):
        """Test creating a tool in the database."""
        tool = Tool(
            tool_id="test_elasticsearch",
            name="Test Elasticsearch",
            description="Test Elasticsearch tool",
            category="database",
            provider="elastic",
            tool_purpose="retrieval",
            service_location="retrieval_service",
            mcp_server_type="http",
            mcp_endpoint="http://elasticsearch:9200",
            mcp_protocol_version="2024-11-05",
            capabilities={"tools": ["search"]},
            parameters_schema={"query": {"type": "string"}},
            requires_authentication=True,
            authentication_type="api_key",
            secret_name="elasticsearch_api_key",
            config_options={"index": "documents"},
            timeout_seconds=30,
            rate_limit_per_minute=100,
            max_concurrent_calls=5,
            is_enabled=True,
            health_check_interval_seconds=300,
            version="1.0.0",
            documentation_url="https://docs.example.com",
            tags=["search", "database"],
        )

        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        assert tool.id is not None
        assert tool.tool_id == "test_elasticsearch"
        assert tool.name == "Test Elasticsearch"
        assert tool.category == "database"
        assert tool.tool_purpose == "retrieval"
        assert tool.service_location == "retrieval_service"
        assert tool.mcp_server_type == "http"
        assert tool.is_enabled is True
        assert tool.tags == ["search", "database"]

    @pytest.mark.asyncio
    async def test_create_tool_with_minimal_fields(self, db_session: AsyncSession):
        """Test creating a tool with minimal required fields."""
        tool = Tool(
            tool_id="minimal_tool",
            name="Minimal Tool",
            category="custom",
            tool_purpose="orchestrator",
            service_location="orchestrator",
            mcp_server_type="stdio",
        )

        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        assert tool.id is not None
        assert tool.tool_id == "minimal_tool"
        assert tool.name == "Minimal Tool"
        assert tool.category == "custom"
        assert tool.tool_purpose == "orchestrator"
        assert tool.service_location == "orchestrator"
        assert tool.mcp_server_type == "stdio"
        # Check defaults
        assert tool.description is None
        assert tool.provider is None
        assert tool.requires_authentication is False
        assert tool.timeout_seconds == 30
        assert tool.max_concurrent_calls == 5
        assert tool.is_enabled is False
        assert tool.is_healthy is False
        assert tool.tags == []

    @pytest.mark.asyncio
    async def test_tool_unique_constraint(self, db_session: AsyncSession):
        """Test that tool_id must be unique."""
        # Create first tool
        tool1 = Tool(
            tool_id="duplicate_tool",
            name="First Tool",
            category="database",
            tool_purpose="retrieval",
            service_location="retrieval_service",
            mcp_server_type="stdio",
        )
        db_session.add(tool1)
        await db_session.commit()

        # Try to create second tool with same tool_id
        tool2 = Tool(
            tool_id="duplicate_tool",
            name="Second Tool",
            category="database",
            tool_purpose="retrieval",
            service_location="retrieval_service",
            mcp_server_type="stdio",
        )
        db_session.add(tool2)

        with pytest.raises(Exception):  # Should raise IntegrityError
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_tool_category_constraint(self, db_session: AsyncSession):
        """Test that category must be valid."""
        tool = Tool(
            tool_id="invalid_category_tool",
            name="Invalid Category Tool",
            category="invalid_category",  # Invalid
            tool_purpose="retrieval",
            service_location="retrieval_service",
            mcp_server_type="stdio",
        )
        db_session.add(tool)

        with pytest.raises(Exception):  # Should raise IntegrityError
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_tool_purpose_constraint(self, db_session: AsyncSession):
        """Test that tool_purpose must be valid."""
        tool = Tool(
            tool_id="invalid_purpose_tool",
            name="Invalid Purpose Tool",
            category="database",
            tool_purpose="invalid_purpose",  # Invalid
            service_location="retrieval_service",
            mcp_server_type="stdio",
        )
        db_session.add(tool)

        with pytest.raises(Exception):  # Should raise IntegrityError
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_tool_service_location_constraint(self, db_session: AsyncSession):
        """Test that service_location must be valid."""
        tool = Tool(
            tool_id="invalid_location_tool",
            name="Invalid Location Tool",
            category="database",
            tool_purpose="retrieval",
            service_location="invalid_location",  # Invalid
            mcp_server_type="stdio",
        )
        db_session.add(tool)

        with pytest.raises(Exception):  # Should raise IntegrityError
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_tool_mcp_server_type_constraint(self, db_session: AsyncSession):
        """Test that mcp_server_type must be valid."""
        tool = Tool(
            tool_id="invalid_mcp_type_tool",
            name="Invalid MCP Type Tool",
            category="database",
            tool_purpose="retrieval",
            service_location="retrieval_service",
            mcp_server_type="invalid_type",  # Invalid
        )
        db_session.add(tool)

        with pytest.raises(Exception):  # Should raise IntegrityError
            await db_session.commit()


class TestToolSecretDatabase:
    """Test tool secret database operations."""

    @pytest.mark.asyncio
    async def test_create_tool_secret(self, db_session: AsyncSession, test_tool: Tool):
        """Test creating a tool secret."""
        secret = ToolSecret(
            tool_id=test_tool.id,
            secret_name="test_api_key",
            secret_type="api_key",
            encrypted_value=b"encrypted_data_here",
            encryption_key_id="default",
        )

        db_session.add(secret)
        await db_session.commit()
        await db_session.refresh(secret)

        assert secret.id is not None
        assert secret.tool_id == test_tool.id
        assert secret.secret_name == "test_api_key"
        assert secret.secret_type == "api_key"
        assert secret.encrypted_value == b"encrypted_data_here"
        assert secret.encryption_key_id == "default"
        assert secret.is_active is True
        assert secret.access_count == 0

    @pytest.mark.asyncio
    async def test_tool_secret_unique_constraint(self, db_session: AsyncSession, test_tool: Tool):
        """Test that secret_name must be unique."""
        # Create first secret
        secret1 = ToolSecret(
            tool_id=test_tool.id,
            secret_name="duplicate_secret",
            secret_type="api_key",
            encrypted_value=b"encrypted_data_1",
            encryption_key_id="default",
        )
        db_session.add(secret1)
        await db_session.commit()

        # Try to create second secret with same secret_name
        secret2 = ToolSecret(
            tool_id=test_tool.id,
            secret_name="duplicate_secret",
            secret_type="api_key",
            encrypted_value=b"encrypted_data_2",
            encryption_key_id="default",
        )
        db_session.add(secret2)

        with pytest.raises(Exception):  # Should raise IntegrityError
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_tool_secret_type_constraint(self, db_session: AsyncSession, test_tool: Tool):
        """Test that secret_type must be valid."""
        secret = ToolSecret(
            tool_id=test_tool.id,
            secret_name="invalid_type_secret",
            secret_type="invalid_type",  # Invalid
            encrypted_value=b"encrypted_data",
            encryption_key_id="default",
        )
        db_session.add(secret)

        with pytest.raises(Exception):  # Should raise IntegrityError
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_tool_secret_cascade_delete(self, db_session: AsyncSession, test_tool: Tool):
        """Test that secrets are deleted when tool is deleted."""
        secret = ToolSecret(
            tool_id=test_tool.id,
            secret_name="cascade_test_secret",
            secret_type="api_key",
            encrypted_value=b"encrypted_data",
            encryption_key_id="default",
        )
        db_session.add(secret)
        await db_session.commit()

        secret_id = secret.id

        # Delete the tool
        await db_session.delete(test_tool)
        await db_session.commit()

        # Secret should be deleted due to CASCADE
        deleted_secret = await db_session.get(ToolSecret, secret_id)
        assert deleted_secret is None


class TestToolHealthCheckDatabase:
    """Test tool health check database operations."""

    @pytest.mark.asyncio
    async def test_create_tool_health_check(self, db_session: AsyncSession, test_tool: Tool):
        """Test creating a tool health check."""
        health_check = ToolHealthCheck(
            tool_id=test_tool.id,
            status="online",
            response_time_ms=150.5,
            error_message=None,
            error_code=None,
            mcp_server_info={"version": "1.0.0", "capabilities": ["search"]},
        )

        db_session.add(health_check)
        await db_session.commit()
        await db_session.refresh(health_check)

        assert health_check.id is not None
        assert health_check.tool_id == test_tool.id
        assert health_check.status == "online"
        assert health_check.response_time_ms == 150.5
        assert health_check.error_message is None
        assert health_check.mcp_server_info == {"version": "1.0.0", "capabilities": ["search"]}

    @pytest.mark.asyncio
    async def test_tool_health_check_status_constraint(
        self, db_session: AsyncSession, test_tool: Tool
    ):
        """Test that status must be valid."""
        health_check = ToolHealthCheck(
            tool_id=test_tool.id,
            status="invalid_status",  # Invalid
            response_time_ms=150.5,
        )
        db_session.add(health_check)

        with pytest.raises(Exception):  # Should raise IntegrityError
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_tool_health_check_cascade_delete(
        self, db_session: AsyncSession, test_tool: Tool
    ):
        """Test that health checks are deleted when tool is deleted."""
        health_check = ToolHealthCheck(
            tool_id=test_tool.id, status="online", response_time_ms=150.5
        )
        db_session.add(health_check)
        await db_session.commit()

        health_check_id = health_check.id

        # Delete the tool
        await db_session.delete(test_tool)
        await db_session.commit()

        # Health check should be deleted due to CASCADE
        deleted_health_check = await db_session.get(ToolHealthCheck, health_check_id)
        assert deleted_health_check is None


class TestToolPermissionDatabase:
    """Test tool permission database operations."""

    @pytest.mark.asyncio
    async def test_create_tool_permission(self, db_session: AsyncSession, test_tool: Tool):
        """Test creating a tool permission."""
        permission = ToolPermission(
            tool_id=test_tool.id,
            role="analyst",
            can_view=True,
            can_use=True,
            can_configure=False,
            max_calls_per_hour=100,
            max_calls_per_day=1000,
        )

        db_session.add(permission)
        await db_session.commit()
        await db_session.refresh(permission)

        assert permission.id is not None
        assert permission.tool_id == test_tool.id
        assert permission.role == "analyst"
        assert permission.can_view is True
        assert permission.can_use is True
        assert permission.can_configure is False
        assert permission.max_calls_per_hour == 100
        assert permission.max_calls_per_day == 1000

    @pytest.mark.asyncio
    async def test_tool_permission_unique_constraint(
        self, db_session: AsyncSession, test_tool: Tool
    ):
        """Test that tool_id + role combination must be unique."""
        # Create first permission
        permission1 = ToolPermission(
            tool_id=test_tool.id, role="analyst", can_view=True, can_use=True
        )
        db_session.add(permission1)
        await db_session.commit()

        # Try to create second permission with same tool_id + role
        permission2 = ToolPermission(
            tool_id=test_tool.id,
            role="analyst",  # Same role
            can_view=True,
            can_use=False,
        )
        db_session.add(permission2)

        with pytest.raises(Exception):  # Should raise IntegrityError
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_tool_permission_cascade_delete(self, db_session: AsyncSession, test_tool: Tool):
        """Test that permissions are deleted when tool is deleted."""
        permission = ToolPermission(
            tool_id=test_tool.id, role="analyst", can_view=True, can_use=True
        )
        db_session.add(permission)
        await db_session.commit()

        permission_id = permission.id

        # Delete the tool
        await db_session.delete(test_tool)
        await db_session.commit()

        # Permission should be deleted due to CASCADE
        deleted_permission = await db_session.get(ToolPermission, permission_id)
        assert deleted_permission is None


class TestToolInvocationDatabase:
    """Test tool invocation database operations."""

    @pytest.mark.asyncio
    async def test_create_tool_invocation(self, db_session: AsyncSession, test_tool: Tool):
        """Test creating a tool invocation."""
        invocation = ToolInvocation(
            tool_id=test_tool.id,
            run_id="test_run_123",
            user_id=uuid4(),
            center_id="test_center",
            tool_name="elasticsearch_search",
            tool_parameters={"query": "test query"},
            status="success",
            response_data={"hits": [], "total": 0},
            error_message=None,
            completed_at=datetime.now(UTC),
            duration_ms=150.5,
            mcp_protocol_version="2024-11-05",
            cost_estimate=0.001,
        )

        db_session.add(invocation)
        await db_session.commit()
        await db_session.refresh(invocation)

        assert invocation.id is not None
        assert invocation.tool_id == test_tool.id
        assert invocation.run_id == "test_run_123"
        assert invocation.tool_name == "elasticsearch_search"
        assert invocation.status == "success"
        assert invocation.duration_ms == 150.5
        assert invocation.cost_estimate == 0.001

    @pytest.mark.asyncio
    async def test_tool_invocation_status_constraint(
        self, db_session: AsyncSession, test_tool: Tool
    ):
        """Test that status must be valid."""
        invocation = ToolInvocation(
            tool_id=test_tool.id,
            tool_name="test_tool",
            status="invalid_status",  # Invalid
        )
        db_session.add(invocation)

        with pytest.raises(Exception):  # Should raise IntegrityError
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_tool_invocation_without_tool(self, db_session: AsyncSession):
        """Test creating invocation without tool (tool may be deleted)."""
        invocation = ToolInvocation(
            tool_id=None,  # No tool
            tool_name="deleted_tool",
            status="error",
            error_message="Tool not found",
        )

        db_session.add(invocation)
        await db_session.commit()
        await db_session.refresh(invocation)

        assert invocation.id is not None
        assert invocation.tool_id is None
        assert invocation.tool_name == "deleted_tool"
        assert invocation.status == "error"
        assert invocation.error_message == "Tool not found"


class TestToolRelationships:
    """Test tool model relationships."""

    @pytest.mark.asyncio
    async def test_tool_secrets_relationship(self, db_session: AsyncSession, test_tool: Tool):
        """Test tool-secrets relationship."""
        secret1 = ToolSecret(
            tool_id=test_tool.id,
            secret_name="secret1",
            secret_type="api_key",
            encrypted_value=b"data1",
            encryption_key_id="default",
        )
        secret2 = ToolSecret(
            tool_id=test_tool.id,
            secret_name="secret2",
            secret_type="oauth_token",
            encrypted_value=b"data2",
            encryption_key_id="default",
        )

        db_session.add_all([secret1, secret2])
        await db_session.commit()

        # Refresh tool to load relationships
        await db_session.refresh(test_tool)

        assert len(test_tool.secrets) == 2
        assert secret1 in test_tool.secrets
        assert secret2 in test_tool.secrets

    @pytest.mark.asyncio
    async def test_tool_health_checks_relationship(self, db_session: AsyncSession, test_tool: Tool):
        """Test tool-health_checks relationship."""
        health1 = ToolHealthCheck(tool_id=test_tool.id, status="online", response_time_ms=100.0)
        health2 = ToolHealthCheck(tool_id=test_tool.id, status="offline", response_time_ms=200.0)

        db_session.add_all([health1, health2])
        await db_session.commit()

        # Refresh tool to load relationships
        await db_session.refresh(test_tool)

        assert len(test_tool.health_checks) == 2
        assert health1 in test_tool.health_checks
        assert health2 in test_tool.health_checks

    @pytest.mark.asyncio
    async def test_tool_permissions_relationship(self, db_session: AsyncSession, test_tool: Tool):
        """Test tool-permissions relationship."""
        perm1 = ToolPermission(tool_id=test_tool.id, role="analyst", can_view=True, can_use=True)
        perm2 = ToolPermission(tool_id=test_tool.id, role="user", can_view=True, can_use=False)

        db_session.add_all([perm1, perm2])
        await db_session.commit()

        # Refresh tool to load relationships
        await db_session.refresh(test_tool)

        assert len(test_tool.permissions) == 2
        assert perm1 in test_tool.permissions
        assert perm2 in test_tool.permissions

    @pytest.mark.asyncio
    async def test_tool_invocations_relationship(self, db_session: AsyncSession, test_tool: Tool):
        """Test tool-invocations relationship."""
        inv1 = ToolInvocation(tool_id=test_tool.id, tool_name="test_tool", status="success")
        inv2 = ToolInvocation(tool_id=test_tool.id, tool_name="test_tool", status="error")

        db_session.add_all([inv1, inv2])
        await db_session.commit()

        # Refresh tool to load relationships
        await db_session.refresh(test_tool)

        assert len(test_tool.invocations) == 2
        assert inv1 in test_tool.invocations
        assert inv2 in test_tool.invocations


@pytest_asyncio.fixture
async def test_tool(db_session: AsyncSession):
    """Create a test tool for use in other tests."""
    # Use timestamp to ensure unique tool_id
    timestamp = int(datetime.now(UTC).timestamp() * 1000000)
    tool = Tool(
        tool_id=f"test_tool_{timestamp}",
        name="Test Tool",
        category="database",
        tool_purpose="retrieval",
        service_location="retrieval_service",
        mcp_server_type="stdio",
    )
    db_session.add(tool)
    await db_session.commit()
    await db_session.refresh(tool)
    yield tool
    # Cleanup: fixture rollback handles cleanup automatically
