# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Running Tests

```bash
# Run all tests (recommended)
python ops/testing/run_all_tests.py

# Run a single component's tests
python ops/testing/run_all_tests.py --component orchestrator
python ops/testing/run_all_tests.py --component corpus_svc

# Run with coverage
python ops/testing/run_all_tests.py --coverage --html-report

# Run service-specific tests via shell scripts
bash src/orchestrator/run_tests.sh --cov=app --cov-report=term-missing
bash src/corpus_svc/run_tests.sh --cov=app --cov-report=term-missing

# Run a specific test file or test
pytest tests/unit/path/to/test_file.py::test_function_name
pytest tests/integration/
pytest tests/e2e/
```

### Linting and Formatting

```bash
# Ruff lint (auto-fix)
ruff check --fix src/ tests/ ops/

# Black format
black src/ tests/ ops/

# Run all pre-commit hooks
pre-commit run --all-files

# Skip a specific hook for one commit
SKIP=mypy git commit -m "..."
```

### Type Checking

```bash
python -m mypy --config-file mypy.ini src tests ops
```

### Starting the Platform

```bash
# First-time setup (creates network, data dirs, env file)
make setup
# Edit config/env/.env — set POSTGRES_PASSWORD, JWT_SECRET, TOOL_SECRETS_KEY

# Build images and download models (local profile)
make build
make models

# Start services
make up

# Common operations
make status                        # running containers + ports
make logs                          # tail all logs
make logs SVC=orchestrator-api     # tail one service
make restart                       # stop + start
make down                          # stop

# Enterprise profile
make build PROFILE=enterprise
make up PROFILE=enterprise

# Offline build (no internet — uses src/wheelhouse)
make build-offline

# x86_64 hosts: set platform override before build
export DOCKER_DEFAULT_PLATFORM=linux/amd64
```

## Architecture

This is a multi-service SOC AI Assistant platform. Services communicate over a Docker network named `observability` (must be created externally with `docker network create observability`).

### Services

| Service | Port | Description |
|---|---|---|
| `orchestrator-api` (`src/orchestrator`) | 18000→8000 | Central FastAPI backend — RAG query pipeline, admin, tools, WebSocket |
| `corpus-service` (`src/corpus_svc`) | 18001→8001 | Document ingestion, chunking, Qdrant indexing |
| `embedding-service` (`src/embedding`) | 18005→8000 | Sentence-transformer embedding endpoint |
| `inference-gateway` (`src/inference-gateway`) | 18002→8002 | OpenAI-compatible LLM proxy with rate limiting, circuit breaking, Redis caching |
| `llm-guard-svc` (`src/llm_guard_svc`) | 18081→8081 | Prompt safety scanning (native ONNX + Presidio/GLiNER) |
| `ui-webapp` (`src/frontend-angular`) | 4200→80 | Angular SPA served via Nginx |
| `postgres-db` | 5532→5432 | Primary relational store |
| `vector-db` (Qdrant) | 6333 | Vector similarity search |
| `redis-cache` | 6379 | Rate limit counters, response caching |

### Shared Module (`src/shared/`)

All Python services import from `src/shared/` (available on `PYTHONPATH` as `shared`). It provides:
- `shared.auth` — JWT auth router and dependency injection
- `shared.config.loader` — Pydantic-based config loaders per service (`load_orchestrator_config()`, `load_inference_gateway_config()`, etc.)
- `shared.logging_utils.fastapi` — Structured JSON logging, request ID middleware
- `shared.db`, `shared.database` — SQLAlchemy session factories
- `shared.telemetry_utils` — OpenTelemetry setup

### Orchestrator Pipeline

The orchestrator uses a **manifest-driven pipeline** (`src/orchestrator/app/orchestrator/`):
- `runner.py` — `Step` protocol; composes steps into a pipeline from a `RequestContext`
- `controller.py` — Entry point; builds context and dispatches to runner
- `intent_parser.py` → `llm_router.py` → `model_selection.py` — Intent-based routing picks the model from `intent_model_defaults` DB table; `ParameterManager` fills defaults when DB values are absent
- `prompt_assembler.py` / `template_engine.py` — Prompt construction from use-case templates
- `streaming_response.py` — SSE streaming back to the client
- `tool_registry.py` / `tool_validator.py` — MCP tool wiring

MCP client integration is in `src/orchestrator/app/mcp/` (stdio and HTTP transports).

### Corpus / RAG Flow

1. Documents uploaded to `corpus-service` → chunked (configurable `CORPUS_CHUNK_SIZE`/`CORPUS_CHUNK_OVERLAP`) → sent to `embedding-service` → stored in Qdrant collection
2. Query arrives at `orchestrator-api` → retrieval from Qdrant via `corpus-service` → injected into prompt → sent through `inference-gateway` to the LLM

### Inference Gateway

An OpenAI-compatible proxy (`/v1/chat/completions`, `/v1/embeddings`, `/v1/responses`) with:
- Per-user/per-provider rate limiting backed by Redis
- Circuit breaker per provider
- Usage logging to Postgres

### Frontend (Angular)

Located at `src/frontend-angular/src/app/`. Uses a feature-based folder structure (`features/`, `pages/`, `core/`, `shared/`). Husky pre-commit hook runs lint, format check, and tests on every commit.

## Configuration

All services share the same `config/env/.env` file (loaded via Docker Compose environment blocks). The key variables are documented in `config/env/env.template`. Run `python ops/validate_configuration.py` to check consistency before starting.

OpenTelemetry export is opt-in via `OTEL_ENABLED=true` / `OTEL_EXPORTER_OTLP_ENDPOINT`.

## Code Conventions

- **Python 3.12**, line length 100 (Black + Ruff). Ruff replaces flake8/isort.
- `src/` code requires full type annotations (`disallow_untyped_defs = True` in mypy). Tests and `ops/` scripts are relaxed.
- FastAPI router files in `src/**/routers/` may have unused `current_user` args (needed for auth); Ruff `ARG001` is suppressed there.
- Pydantic schema validators use `cls` (not `self`); Ruff `N805` is suppressed in `src/**/schemas/`.
