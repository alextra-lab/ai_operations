#!/bin/bash
set -e

# Configuration (edit as needed)
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5532}"  # Use 5432 if running inside Docker, 5532 if on host
DB_USER="${DB_USER:-user}"
DB_NAME="${DB_NAME:-aio-test}"
MIGRATIONS_DIR="${MIGRATIONS_DIR:-./scripts/migrations/sql}"

# Prompt for password if not set
export PGPASSWORD="${PGPASSWORD:-password}"

echo "Resetting test database: $DB_NAME on $DB_HOST:$DB_PORT as $DB_USER"
echo "Dropping database (if exists)..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$DB_NAME\";"

echo "Creating database..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE \"$DB_NAME\";"

echo "Applying migrations from $MIGRATIONS_DIR..."
for f in "$MIGRATIONS_DIR"/*.sql; do
    echo "  Running migration: $f"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$f"
done

echo "Test database $DB_NAME is ready and migrated."
