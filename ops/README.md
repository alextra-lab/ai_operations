# Scripts Directory

## Overview

This directory contains all operational scripts for the AI Operations Platform project, organized by category and purpose.

## Directory Structure

```
/ops/
├── bootstrap/          # System initialization and setup
├── ci/                # CI/CD and deployment scripts
├── cli/               # Command-line utilities
├── database/          # Database init, migrations, seed (SQL)
├── operations/        # Operational and maintenance scripts
├── testing/           # Test execution and analysis utilities
└── README.md          # This file
```

## Categories

### Bootstrap Scripts (`bootstrap/`)
System initialization and setup scripts that prepare the environment for development or deployment.

**Key Scripts:**
- `build_llm_guard.sh` - Build LLM Guard service
- `download_embedding_models.py` - Download embedding models
- Seed data: SQL in `ops/database/seed/`

### CI/CD Scripts (`ci/`)
Continuous integration and deployment scripts for automated builds and deployments.

**Key Scripts:**
- `build_images.sh` - Build all Docker images
- `scan_images.sh` - Security scan Docker images

### CLI Scripts (`cli/`)
Command-line utilities and tools for development and maintenance.

**Key Scripts:**
- `configure_llm_guard.py` - Configure LLM Guard service
- `run_integration_tests.sh` - Run integration tests
- `verify_mypy.sh` - Run type checking

### Operations Scripts (`operations/`)
Operational and maintenance scripts for running and managing services.

**Key Scripts:**
- `rebuild_retrieval_service.sh` - Rebuild corpus service (corpus_svc)
- `restart_llm_guard.sh` - Restart LLM Guard service
- `run_rag_services.sh` - Start all RAG services
- `reset_and_migrate_test_db.sh` - Reset test database

### Testing Scripts (`testing/`)
Test execution, analysis, and utility scripts.

**Key Scripts:**
- `run_all_tests.py` - Master test runner
- `run_coverage.py` - Generate coverage reports
- `init_test_environment.sh` / `setup_environment.py` - Test environment setup
- `fix_imports.py` - Fix import path issues

### Database (`database/`)
Database init, migrations, and seed SQL.

**Key paths:**
- `database/init/` - Schema init
- `database/migrations/` - Migration SQL
- `database/seed/` - Seed data SQL

## Usage

### Quick Start
```bash
# Set up development environment
python ops/bootstrap/download_embedding_models.py
# Seed database: apply ops/database/seed/*.sql (see ops/database/README.md)

# Start all services
bash ops/operations/run_rag_services.sh

# Run tests
python ops/testing/run_all_tests.py --coverage
```

### Common Operations
```bash
# Rebuild a service
bash ops/operations/rebuild_retrieval_service.sh

# Run integration tests
bash ops/cli/run_integration_tests.sh

# Generate coverage report
python ops/testing/run_coverage.py --component backend
```

## Script Index

For detailed information about each script, including usage, dependencies, and examples, see the [Script Index](../docs/testing/SCRIPT_INDEX.md).

## Guidelines

### Adding New Scripts
1. Place in appropriate category directory
2. Use descriptive names
3. Include proper shebang and error handling
4. Document in the script index
5. Test thoroughly

### Script Standards
- Use `#!/bin/bash` for shell scripts
- Use `#!/usr/bin/env python3` for Python scripts
- Include error handling and exit codes
- Use absolute paths when possible
- Document usage and dependencies

### Maintenance
- Keep scripts up to date with codebase changes
- Remove deprecated scripts
- Update documentation when scripts change
- Test scripts regularly

## Related Documentation

- [Script Index](../docs/testing/SCRIPT_INDEX.md) - Detailed script reference
- [Testing Guide](../docs/testing/TESTING_GUIDE.md) - Testing practices
- [Developer Guide](../docs/development/DEVELOPER_GUIDE.md) - Development practices

## Temporary Scripts

For temporary scripts that are not part of the main codebase, use the `/temp_ops/` directory. This directory is gitignored and intended for throwaway scripts.

See `/temp_ops/README.md` for more information.
