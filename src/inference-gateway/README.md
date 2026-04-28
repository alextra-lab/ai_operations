# Inference Gateway

**Status:** Phase 4.5 - In Development
**Version:** 0.1.0
**Port (Test):** 8007 → 8002 (external → internal)

## Overview

The Inference Gateway provides centralized access to LLM and embedding providers, implementing:

- OpenAI-compatible API endpoints
- Rate limiting and circuit breaking
- Usage tracking and cost calculation
- Provider routing and failover
- Unified authentication and authorization

## Architecture

See: `docs/development/adrs/ADR-050-Inference-Gateway-and-Responsibility-Split.md`

**Key Principles:**
- Dumb Pipe v1 (simple routing by model ID)
- Reuses existing `src/shared/` infrastructure
- Minimal code, maximum leverage
- OpenAI SDK compatible

## Port Assignment (TEST Environment)

**Per PORT_MANAGEMENT.md:**
- **External (host):** `localhost:8007`
- **Internal (container):** `8002`
- **Docker network:** `inference-gateway-test:8002`

**Rationale:** Port 8002 external was already used by embedding-service (test: 8005). Using 8007 for test external access to avoid conflicts.

## Development Status

**Phase 1: Core Gateway (Week 1)**
- ✅ P1-T1: Project Setup & Docker Integration (COMPLETE)
- ⏸️ P1-T2: Database Schema & Migrations (PENDING)
- ⏸️ P1-T3: Authentication Integration (PENDING)
- ⏸️ P1-T4: Simple Router & Provider Manager (PENDING)
- ⏸️ P1-T5: Chat Completions Endpoint (PENDING)

## Quick Start

### Build and Run (Test Environment)

```bash
# Load test environment
set -Eeuo pipefail && set -a && source config/env/env.test && set +a

# Build container (with --no-cache for clean build)
docker-compose -f deploy/docker-compose.test.yml build --no-cache inference-gateway

# Start service
docker-compose -f deploy/docker-compose.test.yml up -d inference-gateway

# Check health
curl http://localhost:8007/health
```

### Run Tests

```bash
# From src/inference-gateway directory
cd src/inference-gateway

# Run unit tests
pytest tests/unit/ -v

# Run all tests with coverage
pytest tests/ -v --cov=app --cov-report=term-missing
```

## Project Structure

```
src/inference-gateway/
├── Dockerfile                 # Multi-stage build (follows backend pattern)
├── requirements.txt           # Python dependencies
├── pyproject.toml            # Black, Ruff, MyPy config
├── pytest.ini                 # Pytest configuration
├── README.md                  # This file
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI app and lifespan
│   ├── database/              # Connection, usage schema
│   ├── middleware/            # Rate limit middleware
│   ├── models/                # Request/response Pydantic models
│   ├── providers/             # OpenAI, Anthropic, Azure, Mistral
│   ├── routers/               # chat, embeddings, responses, admin
│   ├── services/              # Router, provider_manager, rate_limiter, usage_logger, redis, circuit_breaker
│   └── utils/                 # Error handling
└── tests/
    ├── unit/                  # Unit tests
    └── integration/           # Integration tests
```

## Dependencies

**Infrastructure:**
- PostgreSQL 17 (existing: `postgres-test`)
- Redis 7 (future: P2-T4)

**Code Dependencies (Reuse `src/shared/`):**
- `shared.auth` - JWT validation, RBAC
- `shared.logging_utils` - Structured JSON logging
- `shared.database` - PostgreSQL connection pooling

**External Services:**
- None yet (providers added in P1-T7)

## Related Documentation

- **Implementation Plan:** `docs/development/plans/INFERENCE_GATEWAY_IMPLEMENTATION_PLAN.md`
- **Master Roadmap:** `docs/development/plans/MASTER_ROADMAP.md` (Phase 4.5)
- **Technical Spec:** `docs/development/specs/INFERENCE_GATEWAY_V1_SPEC.md`
- **ADR-050:** Inference Gateway Architecture
- **ADR-051:** Provider Secrets and S2S Auth
- **ADR-052:** Model Routing and Provider Fallback
- **ADR-053:** Rate Limiting and Usage Tracking
- **ADR-054:** OpenAI Compatibility and Error Taxonomy
- **ADR-055:** Observability, Metering, and Cost Accounting

## Environment Variables

See `config/env/env.template` or `config/env/env.test.template` for the full list. Key variables:

```bash
# Database
DATABASE_URL=postgresql://testuser:testpassword@postgres-test:5432/aio-test

# Authentication
JWT_SECRET=<from config/env/env.test>
JWT_ALGORITHM=HS256

# Gateway Config
GATEWAY_PORT=8002
GATEWAY_DEBUG=true
```

## Next Tasks

**P1-T2: Database Schema & Migrations (0.5 day)**
- Create `gateway_providers` table
- Create `gateway_usage_log` table
- Create `gateway_rate_limits` table
- Extend `run_manifests` with `gateway_metrics` JSONB

**P1-T3: Authentication Integration (0.5 day)**
- Extend `TokenPayload` with `scopes` field
- Create `requires_scope()` dependency
- Integrate with `shared.auth`

## Troubleshooting

**Container won't start:**
```bash
# Check logs
docker logs inference-gateway-test

# Rebuild with --no-cache
docker-compose -f deploy/docker-compose.test.yml build --no-cache inference-gateway
docker-compose -f deploy/docker-compose.test.yml up -d inference-gateway
```

**Health check failing:**
```bash
# Check if service is running inside container
docker exec inference-gateway-test curl -f http://localhost:8002/health

# Check port mapping
docker port inference-gateway-test
```

**Import errors:**
```bash
# Ensure shared module is copied in Dockerfile
# Check Dockerfile COPY statements
```

---

**Owner:** Backend Team
**Status:** Active Development
**Last Updated:** 2026-01-30
