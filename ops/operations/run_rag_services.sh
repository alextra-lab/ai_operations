#!/bin/bash
# Script to run RAG services for development and testing
#
# NOTE: If you're using VSCode with devcontainers, you typically don't need to run this script
# as the RAG services are already integrated into the devcontainer configuration.
# This script is provided as an alternative for:
# 1. Non-devcontainer development workflows
# 2. Testing the services independently
# 3. Running the services in environments without VSCode
#

# Set default environment variables
export SECRET_KEY=${SECRET_KEY:-"mysecretkey"}
export LOG_LEVEL=${LOG_LEVEL:-"INFO"}
export DEBUG=${DEBUG:-"false"}

# Directory setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$PROJECT_ROOT/data"

# Note if we're running inside Docker (for informational purposes)
INSIDE_DOCKER=false
if [ -f /.dockerenv ]; then
    INSIDE_DOCKER=true
    echo "Info: Running inside a Docker container with Docker socket mounted."
    echo "      Using Docker-in-Docker via socket mount."
fi

# Create required directories if they don't exist
mkdir -p "$DATA_DIR/models" "$DATA_DIR/documents" "$DATA_DIR/tmp"

echo "Setting up environment for RAG services..."

# Check if docker-compose is installed
if ! command -v docker compose &> /dev/null; then
    echo "Error: docker compose is not installed"
    exit 1
fi

# Run the RAG services using Docker Compose
echo "Building and starting RAG services..."

# Build the services first
docker compose -f "$PROJECT_ROOT/deploy/docker-compose.yml" build embedding-service corpus-service

# Check if build was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to build services. Please check the error messages above."
    exit 1
fi

# Start the services
echo "Starting services..."
docker compose -f "$PROJECT_ROOT/deploy/docker-compose.yml" up -d

# Check if services started successfully
if [ $? -ne 0 ]; then
    echo "Error: Failed to start services. Please check the error messages above."
    exit 1
fi

# Verify services are running
echo "Verifying services..."
sleep 5  # Give services a moment to initialize

# Check embedding service
if ! curl -s http://localhost:8002/health > /dev/null; then
    echo "Warning: Embedding service may not be running correctly. Check logs with:"
    echo "docker compose -f $PROJECT_ROOT/deploy/docker-compose.yml logs embedding-service"
else
    echo "✓ Embedding Service is running"
fi

# Check retrieval service
if ! curl -s http://localhost:8003/health > /dev/null; then
    echo "Warning: Retrieval service may not be running correctly. Check logs with:"
    echo "docker compose -f $PROJECT_ROOT/deploy/docker-compose.yml logs corpus-service"
else
    echo "✓ Retrieval Service is running"
fi

echo ""
echo "Service endpoints:"
echo "- Embedding Service: http://localhost:8002/docs"
echo "- Retrieval Service: http://localhost:8003/docs"

echo ""
echo "To stop the services, run:"
echo "docker compose -f $PROJECT_ROOT/deploy/docker-compose.yml down"

echo ""
echo "To check logs, run:"
echo "docker compose -f $PROJECT_ROOT/deploy/docker-compose.yml logs -f [service-name]"
