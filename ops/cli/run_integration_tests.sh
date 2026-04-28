#!/bin/bash
# Script to run integration tests for the AI Operations Platform project

# Set environment variables for testing
export PYTHONPATH=${PYTHONPATH:-.}
export TESTING=1

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Navigate to project root
cd "$(dirname "$0")/../.." || { echo -e "${RED}Failed to navigate to project root${NC}"; exit 1; }

# Display help information
function show_help {
    echo -e "${BLUE}Usage: $0 [options] [pytest_args]${NC}"
    echo
    echo -e "${BLUE}Options:${NC}"
    echo "  -h, --help        Show this help message"
    echo "  -f, --file FILE   Run tests from specific file(s)"
    echo "  -t, --test TEST   Run specific test function(s)"
    echo "  -m, --marker MARK Run tests with specific marker"
    echo "  -v, --verbose     Increase verbosity"
    echo "  -x, --exitfirst   Exit on first test failure"
    echo
    echo -e "${BLUE}Examples:${NC}"
    echo "  $0                               # Run all integration tests"
    echo "  $0 -f test_llm_guard_integration.py  # Run specific test file"
    echo "  $0 -t test_health_endpoint       # Run specific test function"
    echo "  $0 -m anyio                      # Run tests with marker 'anyio'"
    echo "  $0 -- -xvs                       # Pass -xvs options to pytest"
    exit 0
}

# Initialize variables
PYTEST_ARGS=()
FILE_FILTER=""
TEST_FILTER=""
MARKER_FILTER=""

# Parse command-line options
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            ;;
        -f|--file)
            FILE_FILTER="$2"
            shift 2
            ;;
        -t|--test)
            TEST_FILTER="$2"
            shift 2
            ;;
        -m|--marker)
            MARKER_FILTER="$2"
            shift 2
            ;;
        -v|--verbose)
            PYTEST_ARGS+=("-v")
            shift
            ;;
        -x|--exitfirst)
            PYTEST_ARGS+=("-x")
            shift
            ;;
        --)
            shift
            PYTEST_ARGS+=("$@")
            break
            ;;
        *)
            PYTEST_ARGS+=("$1")
            shift
            ;;
    esac
done

# Check for required Python packages
function check_package {
    python - <<EOF
import sys
try:
    import $1
except ImportError:
    sys.exit(1)
EOF
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: $1 is not installed. Please install it with 'pip install $1'.${NC}"
        exit 1
    fi
}

echo -e "${YELLOW}Checking required packages...${NC}"
check_package pytest
check_package anyio
echo -e "${GREEN}All required packages installed.${NC}"

# Build the pytest command
PYTEST_CMD="python -m pytest tests/integration"

# Apply filters if specified
if [ -n "$FILE_FILTER" ]; then
    PYTEST_CMD+=" tests/integration/${FILE_FILTER}"
fi
if [ -n "$TEST_FILTER" ]; then
    PYTEST_CMD+=" -k ${TEST_FILTER}"
fi
if [ -n "$MARKER_FILTER" ]; then
    PYTEST_CMD+=" -m ${MARKER_FILTER}"
fi
if [ ${#PYTEST_ARGS[@]} -gt 0 ]; then
    PYTEST_CMD+=" ${PYTEST_ARGS[*]}"
fi

# Run the integration tests
echo -e "${YELLOW}Running integration tests for AI Operations Platform${NC}"
echo -e "${YELLOW}=====================================================${NC}"
echo -e "${YELLOW}Executing: ${PYTEST_CMD}${NC}"

eval $PYTEST_CMD
RESULT=$?

# Report results
if [ $RESULT -eq 0 ]; then
    echo -e "${GREEN}Integration tests completed successfully!${NC}"
    exit 0
else
    echo -e "${RED}Integration tests failed with exit code $RESULT. Please review the output above for details.${NC}"
    exit $RESULT
fi
