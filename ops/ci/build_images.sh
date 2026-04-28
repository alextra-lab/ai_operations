#!/bin/bash
# Build Docker images for all services with proper tagging and optimizations

set -e

# Default tag if not provided
TAG=${1:-"latest"}

# Project name for image tagging
PROJECT_NAME="aio"

# Get current directory (should be scripts/ci)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
# Navigate to project root directory (two levels up)
cd "$SCRIPT_DIR/../.."
ROOT_DIR="$(pwd)"

# Service directories - using separate arrays instead of associative array
SERVICES=("ui-webapp" "orchestrator-api" "llm-service" "llm-guard")
DIRECTORIES=("$ROOT_DIR/src/frontend" "$ROOT_DIR/src/backend" "$ROOT_DIR/src/llm-service" "$ROOT_DIR/src/llm-guard")

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

echo "Building Docker images for AI Operations Platform..."
echo "Tag: $TAG"
echo "-------------------------------------------"

# Initialize counter for successful builds
SUCCESS=0
TOTAL=${#SERVICES[@]}

# Build each service image
for i in "${!SERVICES[@]}"; do
    SERVICE=${SERVICES[$i]}
    DIR=${DIRECTORIES[$i]}
    IMAGE_NAME="${PROJECT_NAME}/${SERVICE}:${TAG}"

    echo "Building $IMAGE_NAME from $DIR..."

    # Ensure we're in the root directory before using relative paths
    cd "$ROOT_DIR"

    # Check if directory exists
    if [ ! -d "$DIR" ]; then
        echo "⚠️ Directory $DIR not found. Skipping build for $SERVICE."
        continue
    fi

    # Check if Dockerfile exists
    if [ ! -f "$DIR/Dockerfile" ]; then
        echo "⚠️ Dockerfile not found in $DIR. Skipping build for $SERVICE."
        continue
    fi

    # Build the Docker image with optimizations
    if docker build -t "$IMAGE_NAME" \
       --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
       --build-arg VCS_REF="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')" \
       --build-arg VERSION="$TAG" \
       "$DIR"; then
        echo "✅ Successfully built $IMAGE_NAME"
        SUCCESS=$((SUCCESS + 1))
    else
        echo "❌ Failed to build $IMAGE_NAME"
    fi
    echo "-------------------------------------------"
done

# Report overall status
echo "Build Summary: $SUCCESS/$TOTAL images built successfully"

if [ $SUCCESS -eq $TOTAL ]; then
    echo "✅ All images built successfully!"
    exit 0
else
    echo "⚠️ Some builds failed. Check the logs above for details."
    exit 1
fi
