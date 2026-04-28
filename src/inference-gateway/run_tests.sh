#!/bin/bash
# Inference Gateway Test Runner
# Usage: ./run_tests.sh [pytest options]
#
# Examples:
#   ./run_tests.sh                                    # Run all tests with coverage
#   ./run_tests.sh --cov-report=html                 # Generate HTML coverage report
#   ./run_tests.sh -k test_chat                      # Run specific tests
#   ./run_tests.sh tests/unit/                       # Run unit tests only

set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Inference Gateway Test Suite ===${NC}"

# Set test environment variables
export DATABASE_URL="postgresql://testuser:test_password_123@localhost:5433/aio-test"
export REDIS_HOST=localhost
export REDIS_PORT=6380
export TESTING=true

# Check if test database is accessible
echo -e "${YELLOW}Checking test database...${NC}"
if docker exec postgres-test psql -U testuser -d aio-test -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Database connection successful${NC}"
else
    echo -e "${RED}✗ Database connection failed${NC}"
    echo -e "${YELLOW}Starting test database...${NC}"
    cd ../..
    source <(grep -Ev '^(#|$)' config/env/env.test | sed 's/^/export /')
    docker-compose -f deploy/docker-compose.test.yml up -d postgres-db redis-cache
    sleep 3
    cd "$SCRIPT_DIR"
fi

# Check if Redis is accessible
echo -e "${YELLOW}Checking Redis...${NC}"
if docker exec redis-test redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis connection successful${NC}"
else
    echo -e "${RED}✗ Redis connection failed${NC}"
    echo -e "${YELLOW}Starting Redis...${NC}"
    cd ../..
    source <(grep -Ev '^(#|$)' config/env/env.test | sed 's/^/export /')
    docker-compose -f deploy/docker-compose.test.yml up -d redis-cache
    sleep 2
    cd "$SCRIPT_DIR"
fi

# Run tests with coverage by default
echo -e "${GREEN}Running tests...${NC}"
if [ $# -eq 0 ]; then
    # Default: run all tests with coverage
    pytest tests/ \
        --cov=app \
        --cov-report=term-missing \
        --cov-report=html:htmlcov \
        -v
else
    # Custom pytest options provided
    pytest "$@"
fi

# Show coverage summary
if [ -f htmlcov/index.html ]; then
    echo -e "${GREEN}✓ HTML coverage report generated: htmlcov/index.html${NC}"
fi

echo -e "${GREEN}=== Test execution complete ===${NC}"
