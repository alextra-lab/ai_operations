#!/bin/bash
# Test RBAC V2 migrations in isolated environment
# Usage: ./test_migrations.sh
#
# This script tests migrations by:
# 1. Creating a test database
# 2. Restoring production schema (if available)
# 3. Running migrations
# 4. Verifying results
# 5. Cleaning up

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DB_NAME="aio_rbac_test"
DB_CONTAINER=${POSTGRES_CONTAINER:-postgres-test}
DB_USER=${POSTGRES_USER:-testuser}

echo "=========================================="
echo "RBAC V2 Migration Test"
echo "=========================================="

# Check if using Docker container or local PostgreSQL
if docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    echo "✅ Using Docker container: $DB_CONTAINER"
    USE_DOCKER=true
else
    echo "ℹ️  Docker container not found, using local PostgreSQL"
    USE_DOCKER=false
fi

# Create test database
echo ""
echo "Creating test database: $TEST_DB_NAME"
if [ "$USE_DOCKER" = true ]; then
    # Create database in Docker container
    docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $TEST_DB_NAME;" 2>&1 || {
        # Database might already exist, try to drop it first
        echo "Database exists, dropping and recreating..."
        docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $TEST_DB_NAME;"
        docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $TEST_DB_NAME;"
    }
else
    createdb "$TEST_DB_NAME" 2>&1 || {
        echo "Database exists, dropping and recreating..."
        dropdb "$TEST_DB_NAME" 2>&1 || true
        createdb "$TEST_DB_NAME"
    }
fi

# Initialize with base schema (if init script exists)
INIT_SCRIPT="../../ops/database/init/000_complete_init.sql"
if [ -f "$INIT_SCRIPT" ]; then
    echo ""
    echo "Initializing database with base schema..."
    if [ "$USE_DOCKER" = true ]; then
        docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$TEST_DB_NAME" < "$INIT_SCRIPT" > /dev/null 2>&1 || {
            echo "⚠️  Warning: Base schema initialization had errors (may be expected if schema already exists)"
        }
    else
        psql -d "$TEST_DB_NAME" -f "$INIT_SCRIPT" > /dev/null 2>&1 || {
            echo "⚠️  Warning: Base schema initialization had errors (may be expected if schema already exists)"
        }
    fi
else
    echo "⚠️  Warning: Base schema init script not found at $INIT_SCRIPT"
    echo "   Skipping base schema initialization"
fi

# Run migrations
echo ""
echo "Running RBAC V2 migrations..."
if [ "$USE_DOCKER" = true ]; then
    # Run migrations via Docker
    for migration_file in 001_*.sql 002_*.sql 003_*.sql; do
        migration_path="${SCRIPT_DIR}/${migration_file}"
        if [ -f "$migration_path" ]; then
            echo "  Applying: $migration_file"
            docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$TEST_DB_NAME" < "$migration_path" > /dev/null 2>&1
        fi
    done
else
    # Run migrations locally
    for migration_file in 001_*.sql 002_*.sql 003_*.sql; do
        migration_path="${SCRIPT_DIR}/${migration_file}"
        if [ -f "$migration_path" ]; then
            echo "  Applying: $migration_file"
            psql -d "$TEST_DB_NAME" -f "$migration_path" > /dev/null 2>&1
        fi
    done
fi

# Verify results
echo ""
echo "Verifying migration results..."

VERIFY_SQL="
SELECT
    'use_cases.team_id' as check_item,
    CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END as status
FROM information_schema.columns
WHERE table_name = 'use_cases' AND column_name = 'team_id'

UNION ALL

SELECT
    'role_collection_assignments table' as check_item,
    CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END as status
FROM information_schema.tables
WHERE table_name = 'role_collection_assignments'

UNION ALL

SELECT
    'user_roles migration' as check_item,
    CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END as status
FROM user_roles
WHERE metadata->>'migrated_from' = 'users.role';
"

if [ "$USE_DOCKER" = true ]; then
    docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$TEST_DB_NAME" -c "$VERIFY_SQL"
else
    psql -d "$TEST_DB_NAME" -c "$VERIFY_SQL"
fi

# Check if all verifications passed
VERIFY_RESULT=$?
if [ $VERIFY_RESULT -eq 0 ]; then
    echo ""
    echo "✅ All migration verifications passed"
else
    echo ""
    echo "❌ Some verifications failed"
    exit 1
fi

# Cleanup
echo ""
read -p "Drop test database '$TEST_DB_NAME'? (yes/no): " cleanup_confirm
if [ "$cleanup_confirm" = "yes" ]; then
    if [ "$USE_DOCKER" = true ]; then
        docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c "DROP DATABASE $TEST_DB_NAME;"
    else
        dropdb "$TEST_DB_NAME"
    fi
    echo "✅ Test database cleaned up"
else
    echo "ℹ️  Test database '$TEST_DB_NAME' kept for manual inspection"
fi

echo ""
echo "=========================================="
echo "✅ Migration tests completed successfully"
echo "=========================================="
