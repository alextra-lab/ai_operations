#!/usr/bin/env bash
set -e

# Usage: ./run_tests_with_coverage.sh [extra pytest args]
# Example: ./run_tests_with_coverage.sh -m "not slow"

cd "$(dirname "$0")/../.."

export PYTHONPATH=src:tests:$PYTHONPATH

echo "Running pytest with coverage..."

pytest --cov=src --cov-report=term-missing --cov-report=html "$@" tests

echo "Coverage HTML report available in htmlcov/index.html"
