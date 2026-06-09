# AI Operations Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A security-first platform for building governed AI Operations — discrete, auditable
LLM execution units with validated inputs, scanned outputs, and structured results.
AI Operations are created via a wizard and can be deployed by any enterprise team
(security, IT, compliance, legal, HR, and more). Backend is FastAPI + PostgreSQL +
Qdrant; frontend is Angular.

> **Status: Beta — not production-ready.** This platform has not yet been deployed to or
> validated in a production environment. APIs, schemas, and defaults may change. It is
> intended for local evaluation use (local profile) at this stage.

- **Source:** https://github.com/alextra-lab/ai_operations
- **Getting started (local):** [GETTING_STARTED.md](GETTING_STARTED.md)
- **Getting started (enterprise):** [ENTERPRISE_GETTING_STARTED.md](ENTERPRISE_GETTING_STARTED.md)
- **License:** [MIT](LICENSE)
- **Security policy:** [SECURITY.md](SECURITY.md)
- **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md)
- **Changelog:** [CHANGELOG.md](CHANGELOG.md)

## Recent Updates

### ✅ Phase E-I Dependency Upgrades Completed

All major dependencies have been successfully upgraded to their latest stable versions:

- **Security**: bcrypt 4.3.0, cryptography 44.0.3, python-jose 3.5.0
- **ML**: datasets 3.6.0, spacy 3.7.5 (transformers version split maintained for llm_guard_svc gliner compatibility)
- **Development**: mypy 1.15.0, pytest 8.4.0, black 25.1.0, ruff 0.11.12
- **Document Processing**: pdfplumber 0.11.x, PyPDF2 3.0.x, beautifulsoup4 4.13.3, lxml 5.4.0
- **Database**: psycopg 3.2.10, qdrant-client 1.14.2

See [Dependency Management Guide](docs/development/guidelines/Dependency_Management.md) for details.

## Quick Start

### Prerequisites

- Docker (with the Compose v2 plugin) or Docker Desktop.
- Python **3.12** for running validation scripts on the host.
- Node **24** if you plan to develop the Angular frontend on the host.
- An external Docker network named `observability` (the compose file expects it).
  `make setup` (Step 1) creates it for you; to create it manually:

  ```bash
  docker network create observability
  ```

- The compose file defaults to `platform: linux/arm64` (Apple Silicon).
  On x86_64 / amd64 hosts, override per service with the
  `DOCKER_DEFAULT_PLATFORM` env var:

  ```bash
  export DOCKER_DEFAULT_PLATFORM=linux/amd64
  ```

  or edit `deploy/docker-compose.yml` and change `platform:` lines as needed.

### Steps

> Condensed flow. For the full local walkthrough — including health checks and
> troubleshooting — see **[GETTING_STARTED.md](GETTING_STARTED.md)**.

1. **One-time setup** — creates the `observability` network, the `data/` directory
   tree, and `config/env/.env` from the template:

   ```bash
   make setup
   ```

2. **Edit secrets** in `config/env/.env` — set `POSTGRES_PASSWORD`, `JWT_SECRET`, and
   `TOOL_SECRETS_KEY`. Generate values with:

   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

3. **Set up the host Python environment and validate the config.** Use Python 3.12 and
   an isolated virtualenv so dependencies stay off your system Python:

   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements-ops.txt
   python ops/validate_configuration.py
   ```

4. **Build, fetch models, and start the stack:**

   ```bash
   make build         # build service images
   make models        # download embedding + llm-guard models into data/
   make up            # start backend-core; or `make up-full` for llm-guard + UI
   ```

   `make up` wraps `docker compose` with the correct `--env-file` and local override —
   prefer it over a raw `docker compose up`, which skips both.

## Developer setup (host)

Running the test suites, linters, or `python ops/...` scripts **on the host** (rather than
inside the containers) needs the Python dependencies installed in a virtualenv. Use Python
**3.12** and keep dependencies off your system Python:

```bash
python3.12 -m venv .venv
source .venv/bin/activate

# Lightweight — only the host ops scripts (config validation, etc.)
pip install -r requirements-ops.txt

# Full — everything needed to run the service test suites on the host
pip install -r requirements-all.txt
pip install -e ".[dev]"          # black, ruff, mypy, pre-commit
```

> The full install pulls the complete ML stack (torch, transformers) and is large. You do
> **not** need it just to run the platform — each service ships its own dependencies inside
> Docker (see [GETTING_STARTED.md](GETTING_STARTED.md)). Install `requirements-all.txt` only
> when you intend to run tests or develop service code directly on the host.

## Pre-commit hooks

Pre-commit checks are integrated in two places:

### 1. Frontend (Angular) — Husky

Already integrated in `src/frontend-angular/`. The hook runs **lint**, **format:check**, and **tests** on commit. It is installed when you install frontend dependencies:

```bash
cd src/frontend-angular
npm install
```

The `prepare` script runs `husky`, which configures Git to use `.husky` in that directory. Hook script: [src/frontend-angular/.husky/pre-commit](src/frontend-angular/.husky/pre-commit).

### 2. Repo-wide (Python) — pre-commit

Ruff (lint), Black (format), and mypy (type check) run on commit once installed:

```bash
pip install pre-commit   # or: pip install -e ".[dev]"
pre-commit install
```

Run manually: `pre-commit run --all-files`. Config: [.pre-commit-config.yaml](.pre-commit-config.yaml).

## Testing

### Running Tests

The project provides multiple ways to run tests:

#### Centralized Test Runner (Recommended)

```bash
# Run all tests
python ops/testing/run_all_tests.py

# Run specific component
python ops/testing/run_all_tests.py --component orchestrator

# Run with coverage
python ops/testing/run_all_tests.py --coverage --html-report
```

#### Service-Specific Test Runners

```bash
# Orchestrator tests
bash src/orchestrator/run_tests.sh --cov=app --cov-report=term-missing

# Corpus service tests
bash src/corpus_svc/run_tests.sh --cov=app --cov-report=term-missing

# Shared module tests
bash src/shared/run_tests.sh --cov=shared/auth --cov-report=term-missing
```

#### Integration and E2E Tests

```bash
# Integration tests
pytest tests/integration/

# End-to-end tests
pytest tests/e2e/
```

### Test Documentation

- [Testing Guide](docs/testing/TESTING_GUIDE.md) - Comprehensive testing practices
- [Troubleshooting Guide](docs/testing/TROUBLESHOOTING.md) - Common issues and solutions
- [Script Index](docs/testing/SCRIPT_INDEX.md) - All script references

## Configuration Management

This project uses a **centralized configuration management system** that provides:

- ✅ **Unified configuration schemas** for all services
- ✅ **Environment variable validation** and consistency checking
- ✅ **Secure defaults** and configuration templates
- ✅ **Automated validation** to prevent configuration drift

### Key Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JWT_SECRET` | Secret key for JWT authentication | **Required** |
| `POSTGRES_USER` | Database username | `user` |
| `POSTGRES_PASSWORD` | Database password | `password` |
| `POSTGRES_DB` | Database name | `aio` |
| `POSTGRES_HOST` | Database host | `postgres-db` (Docker) / `localhost` (Host) |
| `POSTGRES_PORT` | Database port | `5432` (Docker) / `5532` (Host) |
| `QDRANT_HOST` | Vector database host | `vector-db` |
| `QDRANT_PORT` | Vector database port | `6333` |

### Configuration Validation

Run the configuration validation script to ensure consistency:

```bash
# Validate current configuration
python ops/validate_configuration.py

# Expected output: "🎉 Configuration is consistent and secure!"
```

### Environment Setup

The `make` targets load `config/env/.env` for you via `--env-file`, so you don't need to
export anything manually:

```bash
make up          # start backend-core services
make up-full     # full stack incl. llm-guard + UI
```

**For host development** (running a service directly on the host rather than in Docker), point
it at the host-published Postgres port in `config/env/.env`:

```bash
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5532
```

## Documentation

- **[Developer Guide](docs/development/guidelines/Developer_Guide.md)** - Development setup and workflows
- **[Architecture Documentation](docs/architecture/)** - System architecture and design patterns

## Security Notes

- **Never commit `.env` files** to version control
- **Use strong JWT secrets** (minimum 32 characters)
- **Secure database passwords** in production
- **Run configuration validation** regularly
