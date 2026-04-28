# Test Infrastructure

This directory contains the integrated test infrastructure for the Cyber Defense Analyst AI Assistant project.

## Overview

The test infrastructure provides tools and utilities for:

1. Setting up test environments
2. Running tests with proper dependency management
3. Generating comprehensive coverage reports
4. Fixing common test issues

## Directory Structure

- `run_tests.py`: Main test runner for executing tests across all components
- `run_coverage.py`: Test coverage analysis and reporting tool
- `setup_environment.py`: Test environment configuration utility
- `fix_imports.py`: Utility for resolving import path issues

## Usage

### Running Tests

```bash
# Run all tests
python ops/testing/run_tests.py

# Run tests for a specific component
python ops/testing/run_tests.py --component embedding

# Run only unit tests
python ops/testing/run_tests.py --type unit
```

### Coverage Reports

```bash
# Generate coverage report
python ops/testing/run_coverage.py --component all

# Generate HTML coverage report for a specific component
python ops/testing/run_coverage.py --component retrieval --format html
```

### Environment Setup

```bash
# Set up test environment
python ops/testing/setup_environment.py

# Set up environment for a specific component
python ops/testing/setup_environment.py --component embedding
```

### Fix Import Issues

```bash
# Fix import issues in test files
python ops/testing/fix_imports.py --directory tests/retrieval
```

## Notes

- All scripts include help documentation accessible via `--help` flag
- Coverage reports are written to the `coverage_reports/` directory
- Test failures are logged and summarized for easier debugging
