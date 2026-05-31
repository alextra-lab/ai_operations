#!/usr/bin/env bash
# =============================================================================
# db-init entrypoint — runs inside the db-init container
# Applies: schema init → migrations → seeds → intent defaults
# =============================================================================
set -euo pipefail

# run_migrations.sh defaults PSQL to "psql-17"; override to the standard binary
export PSQL=psql

# Validate required environment variables
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set}"
: "${POSTGRES_HOST:?POSTGRES_HOST must be set}"
: "${POSTGRES_USER:?POSTGRES_USER must be set}"
: "${POSTGRES_DB:?POSTGRES_DB must be set}"

# Convenience wrapper
run_psql() {
    PGPASSWORD="$POSTGRES_PASSWORD" psql \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        "$@"
}

# Check if DB was already initialized (schema_migrations table exists)
ALREADY_INIT=$(run_psql -t -A -c \
    "SELECT 1 FROM information_schema.tables WHERE table_name = 'schema_migrations' LIMIT 1" \
    2>/dev/null || true)

if [ "$ALREADY_INIT" = "1" ]; then
    echo "=== db-init: DB already initialized — running migrations only ==="
    cd /ops/database
    ./run_migrations.sh
    echo "=== db-init: Complete (resume) ==="
    exit 0
fi

echo "=== db-init: Phase 1 — Schema init (000_complete_init.sql) ==="
run_psql -v ON_ERROR_STOP=1 -f /ops/database/init/000_complete_init.sql

# Seeds run BEFORE migrations: run_migrations.sh documents "Use after init + seed".
# Several migrations (e.g. 036) insert data that references seeded rows (intent_categories).
echo "=== db-init: Phase 2 — Seeds ==="
while IFS= read -r f; do
    [ -f "$f" ] || continue
    echo "  Seeding: $(basename "$f")"
    run_psql -v ON_ERROR_STOP=1 -f "$f"
done < <(printf '%s\n' /ops/database/seed/0[0-9][0-9]_*.sql | sort)

echo "=== db-init: Phase 3 — Migrations (run_migrations.sh) ==="
cd /ops/database
./run_migrations.sh

echo "=== db-init: Phase 4 — Intent defaults ==="
python /ops/database/seed_intent_defaults_from_env.py

echo "=== db-init: Complete ==="
