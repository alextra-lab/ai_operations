#!/usr/bin/env bash
# =============================================================================
# Run post-init migrations (ops/database/migrations/*.sql)
# =============================================================================
# Thin wrapper around init_db.py --migrations-only — one implementation for
# host and container; psql is no longer required. Host prerequisite:
#   pip install -r requirements-ops.txt   (provides psycopg)
#
# Usage (unchanged):
#   export $(grep -v '^#' config/env/env.test | xargs)  # or .env
#   ./ops/database/run_migrations.sh
#
# Or with explicit vars:
#   POSTGRES_HOST=localhost POSTGRES_PORT=5432 POSTGRES_USER=... \\
#   POSTGRES_PASSWORD=... POSTGRES_DB=aio ./ops/database/run_migrations.sh
# =============================================================================
set -e
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/init_db.py" --migrations-only
