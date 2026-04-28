"""
Tool registration workflow schemas.

Provides Pydantic models for multi-phase tool registration.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class ToolRegistrationPhase(str, Enum):
    """Registration workflow phases."""

    BASIC_INFO = "basic_info"
    MCP_CONFIG = "mcp_config"
    CONNECTION_TEST = "connection_test"
    SECURITY_CONFIG = "security_config"
    PERMISSIONS = "permissions"
    REVIEW = "review"
    COMMIT = "commit"


class ToolRegistrationRequest(BaseModel):
    """Registration phase request."""

    session_id: str | None = Field(
        None,
        description="Session ID for multi-step workflow (None for first phase)",
    )
    phase: ToolRegistrationPhase = Field(
        ...,
        description="Current registration phase",
    )
    data: dict[str, Any] = Field(
        ...,
        description="Phase-specific data",
    )


class ToolRegistrationResponse(BaseModel):
    """Registration phase response."""

    session_id: str
    current_phase: ToolRegistrationPhase
    next_phase: ToolRegistrationPhase | None
    validation_errors: dict[str, list[str]] = Field(default_factory=dict)
    can_proceed: bool
    discovered_capabilities: dict[str, Any] | None = None
    tool_id: UUID | None = None
    message: str


class RegistrationSessionResponse(BaseModel):
    """Registration session state."""

    session_id: str
    current_phase: ToolRegistrationPhase
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    collected_data: dict[str, Any]
    validation_status: dict[str, bool]


class BasicInfoData(BaseModel):
    """Phase 1: Basic tool information."""

    tool_id: str = Field(..., min_length=1, max_length=255, pattern="^[a-z0-9_-]+$")
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category: str  # ToolCategory enum value
    tool_purpose: str  # ToolPurpose enum value
    service_location: str  # ServiceLocation enum value
    provider: str | None = Field(None, max_length=100)
    version: str | None = Field(None, max_length=50)
    documentation_url: str | None = Field(None, max_length=500)
    tags: list[str] = Field(default_factory=list)


class McpConfigData(BaseModel):
    """Phase 2: MCP server configuration."""

    mcp_server_type: str  # MCPServerType enum value
    mcp_command: list[str] | None = None
    mcp_endpoint: str | None = Field(None, max_length=500)
    mcp_protocol_version: str = Field(default="2024-11-05", max_length=20)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    config_options: dict[str, Any] | None = None

    @field_validator("mcp_endpoint")
    @classmethod
    def validate_endpoint(cls, v: str | None, _info: ValidationInfo) -> str | None:
        """Validate endpoint URL format."""
        if v and not (v.startswith(("http://", "https://"))):
            raise ValueError("Endpoint must start with http:// or https://")
        return v


class ConnectionTestData(BaseModel):
    """Phase 3: Connection test action."""

    action: str = Field(..., pattern="^(test|skip)$")


class SecurityConfigData(BaseModel):
    """Phase 4: Security configuration including classification (ADR-057)."""

    # Security Classification (ADR-057)
    data_source_type: str = Field(
        default="internal",
        description="Trust level: internal/external/none/mixed",
    )
    data_flow_direction: str = Field(
        default="ingress",
        description="Data flow: ingress/egress/bidirectional/none",
    )
    network_access_level: str = Field(
        default="internal",
        description="Network access: isolated/internal/external",
    )
    max_data_sensitivity: str = Field(
        default="internal",
        description="Max data sensitivity: public/internal/confidential/restricted",
    )

    # Authentication
    requires_authentication: bool = False
    authentication_type: str | None = Field(None, max_length=50)
    secret_name: str | None = Field(None, max_length=255)
    secret_value: str | None = Field(None, min_length=1)
    secret_expires_at: datetime | None = None
    config_options: dict[str, Any] | None = None


class RolePermissionData(BaseModel):
    """Per-role permission configuration."""

    role: str = Field(..., min_length=1, max_length=50)
    can_view: bool = False
    can_use: bool = False
    can_configure: bool = False
    max_calls_per_hour: int | None = Field(None, ge=1)
    max_calls_per_day: int | None = Field(None, ge=1)


class PermissionsData(BaseModel):
    """Phase 5: Permissions and limits."""

    rate_limit_per_minute: int | None = Field(None, ge=1)
    max_concurrent_calls: int = Field(default=5, ge=1, le=100)
    health_check_interval_seconds: int = Field(default=300, ge=60)
    role_permissions: list[RolePermissionData] = Field(default_factory=list)


class ReviewData(BaseModel):
    """Phase 6: Review action."""

    action: str = Field(..., pattern="^(confirm|edit)$")


class CommitData(BaseModel):
    """Phase 7: Final commit confirmation."""

    confirmed: bool = Field(..., description="Must be true to commit")
