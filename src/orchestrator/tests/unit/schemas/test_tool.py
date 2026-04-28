"""
Unit tests for tool management schemas.

Tests Pydantic model validation, serialization, and business logic.
"""

import pytest
from pydantic import ValidationError

from src.orchestrator.app.schemas.tool import (
    InvocationStatus,
    MCPServerType,
    ServiceLocation,
    ToolBase,
    ToolCategory,
    ToolCreate,
    ToolHealthCheck,
    ToolInvocationCreate,
    ToolListItem,
    ToolPermissionCreate,
    ToolPurpose,
    ToolSecretCreate,
    ToolStatus,
)


class TestToolCategory:
    """Test tool category enum."""

    def test_valid_categories(self):
        """All valid categories should be accepted."""
        valid_categories = [
            "database",
            "vector_db",
            "web_scraping",
            "reasoning",
            "documentation",
            "code_analysis",
            "threat_intel",
            "custom",
        ]

        for category in valid_categories:
            assert ToolCategory(category) == category

    def test_invalid_category_raises_error(self):
        """Invalid category should raise ValidationError."""
        with pytest.raises(ValueError):
            ToolCategory("invalid_category")


class TestToolPurpose:
    """Test tool purpose enum."""

    def test_valid_purposes(self):
        """All valid purposes should be accepted."""
        assert ToolPurpose("retrieval") == "retrieval"
        assert ToolPurpose("orchestrator") == "orchestrator"

    def test_invalid_purpose_raises_error(self):
        """Invalid purpose should raise ValidationError."""
        with pytest.raises(ValueError):
            ToolPurpose("invalid_purpose")


class TestServiceLocation:
    """Test service location enum."""

    def test_valid_locations(self):
        """All valid locations should be accepted."""
        assert ServiceLocation("retrieval_service") == "retrieval_service"
        assert ServiceLocation("orchestrator") == "orchestrator"

    def test_invalid_location_raises_error(self):
        """Invalid location should raise ValidationError."""
        with pytest.raises(ValueError):
            ServiceLocation("invalid_location")


class TestMCPServerType:
    """Test MCP server type enum."""

    def test_valid_types(self):
        """All valid server types should be accepted."""
        assert MCPServerType("stdio") == "stdio"
        assert MCPServerType("sse") == "sse"
        assert MCPServerType("http") == "http"

    def test_invalid_type_raises_error(self):
        """Invalid server type should raise ValidationError."""
        with pytest.raises(ValueError):
            MCPServerType("invalid_type")


class TestToolBase:
    """Test base tool configuration."""

    def test_minimal_valid_tool(self):
        """Minimal valid tool configuration should pass."""
        tool_data = {
            "tool_id": "test_tool",
            "name": "Test Tool",
            "category": "database",
            "tool_purpose": "retrieval",
            "service_location": "retrieval_service",
            "mcp_server_type": "stdio",
        }

        tool = ToolBase(**tool_data)
        assert tool.tool_id == "test_tool"
        assert tool.name == "Test Tool"
        assert tool.category == ToolCategory.DATABASE
        assert tool.tool_purpose == ToolPurpose.RETRIEVAL
        assert tool.service_location == ServiceLocation.RETRIEVAL_SERVICE
        assert tool.mcp_server_type == MCPServerType.STDIO

    def test_tool_with_all_fields(self):
        """Tool with all fields should pass validation."""
        tool_data = {
            "tool_id": "elasticsearch_search",
            "name": "Elasticsearch Search",
            "description": "Search Elasticsearch indices",
            "category": "database",
            "provider": "elastic",
            "tool_purpose": "retrieval",
            "service_location": "retrieval_service",
            "mcp_server_type": "http",
            "mcp_endpoint": "http://elasticsearch:9200",
            "mcp_protocol_version": "2024-11-05",
            "capabilities": {"tools": ["search"], "resources": []},
            "parameters_schema": {"query": {"type": "string"}},
            "requires_authentication": True,
            "authentication_type": "api_key",
            "secret_name": "elasticsearch_api_key",
            "config_options": {"index": "documents"},
            "timeout_seconds": 30,
            "rate_limit_per_minute": 100,
            "max_concurrent_calls": 5,
            "is_enabled": True,
            "health_check_interval_seconds": 300,
            "version": "1.0.0",
            "documentation_url": "https://docs.example.com",
            "tags": ["search", "database"],
        }

        tool = ToolBase(**tool_data)
        assert tool.tool_id == "elasticsearch_search"
        assert tool.description == "Search Elasticsearch indices"
        assert tool.provider == "elastic"
        assert tool.mcp_endpoint == "http://elasticsearch:9200"
        assert tool.requires_authentication is True
        assert tool.timeout_seconds == 30
        assert tool.tags == ["search", "database"]

    def test_tool_validation_errors(self):
        """Invalid tool data should raise ValidationError."""
        # Missing required fields
        with pytest.raises(ValidationError) as exc_info:
            ToolBase(tool_id="test")
        assert "name" in str(exc_info.value)
        assert "category" in str(exc_info.value)

        # Invalid category
        with pytest.raises(ValidationError) as exc_info:
            ToolBase(
                tool_id="test",
                name="Test",
                category="invalid_category",
                tool_purpose="retrieval",
                service_location="retrieval_service",
                mcp_server_type="stdio",
            )
        assert "category" in str(exc_info.value)

        # Invalid timeout
        with pytest.raises(ValidationError) as exc_info:
            ToolBase(
                tool_id="test",
                name="Test",
                category="database",
                tool_purpose="retrieval",
                service_location="retrieval_service",
                mcp_server_type="stdio",
                timeout_seconds=0,  # Invalid: must be >= 1
            )
        assert "timeout_seconds" in str(exc_info.value)

    def test_tool_defaults(self):
        """Tool should have correct default values."""
        tool_data = {
            "tool_id": "test_tool",
            "name": "Test Tool",
            "category": "database",
            "tool_purpose": "retrieval",
            "service_location": "retrieval_service",
            "mcp_server_type": "stdio",
        }

        tool = ToolBase(**tool_data)
        assert tool.description is None
        assert tool.provider is None
        assert tool.mcp_command is None
        assert tool.mcp_endpoint is None
        assert tool.mcp_protocol_version == "2024-11-05"
        assert tool.capabilities is None
        assert tool.parameters_schema is None
        assert tool.requires_authentication is False
        assert tool.authentication_type is None
        assert tool.secret_name is None
        assert tool.config_options is None
        assert tool.timeout_seconds == 30
        assert tool.rate_limit_per_minute is None
        assert tool.max_concurrent_calls == 5
        assert tool.is_enabled is False
        assert tool.health_check_interval_seconds == 300
        assert tool.version is None
        assert tool.documentation_url is None
        assert tool.tags == []


class TestToolCreate:
    """Test tool creation schema."""

    def test_tool_create_inherits_from_base(self):
        """ToolCreate should inherit all fields from ToolBase."""
        tool_data = {
            "tool_id": "test_tool",
            "name": "Test Tool",
            "category": "database",
            "tool_purpose": "retrieval",
            "service_location": "retrieval_service",
            "mcp_server_type": "stdio",
        }

        tool = ToolCreate(**tool_data)
        assert isinstance(tool, ToolBase)
        assert tool.tool_id == "test_tool"


class TestToolSecretCreate:
    """Test tool secret creation schema."""

    def test_valid_secret_creation(self):
        """Valid secret creation should pass."""
        secret_data = {
            "secret_name": "api_key",
            "secret_type": "api_key",
            "secret_value": "super_secret_key_12345",
        }

        secret = ToolSecretCreate(**secret_data)
        assert secret.secret_name == "api_key"
        assert secret.secret_type == "api_key"
        assert secret.secret_value == "super_secret_key_12345"
        assert secret.expires_at is None

    def test_secret_with_expiration(self):
        """Secret with expiration should pass."""
        from datetime import UTC, datetime

        secret_data = {
            "secret_name": "oauth_token",
            "secret_type": "oauth_token",
            "secret_value": "token_12345",
            "expires_at": datetime.now(UTC),
        }

        secret = ToolSecretCreate(**secret_data)
        assert secret.expires_at is not None

    def test_secret_validation_errors(self):
        """Invalid secret data should raise ValidationError."""
        # Missing required fields
        with pytest.raises(ValidationError) as exc_info:
            ToolSecretCreate(secret_name="test")
        assert "secret_type" in str(exc_info.value)
        assert "secret_value" in str(exc_info.value)

        # Empty secret name
        with pytest.raises(ValidationError) as exc_info:
            ToolSecretCreate(secret_name="", secret_type="api_key", secret_value="test")
        assert "secret_name" in str(exc_info.value)


class TestToolPermissionCreate:
    """Test tool permission creation schema."""

    def test_valid_permission_creation(self):
        """Valid permission creation should pass."""
        permission_data = {
            "role": "analyst",
            "can_view": True,
            "can_use": True,
            "can_configure": False,
            "max_calls_per_hour": 100,
            "max_calls_per_day": 1000,
        }

        permission = ToolPermissionCreate(**permission_data)
        assert permission.role == "analyst"
        assert permission.can_view is True
        assert permission.can_use is True
        assert permission.can_configure is False
        assert permission.max_calls_per_hour == 100
        assert permission.max_calls_per_day == 1000

    def test_permission_defaults(self):
        """Permission should have correct defaults."""
        permission_data = {"role": "user"}

        permission = ToolPermissionCreate(**permission_data)
        assert permission.role == "user"
        assert permission.can_view is True
        assert permission.can_use is False
        assert permission.can_configure is False
        assert permission.max_calls_per_hour is None
        assert permission.max_calls_per_day is None

    def test_permission_validation_errors(self):
        """Invalid permission data should raise ValidationError."""
        # Empty role
        with pytest.raises(ValidationError) as exc_info:
            ToolPermissionCreate(role="")
        assert "role" in str(exc_info.value)

        # Invalid rate limits
        with pytest.raises(ValidationError) as exc_info:
            ToolPermissionCreate(role="user", max_calls_per_hour=0)  # Invalid: must be >= 1
        assert "max_calls_per_hour" in str(exc_info.value)


class TestToolInvocationCreate:
    """Test tool invocation creation schema."""

    def test_valid_invocation_creation(self):
        """Valid invocation creation should pass."""
        from datetime import UTC, datetime

        invocation_data = {
            "tool_name": "elasticsearch_search",
            "status": "success",
            "tool_parameters": {"query": "test"},
            "response_data": {"hits": []},
            "completed_at": datetime.now(UTC),
            "duration_ms": 150.5,
            "cost_estimate": 0.001,
        }

        invocation = ToolInvocationCreate(**invocation_data)
        assert invocation.tool_name == "elasticsearch_search"
        assert invocation.status == InvocationStatus.SUCCESS
        assert invocation.tool_parameters == {"query": "test"}
        assert invocation.response_data == {"hits": []}
        assert invocation.duration_ms == 150.5
        assert invocation.cost_estimate == 0.001

    def test_invocation_validation_errors(self):
        """Invalid invocation data should raise ValidationError."""
        # Missing required fields
        with pytest.raises(ValidationError) as exc_info:
            ToolInvocationCreate(status="success")
        assert "tool_name" in str(exc_info.value)

        # Empty tool name
        with pytest.raises(ValidationError) as exc_info:
            ToolInvocationCreate(tool_name="", status="success")
        assert "tool_name" in str(exc_info.value)

        # Invalid status
        with pytest.raises(ValidationError) as exc_info:
            ToolInvocationCreate(tool_name="test", status="invalid_status")
        assert "status" in str(exc_info.value)


class TestToolStatus:
    """Test tool status enum."""

    def test_valid_statuses(self):
        """All valid statuses should be accepted."""
        assert ToolStatus("online") == "online"
        assert ToolStatus("offline") == "offline"
        assert ToolStatus("degraded") == "degraded"
        assert ToolStatus("unknown") == "unknown"

    def test_invalid_status_raises_error(self):
        """Invalid status should raise ValidationError."""
        with pytest.raises(ValueError):
            ToolStatus("invalid_status")


class TestInvocationStatus:
    """Test invocation status enum."""

    def test_valid_statuses(self):
        """All valid statuses should be accepted."""
        assert InvocationStatus("success") == "success"
        assert InvocationStatus("error") == "error"
        assert InvocationStatus("timeout") == "timeout"
        assert InvocationStatus("blocked") == "blocked"
        assert InvocationStatus("rate_limited") == "rate_limited"

    def test_invalid_status_raises_error(self):
        """Invalid status should raise ValidationError."""
        with pytest.raises(ValueError):
            InvocationStatus("invalid_status")


class TestToolListItem:
    """Test tool list item schema."""

    def test_tool_list_item_creation(self):
        """Tool list item should be created correctly."""
        from uuid import uuid4

        item_data = {
            "id": uuid4(),
            "tool_id": "test_tool",
            "name": "Test Tool",
            "description": "Test description",
            "category": "database",
            "is_enabled": True,
            "is_healthy": True,
            "requires_authentication": False,
        }

        item = ToolListItem(**item_data)
        assert item.tool_id == "test_tool"
        assert item.name == "Test Tool"
        assert item.category == ToolCategory.DATABASE
        assert item.is_enabled is True
        assert item.is_healthy is True
        assert item.requires_authentication is False


class TestToolHealthCheck:
    """Test tool health check schema."""

    def test_health_check_creation(self):
        """Health check should be created correctly."""
        from datetime import UTC, datetime
        from uuid import uuid4

        health_data = {
            "id": uuid4(),
            "tool_id": uuid4(),
            "status": "online",
            "response_time_ms": 150.5,
            "error_message": None,
            "checked_at": datetime.now(UTC),
            "mcp_server_info": {"version": "1.0.0"},
        }

        health = ToolHealthCheck(**health_data)
        assert health.status == ToolStatus.ONLINE
        assert health.response_time_ms == 150.5
        assert health.error_message is None
        assert health.mcp_server_info == {"version": "1.0.0"}

    def test_health_check_with_error(self):
        """Health check with error should be created correctly."""
        from datetime import UTC, datetime
        from uuid import uuid4

        health_data = {
            "id": uuid4(),
            "tool_id": uuid4(),
            "status": "offline",
            "response_time_ms": None,
            "error_message": "Connection timeout",
            "checked_at": datetime.now(UTC),
            "mcp_server_info": None,
        }

        health = ToolHealthCheck(**health_data)
        assert health.status == ToolStatus.OFFLINE
        assert health.response_time_ms is None
        assert health.error_message == "Connection timeout"
        assert health.mcp_server_info is None
