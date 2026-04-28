#!/bin/bash

# Start test services with Docker Compose
# This script starts all services with test environment configuration

set -e

echo "🚀 Starting AI Operations Platform (AIOP) Test Services..."

# Navigate to project root
cd "$(dirname "$0")/../.."

# Load test environment variables
echo "📋 Loading test environment variables..."
export $(grep -v '^#' config/env/env.test | xargs)

# Create test data directories
echo "📁 Creating test data directories..."
mkdir -p data/postgres-test data/qdrant-test

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f deploy/docker-compose.test.yml down

# Start test services (isolated test environment)
echo "🏗️  Starting test services..."
docker-compose -f deploy/docker-compose.test.yml up -d

# Initialize test database if needed
echo "🗄️  Checking test database..."
if ! ./scripts/testing/init_test_database.sh; then
    echo "❌ Database initialization failed"
    exit 1
fi

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 15

# Check service health
echo "🔍 Checking service health..."
docker-compose -f deploy/docker-compose.test.yml ps

echo "✅ Test services started successfully!"
echo ""
echo "🌐 Test Environment URLs:"
echo "  - UI Webapp: http://localhost:4201"
echo "  - Orchestrator API: http://localhost:8006"
echo "  - Retrieval Service: http://localhost:8004"
echo "  - Embedding Service: http://localhost:8005"
echo "  - LLM Guard Service: http://localhost:8082"
echo "  - PostgreSQL: localhost:5433 (external access)"
echo "  - Qdrant: http://localhost:6335 (external access)"
echo ""
echo "🔒 All services are running in isolated test network: aio-test-network"
echo ""
echo "📊 To view logs:"
echo "  docker-compose -f deploy/docker-compose.test.yml logs -f"
echo ""
echo "🛑 To stop services:"
echo "  docker-compose -f deploy/docker-compose.test.yml down"
echo ""
echo "🔄 To reset database:"
echo "  ./scripts/testing/reset_test_database.sh"
echo ""
echo "🗄️  To check database status:"
echo "  ./scripts/testing/init_test_database.sh"
