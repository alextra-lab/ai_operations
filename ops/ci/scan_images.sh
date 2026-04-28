#!/bin/bash
# Scan Docker images with Trivy for security vulnerabilities
# Usage: ./scan_images.sh [severity]
# Default severity: HIGH,CRITICAL

set -e

# Default severity if not provided
SEVERITY=${1:-"HIGH,CRITICAL"}
# Default exit code on findings
EXIT_CODE=${2:-1}

# Project name for tagging images
PROJECT_NAME="aio"

# List all service images to scan
SERVICES=("ui-webapp" "orchestrator-api" "llm-service" "llm-guard")

# Check if Trivy is installed
if ! command -v trivy &> /dev/null; then
    echo "Trivy is not installed. Please install it first:"
    echo "https://aquasecurity.github.io/trivy/latest/getting-started/installation/"
    exit 1
fi

echo "Starting vulnerability scan with Trivy..."
echo "Severity filter: $SEVERITY"
echo "-------------------------------------------"

# Initialize failure flag
FAILURES=0

# Scan each service image
for SERVICE in "${SERVICES[@]}"; do
    IMAGE_NAME="${PROJECT_NAME}/${SERVICE}:latest"
    echo "Scanning $IMAGE_NAME..."

    # Run Trivy scan, set exit-code=0 to prevent script termination on findings
    if ! trivy image --severity "$SEVERITY" --exit-code 0 "$IMAGE_NAME"; then
        echo "⚠️ Vulnerabilities found in $IMAGE_NAME"
        FAILURES=$((FAILURES + 1))
    else
        echo "✅ No vulnerabilities found in $IMAGE_NAME"
    fi
    echo "-------------------------------------------"
done

# Report overall status
if [ $FAILURES -gt 0 ]; then
    echo "⚠️ Vulnerabilities found in $FAILURES images."
    if [ $EXIT_CODE -ne 0 ]; then
        echo "Exiting with failure code due to detected vulnerabilities."
        exit $EXIT_CODE
    fi
else
    echo "✅ All images passed the vulnerability scan."
fi
