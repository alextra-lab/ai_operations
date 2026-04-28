"""
Capabilities Schema for Stateless Core v1

This module defines Pydantic schemas for the capabilities system (ADR-032)
which provides runtime discovery of available features and provider configurations.

Supports:
- Edition flags (Core vs Plus)
- Provider configuration (none vs governed)
- Feature flags for optional capabilities
- Runtime capability discovery
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class Edition(str, Enum):
    """Available editions."""

    CORE = "core"  # Stateless edition
    PLUS = "plus"  # Future stateful edition


class ProviderType(str, Enum):
    """Provider types for different capabilities."""

    NONE = "none"  # No-op providers (v1)
    GOVERNED = "governed"  # Full providers (v2+)


class CapabilityStatus(str, Enum):
    """Status of a capability."""

    AVAILABLE = "available"
    FEATURE_FLAGGED = "feature_flagged"
    DISABLED = "disabled"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


class CapabilityCategory(str, Enum):
    """Categories of capabilities."""

    CHUNKING = "chunking"
    TELEMETRY = "telemetry"
    ANALYSIS = "analysis"
    STORAGE = "storage"
    SECURITY = "security"


class Capability(BaseModel):
    """A system capability."""

    name: str = Field(..., description="Capability name")
    display_name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Capability description")
    category: CapabilityCategory = Field(..., description="Capability category")
    status: CapabilityStatus = Field(..., description="Current status")
    edition: str = Field(..., description="Required edition")
    version: str = Field(..., description="Capability version")


class EditionCapabilities(BaseModel):
    """Capabilities for a specific edition."""

    edition: str = Field(..., description="Edition name")
    total_capabilities: int = Field(..., description="Total capabilities")
    available_capabilities: int = Field(..., description="Available capabilities")
    capabilities: list[Capability] = Field(..., description="All capabilities")
    available: list[Capability] = Field(..., description="Available capabilities")
    disabled: list[Capability] = Field(..., description="Disabled capabilities")


class CapabilityInfo(BaseModel):
    """Information about a specific capability."""

    name: str = Field(..., description="Name of the capability")
    status: CapabilityStatus = Field(..., description="Current status of the capability")
    description: str = Field(..., description="Description of the capability")
    edition_required: Edition = Field(..., description="Minimum edition required")
    provider_required: ProviderType | None = Field(None, description="Provider type required")
    config: dict[str, Any] = Field(
        default_factory=dict, description="Capability-specific configuration"
    )


class ProviderConfig(BaseModel):
    """Configuration for a provider."""

    history: ProviderType = Field(..., description="History provider type")
    evidence: ProviderType = Field(..., description="Evidence provider type")
    crypto: ProviderType = Field(..., description="Crypto provider type")


class FeatureFlags(BaseModel):
    """Feature flags for optional capabilities."""

    expert_chunking: bool = Field(False, description="Enable expert chunking strategies")
    advanced_analytics: bool = Field(False, description="Enable advanced analytics")
    run_manifests: bool = Field(True, description="Enable run manifest collection")
    exports: bool = Field(True, description="Enable conversation exports")
    summaries: bool = Field(True, description="Enable summary generation")
    preflight_analysis: bool = Field(True, description="Enable preflight analysis")
    quality_metrics: bool = Field(True, description="Enable quality metrics")
    test_harness: bool = Field(True, description="Enable test harness functionality")


class CapabilitiesResponse(BaseModel):
    """Response from the capabilities endpoint."""

    edition: Edition = Field(..., description="Current edition")
    stateful_enabled: bool = Field(..., description="Whether stateful features are enabled")
    providers: ProviderConfig = Field(..., description="Provider configuration")
    features: FeatureFlags = Field(..., description="Feature flags")
    capabilities: dict[str, bool] = Field(..., description="Available capabilities")
    version: str = Field(..., description="System version")
    build_info: dict[str, Any] = Field(default_factory=dict, description="Build information")

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, v: dict[str, bool]) -> dict[str, bool]:
        """Validate that capabilities are reasonable."""
        # Basic validation - more complex validation should be done at the model level
        for key, value in v.items():
            if not isinstance(value, bool):
                raise ValueError(f"Capability {key} must be a boolean")
        return v

    @model_validator(mode="after")
    def validate_capability_constraints(self) -> "CapabilitiesResponse":
        """Validate capability constraints based on edition and providers."""
        # Core edition cannot have conversation_storage capability
        if self.edition == Edition.CORE and self.capabilities.get("conversation_storage", False):
            raise ValueError("Core edition cannot have conversation_storage capability")

        # No history provider means no conversation storage capability
        if self.providers.history == ProviderType.NONE and self.capabilities.get(
            "conversation_storage", False
        ):
            raise ValueError("No history provider means no conversation storage capability")

        return self


class CapabilityRequest(BaseModel):
    """Request for capability information."""

    capability_name: str | None = Field(None, description="Specific capability to query")
    include_experimental: bool = Field(False, description="Include experimental capabilities")
    include_deprecated: bool = Field(False, description="Include deprecated capabilities")


class CapabilityDetails(BaseModel):
    """Detailed information about a capability."""

    name: str = Field(..., description="Capability name")
    status: CapabilityStatus = Field(..., description="Current status")
    description: str = Field(..., description="Detailed description")
    edition_required: Edition = Field(..., description="Minimum edition required")
    provider_required: ProviderType | None = Field(None, description="Provider type required")
    dependencies: list[str] = Field(default_factory=list, description="Capability dependencies")
    configuration: dict[str, Any] = Field(default_factory=dict, description="Configuration options")
    examples: list[str] = Field(default_factory=list, description="Usage examples")
    limitations: list[str] = Field(default_factory=list, description="Known limitations")


class SystemInfo(BaseModel):
    """System information for capabilities."""

    version: str = Field(..., description="System version")
    edition: Edition = Field(..., description="Current edition")
    build_date: str = Field(..., description="Build date")
    git_commit: str | None = Field(None, description="Git commit hash")
    environment: str = Field(..., description="Deployment environment")
    features_enabled: list[str] = Field(default_factory=list, description="Enabled features")
    providers_configured: list[str] = Field(
        default_factory=list, description="Configured providers"
    )


class CapabilityHealthCheck(BaseModel):
    """Health check for capabilities."""

    capability_name: str = Field(..., description="Name of the capability")
    healthy: bool = Field(..., description="Whether the capability is healthy")
    check_time: str = Field(..., description="When the check was performed")
    response_time_ms: int = Field(..., ge=0, description="Health check response time")
    error_message: str | None = Field(None, description="Error message if unhealthy")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional health details")


class CapabilityMetrics(BaseModel):
    """Metrics for a capability."""

    capability_name: str = Field(..., description="Name of the capability")
    total_requests: int = Field(0, ge=0, description="Total requests processed")
    successful_requests: int = Field(0, ge=0, description="Successful requests")
    failed_requests: int = Field(0, ge=0, description="Failed requests")
    avg_response_time_ms: float = Field(0.0, ge=0.0, description="Average response time")
    error_rate: float = Field(0.0, ge=0.0, le=1.0, description="Error rate (0-1)")
    last_request_at: str | None = Field(None, description="Last request timestamp")
    throughput_per_minute: float = Field(0.0, ge=0.0, description="Requests per minute")
