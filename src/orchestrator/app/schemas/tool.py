"""
Tool management schemas for platform-level MCP integration.

Provides Pydantic models for tool configuration, secrets, permissions,
health monitoring, and audit logging.
"""

import json
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ToolCategory(str, Enum):
    """Standard tool categories."""

    DATABASE = "database"
    VECTOR_DB = "vector_db"
    WEB_SCRAPING = "web_scraping"
    REASONING = "reasoning"
    DOCUMENTATION = "documentation"
    CODE_ANALYSIS = "code_analysis"
    THREAT_INTEL = "threat_intel"
    CUSTOM = "custom"


# =============================================================================
# DEPRECATED: Legacy classification (ADR-001)
# Use security classification below instead (ADR-057)
# =============================================================================


class ToolPurpose(str, Enum):
    """
    DEPRECATED: Use DataSourceType + DataFlowDirection instead.

    Tool purpose classification for hybrid architecture.
    Kept for backward compatibility during migration.
    """

    RETRIEVAL = "retrieval"  # Internal data access (runs in Retrieval Service)
    ORCHESTRATOR = "orchestrator"  # Reasoning or external data (runs in Orchestrator)


class ServiceLocation(str, Enum):
    """
    DEPRECATED: All MCPs now run in Orchestrator.

    Service where tool executor runs.
    Kept for backward compatibility during migration.
    """

    RETRIEVAL_SERVICE = "retrieval_service"
    ORCHESTRATOR = "orchestrator"


# =============================================================================
# NEW: Security-focused classification (ADR-057)
# =============================================================================


class DataSourceType(str, Enum):
    """Trust level of data sources the tool accesses."""

    INTERNAL = "internal"  # Company-controlled sources (ES datalake, internal APIs)
    EXTERNAL = "external"  # Third-party/public sources (web scraping, public APIs)
    NONE = "none"  # No data retrieval (reasoning tools like ClearThought)
    MIXED = "mixed"  # Aggregated/gateway tools (Docker MCP Gateway)


class DataFlowDirection(str, Enum):
    """Direction of data flow relative to the platform."""

    INGRESS = "ingress"  # Data comes INTO system (retrieval)
    EGRESS = "egress"  # Data goes OUT of system (notifications)
    BIDIRECTIONAL = "bidirectional"  # Both directions
    NONE = "none"  # No external data flow (pure reasoning)


class NetworkAccessLevel(str, Enum):
    """Network access requirements for the tool."""

    ISOLATED = "isolated"  # No network access (pure computation)
    INTERNAL = "internal"  # Internal/company network only
    EXTERNAL = "external"  # Public internet access required


class MaxDataSensitivity(str, Enum):
    """Maximum data classification the tool can process."""

    PUBLIC = "public"  # Public data only
    INTERNAL = "internal"  # Internal business data
    CONFIDENTIAL = "confidential"  # Sensitive business data
    RESTRICTED = "restricted"  # PII, PHI, regulated data


class MCPServerType(str, Enum):
    """MCP server communication types."""

    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"


class ToolStatus(str, Enum):
    """Tool health status."""

    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class InvocationStatus(str, Enum):
    """Tool invocation result status."""

    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    RATE_LIMITED = "rate_limited"


class ToolBase(BaseModel):
    """Base tool configuration."""

    tool_id: str = Field(..., min_length=1, max_length=255, description="Unique tool identifier")
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable tool name")
    description: str | None = Field(None, description="Tool description")
    category: ToolCategory = Field(..., description="Tool category")
    provider: str | None = Field(None, max_length=100, description="Tool provider/vendor")

    # DEPRECATED: Hybrid Architecture (ADR-001)
    # These fields are kept for backward compatibility during migration
    tool_purpose: ToolPurpose = Field(
        default=ToolPurpose.ORCHESTRATOR,
        description="DEPRECATED: Use security classification instead",
    )
    service_location: ServiceLocation = Field(
        default=ServiceLocation.ORCHESTRATOR, description="DEPRECATED: All MCPs run in Orchestrator"
    )

    # NEW: Security Classification (ADR-057)
    data_source_type: DataSourceType = Field(
        default=DataSourceType.INTERNAL,
        description="Trust level of data sources (internal/external/none/mixed)",
    )
    data_flow_direction: DataFlowDirection = Field(
        default=DataFlowDirection.INGRESS,
        description="Direction of data flow (ingress/egress/bidirectional/none)",
    )
    network_access_level: NetworkAccessLevel = Field(
        default=NetworkAccessLevel.INTERNAL,
        description="Network access requirements (isolated/internal/external)",
    )
    max_data_sensitivity: MaxDataSensitivity = Field(
        default=MaxDataSensitivity.INTERNAL,
        description="Maximum data classification allowed (public/internal/confidential/restricted)",
    )

    # MCP Configuration
    mcp_server_type: MCPServerType = Field(..., description="MCP communication protocol")
    mcp_command: list[str] | None = Field(None, description="Command for stdio MCP servers")
    mcp_endpoint: str | None = Field(
        None, max_length=500, description="Endpoint for http/sse MCP servers"
    )
    mcp_protocol_version: str = Field(default="2024-11-05", description="MCP protocol version")

    # Capabilities
    capabilities: dict[str, Any] | None = Field(None, description="MCP server capabilities")
    parameters_schema: dict[str, Any] | None = Field(None, description="Tool parameter schema")

    # Authentication
    requires_authentication: bool = Field(
        default=False, description="Whether tool requires authentication"
    )
    authentication_type: str | None = Field(None, description="Authentication type")
    secret_name: str | None = Field(
        None, max_length=255, description="Reference to encrypted secret"
    )
    config_options: dict[str, Any] | None = Field(None, description="Tool-specific configuration")

    # Limits
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Tool execution timeout")
    rate_limit_per_minute: int | None = Field(None, ge=1, description="Rate limit per minute")
    max_concurrent_calls: int = Field(
        default=5, ge=1, le=100, description="Max concurrent executions"
    )

    # Lifecycle
    is_enabled: bool = Field(default=False, description="Whether tool is enabled")
    health_check_interval_seconds: int = Field(
        default=300, ge=60, description="Health check interval"
    )

    # Metadata
    version: str | None = Field(None, max_length=50, description="Tool version")
    documentation_url: str | None = Field(None, max_length=500, description="Documentation URL")
    tags: list[str] = Field(default_factory=list, description="Tool tags")


class ToolCreate(ToolBase):
    """Tool creation request."""


class ToolUpdate(BaseModel):
    """Tool update request (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    is_enabled: bool | None = None
    timeout_seconds: int | None = Field(None, ge=1, le=300)
    rate_limit_per_minute: int | None = Field(None, ge=1)
    config_options: dict[str, Any] | None = None
    tags: list[str] | None = None


class Tool(ToolBase):
    """Complete tool record."""

    id: UUID
    is_healthy: bool
    last_health_check: datetime | None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    @field_validator("mcp_command", mode="before")
    @classmethod
    def parse_mcp_command(cls, v: Any) -> list[str] | None:
        """Parse mcp_command from JSON string if needed."""
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
        return None

    class Config:
        from_attributes = True


class ToolListItem(BaseModel):
    """Minimal tool information for lists."""

    id: UUID
    tool_id: str
    name: str
    description: str | None
    category: ToolCategory
    is_enabled: bool
    is_healthy: bool
    requires_authentication: bool
    # Security classification (ADR-057)
    data_source_type: DataSourceType = DataSourceType.INTERNAL
    data_flow_direction: DataFlowDirection = DataFlowDirection.INGRESS
    network_access_level: NetworkAccessLevel = NetworkAccessLevel.INTERNAL
    max_data_sensitivity: MaxDataSensitivity = MaxDataSensitivity.INTERNAL


class ToolSecret(BaseModel):
    """Tool secret (never expose encrypted value)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tool_id: UUID
    secret_name: str
    secret_type: str
    is_active: bool
    expires_at: datetime | None
    created_at: datetime


class ToolSecretCreate(BaseModel):
    """Create tool secret."""

    secret_name: str = Field(..., min_length=1, max_length=255)
    secret_type: str = Field(..., description="Type of secret")
    secret_value: str = Field(..., description="Plain-text secret value (will be encrypted)")
    expires_at: datetime | None = Field(None, description="Secret expiration")


class ToolHealthCheck(BaseModel):
    """Tool health check result."""

    id: UUID
    tool_id: UUID
    status: ToolStatus
    response_time_ms: float | None
    error_message: str | None
    checked_at: datetime
    mcp_server_info: dict[str, Any] | None


class ToolPermission(BaseModel):
    """Tool permission for a role."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tool_id: UUID
    role: str
    can_view: bool
    can_use: bool
    can_configure: bool
    max_calls_per_hour: int | None
    max_calls_per_day: int | None


class ToolPermissionCreate(BaseModel):
    """Create tool permission."""

    role: str = Field(..., min_length=1, max_length=50)
    can_view: bool = Field(default=True)
    can_use: bool = Field(default=False)
    can_configure: bool = Field(default=False)
    max_calls_per_hour: int | None = Field(None, ge=1)
    max_calls_per_day: int | None = Field(None, ge=1)


class ToolInvocation(BaseModel):
    """Tool invocation audit record."""

    id: UUID
    tool_id: UUID | None
    use_case_id: UUID | None
    run_id: str | None
    user_id: UUID | None
    center_id: str | None
    tool_name: str
    tool_parameters: dict[str, Any] | None
    status: InvocationStatus
    response_data: dict[str, Any] | None
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None
    duration_ms: float | None
    cost_estimate: float | None


class ToolInvocationCreate(BaseModel):
    """Create tool invocation record."""

    tool_id: UUID | None = None
    use_case_id: UUID | None = None
    run_id: str | None = None
    user_id: UUID | None = None
    center_id: str | None = None
    tool_name: str = Field(..., min_length=1, max_length=255)
    tool_parameters: dict[str, Any] | None = None
    status: InvocationStatus
    response_data: dict[str, Any] | None = None
    error_message: str | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = None
    cost_estimate: float | None = None


class ToolHealthSummary(BaseModel):
    """Tool health summary for monitoring."""

    tool_id: str
    name: str
    status: ToolStatus
    last_check: datetime | None
    response_time_ms: float | None
    error_count_24h: int
    success_rate_24h: float


class ToolUsageStats(BaseModel):
    """Tool usage statistics."""

    tool_id: str
    name: str
    total_invocations: int
    successful_invocations: int
    failed_invocations: int
    avg_duration_ms: float
    total_cost: float
    last_used: datetime | None


# =============================================================================
# Use Case Tool Restrictions (ADR-057)
# =============================================================================


class UseCaseToolRestrictions(BaseModel):
    """
    Security-based tool restrictions for a Use Case.

    These restrictions control which tools can be used within a Use Case
    based on their security classification attributes.
    """

    # Data source restrictions - which source types are allowed
    allowed_data_sources: list[DataSourceType] = Field(
        default=[DataSourceType.INTERNAL, DataSourceType.NONE],
        description="Allowed data source types for tools in this Use Case",
    )

    # Data flow restrictions - which flow directions are allowed
    allowed_data_flows: list[DataFlowDirection] = Field(
        default=[DataFlowDirection.INGRESS, DataFlowDirection.NONE],
        description="Allowed data flow directions for tools in this Use Case",
    )

    # Network access restrictions - which network levels are allowed
    allowed_network_levels: list[NetworkAccessLevel] = Field(
        default=[NetworkAccessLevel.ISOLATED, NetworkAccessLevel.INTERNAL],
        description="Allowed network access levels for tools in this Use Case",
    )

    # Minimum required sensitivity level
    # Tool must support AT LEAST this sensitivity level
    required_data_sensitivity: MaxDataSensitivity = Field(
        default=MaxDataSensitivity.INTERNAL,
        description="Minimum data sensitivity level tools must support",
    )

    # Explicit tool allowlist (overrides attribute checks if specified)
    explicit_tool_allowlist: list[str] = Field(
        default_factory=list,
        description="Explicit list of allowed tool_ids (if empty, uses attribute filtering)",
    )

    # Explicit tool blocklist (always blocks these tools)
    explicit_tool_blocklist: list[str] = Field(
        default_factory=list, description="Explicit list of blocked tool_ids (always enforced)"
    )

    def is_tool_allowed(self, tool: "ToolListItem") -> tuple[bool, str | None]:
        """
        Check if a tool is allowed by these restrictions.

        Returns:
            Tuple of (is_allowed, rejection_reason)
        """
        # Check explicit blocklist first
        if tool.tool_id in self.explicit_tool_blocklist:
            return False, f"Tool '{tool.tool_id}' is explicitly blocked"

        # Check explicit allowlist (if specified, overrides other checks)
        if self.explicit_tool_allowlist:
            if tool.tool_id in self.explicit_tool_allowlist:
                return True, None
            return False, f"Tool '{tool.tool_id}' not in allowlist"

        # Check data source type
        if tool.data_source_type not in self.allowed_data_sources:
            return False, (
                f"Tool data source '{tool.data_source_type.value}' not allowed. "
                f"Allowed: {[s.value for s in self.allowed_data_sources]}"
            )

        # Check data flow direction
        if tool.data_flow_direction not in self.allowed_data_flows:
            return False, (
                f"Tool data flow '{tool.data_flow_direction.value}' not allowed. "
                f"Allowed: {[f.value for f in self.allowed_data_flows]}"
            )

        # Check network access level
        if tool.network_access_level not in self.allowed_network_levels:
            return False, (
                f"Tool network access '{tool.network_access_level.value}' not allowed. "
                f"Allowed: {[n.value for n in self.allowed_network_levels]}"
            )

        # Check data sensitivity (tool must support required level)
        sensitivity_order = [
            MaxDataSensitivity.PUBLIC,
            MaxDataSensitivity.INTERNAL,
            MaxDataSensitivity.CONFIDENTIAL,
            MaxDataSensitivity.RESTRICTED,
        ]
        tool_level = sensitivity_order.index(tool.max_data_sensitivity)
        required_level = sensitivity_order.index(self.required_data_sensitivity)

        if tool_level < required_level:
            tool_sens = (
                str(tool.max_data_sensitivity.value)
                if hasattr(tool.max_data_sensitivity, "value")
                else str(tool.max_data_sensitivity)
            )
            req_sens = (
                str(self.required_data_sensitivity.value)
                if hasattr(self.required_data_sensitivity, "value")
                else str(self.required_data_sensitivity)
            )
            return False, (
                f"Tool max sensitivity '{tool_sens}' insufficient. Required: '{req_sens}'"
            )

        return True, None


# Preset restriction configurations for common use cases
RESTRICTION_PRESETS = {
    "high_security": UseCaseToolRestrictions(
        allowed_data_sources=[DataSourceType.INTERNAL, DataSourceType.NONE],
        allowed_data_flows=[DataFlowDirection.INGRESS, DataFlowDirection.NONE],
        allowed_network_levels=[NetworkAccessLevel.ISOLATED, NetworkAccessLevel.INTERNAL],
        required_data_sensitivity=MaxDataSensitivity.RESTRICTED,
    ),
    "internal_only": UseCaseToolRestrictions(
        allowed_data_sources=[DataSourceType.INTERNAL, DataSourceType.NONE],
        allowed_data_flows=[DataFlowDirection.INGRESS, DataFlowDirection.NONE],
        allowed_network_levels=[NetworkAccessLevel.ISOLATED, NetworkAccessLevel.INTERNAL],
        required_data_sensitivity=MaxDataSensitivity.INTERNAL,
    ),
    "research_open": UseCaseToolRestrictions(
        allowed_data_sources=[
            DataSourceType.INTERNAL,
            DataSourceType.EXTERNAL,
            DataSourceType.NONE,
            DataSourceType.MIXED,
        ],
        allowed_data_flows=[
            DataFlowDirection.INGRESS,
            DataFlowDirection.BIDIRECTIONAL,
            DataFlowDirection.NONE,
        ],
        allowed_network_levels=[
            NetworkAccessLevel.ISOLATED,
            NetworkAccessLevel.INTERNAL,
            NetworkAccessLevel.EXTERNAL,
        ],
        required_data_sensitivity=MaxDataSensitivity.PUBLIC,
    ),
    "no_egress": UseCaseToolRestrictions(
        allowed_data_sources=[
            DataSourceType.INTERNAL,
            DataSourceType.EXTERNAL,
            DataSourceType.NONE,
            DataSourceType.MIXED,
        ],
        allowed_data_flows=[DataFlowDirection.INGRESS, DataFlowDirection.NONE],
        allowed_network_levels=[
            NetworkAccessLevel.ISOLATED,
            NetworkAccessLevel.INTERNAL,
            NetworkAccessLevel.EXTERNAL,
        ],
        required_data_sensitivity=MaxDataSensitivity.INTERNAL,
    ),
}
