# Backend Security Guardrails (Phase 1)

## Overview

Phase 1 introduces hardened middleware for the FastAPI orchestrator service to
meet SOC audit requirements and enterprise security baselines.

- Request IDs are generated or propagated for every request.
- Request bodies are sanitized through LLM Guard when appropriate.
- Audit events persist to PostgreSQL and emit structured JSON logs.
- Security headers enforce HSTS, CSP, referrer policy, and related protections.

## Middleware Stack

The `create_app` factory registers middleware in the following order:

1. `RequestIDLoggerMiddleware`
2. `sanitize_request`
3. `audit_middleware`
4. `security_headers_middleware`

This ordering ensures audit persistence captures the sanitized request and that
security headers are attached even when downstream endpoints raise exceptions.

## Audit Persistence

`audit_middleware` now records each request to the `audit_logs` table while logging
request metadata. Entries include:

- `actor_user_id` and `actor_roles` derived from JWT payloads
- Request method, path, status code, and duration (ms)
- Request ID correlation
- Client IP and user agent strings
- JSON details capturing query parameters and response status

Failures to persist audits are logged but do not block responses, preserving
availability guarantees.

## Security Headers

`security_headers_middleware` applies default headers when not already set by the
response:

```
Strict-Transport-Security: max-age=63072000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
X-XSS-Protection: 1; mode=block
Permissions-Policy: geolocation=(), microphone=(), camera=()
Content-Security-Policy: default-src 'self'
```

These headers should be reviewed with the security team for production ingress
configurations.

## Operations Checklist

1. Verify migrations applied: `ops/migrations/sql/001_phase1_foundation.sql`
2. Run backend unit tests: `bash src/orchestrator/run_tests.sh --cov=app --cov-report=term-missing`
3. Exercise login flow to confirm audit rows insert successfully.
4. Ensure log aggregation captures `audit_middleware` structured logs.
5. Confirm browser clients receive expected security headers via `curl -I`.
6. Install frontend dependencies (including `python-jose`) with `pip install -r src/frontend/requirements.txt` before running the Streamlit UI.

## Future Enhancements

- Integrate metrics exporter for middleware timings.
- Add optional Prometheus counter for audit persistence outcomes.
- Provide administrative UI for querying audit records.
# Developer Guide

This guide explains how to develop and work with the services in AI Operations Platform, using either the VSCode devcontainer setup or the standalone script.

## Development Approaches

There are two main approaches for developing the services:

1. **VSCode Devcontainer (Recommended)**: Integrated development environment with all services
2. **Standalone Script**: Alternative for non-VSCode workflows or isolated testing

## VSCode Devcontainer Workflow

### Setup

1. Open the project in VSCode
2. When prompted, click "Reopen in Container"
3. VSCode will build and start all services

### Development

- Edit code in the `/src` directory
- Changes are automatically reflected in the running containers
- Access services at their respective ports (e.g., `http://localhost:8000/docs` for the backend)
- View logs in the Docker extension or terminal

### Debugging

1. Set breakpoints directly in VSCode
2. Use the Python debugger to attach to running processes
3. View console output in the terminal

### Common Tasks

- **Restart a service**: Use Docker extension or run `docker compose restart [service-name]`
- **View logs**: Use Docker extension or run `docker compose logs -f [service-name]`
- **Run tests**: Execute in the devcontainer terminal
- **Validate configuration**: Run `python ops/validate_configuration.py`
- **Update environment**: Edit `config/env/.env` and reload with `export $(grep -v '^#' config/env/.env | xargs)`
- **Manage dependencies**: See [Dependency Management Guide](Dependency_Management.md) for upgrade procedures

## Dependency Management

The project uses a phased approach to dependency upgrades to ensure system stability. For detailed information about:

- Current dependency versions
- Upgrade procedures and phases
- Troubleshooting common issues
- Container rebuild processes

See the [Dependency Management Guide](Dependency_Management.md).

### Node.js (frontend)

- **Supported:** Node.js 20 LTS or newer (see `engines` in `src/frontend-angular/package.json`). Production and Docker builds use **Node 24 LTS** (`node:24-alpine`). Local development may use the "Current" line (e.g. Node 25.x); odd-numbered releases are not LTS and will show an informational warning during build—this is expected and safe to ignore for local dev.
- **baseline-browser-mapping:** If the Angular build reports that baseline data is outdated, update with `npm i baseline-browser-mapping@latest -D` in `src/frontend-angular` (use `--legacy-peer-deps` if install reports peer dependency conflicts).

### Quick Reference

```bash
# Check current package versions
pip list | grep -E "(bcrypt|cryptography|python-jose|datasets|spacy|mypy|pytest|black|ruff|pdfplumber|PyPDF2|beautifulsoup4|lxml|psycopg|qdrant-client)"

# Verify container health after upgrades
docker-compose -f deploy/docker-compose.yml ps

# Export environment variables for container operations
export $(grep -v '^#' config/env/.env | xargs)
```

## Standalone Script Workflow

Use this approach if you:

- Don't use VSCode
- Want to test services independently
- Need to run in an environment without devcontainers

### Setup and Usage

1. Ensure Docker and Docker Compose are installed
2. Run the script:

   ```bash
   bash ops/operations/run_rag_services.sh
   ```

3. The script will:
   - Create necessary directories
   - Build the services
   - Start the services
   - Verify they're running properly

### Development

- Edit code in the `/src` directory
- Rebuild and restart services:

  ```bash
  docker compose -f deploy/docker-compose.yml build [service-name]
  docker compose -f deploy/docker-compose.yml up -d
  ```

### Stopping Services

```bash
docker compose -f deploy/docker-compose.yml down
```

## Directory Structure

```
/src
  /backend              # Backend Service
  /embedding            # Embedding Service
  /frontend             # Frontend Service
  /ingestion            # Ingestion Service
  /llm_guard_svc        # LLM Guard Service
  /retrieval            # Retrieval Service
  /shared               # Shared utilities
```

## Temporary Scripts

- Place one-off or cleanup scripts in `temp_ops/` only; never commit them to the project root.
- Name scripts descriptively, e.g. `feature_fix_imports.py`, so purpose is obvious.
- Include a module docstring describing goals, inputs/outputs, source-file changes, and side effects.
- Delete temporary scripts once their task is complete, documenting any permanent modifications they made.

## Import Style

- Within a service package (e.g. `src/orchestrator/app/...`), prefer package-relative imports (`from ..utils import helper`).
- Use repository-level absolute imports only when intentionally crossing service boundaries (e.g. referencing modules in `src/shared`).
- This keeps modules resilient to repository layout changes and aligns with existing code organization.

## Configuration

### Environment Variables

All services support these common variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `ENV` | Environment (development/production) | `development` |
| `JWT_SECRET` | Secret key for JWT | **Required** (32+ chars) |
| `DEBUG` | Debug mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `FRONTEND_VERBOSE_LOGGING` | Verbose UI request logging | `false` |

### Configuration Management

The project uses a **centralized configuration management system**:

```bash
# Validate configuration consistency
python ops/validate_configuration.py

# Load environment variables
export $(grep -v '^#' config/env/.env | xargs)
```

**Configuration files:**

- `config/env/env.template` - Environment variable template
- `config/env/.env` - Your local environment variables (not committed)
- `src/shared/config/` - Centralized configuration schemas
- `CONFIG_SCHEMA_VERSION` marks schema revisions; run `python ops/validate_configuration.py`
  to verify local files and `.env` copies match the current version before starting services.

## Database Migrations & Seeding (Phase 1)

### Environment Setup

```bash
export $(grep -v '^#' config/env/.env | xargs)
```

### Apply SQL migrations locally

```bash
docker compose -f deploy/docker-compose.yml up -d postgres-db
PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
  -h ${POSTGRES_HOST:-localhost} \
  -p ${POSTGRES_PORT:-5532} \
  -U $POSTGRES_USER \
  -d $POSTGRES_DB \
  -f ops/migrations/sql/001_phase1_foundation.sql
```

### Run migrations and seed (SQL)

Database schema and seed data are in `ops/database/`. Apply init, then migrations, then seed SQL via psql. See [ops/database/README.md](../../ops/database/README.md) for exact commands.

```bash
# Example: init + seed (from project root with env loaded)
PGPASSWORD=$POSTGRES_PASSWORD psql-17 -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB \
  -f ops/database/init/000_complete_init.sql
for f in ops/database/seed/*.sql; do
  PGPASSWORD=$POSTGRES_PASSWORD psql-17 -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -f "$f"
done
```

### Validate roles & RLS

```bash
PGPASSWORD=$POSTGRES_PASSWORD psql-17 -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB <<'SQL'
SET SESSION aio.user_id = (SELECT id FROM users WHERE username = 'admin');
SET SESSION aio.user_roles = '{admin,developer}';
SELECT use_case_id, name FROM use_cases;
SQL
```

## Troubleshooting

### Common Issues

1. **Service fails to start**
   - Check logs: `docker compose logs [service-name]`
   - Verify dependencies are running (PostgreSQL, Qdrant)
   - Ensure required directories exist

2. **Changes not reflected**
   - In devcontainer: Restart the service
   - With script: Rebuild and restart the service

3. **Can't connect to service**
   - Verify the service is running
   - Check if port is correctly forwarded (especially in devcontainer)
   - Ensure no port conflicts with other applications

### Getting Help

- Check the service logs for detailed error messages
- Refer to the README.md in each service directory
- Review the error handling in the FastAPI application
