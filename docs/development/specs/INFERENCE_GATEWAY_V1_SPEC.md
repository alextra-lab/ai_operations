# Inference Gateway v1 - Technical Specification

**Version:** 1.0
**Date:** 2025-11-02
**Status:** Approved for Implementation
**Related ADRs:** ADR-050, ADR-051, ADR-052, ADR-053, ADR-054, ADR-055

---

## Overview

This document specifies the technical implementation of the Inference Gateway v1 for department-scale deployment (10-100 users). The Gateway centralizes LLM and embedding provider access with focus on **simplicity, reliability, and reuse of existing infrastructure**.

**Scope:** OpenAI-compatible API with basic rate limiting, usage tracking, and provider routing.

**Out of Scope:** Smart routing, semantic caching, advanced failover (deferred to v2).

---

## System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  Inference Gateway                        │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │  FastAPI Application (src/inference-gateway/app)  │  │
│  │                                                    │  │
│  │  ┌──────────────────────────────────────────────┐ │  │
│  │  │ Routers                                      │ │  │
│  │  │  - /v1/chat/completions                     │ │  │
│  │  │  - /v1/embeddings                           │ │  │
│  │  │  - /v1/models                               │ │  │
│  │  │  - /admin/gateway/* (control plane)        │ │  │
│  │  └──────────────────────────────────────────────┘ │  │
│  │                                                    │  │
│  │  ┌──────────────────────────────────────────────┐ │  │
│  │  │ Services                                     │ │  │
│  │  │  - SimpleRouter (model → provider)          │ │  │
│  │  │  - ProviderManager (config, health)        │ │  │
│  │  │  - CostCalculator (pricing lookups)        │ │  │
│  │  │  - UsageLogger (batch insert)              │ │  │
│  │  │  - RateLimiter (Redis/PostgreSQL)         │ │  │
│  │  └──────────────────────────────────────────────┘ │  │
│  │                                                    │  │
│  │  ┌──────────────────────────────────────────────┐ │  │
│  │  │ Provider Clients (adapters)                  │ │  │
│  │  │  - OpenAIProvider                           │ │  │
│  │  │  - MistralProvider (OpenAI-compatible)     │ │  │
│  │  │  - LocalProvider (LMStudio/Ollama)         │ │  │
│  │  └──────────────────────────────────────────────┘ │  │
│  │                                                    │  │
│  │  ┌──────────────────────────────────────────────┐ │  │
│  │  │ Middleware                                   │ │  │
│  │  │  - RequestLoggingMiddleware (shared.logging)│ │  │
│  │  │  - RateLimitMiddleware (optional)          │ │  │
│  │  └──────────────────────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Shared Infrastructure (REUSE, DON'T REBUILD)     │  │
│  │                                                    │  │
│  │  - shared.auth (JWT validation, RBAC)             │  │
│  │  - shared.logging_utils (structured logs)         │  │
│  │  - shared.database (PostgreSQL connection)        │  │
│  │  - PricingHistoryService (cost calculation)       │  │
│  │  - models table (model metadata)                  │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
           │                           │
           ├─ PostgreSQL               ├─ Redis (optional, recommended)
           │   - gateway_providers     │   - Rate limit counters
           │   - gateway_usage_log     │   - Circuit breaker state
           │   - models (existing)     │
           │   - model_pricing_history │
           └───────────────────────────┘
```

---

## Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Framework** | FastAPI 0.104+ | Existing pattern, async support, OpenAPI auto-generation |
| **Language** | Python 3.12 | Project standard |
| **Database** | PostgreSQL 17 | Existing infrastructure |
| **Cache** | Redis 7-alpine | Rate limiting, circuit state (optional fallback to PostgreSQL) |
| **HTTP Client** | httpx | Async support, connection pooling |
| **Auth** | shared.auth (JWT) | Existing module, zero duplication |
| **Logging** | shared.logging_utils | Existing module, ADR-045 compliant |
| **Validation** | Pydantic 2.7+ | Type safety, OpenAPI schemas |
| **Testing** | pytest + httpx | Existing test infrastructure |

---

## File Structure

```
src/inference-gateway/
├── Dockerfile                    # Multi-stage build
├── requirements.txt              # Dependencies
├── pyproject.toml                # Package metadata
├── pytest.ini                    # Test configuration
├── .env.example                  # Environment template
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI app, startup/shutdown
│   ├── config.py                 # Settings (Pydantic BaseSettings)
│   │
│   ├── routers/                  # API endpoints
│   │   ├── __init__.py
│   │   ├── chat.py               # POST /v1/chat/completions
│   │   ├── embeddings.py         # POST /v1/embeddings
│   │   ├── models.py             # GET /v1/models
│   │   └── admin.py              # /admin/gateway/* (control plane)
│   │
│   ├── services/                 # Business logic
│   │   ├── __init__.py
│   │   ├── router.py             # SimpleRouter (model → provider)
│   │   ├── provider_manager.py   # Provider config, health
│   │   ├── cost_calculator.py    # Cost calculation (uses existing PricingHistoryService)
│   │   ├── usage_logger.py       # Batch usage logging
│   │   └── rate_limiter.py       # Rate limiting (Redis/PostgreSQL)
│   │
│   ├── providers/                # Provider adapters
│   │   ├── __init__.py
│   │   ├── base.py               # Provider protocol/interface
│   │   ├── openai_provider.py    # OpenAI API client
│   │   ├── mistral_provider.py   # Mistral (OpenAI-compatible)
│   │   └── local_provider.py     # LMStudio/Ollama
│   │
│   ├── models/                   # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── requests.py           # Chat/embedding request schemas
│   │   ├── responses.py          # Chat/embedding response schemas
│   │   ├── provider_config.py    # Provider configuration
│   │   └── errors.py             # Error response schemas
│   │
│   ├── database/                 # Database models
│   │   ├── __init__.py
│   │   ├── provider.py           # GatewayProvider model
│   │   └── usage.py              # GatewayUsageLog model
│   │
│   ├── middleware/               # Request processing
│   │   ├── __init__.py
│   │   ├── logging_middleware.py # Request/response logging
│   │   └── rate_limit_middleware.py # Optional rate limiting
│   │
│   └── utils/                    # Utilities
│       ├── __init__.py
│       ├── errors.py             # Exception classes
│       └── streaming.py          # SSE streaming helpers
│
└── tests/
    ├── __init__.py
    ├── conftest.py               # Pytest fixtures
    ├── unit/                     # Unit tests
    │   ├── test_router.py
    │   ├── test_cost_calculator.py
    │   └── test_rate_limiter.py
    ├── integration/              # Integration tests
    │   ├── test_chat_completions.py
    │   ├── test_embeddings.py
    │   └── test_provider_failover.py
    └── fixtures/                 # Test data
        ├── openai_responses.json
        └── provider_configs.yaml
```

---

## Core Components

### 1. Main Application (`app/main.py`)

```python
"""
Gateway FastAPI application.

VERIFICATION CHECKLIST:
□ Uses shared.auth for authentication
□ Uses shared.logging_utils for logging
□ Uses shared.database for DB connection
□ Minimal code - maximum reuse of existing infrastructure
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.auth import create_auth_router, get_current_user  # REUSE shared auth
from shared.logging_utils.fastapi import configure_logging    # REUSE shared logging
from shared.database import init_database, close_database      # REUSE shared DB

from .config import settings
from .routers import chat, embeddings, models, admin
from .middleware.logging_middleware import RequestLoggingMiddleware
from .services.provider_manager import provider_manager
from .services.usage_logger import batch_usage_logger

# Configure logging (existing pattern)
logger = configure_logging(service_name="inference_gateway")

# Create FastAPI app
app = FastAPI(
    title="Inference Gateway",
    version="1.0.0",
    description="Centralized LLM and embedding provider access",
    docs_url="/docs" if settings.DEVELOPMENT else None,  # Disable in prod
    redoc_url="/redoc" if settings.DEVELOPMENT else None
)

# CORS (existing pattern)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging middleware (structured logs)
app.add_middleware(RequestLoggingMiddleware)

# Routers
app.include_router(chat.router, prefix="/v1", tags=["Chat"])
app.include_router(embeddings.router, prefix="/v1", tags=["Embeddings"])
app.include_router(models.router, prefix="/v1", tags=["Models"])
app.include_router(admin.router, prefix="/admin/gateway", tags=["Admin"])

# Health endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "inference-gateway",
        "version": "1.0.0"
    }

# Startup/shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Inference Gateway starting...")

    # Initialize database (existing pattern)
    await init_database(settings.DATABASE_URL)

    # Load provider configurations
    await provider_manager.load_providers()

    # Start batch usage logger
    await batch_usage_logger.start()

    logger.info("Inference Gateway ready")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Inference Gateway shutting down...")

    # Flush pending usage logs
    await batch_usage_logger.flush()

    # Close database connections
    await close_database()

    logger.info("Inference Gateway stopped")
```

### 2. Configuration (`app/config.py`)

```python
"""
Gateway configuration using Pydantic BaseSettings.

VERIFICATION CHECKLIST:
□ Follows existing config pattern (see src/orchestrator/app/config.py)
□ Uses environment variables
□ Validates required settings
"""
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Gateway settings loaded from environment."""

    # Environment
    ENV: str = Field("development", env="ENV")
    DEVELOPMENT: bool = Field(True, env="DEVELOPMENT")

    # Database (PostgreSQL)
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # Redis (optional, fallback to PostgreSQL)
    REDIS_URL: str | None = Field(None, env="REDIS_URL")
    CACHE_BACKEND: str = Field("redis", env="CACHE_BACKEND")  # or "postgres"

    # Authentication (use existing JWT_SECRET from shared.auth)
    JWT_SECRET: str = Field(..., env="JWT_SECRET")
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    JWT_ISSUER: str = Field("ai-operations-platform", env="JWT_ISSUER")

    # Rate Limiting (Phase 1: disabled, Phase 2: enabled)
    RATE_LIMIT_ENABLED: bool = Field(False, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_GLOBAL_RPM: int = Field(500, env="RATE_LIMIT_GLOBAL_RPM")

    # Usage Logging
    USAGE_LOG_BATCH_SIZE: int = Field(10, env="USAGE_LOG_BATCH_SIZE")
    USAGE_LOG_FLUSH_INTERVAL: float = Field(5.0, env="USAGE_LOG_FLUSH_INTERVAL")

    # CORS
    CORS_ORIGINS: list[str] = Field(
        ["http://localhost:4200", "http://ui-webapp:80"],
        env="CORS_ORIGINS"
    )

    # Provider defaults
    DEFAULT_TIMEOUT: float = Field(10.0, env="GATEWAY_DEFAULT_TIMEOUT")
    MAX_RETRIES: int = Field(2, env="GATEWAY_MAX_RETRIES")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

### 3. Simple Router (`app/services/router.py`)

```python
"""
Simple model-to-provider routing (v1).

VERIFICATION CHECKLIST:
□ Queries existing `models` table (don't duplicate model registry)
□ Uses ProviderManager (don't access providers directly)
□ Simple dictionary lookup (<1ms latency)
"""
from typing import Protocol
from src.backend.app.db.models import Model  # REUSE existing model
from shared.database import get_db

class Provider(Protocol):
    """Provider interface."""
    name: str
    enabled: bool
    async def chat_completion(self, request: dict) -> dict: ...
    async def create_embeddings(self, request: dict) -> dict: ...

class SimpleRouter:
    """
    V1: Dictionary-based routing (model ID → provider name).

    Future: Strategy pattern allows v2 smart router without breaking changes.
    """

    def __init__(self, provider_manager: "ProviderManager"):
        self.provider_manager = provider_manager
        self.routes: dict[str, str] = {}  # model_id → provider_name

    async def load_routes(self):
        """
        Load routes from existing `models` table.

        VERIFICATION: Use existing Model SQLAlchemy model,
        don't create duplicate schema.
        """
        async with get_db() as db:
            # Query active models
            models = await db.execute(
                """
                SELECT model_id, provider
                FROM models
                WHERE is_active = true
                """
            )

            for row in models:
                self.routes[row.model_id] = row.provider

            logger.info(f"Loaded {len(self.routes)} model routes")

    def route(self, model: str) -> Provider:
        """
        Route model to provider.

        Args:
            model: Concrete model ID (e.g., "gpt-4o-mini")

        Returns:
            Provider instance

        Raises:
            ModelNotFoundError: Model not in routing table
            ProviderUnavailableError: Provider disabled/unhealthy
        """
        provider_name = self.routes.get(model)

        if not provider_name:
            raise ModelNotFoundError(
                f"Model '{model}' not found. "
                f"Available: {list(self.routes.keys())}"
            )

        provider = self.provider_manager.get_provider(provider_name)

        if not provider or not provider.enabled:
            raise ProviderUnavailableError(
                f"Provider '{provider_name}' unavailable"
            )

        return provider
```

### 4. Cost Calculator (`app/services/cost_calculator.py`)

```python
"""
Cost calculation using existing pricing infrastructure.

VERIFICATION CHECKLIST:
□ Uses existing PricingHistoryService (don't duplicate)
□ Queries model_pricing_history table (don't create new table)
□ Returns cost in EUR (consistent with existing system)
"""
from src.backend.app.services.pricing_history_service import PricingHistoryService
from src.backend.app.db.models import Model
from shared.database import get_db

class CostCalculator:
    """Calculate cost using existing pricing tables."""

    async def calculate(
        self,
        model_id: str,
        tokens_in: int,
        tokens_out: int
    ) -> dict:
        """
        Calculate cost using existing PricingHistoryService.

        VERIFICATION: Don't duplicate cost calculation logic,
        use existing service from src/orchestrator/app/services/.
        """
        async with get_db() as db:
            pricing_service = PricingHistoryService(db)

            # Get active pricing (existing method)
            pricing = await pricing_service.get_active_pricing(model_id)

            if pricing:
                input_cost = (tokens_in / 1_000_000) * pricing.input_price_per_million
                output_cost = (tokens_out / 1_000_000) * pricing.output_price_per_million

                return {
                    "input_cost_eur": round(input_cost, 6),
                    "output_cost_eur": round(output_cost, 6),
                    "total_cost_eur": round(input_cost + output_cost, 6),
                    "pricing_source": "pricing_history"
                }

            # Fallback to model registry
            model = await db.query(Model).filter_by(model_id=model_id).first()
            if model:
                input_cost = (tokens_in / 1_000_000) * (model.input_price_per_million or 0)
                output_cost = (tokens_out / 1_000_000) * (model.output_price_per_million or 0)

                return {
                    "input_cost_eur": round(input_cost, 6),
                    "output_cost_eur": round(output_cost, 6),
                    "total_cost_eur": round(input_cost + output_cost, 6),
                    "pricing_source": "model_registry"
                }

            # No pricing data
            return {
                "input_cost_eur": 0.0,
                "output_cost_eur": 0.0,
                "total_cost_eur": 0.0,
                "pricing_source": "unknown"
            }
```

---

## API Endpoints

### Chat Completions (`app/routers/chat.py`)

```python
"""
OpenAI-compatible chat completions endpoint.

VERIFICATION CHECKLIST:
□ Uses shared.auth for JWT validation (get_current_user dependency)
□ Uses requires_scope("inference:chat") for authorization
□ Returns OpenAI-compatible response format
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from shared.auth import TokenPayload, requires_scope

from ..models.requests import ChatCompletionRequest
from ..models.responses import ChatCompletionResponse
from ..services.router import simple_router
from ..services.cost_calculator import cost_calculator
from ..services.usage_logger import batch_usage_logger

router = APIRouter()

@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    token: TokenPayload = Depends(requires_scope("inference:chat"))
):
    """
    OpenAI-compatible chat completions endpoint.

    VERIFICATION:
    - Uses shared.auth.requires_scope (don't create new auth logic)
    - Returns OpenAI format (compatible with existing LLMClient)
    """
    # Route to provider
    provider = simple_router.route(request.model)

    # Call provider
    start_time = time.time()
    response = await provider.chat_completion(request.dict())
    provider_latency_ms = int((time.time() - start_time) * 1000)

    # Calculate cost (uses existing pricing service)
    cost_data = await cost_calculator.calculate(
        model_id=request.model,
        tokens_in=response["usage"]["prompt_tokens"],
        tokens_out=response["usage"]["completion_tokens"]
    )

    # Log usage (batch insert)
    await batch_usage_logger.log_usage({
        "request_id": request_id,
        "user_id": token.user_id,
        "provider": provider.name,
        "model": request.model,
        "tokens_in": response["usage"]["prompt_tokens"],
        "tokens_out": response["usage"]["completion_tokens"],
        "cost_eur": cost_data["total_cost_eur"],
        "latency_ms": provider_latency_ms
    })

    # Add custom headers
    headers = {
        "X-Gateway-Provider": provider.name,
        "X-Gateway-Model": request.model,
        "X-Gateway-Cost-Eur": str(cost_data["total_cost_eur"]),
        "X-Provider-Latency-Ms": str(provider_latency_ms)
    }

    return Response(
        content=json.dumps(response),
        media_type="application/json",
        headers=headers
    )
```

---

## Database Schema

### Provider Configuration

```sql
-- Gateway-specific tables
CREATE TABLE gateway_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,  -- 'openai', 'openai_compatible', 'vllm'
    base_url TEXT NOT NULL,
    api_key_encrypted TEXT,  -- pgcrypto encrypted
    enabled BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 100,
    config JSONB DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);
```

### Usage Logging

```sql
-- Usage tracking (from ADR-053)
CREATE TABLE gateway_usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    request_id TEXT NOT NULL,

    -- Caller identity
    user_id UUID REFERENCES users(id),
    service_id TEXT,
    role TEXT,

    -- Provider & model
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    endpoint TEXT NOT NULL,

    -- Usage metrics
    tokens_in INTEGER,
    tokens_out INTEGER,
    total_tokens INTEGER,
    cost_eur NUMERIC(10, 6),

    -- Performance
    latency_ms INTEGER,
    gateway_latency_ms INTEGER,
    provider_latency_ms INTEGER,

    -- Status
    status_code INTEGER,
    error_type TEXT,

    -- Indexes
    INDEX idx_gateway_usage_timestamp (timestamp),
    INDEX idx_gateway_usage_user (user_id, timestamp),
    INDEX idx_gateway_usage_provider (provider, timestamp)
);
```

---

## Deployment

### Docker Compose

```yaml
# deploy/docker-compose.yml (add to existing file)
services:
  inference-gateway:
    build:
      context: ../src
      dockerfile: inference-gateway/Dockerfile
    container_name: inference-gateway
    networks: [observability]
    ports: ["8002:8002"]
    environment:
      - ENV=${ENV:-development}
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis-cache:6379
      - JWT_SECRET=${JWT_SECRET}
      - RATE_LIMIT_ENABLED=false  # Phase 1: disabled
    depends_on:
      - postgres-db
      - redis-cache  # NEW
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: always
    platform: linux/arm64

  redis-cache:  # NEW service
    image: redis:7-alpine
    container_name: redis-cache
    networks: [observability]
    ports: ["6379:6379"]
    volumes: ["../data/redis:/data"]
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: always
    platform: linux/arm64
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_router.py
"""
Test simple router logic.

VERIFICATION:
- Mock provider_manager (don't hit real providers)
- Test unknown model error
- Test disabled provider error
"""
def test_route_known_model():
    """Route known model to correct provider."""
    router = SimpleRouter(mock_provider_manager)
    router.routes = {"gpt-4o-mini": "openai"}

    provider = router.route("gpt-4o-mini")
    assert provider.name == "openai"

def test_route_unknown_model():
    """Raise error for unknown model."""
    router = SimpleRouter(mock_provider_manager)
    router.routes = {}

    with pytest.raises(ModelNotFoundError):
        router.route("unknown-model")
```

### Integration Tests

```python
# tests/integration/test_chat_completions.py
"""
Test chat completions endpoint end-to-end.

VERIFICATION:
- Test with real OpenAI mock server
- Verify response format matches OpenAI
- Verify cost calculation correct
"""
@pytest.mark.asyncio
async def test_chat_completions_success(test_client, mock_openai):
    """Test successful chat completion."""
    response = await test_client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "test"}]
        },
        headers={"Authorization": f"Bearer {test_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    assert data["model"] == "gpt-4o-mini"

    # Verify cost header present
    assert "X-Gateway-Cost-Eur" in response.headers
```

---

## Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Routing Decision** | <1ms (p95) | Time from model ID → provider instance |
| **Added Latency (Sync)** | <10ms (p95) | Gateway overhead vs direct provider |
| **Streaming First Byte** | <200ms | Time to first SSE chunk |
| **Cost Calculation** | <5ms | Database query for pricing |
| **Usage Log Insert** | <10ms (batch) | Async queue → DB write |
| **Rate Limit Check** | <1ms (Redis) | Token bucket operation |

---

## Security Checklist

✅ **Authentication:**

- [ ] All endpoints require valid JWT (except `/health`)
- [ ] JWT validated using `shared.auth.get_current_user`
- [ ] Scopes enforced (`inference:chat`, `inference:embed`, `gateway:admin`)

✅ **Secrets:**

- [ ] Provider API keys encrypted in database (pgcrypto)
- [ ] Keys never logged (ADR-045 compliance)
- [ ] Keys never in error messages

✅ **Logging:**

- [ ] Prompts/responses not logged by default
- [ ] Structured JSON logs (shared.logging_utils)
- [ ] Request ID propagated from orchestrator

✅ **Database:**

- [ ] Parameterized queries (no SQL injection)
- [ ] RLS policies applied (if multi-tenant in future)

---

## Migration Checklist

### From Current (Direct OpenAI) → Gateway

**Orchestrator Changes:**

```python
# Before
LLMAAS_BASE_URL=https://api.openai.com/v1

# After
INFERENCE_GATEWAY_URL=http://inference-gateway:8002
LLMAAS_BASE_URL=http://inference-gateway:8002  # Optional fallback for legacy tooling

# Code changes: ZERO (OpenAI-compatible API)
```

**Database Migrations:**

```sql
-- Run these migrations
001_create_gateway_providers_table.sql
002_create_gateway_usage_log_table.sql
003_extend_run_manifests_with_gateway_metrics.sql
```

**Service Account Token:**

```bash
# Create service account JWT with inference:chat scope
python ops/cli/create_service_token.py \
  --service orchestrator-api \
  --scopes inference:chat \
  --output orchestrator_gateway_token.txt

# Add to orchestrator .env
GATEWAY_SERVICE_TOKEN=<generated-token>
```

---

## Acceptance Criteria

### Functional

✅ OpenAI Python SDK works with Gateway (no code changes in orchestrator)
✅ Streaming SSE matches OpenAI format (`data:` prefix, `[DONE]` terminator)
✅ Cost calculated using existing pricing tables
✅ Usage logged to `gateway_usage_log` table
✅ Run manifests extended with `gateway_metrics` JSONB field
✅ Admin UI can manage providers (add, edit, enable/disable)

### Performance

✅ p95 added latency <10ms (sync requests)
✅ Streaming first byte <200ms
✅ Routing decision <1ms
✅ Cost calculation <5ms

### Security

✅ All requests require valid JWT
✅ Scopes enforced correctly
✅ Provider keys encrypted in database
✅ No secrets in logs or error messages

### Operational

✅ Gateway starts in <10 seconds
✅ Provider reload works without restart
✅ Rollback to direct provider takes <60 seconds

---

**Document Owner:** Backend Team
**Last Updated:** 2025-11-02
**Status:** Ready for Implementation
