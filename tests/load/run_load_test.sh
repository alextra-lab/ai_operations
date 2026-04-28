#!/usr/bin/env bash
#
# Load test runner script for Inference Gateway
#
# This script sets up the environment and runs load tests against the Gateway.
#
# Usage:
#   bash tests/load/run_load_test.sh [OPTIONS]
#
# Examples:
#   bash tests/load/run_load_test.sh                    # Default 500 req/min test
#   bash tests/load/run_load_test.sh --rps 6.67         # 400 req/min test
#   bash tests/load/run_load_test.sh --mode both        # Test direct + proxy

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"

echo "=============================================================================="
echo "INFERENCE GATEWAY LOAD TEST RUNNER"
echo "=============================================================================="
echo ""

# Load environment variables
ENV_FILE="config/env/env.test"
if [[ -f "$ENV_FILE" ]]; then
    echo "Loading environment from: $ENV_FILE"
    set -a
    # shellcheck disable=SC1090
    source <(grep -Ev '^(#|$)' "$ENV_FILE")
    set +a
else
    echo "⚠️  Warning: $ENV_FILE not found, using defaults"
fi

# Verify required environment variables
: "${JWT_SECRET:?ERROR: JWT_SECRET not set}"
: "${JWT_ALGORITHM:=HS256}"
: "${JWT_ISSUER:=ai-operations-platform}"

echo "JWT Configuration:"
echo "  Issuer: $JWT_ISSUER"
echo "  Algorithm: $JWT_ALGORITHM"
echo "  Secret: ${JWT_SECRET:0:10}... (${#JWT_SECRET} chars)"
echo ""

# Check Gateway health
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8007}"
echo "Checking Gateway health at $GATEWAY_URL..."
if curl -sf "$GATEWAY_URL/health" > /dev/null 2>&1; then
    echo "✓ Gateway is healthy"
else
    echo "❌ ERROR: Gateway is not responding at $GATEWAY_URL"
    echo ""
    echo "Start the Gateway with:"
    echo "  cd deploy"
    echo "  docker-compose -f docker-compose.test.yml up -d inference-gateway"
    exit 1
fi
echo ""

# Check Redis (optional but recommended)
REDIS_URL="${REDIS_URL:-redis://localhost:6380}"
if docker exec redis-test redis-cli ping > /dev/null 2>&1; then
    echo "✓ Redis is healthy"
else
    echo "⚠️  Warning: Redis is not responding (rate limiting may not work)"
fi
echo ""

# Run load test
echo "Running load test..."
echo ""

python tests/load/load_test.py "$@"

EXIT_CODE=$?

echo ""
echo "=============================================================================="
if [[ $EXIT_CODE -eq 0 ]]; then
    echo "✅ LOAD TEST PASSED"
else
    echo "❌ LOAD TEST FAILED (exit code: $EXIT_CODE)"
fi
echo "=============================================================================="

exit $EXIT_CODE
