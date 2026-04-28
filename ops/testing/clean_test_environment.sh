#!/bin/bash

# Complete test environment cleanup
# This script stops all test services and removes all test data

set -e

echo "🧹 Cleaning test environment..."

# Navigate to project root
cd "$(dirname "$0")/../.."

# Stop and remove all test containers and volumes
echo "🛑 Stopping test services..."
docker-compose -f deploy/docker-compose.test.yml down -v

# Remove test data directories
echo "🗑️  Removing test data directories..."
rm -rf data/postgres-test data/qdrant-test

echo "✅ Test environment cleaned successfully!"
echo ""
echo "📁 Test data directories removed:"
echo "  - data/postgres-test/"
echo "  - data/qdrant-test/"
echo ""
echo "🚀 To start fresh test environment:"
echo "  ./scripts/testing/start_test_services.sh"
