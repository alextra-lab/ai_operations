"""
Shared provider configuration models.

Consolidates provider schemas used across:
- Inference Gateway (admin API, provider routing)
- Backend Orchestrator (gateway client)
- Embedding Service (provider configuration)

This prevents schema drift and ensures consistent validation.
"""

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ProviderType(str, Enum):
    """Provider types supported across services."""

    OPENAI_COMPATIBLE = "openai_compatible"
    OPENAI = "openai"
    MISTRAL = "mistral"
    ANTHROPIC = "anthropic"
    LOCAL_MODEL = "local"
    CUSTOM = "custom"


class ProviderStatus(str, Enum):
    """Provider operational status."""

    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"
    TESTING = "testing"


class ConnectionConfig(BaseModel):
    """
    Connection configuration for OpenAI-compatible providers.

    Used by embedding service for remote inference servers.
    """

    url: str = Field(..., description="Base URL for the API endpoint")
    auth_type: str = Field("API_KEY", description="Authentication type")
    api_key_env: str | None = Field(
        "OPENAI_API_KEY", description="Environment variable for API key"
    )
    timeout_seconds: int = Field(30, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retries")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL is well-formed."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class ModelConfig(BaseModel):
    """
    Configuration for an AI model (LLM or embedding).

    Used by embedding service to define available models per provider.
    """

    name: str = Field(..., description="Model name")
    dimensions: int | None = Field(None, description="Embedding dimensions (embedding models only)")
    path: str | None = Field(None, description="Path to local model files")
    batch_size: int = Field(32, description="Batch size for processing")
    default: bool = Field(False, description="Whether this is the default model")
    server_model_name: str | None = Field(None, description="Model name on inference server")
    metadata: dict[str, Any] | None = Field(None, description="Additional model metadata")

    @field_validator("dimensions")
    @classmethod
    def validate_dimensions(cls, v: int | None) -> int | None:
        """Validate dimensions are reasonable."""
        if v is not None and v <= 0:
            raise ValueError("Dimensions must be positive")
        return v

    @field_validator("batch_size")
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        """Validate batch size is reasonable."""
        if v <= 0:
            raise ValueError("Batch size must be positive")
        return v


class ProviderConfig(BaseModel):
    """
    Unified provider configuration schema.

    Used across:
    - Gateway admin API (CRUD operations)
    - Gateway provider routing (runtime config)
    - Backend orchestrator (gateway client)
    - Embedding service (YAML config)

    Fields:
    - id: UUID (optional, only for database-backed providers)
    - name: Provider name (e.g., "openai", "mistral", "local")
    - provider_type: Type enum (openai, mistral, local, etc.)
    - base_url: API endpoint URL
    - api_key: API key (optional, not returned in responses)
    - is_enabled: Enable/disable toggle
    - status: Operational status (active, disabled, error, testing)
    - priority: Routing priority (lower = higher priority)
    - config_json: Provider-specific configuration (JSON)
    - models: Available models (embedding service only)
    - connection: Connection details (embedding service only)
    - health_check_url: Health check endpoint (optional)
    - timeout_seconds: Request timeout (optional)
    - error_count: Cumulative error count (gateway only)
    - success_count: Cumulative success count (gateway only)
    - circuit_state: Circuit breaker state (gateway only)
    - last_health_check: Last health check timestamp (gateway only)
    - last_health_status: Last health check result (gateway only)
    - created_at: Creation timestamp (gateway only)
    - updated_at: Update timestamp (gateway only)
    """

    # Core fields (all services)
    id: UUID | None = Field(None, description="Provider ID (database-backed only)")
    name: str = Field(..., min_length=1, max_length=255, description="Provider name")
    provider_type: ProviderType | str = Field(..., description="Provider type (enum or string)")
    base_url: str = Field(..., description="Provider base URL")
    api_key: str | None = Field(None, description="API key (input only, not returned)")
    is_enabled: bool = Field(True, description="Enable/disable toggle")
    status: ProviderStatus | str = Field(default="testing", description="Operational status")
    priority: int = Field(
        default=100, ge=0, description="Routing priority (lower = higher priority)"
    )

    # Extended configuration
    config_json: dict[str, Any] = Field(
        default_factory=dict, description="Provider-specific configuration"
    )
    health_check_url: str | None = Field(None, description="Health check endpoint URL")
    timeout_seconds: float = Field(default=30.0, description="Request timeout")

    # Embedding service fields
    models: list[ModelConfig] | None = Field(
        None, description="Available models (embedding service)"
    )
    connection: ConnectionConfig | None = Field(
        None, description="Connection details (embedding service)"
    )

    # Gateway runtime fields (read-only)
    error_count: int | None = Field(default=0, description="Cumulative error count")
    success_count: int | None = Field(default=0, description="Cumulative success count")
    circuit_state: str | None = Field(default="CLOSED", description="Circuit breaker state")
    last_health_check: str | None = Field(None, description="Last health check timestamp")
    last_health_status: bool | None = Field(None, description="Last health check result")
    created_at: str | None = None
    updated_at: str | None = None

    @field_validator("provider_type", mode="before")
    @classmethod
    def normalize_provider_type(cls, v: Any) -> str:
        """Normalize provider type to string."""
        if isinstance(v, Enum):
            return str(v.value)
        return str(v)

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> str:
        """Normalize status to string."""
        if isinstance(v, Enum):
            return str(v.value)
        return str(v)


class ProviderListResponse(BaseModel):
    """Paginated provider list response."""

    items: list[ProviderConfig]
    total: int
    limit: int
    offset: int


class ProviderConfigUpdate(BaseModel):
    """
    Partial provider configuration for updates.

    All fields are optional to support partial updates.
    Used by Gateway PUT endpoint to allow updating only specific fields.
    """

    name: str | None = Field(None, min_length=1, max_length=255, description="Provider name")
    provider_type: ProviderType | str | None = Field(
        None, description="Provider type (enum or string)"
    )
    base_url: str | None = Field(None, description="Provider base URL")
    api_key: str | None = Field(None, description="API key (input only, not returned)")
    is_enabled: bool | None = Field(None, description="Enable/disable toggle")
    status: ProviderStatus | str | None = Field(None, description="Operational status")
    priority: int | None = Field(
        None, ge=0, description="Routing priority (lower = higher priority)"
    )
    config_json: dict[str, Any] | None = Field(None, description="Provider-specific configuration")
    health_check_url: str | None = Field(None, description="Health check endpoint URL")
    timeout_seconds: float | None = Field(None, description="Request timeout")

    @field_validator("provider_type", mode="before")
    @classmethod
    def normalize_provider_type(cls, v: Any) -> str | None:
        """Normalize provider type to string."""
        if v is None:
            return None
        if isinstance(v, Enum):
            return str(v.value)
        return str(v)

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> str | None:
        """Normalize status to string."""
        if v is None:
            return None
        if isinstance(v, Enum):
            return str(v.value)
        return str(v)


class ProviderTestResult(BaseModel):
    """Provider connectivity test result."""

    success: bool
    message: str
    response_time_ms: float | None = None
    error_details: dict | None = None
