#!/bin/bash

# Reset test database to clean state
# This script drops and recreates the test database

set -e

echo "🔄 Resetting test database..."

# Set test database configuration for containerized PostgreSQL
export POSTGRES_USER=testuser
export POSTGRES_PASSWORD=test_password_123
export POSTGRES_DB=aio-test
export POSTGRES_HOST=localhost  # For external access to container
export POSTGRES_PORT=5433       # External port mapping

# Check if PostgreSQL container is running
if ! docker ps | grep -q postgres-test; then
    echo "❌ PostgreSQL container is not running. Please start test services first."
    exit 1
fi

# Drop and recreate database in containerized PostgreSQL
echo "🗑️  Dropping existing test database..."
docker exec postgres-test psql -U ${POSTGRES_USER} -d postgres -c "DROP DATABASE IF EXISTS ${POSTGRES_DB}"

echo "🏗️  Creating fresh test database..."
docker exec postgres-test psql -U ${POSTGRES_USER} -d postgres -c "CREATE DATABASE ${POSTGRES_DB}"

# Run migrations
echo "📋 Running database migrations..."
POSTGRES_HOST=localhost POSTGRES_PORT=5433 python ops/database/migrations/runner.py 2>/dev/null || true

# Seed database
echo "🌱 Seeding database with test data..."
POSTGRES_HOST=localhost POSTGRES_PORT=5433 python ops/bootstrap/seed_users.py 2>/dev/null || true
POSTGRES_HOST=localhost POSTGRES_PORT=5433 python ops/bootstrap/seed_templates.py 2>/dev/null || true

echo "✅ Test database reset complete"
echo ""
echo "💡 Note: Test data directories are preserved:"
echo "  - data/postgres-test/ (PostgreSQL data)"
echo "  - data/qdrant-test/ (Qdrant data)"
echo ""
echo "To completely reset test environment:"
echo "  docker-compose -f deploy/docker-compose.test.yml down -v"
echo "  rm -rf data/postgres-test data/qdrant-test"
