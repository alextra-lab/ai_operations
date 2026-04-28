# Shared Provider Models Architecture

**Version:** 1.0
**Date:** November 7, 2025
**Status:** Implemented
**Location:** `src/shared/providers/`

---

## Overview

The shared provider models module provides a unified schema for AI provider configuration across all services. This eliminates schema drift, ensures type safety, and provides a single source of truth for provider-related data structures.

## Purpose

**Problem Solved:**

- Multiple services had duplicate `ProviderConfig` definitions
- Schemas were drifting with different field names and validation rules
- Type safety was compromised at service boundaries
- Changes required updates in 4+ locations

**Solution:**

- Centralized provider schemas in `src/shared/providers/`
- All services import from shared module
- Pydantic validation ensures consistency
- Services can extend base models for specific needs

---

## Module Structure

```
src/shared/providers/
├── __init__.py          # Public API exports
└── models.py            # Core schemas (197 lines)
```

### Exports

```python
from shared.providers import (
    # Enums
    ProviderType,
    ProviderStatus,

    # Configuration Models
    ConnectionConfig,
    ModelConfig,
    ProviderConfig,

    # Response Models
    ProviderListResponse,
    ProviderTestResult,
)
```

---

## Core Models

### ProviderType (Enum)

```python
class ProviderType(str, Enum):
    """Supported provider types"""
    OPENAI_COMPATIBLE = "openai_compatible"
    OPENAI = "openai"
    MISTRAL = "mistral"
    ANTHROPIC = "anthropic"
    LOCAL_MODEL = "local"
    CUSTOM = "custom"
```

**Usage:** Standardizes provider type identification across services.

### ProviderStatus (Enum)

```python
class ProviderStatus(str, Enum):
    """Provider operational status"""
    ACTIVE = "active"          # Production-ready
    DISABLED = "disabled"      # Manually disabled
    ERROR = "error"            # Experiencing errors
    TESTING = "testing"        # Under validation
```

**Usage:** Tracks provider health and availability.

### ConnectionConfig

```python
class ConnectionConfig(BaseModel):
    """OpenAI-compatible connection configuration"""
    url: str                              # Base URL
    auth_type: str = "API_KEY"            # Authentication method
    api_key_env: str | None = "OPENAI_API_KEY"  # Env var name
    timeout_seconds: int = 30             # Request timeout
    max_retries: int = 3                  # Retry attempts
```

**Usage:** Embedding service uses this for remote inference server connections.

**Validation:**

- URL must start with `http://` or `https://`

### ModelConfig

```python
class ModelConfig(BaseModel):
    """AI model configuration (LLM or embedding)"""
    name: str                             # Model identifier
    dimensions: int | None                # Embedding dimensions
    path: str | None                      # Local model path
    batch_size: int = 32                  # Processing batch size
    default: bool = False                 # Is default model
    server_model_name: str | None         # Remote model name
    metadata: dict[str, Any] | None       # Additional metadata
```

**Usage:** Embedding service defines available models per provider.

**Validation:**

- `dimensions` must be positive (if provided)
- `batch_size` must be positive

### ProviderConfig

```python
class ProviderConfig(BaseModel):
    """Unified provider configuration schema"""

    # Core fields (all services)
    id: UUID | None                       # Database ID
    name: str                             # Provider name
    provider_type: ProviderType | str     # Provider type
    base_url: str                         # API endpoint
    api_key: str | None                   # API key (write-only)
    is_enabled: bool = True               # Enable/disable toggle
    status: ProviderStatus | str = "testing"  # Operational status
    priority: int = 100                   # Routing priority (lower = higher)

    # Extended configuration
    config_json: dict[str, Any] = Field(default_factory=dict)  # Custom config
    health_check_url: str | None          # Health check endpoint
    timeout_seconds: float = 30.0         # Request timeout

    # Embedding service fields
    models: list[ModelConfig] | None      # Available models
    connection: ConnectionConfig | None   # Connection details

    # Gateway runtime fields (read-only)
    error_count: int | None = 0           # Cumulative errors
    success_count: int | None = 0         # Cumulative successes
    circuit_state: str | None = "CLOSED"  # Circuit breaker state
    last_health_check: str | None         # Last check timestamp
    last_health_status: bool | None       # Last check result
    created_at: str | None                # Creation timestamp
    updated_at: str | None                # Update timestamp
```

**Field Groups:**

1. **Core Fields:** Required by all services
2. **Extended Configuration:** Optional customization
3. **Embedding Service Fields:** YAML config support
4. **Gateway Runtime Fields:** Operational metrics

**Validation:**

- `provider_type` auto-converts from enum to string
- `status` auto-converts from enum to string

---

## Service Usage

### Inference Gateway

**Files:**

- `src/inference-gateway/app/routers/admin.py` - Admin API
- `src/inference-gateway/app/providers/base.py` - Provider routing

**Usage:**

```python
from shared.providers import ProviderConfig, ProviderListResponse

@router.get("/providers", response_model=ProviderListResponse)
async def list_providers(...) -> ProviderListResponse:
    # Query database
    items = [ProviderConfig(...) for row in rows]
    return ProviderListResponse(items=items, total=total, ...)
```

**Benefits:**

- Consistent admin API responses
- Type-safe provider instantiation
- Automatic validation

### Orchestrator Service

**Files:**

- `src/orchestrator/app/routers/admin_gateway_providers.py` - Gateway proxy

**Usage:**

```python
from shared.providers import ProviderConfig, ProviderListResponse

@router.get("", response_model=ProviderListResponse)
async def list_providers(...) -> ProviderListResponse:
    # Proxy to Gateway
    result = await proxy_to_gateway(...)
    return ProviderListResponse(**result)
```

**Benefits:**

- Type safety across service boundary
- Consistent request/response schemas
- Simplified proxy implementation

### Embedding Service

**Files:**

- `src/embedding/app/config/models.py` - YAML config loader

**Usage:**

```python
from shared.providers import (
    ConnectionConfig,
    ModelConfig,
    ProviderConfig as BaseProviderConfig,
)

class ProviderConfig(BaseProviderConfig):
    """Embedding service provider configuration"""

    # Override to make required
    models: list[ModelConfig] = Field(..., description="...")

    @model_validator(mode="before")
    @classmethod
    def map_yaml_fields(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Map YAML field names to shared model field names"""
        # Map 'type' → 'provider_type'
        if "type" in values and "provider_type" not in values:
            values["provider_type"] = str(values["type"])

        # Map 'enabled' → 'is_enabled'
        if "enabled" in values and "is_enabled" not in values:
            values["is_enabled"] = values["enabled"]

        return values
```

**Benefits:**

- Backward compatible with existing YAML configs
- Shared validation logic
- Extensible pattern for service-specific needs

---

## Extension Pattern

Services can extend base models for specific requirements:

```python
from shared.providers import ProviderConfig as BaseProviderConfig

class ServiceSpecificProviderConfig(BaseProviderConfig):
    """Extended provider config with service-specific fields"""

    # Add service-specific fields
    custom_field: str | None = None

    # Override to make fields required
    models: list[ModelConfig] = Field(..., description="Required for this service")

    # Add service-specific validation
    @model_validator(mode="after")
    def validate_service_requirements(self) -> "ServiceSpecificProviderConfig":
        if self.custom_field is None:
            raise ValueError("custom_field required")
        return self
```

---

## Design Decisions

### 1. Optional vs Required Fields

**Decision:** Most fields are optional in base model
**Rationale:**

- Different services have different requirements
- Allows flexible usage across contexts (create/update/read)
- Services can override to make fields required

**Example:**

- Gateway: `models` is optional (not used)
- Embedding: `models` is required (overridden)

### 2. String vs Enum for Types

**Decision:** Accept both `ProviderType | str` and `ProviderStatus | str`
**Rationale:**

- Database stores as string
- Allows flexibility for custom types
- Auto-converts enums to strings

**Validation:**

```python
@field_validator("provider_type", mode="before")
@classmethod
def normalize_provider_type(cls, v: Any) -> str:
    if isinstance(v, Enum):
        return v.value
    return str(v)
```

### 3. Separate Response Models

**Decision:** Create `ProviderListResponse` and `ProviderTestResult`
**Rationale:**

- Clear API contracts
- Type-safe pagination
- Consistent response structure

### 4. JSONB as dict[str, Any]

**Decision:** Use `dict[str, Any]` for `config_json`
**Rationale:**

- Maximum flexibility for provider-specific config
- No schema enforcement (intentional)
- Services can define their own structure

---

## Migration Guide

### For New Services

1. Import shared models:

```python
from shared.providers import ProviderConfig, ModelConfig
```

2. Use directly or extend:

```python
# Direct usage
provider = ProviderConfig(name="openai", ...)

# Extended usage
class MyProviderConfig(ProviderConfig):
    my_field: str
```

### For Existing Services

1. Remove local definitions
2. Import from shared
3. Update type hints
4. Test thoroughly

**Example:**

```python
# Before
class ProviderConfig(BaseModel):
    name: str
    # ... local definition

# After
from shared.providers import ProviderConfig
```

---

## Known Limitations

### 1. CRUD Operations

**Issue:** Base model requires all fields, but UI sends partial updates
**Solution:** Create separate update models with optional fields

```python
class ProviderUpdateRequest(BaseModel):
    """Provider update with optional fields"""
    name: str | None = None
    provider_type: str | None = None
    # ... all fields optional
```

### 2. Naming Collision

**Issue:** Multiple classes named `ProviderConfig` for different purposes
**Solution:** Planned refactoring (P3-REFACTOR-01)

- Inference providers: Keep `ProviderConfig`
- Stateful providers: Rename to `StatefulProviderConfig`
- Capabilities providers: Rename to `CapabilitiesProviderConfig`

### 3. Validation Strictness

**Issue:** Shared validation may be too strict for some use cases
**Solution:** Services can override validators or use `model_validator(mode="before")`

---

## Testing

### Unit Tests

**Location:** `src/shared/tests/unit/test_providers.py` (TODO)

**Coverage:**

- Model instantiation
- Field validation
- Enum conversions
- Extension pattern

### Integration Tests

**Locations:**

- `src/inference-gateway/tests/unit/test_admin_providers.py` (7/11 passing)
- `src/orchestrator/tests/integration/` (TODO)
- `src/embedding/tests/unit/` (TODO)

---

## Future Enhancements

### 1. Stricter Validation

Add provider-type-specific validation:

```python
@model_validator(mode="after")
def validate_provider_requirements(self) -> "ProviderConfig":
    if self.provider_type == ProviderType.OPENAI:
        if not self.api_key:
            raise ValueError("OpenAI providers require api_key")
    return self
```

### 2. Secrets Management

Integrate with secrets backend:

```python
@property
def resolved_api_key(self) -> str:
    """Resolve API key from environment or secrets backend"""
    if self.api_key:
        return self.api_key
    if self.api_key_env:
        return os.getenv(self.api_key_env)
    raise ValueError("No API key configured")
```

### 3. Health Check Integration

Add built-in health check method:

```python
async def check_health(self) -> bool:
    """Perform health check against provider"""
    url = self.health_check_url or f"{self.base_url}/health"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=5.0)
        return response.status_code == 200
```

---

## References

- **Implementation:** P3-REFACTOR-00 (Completed Nov 7, 2025)
- **Future Work:** P3-REFACTOR-01 (Provider class naming)
- **ADR-050:** Inference Gateway Architecture
- **ADR-051:** Gateway Database Schema
- **Plan:** INFERENCE_GATEWAY_IMPLEMENTATION_PLAN.md

---

## Changelog

### Version 1.0 (November 7, 2025)

- Initial implementation
- Consolidated Gateway, Backend, Embedding service models
- Added extension pattern for service-specific needs
- Documented usage and migration guide
