#!/bin/bash

# Initialize test database if needed
# This script checks if the test database exists and is properly initialized

set -e

echo "🔍 Checking test database initialization..."

# Set test database configuration for containerized PostgreSQL
export POSTGRES_USER=testuser
export POSTGRES_PASSWORD=test_password_123
export POSTGRES_DB=aio-test
export POSTGRES_HOST=localhost  # For external access to container
export POSTGRES_PORT=5433       # External port mapping

# Check if PostgreSQL container is running
check_postgres_container() {
    if ! docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "postgres-test.*healthy"; then
        echo "❌ PostgreSQL container is not running or not healthy"
        echo "💡 Please start the test services first:"
        echo "   ./ops/testing/start_test_services.sh"
        return 1
    fi
    echo "✅ PostgreSQL container is running and healthy"
    return 0
}

# Wait for containerized PostgreSQL to be ready
wait_for_postgres() {
    echo "⏳ Waiting for containerized PostgreSQL to be ready..."
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker exec postgres-test pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB} >/dev/null 2>&1; then
            echo "✅ Containerized PostgreSQL is ready"
            return 0
        fi
        echo "Attempt $attempt/$max_attempts - waiting for PostgreSQL..."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo "❌ PostgreSQL container is not ready after $max_attempts attempts"
    return 1
}

# Check if database exists and has required tables in containerized PostgreSQL
check_database_initialized() {
    # Check if required tables exist
    local table_count=$(docker exec postgres-test psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='users'" 2>/dev/null || echo "0")

    if [ "$table_count" != "1" ]; then
        echo "❌ Database ${POSTGRES_DB} exists but is not properly initialized"
        return 1
    fi

    echo "✅ Database ${POSTGRES_DB} is properly initialized"
    return 0
}

# Initialize database if needed
initialize_database() {
    echo "🏗️  Initializing test database in containerized PostgreSQL..."

    # The testuser is already created by the Docker container
    echo "👤 Using existing testuser role..."

    # Grant permissions
    docker exec postgres-test psql -U ${POSTGRES_USER} -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB} TO ${POSTGRES_USER};" 2>/dev/null || echo "Permissions already granted"
    docker exec postgres-test psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "GRANT ALL PRIVILEGES ON SCHEMA public TO ${POSTGRES_USER};" 2>/dev/null || echo "Schema permissions already granted"

    # Run migrations in containerized PostgreSQL
    echo "📋 Running database migrations..."
    docker exec postgres-test psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -f /dev/stdin << 'EOF'
-- Create schema_migrations table if it doesn't exist
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    checksum VARCHAR(32) NOT NULL
);
EOF

    # Run post-init migrations (027..038; required for Use Case Authoring / config API)
    echo "📋 Running application migrations..."
    POSTGRES_HOST=localhost POSTGRES_PORT=5433 POSTGRES_USER=${POSTGRES_USER} POSTGRES_PASSWORD=${POSTGRES_PASSWORD} POSTGRES_DB=${POSTGRES_DB} ./ops/database/run_migrations.sh 2>/dev/null || \
    echo "   (Run: POSTGRES_HOST=localhost POSTGRES_PORT=5433 ./ops/database/run_migrations.sh)"

    # Seed database (SQL in ops/database/seed/ or Python seed scripts if present)
    echo "🌱 Seeding database with test data..."
    POSTGRES_HOST=localhost POSTGRES_PORT=5433 python ops/bootstrap/seed_users.py 2>/dev/null || true
    POSTGRES_HOST=localhost POSTGRES_PORT=5433 python ops/bootstrap/seed_templates.py 2>/dev/null || \
    echo "   Apply ops/database/seed/*.sql manually if Python seed scripts are not used"

    echo "✅ Database initialization complete"
}

# Main logic
# First check if PostgreSQL container is running
if ! check_postgres_container; then
    exit 1
fi

# Then wait for PostgreSQL to be ready
if ! wait_for_postgres; then
    echo "❌ Cannot proceed - PostgreSQL container is not ready"
    exit 1
fi

# Then check if database needs initialization
if ! check_database_initialized; then
    echo "🔄 Database needs initialization"
    initialize_database
else
    echo "✅ Database is already initialized, skipping"
fi
