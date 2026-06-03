# shared

Internal Python library shared across all platform services. Every Python service imports from
`shared.*` — it is **not** a pip package; it is source-copied into each container at build time.

## How it reaches services

Each service Dockerfile COPYs the `shared/` tree into `/app/shared` and sets `PYTHONPATH=/app`:

```dockerfile
COPY shared /app/shared
ENV PYTHONPATH=/app
```

Services then import normally:

```python
from shared.auth import get_current_user
from shared.config.loader import load_orchestrator_config
```

There is no `pip install shared` step. If you move or rename a module here, update every
service that imports it.

## Modules

### `shared.auth`

JWT authentication, RBAC dependency injection, and user management.

**Key exports** (`shared/auth/__init__.py`):

| Symbol | Type | Description |
|---|---|---|
| `get_current_user` | FastAPI dependency | Validates Bearer token, returns `User` |
| `admin_required` | FastAPI dependency | Rejects non-admin callers |
| `service_required` | FastAPI dependency | Rejects non-service-role callers |
| `requires_scope(scope)` | FastAPI dependency factory | Scope-based authorization |
| `requires_any_scope(scopes)` | FastAPI dependency factory | Any-of authorization |
| `auth_router` | `APIRouter` | Full auth + user management routes |
| `auth_router_minimal` | `APIRouter` | Auth-only routes (no user mgmt) |
| `create_auth_router(...)` | function | Configurable router factory |
| `UnifiedAuthManager` | class | JWT create/verify, bcrypt hashing, refresh token lifecycle |
| `TokenPayload` | Pydantic model | Decoded token; has `.has_scope()`, `.is_admin()` |

Tokens are HS256 JWTs. Roles follow ADR-060 (`USER`, `ADMIN`, `SERVICE`).

---

### `shared.config.loader`

Pydantic-based config loaders for each service. All read from environment variables (sourced
from `config/env/.env`).

**Load functions** (each returns a validated Pydantic model):

```python
load_orchestrator_config()      → OrchestratorConfig
load_inference_gateway_config() → InferenceGatewayConfig
load_llm_guard_config()         → LLMGuardConfig
load_embedding_config()         → EmbeddingConfig
load_retrieval_config()         → RetrievalConfig
load_database_config()          → DatabaseConfig
load_qdrant_config()            → QdrantConfig
load_jwt_config()               → JWTConfig
load_logging_config(service)    → LoggingConfig
load_opentelemetry_config()     → OpenTelemetryConfig
load_all_configs()              → dict[str, BaseConfig]
validate_all_configs()          → bool
```

The `config_manager` singleton (`shared.config.base`) lets services register and retrieve
configs by name. `resolve_secret(name)` in `shared.config.secrets` handles secret lookup
(currently env-var backed; designed for Vault integration per ADR-061).

---

### `shared.logging_utils`

Structured JSON logging and request-tracing middleware.

**`shared.logging_utils.fastapi`** — import this in FastAPI services:

| Symbol | Description |
|---|---|
| `configure_logging(service_name, log_level, log_format)` | Returns a configured `logging.Logger` |
| `RequestIDLoggerMiddleware` | Starlette middleware — adds `X-Request-ID` to logger context |
| `RequestLoggingMiddleware` | Starlette middleware — logs method, path, status, duration |
| `get_logger(name, context)` | Returns a `LoggingContextAdapter` with extra fields |

**`shared.logging_utils.base`**: `JsonFormatter`, `TextFormatter`, `LoggingContextAdapter`.

**`shared.logging_utils.redaction`**: `redact_value()`, `mask_identifier()`, `safe_config_summary()`,
`client_safe_error_message()` — used to strip PII/secrets from log output (ADR-048).

---

### `shared.db` / `shared.database`

Async SQLAlchemy session factory. Import from either; `shared.database` re-exports everything
from `shared.db.connection` for backwards compatibility.

**Key exports** (`shared/db/connection.py`):

| Symbol | Description |
|---|---|
| `Base` | SQLAlchemy `DeclarativeBase` with `AsyncAttrs` — extend for ORM models |
| `engine` | Module-level `AsyncEngine` |
| `async_session` | Module-level `async_sessionmaker[AsyncSession]` |
| `get_db_session()` | FastAPI dependency — yields `AsyncSession` |
| `get_session()` | Async context manager — same session, non-DI use |
| `check_database_connection()` | Health-check helper |
| `init_db_tables(metadata_bases)` | Creates tables from ORM metadata |

Pool defaults: `size=10`, `max_overflow=20`, `recycle=3600`, `pre_ping=True`. Override via
environment variables read in `get_pool_config()`.

---

### `shared.telemetry_utils`

Optional OpenTelemetry tracing. Degrades gracefully when the library is absent.

```python
from shared.telemetry_utils.telemetry import setup_telemetry, get_tracer, create_span

# In app startup:
setup_telemetry(app, service_name="orchestrator", otlp_endpoint=..., instrument_fastapi=True)

# In business logic:
with create_span("my-operation") as span:
    set_span_attribute("key", "value")
```

`get_tracer()` returns a real OTel tracer if the package is installed, or a `DummyTracer`
(no-op) otherwise. Enabled at runtime via `OTEL_ENABLED=true` / `OTEL_EXPORTER_OTLP_ENDPOINT`.

---

### `shared.providers`

Pydantic models for LLM provider configuration used by the inference gateway:
`ProviderType`, `ProviderStatus`, `ProviderConfig`, `ConnectionConfig`, `ModelConfig`.

## Adding a new module

1. Create `src/shared/new_module/` with an `__init__.py` that declares `__all__`.
2. Follow async-first conventions — use `AsyncSession`, `async def`.
3. Import shared primitives from sibling modules:
   ```python
   from shared.db import Base, get_db_session
   from shared.config.loader import load_database_config
   from shared.logging_utils.fastapi import configure_logging
   ```
4. Services import directly from the submodule — there is no top-level `shared/__init__.py`
   re-export layer.
5. No pip packaging step required — the module is available in containers immediately after
   the next image build.

## Testing

```bash
bash src/shared/run_tests.sh

# Or via the centralised runner
python ops/testing/run_all_tests.py --component shared
```

Tests live in `src/shared/tests/unit/` organised by submodule (`auth/`, `config/`, `db/`,
`logging_utils/`). The test `conftest.py` sets `TESTING=1` and points at the `aio-test`
database on port 5433.
