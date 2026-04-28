#!/bin/bash
# Run tests for shared with coverage

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT/src"

PYTHONPATH=. pytest --cov=shared/auth --cov=shared/logging_utils --cov-report=term-missing shared/tests
