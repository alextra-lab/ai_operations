# Developer Guide

How to develop and work with the services in the AI Operations Platform on the host.
For first-time platform setup (building images, downloading models, starting the stack)
see **[GETTING_STARTED.md](../../../GETTING_STARTED.md)** — this guide assumes the stack
already builds and runs.

## Host Python environment

The services run inside Docker and bundle their own dependencies. You only need a host
Python environment to run the **ops scripts** (`python ops/...`), the **test suites**, or
to develop service code directly on the host. Use Python **3.12** and an isolated
virtualenv so dependencies never touch your system Python:

```bash
python3.12 -m venv .venv
source .venv/bin/activate

# Lightweight — only the host ops scripts (config validation, etc.)
pip install -r requirements-ops.txt

# Full — everything needed to run the service test suites on the host
pip install -r requirements-all.txt
pip install -e ".[dev]"          # black, ruff, mypy, pre-commit
```

> `requirements-all.txt` pulls the complete ML stack (torch, transformers) and is large.
> Install it only when you run tests or develop service code on the host — not just to run
> the platform.

## Running the stack

Use the `make` targets — they wrap `docker compose` with the correct `--env-file` and
profile overrides. Prefer them over raw `docker compose` commands, which skip both.

```bash
make up            # backend-core (no llm-guard / UI)
make up-full       # full stack incl. llm-guard-svc + ui-webapp
make status        # running containers + ports
make logs SVC=orchestrator-api   # tail one service
make restart       # stop + start
make down          # stop

# Rebuild a single service after code changes
docker compose --env-file config/env/.env -f deploy/docker-compose.yml build orchestrator-api
```

See [GETTING_STARTED.md](../../../GETTING_STARTED.md) for the full build → models → up flow
and health checks.

## Project layout

```
src/
  orchestrator/        # Central FastAPI backend — RAG pipeline, admin, tools, WebSocket
  corpus_svc/          # Document ingestion, chunking, Qdrant indexing
  embedding/           # Sentence-transformer embedding endpoint
  inference-gateway/   # OpenAI-compatible LLM proxy (rate limit, circuit breaker, cache)
  llm_guard_svc/       # Prompt safety scanning (ONNX + Presidio/GLiNER)
  frontend-angular/    # Angular SPA served via Nginx
  shared/              # Shared Python module (auth, config, db, logging, telemetry)
```

All Python services import from `src/shared/` (on `PYTHONPATH` as `shared`).

## Import style

- Within a service package (e.g. `src/orchestrator/app/...`), prefer package-relative
  imports (`from ..utils import helper`).
- Use repository-level absolute imports only when intentionally crossing service boundaries
  (e.g. referencing modules in `src/shared`).
- This keeps modules resilient to repository layout changes and aligns with existing code
  organization.

## Configuration

The project uses a centralized configuration system. After editing `config/env/.env`,
validate it (with the host venv active):

```bash
python ops/validate_configuration.py
```

Common variables (see `config/env/env.template` for the full set):

| Variable | Description | Default |
|----------|-------------|---------|
| `ENV` | Environment (development/production) | `development` |
| `JWT_SECRET` | Secret key for JWT | **Required** (32+ chars) |
| `DEBUG` | Debug mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `FRONTEND_VERBOSE_LOGGING` | Verbose UI request logging | `false` |

Configuration files:

- `config/env/env.template` — environment variable template
- `config/env/.env` — your local environment (not committed)
- `src/shared/config/` — centralized configuration schemas
- `CONFIG_SCHEMA_VERSION` marks schema revisions; `validate_configuration.py` verifies that
  your local files and `.env` match the current version before starting services.

## Database migrations & seeding

Schema and seed data live in `ops/database/`. See
[ops/database/README.md](../../../ops/database/README.md) for the authoritative commands.
The variables below come from `config/env/.env`.

Apply a migration against a locally running Postgres:

```bash
# Start only Postgres (make up starts the whole stack)
docker compose --env-file config/env/.env -f deploy/docker-compose.yml up -d postgres-db
PGPASSWORD=$POSTGRES_PASSWORD psql \
  -h ${POSTGRES_HOST:-localhost} \
  -p ${POSTGRES_PORT:-5532} \
  -U $POSTGRES_USER \
  -d $POSTGRES_DB \
  -f ops/migrations/sql/001_phase1_foundation.sql
```

Init + seed from the project root:

```bash
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB \
  -f ops/database/init/000_complete_init.sql
for f in ops/database/seed/*.sql; do
  PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -f "$f"
done
```

Validate roles & row-level security:

```bash
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB <<'SQL'
SET SESSION aio.user_id = (SELECT id FROM users WHERE username = 'admin');
SET SESSION aio.user_roles = '{admin,developer}';
SELECT use_case_id, name FROM use_cases;
SQL
```

## Dependency management

See the [Dependency Management Guide](Dependency_Management.md) for current versions,
upgrade procedures, and container rebuild processes.

### Node.js (frontend)

- **Supported:** Node.js 20 LTS or newer (see `engines` in
  `src/frontend-angular/package.json`). Production and Docker builds use **Node 24 LTS**
  (`node:24-alpine`). Local development may use the "Current" line (e.g. Node 25.x);
  odd-numbered releases are not LTS and show an informational warning during build — expected
  and safe to ignore for local dev.
- **baseline-browser-mapping:** If the Angular build reports baseline data is outdated, update
  with `npm i baseline-browser-mapping@latest -D` in `src/frontend-angular` (add
  `--legacy-peer-deps` if install reports peer dependency conflicts).

## Temporary scripts

- Place one-off or cleanup scripts in `temp_ops/` only; never commit them to the project root.
- Name scripts descriptively, e.g. `feature_fix_imports.py`, so purpose is obvious.
- Include a module docstring describing goals, inputs/outputs, source-file changes, and side
  effects.
- Delete temporary scripts once their task is complete, documenting any permanent
  modifications they made.

## Troubleshooting

1. **Service fails to start** — check `make logs SVC=[service]`; verify dependencies
   (PostgreSQL, Qdrant) are running; ensure required `data/` directories exist.
2. **Changes not reflected** — rebuild and restart the affected service.
3. **Can't connect to a service** — verify it's running (`make status`), check the host port
   mapping, and ensure no port conflicts with other applications.
4. **`No module named '...'` from an ops script** — the host venv isn't active or
   `requirements-ops.txt` / `requirements-all.txt` isn't installed (see *Host Python
   environment* above).

For the full list of bootstrap failure modes, see
[bootstrap-troubleshooting.md](../guides/bootstrap-troubleshooting.md).
