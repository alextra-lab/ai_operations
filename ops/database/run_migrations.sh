#!/usr/bin/env bash
# =============================================================================
# Run post-init migrations (ops/database/migrations/*.sql)
# =============================================================================
# Use after init + seed. Applies 027..038 (and any future migrations) in order.
# Required for Use Case Authoring: 036 (intent capability profiles), etc.
#
# Usage:
#   export $(grep -v '^#' config/env/env.test | xargs)  # or .env
#   ./ops/database/run_migrations.sh
#
# Or with explicit vars:
#   POSTGRES_HOST=localhost POSTGRES_PORT=5432 POSTGRES_USER=... \\
#   POSTGRES_PASSWORD=... POSTGRES_DB=aio ./ops/database/run_migrations.sh
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATIONS_DIR="${SCRIPT_DIR}/migrations"
PSQL="${PSQL:-psql-17}"

# Defaults (override with env)
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-aio}"

if [ -z "${POSTGRES_PASSWORD:-}" ]; then
  echo "Warning: POSTGRES_PASSWORD not set. Connection may fail."
fi

run_psql() {
  PGPASSWORD="$POSTGRES_PASSWORD" "$PSQL" -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$@"
}

echo "Migrations directory: $MIGRATIONS_DIR"
echo "Database: $POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB"
echo ""

# Ensure schema_migrations exists (name-based so we can have 033_a, 033_b, etc.)
run_psql -v ON_ERROR_STOP=1 -c "
CREATE TABLE IF NOT EXISTS schema_migrations (
  name VARCHAR(255) PRIMARY KEY,
  applied_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);
"

# Apply each .sql file in migrations/ (excluding subdirs like rbac_v2) in sorted order
applied=0
for f in $(find "$MIGRATIONS_DIR" -maxdepth 1 -name '*.sql' | sort); do
  name="$(basename "$f")"
  if run_psql -v ON_ERROR_STOP=1 -t -A -c "SELECT 1 FROM schema_migrations WHERE name = '$name' LIMIT 1;" | grep -q 1; then
    echo "Skip (already applied): $name"
  else
    echo "Applying: $name"
    run_psql -v ON_ERROR_STOP=1 -f "$f" && run_psql -v ON_ERROR_STOP=1 -c "INSERT INTO schema_migrations (name) VALUES ('$name');"
    ((applied++)) || true
  fi
done

echo ""
echo "Done. Applied $applied new migration(s)."
