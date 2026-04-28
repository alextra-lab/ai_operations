#!/bin/bash
# RBAC V2 Migration Runner
# Usage: ./run_migrations.sh [test|production]
#
# This script applies RBAC V2 database migrations in order.
# For test environment, it uses Docker container connection.
# For production, it uses direct PostgreSQL connection.

set -e  # Exit on error

ENVIRONMENT=${1:-test}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Determine connection method based on environment
if [ "$ENVIRONMENT" == "test" ]; then
    # Test environment: Use Docker container
    DB_CONTAINER=${POSTGRES_CONTAINER:-postgres-test}
    DB_NAME=${POSTGRES_DB:-aio-test}
    DB_USER=${POSTGRES_USER:-testuser}

    # Check if container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
        echo "❌ Error: Docker container '${DB_CONTAINER}' is not running"
        echo "   Start it with: docker-compose -f deploy/docker-compose.test.yml up -d postgres-db"
        exit 1
    fi

    echo "=========================================="
    echo "RBAC V2 Database Migration"
    echo "Environment: $ENVIRONMENT"
    echo "Container: $DB_CONTAINER"
    echo "Database: $DB_NAME"
    echo "=========================================="

    # For test environment, skip backup (data is ephemeral)
    echo "ℹ️  Test environment - skipping backup (data is ephemeral)"

    # Run migrations in order using Docker exec
    echo ""
    echo "Running migrations..."

    for migration_file in 001_*.sql 002_*.sql 003_*.sql; do
        migration_path="${SCRIPT_DIR}/${migration_file}"
        if [ -f "$migration_path" ]; then
            echo "Applying: $migration_file"
            docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" < "$migration_path"
            if [ $? -eq 0 ]; then
                echo "✅ $migration_file completed"
            else
                echo "❌ $migration_file failed"
                exit 1
            fi
        else
            echo "⚠️  Warning: Migration file not found: $migration_path"
        fi
    done

elif [ "$ENVIRONMENT" == "production" ]; then
    # Production environment: Use direct PostgreSQL connection
    DB_NAME=${POSTGRES_DB:-aio}
    DB_USER=${POSTGRES_USER:-postgres}
    DB_HOST=${POSTGRES_HOST:-localhost}
    DB_PORT=${POSTGRES_PORT:-5432}

    echo "=========================================="
    echo "RBAC V2 Database Migration"
    echo "Environment: $ENVIRONMENT"
    echo "Database: $DB_NAME @ $DB_HOST:$DB_PORT"
    echo "=========================================="

    # Production safety check
    read -p "⚠️  Are you sure you want to run migrations on PRODUCTION? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Migration cancelled."
        exit 0
    fi

    # Backup database before migration
    echo ""
    echo "Creating backup..."
    BACKUP_FILE="${SCRIPT_DIR}/backup_rbac_v2_$(date +%Y%m%d_%H%M%S).sql"

    # Check if pg_dump is available
    if command -v pg_dump &> /dev/null; then
        export PGPASSWORD="${POSTGRES_PASSWORD:-}"
        pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > "$BACKUP_FILE"
        echo "✅ Backup created: $BACKUP_FILE"
    else
        echo "⚠️  Warning: pg_dump not found. Skipping backup."
        echo "   Please create a manual backup before proceeding."
        read -p "Continue without backup? (yes/no): " continue_confirm
        if [ "$continue_confirm" != "yes" ]; then
            echo "Migration cancelled."
            exit 0
        fi
    fi

    # Run migrations in order
    echo ""
    echo "Running migrations..."

    export PGPASSWORD="${POSTGRES_PASSWORD:-}"
    for migration_file in 001_*.sql 002_*.sql 003_*.sql; do
        migration_path="${SCRIPT_DIR}/${migration_file}"
        if [ -f "$migration_path" ]; then
            echo "Applying: $migration_file"
            psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$migration_path"
            if [ $? -eq 0 ]; then
                echo "✅ $migration_file completed"
            else
                echo "❌ $migration_file failed"
                echo "   Backup available at: $BACKUP_FILE"
                exit 1
            fi
        else
            echo "⚠️  Warning: Migration file not found: $migration_path"
        fi
    done

    if [ -f "$BACKUP_FILE" ]; then
        echo ""
        echo "Backup file: $BACKUP_FILE"
        echo "Keep this backup until Phase 5 is complete."
    fi

else
    echo "❌ Error: Invalid environment '$ENVIRONMENT'"
    echo "   Usage: ./run_migrations.sh [test|production]"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ All migrations completed successfully"
echo "=========================================="
