#!/bin/bash
# rebuild_retrieval_service.sh
#
# This script rebuilds and restarts the Corpus service (corpus_svc) container
# after the qdrant-client library version has been updated
#
# Usage: ./ops/operations/rebuild_retrieval_service.sh

set -e

echo "=== Rebuilding Corpus service (corpus_svc) with updated dependencies ==="
echo "This script will rebuild and restart the corpus-service container"
echo "to apply the qdrant-client version update from 1.7.0 to >=1.10.0,<2.0.0"
echo ""

# Navigate to project root
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo "Project root: $PROJECT_ROOT"
echo ""

# Check if docker-compose is installed
if ! command -v docker compose &> /dev/null; then
    echo "Error: docker-compose is not installed or not in PATH"
    exit 1
fi

echo "1. Stopping corpus-service container"
docker compose -f deploy/docker-compose.yml stop corpus-service || true

echo ""
echo "2. Rebuilding corpus-service container"
docker compose -f deploy/docker-compose.yml build corpus-service

echo ""
echo "3. Restarting corpus-service container"
docker compose -f deploy/docker-compose.yml up -d corpus-service

echo ""
echo "4. Checking container status"
docker compose -f deploy/docker-compose.yml ps corpus-service

echo ""
echo "5. Tailing the logs to verify the fix (press Ctrl+C to exit)"
echo "Look for \"Collection {collection_name} validated\" without validation warnings"
docker compose -f deploy/docker-compose.yml logs -f corpus-service

echo ""
echo "=== Rebuild Complete ==="
echo "If you want to test the Qdrant compatibility fix, run:"
echo "python temp_scripts/test_qdrant_compatibility.py"
