# inference-gateway

OpenAI-compatible LLM proxy for the AI Operations Platform. Exposed on port **18002 → 8002**.
All orchestrator LLM and embedding calls route through here.

## Role in the platform

```
orchestrator-api → inference-gateway → LLM provider (OpenAI / Anthropic / Azure / Mistral)
embedding-service → inference-gateway → embedding provider
```

The gateway enforces rate limits, tracks usage, and protects upstream providers with circuit
breakers. It is the single egress point for all model calls.

## Endpoints

| Path | Method | Description |
|---|---|---|
| `/v1/chat/completions` | POST | OpenAI-compatible chat (sync + streaming) |
| `/v1/embeddings` | POST | OpenAI-compatible embeddings |
| `/v1/responses` | POST | OpenAI Responses API (stateful) |
| `/v1/models` | GET | Available models with provider metadata |
| `/health` | GET | Service health with dependency status |
| `/admin/providers` | CRUD | Provider management |
| `/admin/rate-limits` | CRUD | Rate limit configuration |
| `/admin/circuit-breaker/states` | GET | Per-provider circuit breaker state |
| `/admin/circuit-breaker/{provider}/reset` | POST | Force circuit to CLOSED |
| `/admin/metrics/*` | GET | Aggregate, time-series, per-provider, per-model |
| `/admin/router/routes` | GET | Current model → provider routing table |
| `/admin/router/reload` | POST | Reload routing table from DB |

## Rate limiting

Per-scope token bucket with Redis primary / PostgreSQL fallback (ADR-053).

- **Scopes checked in order:** global → provider → integration → use_case
- **Algorithm:** sliding-window token bucket
- **Redis keys:** `ratelimit:global`, `ratelimit:provider:<name>`, `ratelimit:integration:<id>`
- **Config table:** `gateway_rate_limits` (limit_type, identifier, requests_per_minute,
  tokens_per_minute, burst_size, enabled)
- **429 response** includes a `Retry-After` header
- Skips `/health`, `/docs`, `/admin/*`
- Fails open if both Redis and PostgreSQL are unavailable

Key classes: `RateLimiter` (facade), `TokenBucketLimiter` (Redis), `PostgresRateLimiter`
(fallback), `RateLimitMiddleware`.

## Circuit breaker

Per-provider, 3-state (ADR-052). State and counters stored in Redis; falls back to always-CLOSED
if Redis is unavailable.

| State | Behaviour |
|---|---|
| CLOSED | Requests pass through normally |
| OPEN | Fast-fail (<10 ms) with `CircuitOpenError`; waits `timeout_seconds` before testing |
| HALF_OPEN | One probe request; success → CLOSED, failure → OPEN |

Defaults: `failure_threshold=3`, `timeout_seconds=60`, `success_threshold=1` (all configurable
via env vars). Key class: `CircuitBreaker`. Integrated automatically by `ProviderFactory`.

## Provider management

Providers are DB-driven — configured via the admin API, not environment variables (ADR-050,
ADR-051). API keys are stored encrypted in the `gateway_providers` table.

Supported providers: **OpenAI**, **Anthropic**, **Azure OpenAI**, **Mistral**. Each maps to a
concrete class in `app/providers/` (e.g. `OpenAIProvider`, `AnthropicProvider`).

`ProviderManager` maintains an in-memory cache loaded from `gateway_providers` at startup.
Reload without restart: `POST /admin/router/reload`.

## Usage logging

All requests are logged asynchronously to `gateway_usage_log` (PostgreSQL) by `UsageLogger`.
Batch size and flush interval are configurable. The admin metrics endpoints expose aggregate,
time-series, and per-provider/model breakdowns.

Cost is calculated per-request by `CostCalculator` using model-specific token pricing.

## Configuration

Config is loaded via `shared.config.loader.load_inference_gateway_config()`. Key environment
variables (set in `config/env/.env`):

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://redis-cache:6379` | Redis connection |
| `REDIS_ENABLED` | `true` | Enable Redis for rate limits + circuit breaker |
| `REDIS_MAX_CONNECTIONS` | `50` | Redis connection pool size |
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `3` | Failures before OPEN |
| `CIRCUIT_BREAKER_TIMEOUT_SECONDS` | `60` | OPEN → HALF_OPEN wait |
| `CIRCUIT_BREAKER_SUCCESS_THRESHOLD` | `1` | Successes to close from HALF_OPEN |
| `GATEWAY_RATE_LIMITING_ENABLED` | `true` | Enable rate limiting middleware |
| `GATEWAY_USAGE_BATCH_SIZE` | `10` | Usage log batch size |
| `GATEWAY_USAGE_FLUSH_INTERVAL` | `5.0` | Usage log flush interval (seconds) |

Database connection comes from the shared `DATABASE_URL` / `POSTGRES_*` variables.

## Directory structure

```
src/inference-gateway/
├── app/
│   ├── main.py                     # FastAPI app + lifespan
│   ├── database/                   # Connection, usage schema
│   ├── middleware/
│   │   └── rate_limit_middleware.py
│   ├── models/                     # Pydantic request/response schemas
│   ├── providers/
│   │   ├── base.py                 # BaseProvider protocol
│   │   ├── factory.py              # ProviderFactory (wires circuit breaker)
│   │   ├── openai_provider.py
│   │   ├── anthropic_provider.py
│   │   ├── azure_openai_provider.py
│   │   └── mistral_provider.py
│   ├── routers/
│   │   ├── chat.py                 # /v1/chat/completions, /v1/models
│   │   ├── embeddings.py           # /v1/embeddings
│   │   ├── responses.py            # /v1/responses
│   │   └── admin.py                # /admin/* (17 endpoints)
│   └── services/
│       ├── circuit_breaker.py
│       ├── cost_calculator.py
│       ├── provider_manager.py
│       ├── rate_limiter.py
│       ├── redis_client.py
│       ├── router.py               # Model → provider routing
│       └── usage_logger.py
└── tests/
    ├── unit/                       # 22+ unit test files
    └── integration/                # 7+ integration test files
```

## Testing

```bash
# All tests with coverage
bash src/inference-gateway/run_tests.sh

# Or via the centralised runner
python ops/testing/run_all_tests.py --component inference_gateway
```

Integration tests require a PostgreSQL instance on port 5433 and Redis on port 6380 — start
them via the test compose profile before running.

## Related ADRs

| ADR | Decision |
|---|---|
| ADR-050 | Inference Gateway & Responsibility Split |
| ADR-051 | Provider Secrets & Service-to-Service Auth |
| ADR-052 | Model Routing & Provider Fallback |
| ADR-053 | Rate Limiting & Usage Tracking |
| ADR-054 | OpenAI Compatibility & Error Taxonomy |
| ADR-055 | Observability, Metering & Cost Accounting |
