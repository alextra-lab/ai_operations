# Script Index and Reference

## Overview

This document provides a comprehensive index of all scripts in the AI Operations Platform project, organized by category and purpose. Each script includes usage instructions, dependencies, and examples.

**Path convention:** All operational scripts live under **`ops/`** (e.g. `ops/bootstrap/`, `ops/testing/`, `ops/database/`). Do not use `scripts/`—the project uses `ops/` only.

## Quick Reference

### Test Environment Setup

- **Complete Setup**: `./ops/testing/start_test_services.sh`
- **Run Tests**: `python ops/testing/run_all_tests.py`
- **Clean Up**: `./ops/testing/clean_test_environment.sh`
- **Detailed Guide**: [TEST_ENVIRONMENT_SETUP.md](TEST_ENVIRONMENT_SETUP.md)

## Script Categories

### 1. Bootstrap Scripts (`/ops/bootstrap/`)

System initialization and setup scripts.

#### `build_llm_guard.sh`

- **Purpose**: Build LLM Guard service Docker image
- **Usage**: `bash ops/bootstrap/build_llm_guard.sh`
- **Dependencies**: Docker, LLM Guard models
- **Output**: Docker image for LLM Guard service

#### `build_wheelhouse.sh`

- **Purpose**: Build Python wheelhouse for offline deployment (two-pass: secure transformers 4.53.x for most services, 4.51.3 for llm_guard_svc only)
- **Usage**: `bash ops/bootstrap/build_wheelhouse.sh`
- **Dependencies**: Docker, requirements-all-no-llm-guard.txt, constraints.txt, src/llm_guard_svc/requirements.txt
- **Output**: Wheelhouse directory with Python packages (including both transformers versions)

#### `check_outdated_packages.sh`

- **Purpose**: List installed Python packages that have newer versions on PyPI (requires deps installed in active env)
- **Usage**: From project root with venv activated and `pip install -r requirements-all.txt` done: `bash ops/bootstrap/check_outdated_packages.sh`
- **Dependencies**: pip, project dependencies installed (e.g. from requirements-all.txt)
- **Output**: Table of package name, current version, latest version

#### `build_npm_cache_linux.sh`

- **Purpose**: Build npm cache for offline frontend builds
- **Usage**: `bash ops/bootstrap/build_npm_cache_linux.sh`
- **Dependencies**: npm, node, frontend package.json
- **Output**: npm cache directory in src/npm_cache/
- **Benefits**: 11x faster Docker builds with --no-cache

#### `download_embedding_models.py`

- **Purpose**: Download embedding models for offline use
- **Usage**: `python ops/bootstrap/download_embedding_models.py`
- **Dependencies**: sentence-transformers, internet connection
- **Output**: Downloaded models in data/models/

#### `download_llm_guard_models.py`

- **Purpose**: Download LLM Guard models for security validation
- **Usage**: `python ops/bootstrap/download_llm_guard_models.py`
- **Dependencies**: LLM Guard, internet connection
- **Output**: Downloaded models in data/llm-guard-models/

### 2. CI/CD Scripts (`/ops/ci/`)

Continuous integration and deployment scripts.

#### `build_images.sh`

- **Purpose**: Build all Docker images for the project
- **Usage**: `bash ops/ci/build_images.sh`
- **Dependencies**: Docker, Docker Compose
- **Output**: Built Docker images

#### `scan_images.sh`

- **Purpose**: Security scan Docker images for vulnerabilities
- **Usage**: `bash ops/ci/scan_images.sh`
- **Dependencies**: Docker, security scanning tools
- **Output**: Security scan reports

### 3. CLI Scripts (`/ops/cli/`)

Command-line utilities and tools.

#### `configure_llm_guard.py`

- **Purpose**: Configure LLM Guard service settings
- **Usage**: `python ops/cli/configure_llm_guard.py [options]`
- **Dependencies**: LLM Guard service
- **Options**: `--config`, `--validate`, `--reset`

#### `run_integration_tests.sh`

- **Purpose**: Run integration tests across services
- **Usage**: `bash ops/cli/run_integration_tests.sh`
- **Dependencies**: All services running
- **Output**: Integration test results

#### `verify_mypy.sh`

- **Purpose**: Run MyPy type checking
- **Usage**: `bash ops/cli/verify_mypy.sh`
- **Dependencies**: MyPy, Python type stubs
- **Output**: Type checking results

### 4. Operations Scripts (`/ops/operations/`)

Operational and maintenance scripts.

#### `rebuild_retrieval_service.sh`

- **Purpose**: Rebuild and restart corpus service (corpus_svc) after dependency updates
- **Usage**: `bash ops/operations/rebuild_retrieval_service.sh`
- **Dependencies**: Docker, corpus service code
- **Output**: Restarted corpus service container

#### `restart_llm_guard.sh`

- **Purpose**: Restart LLM Guard service
- **Usage**: `bash ops/operations/restart_llm_guard.sh`
- **Dependencies**: Docker, LLM Guard service
- **Output**: Restarted LLM Guard service

#### `run_rag_services.sh`

- **Purpose**: Start all RAG-related services
- **Usage**: `bash ops/operations/run_rag_services.sh`
- **Dependencies**: Docker Compose, all services
- **Output**: Running RAG services

#### `reset_and_migrate_test_db.sh`

- **Purpose**: Reset and migrate test database
- **Usage**: `bash ops/operations/reset_and_migrate_test_db.sh`
- **Dependencies**: PostgreSQL, migration scripts
- **Output**: Fresh test database

#### `reset_datastores.py`

- **Purpose**: Reset Qdrant collection and PostgreSQL documents table
- **Usage**: `python ops/operations/reset_datastores.py`
- **Dependencies**: qdrant-client, psycopg, python-dotenv
- **Output**: Clean Qdrant collection and empty documents table
- **Warning**: Destructive operation - will delete data

### 5. Testing Scripts (`/ops/testing/`)

Test execution and analysis utilities.

#### `run_all_tests.py`

- **Purpose**: Master test runner for all components
- **Usage**: `python ops/testing/run_all_tests.py [options]`
- **Dependencies**: pytest, all test dependencies
- **Options**: `--component`, `--coverage`, `--verbose`

#### `run_coverage.py`

- **Purpose**: Generate test coverage reports
- **Usage**: `python ops/testing/run_coverage.py [options]`
- **Dependencies**: pytest-cov, coverage tools
- **Options**: `--component`, `--format`, `--threshold`

#### `setup_test_env.py`

- **Purpose**: Set up test environment and dependencies
- **Usage**: `python ops/testing/setup_test_env.py`
- **Dependencies**: Python, pip
- **Output**: Configured test environment

#### `fix_imports.py`

- **Purpose**: Fix import path issues in test files
- **Usage**: `python ops/testing/fix_imports.py [directory]`
- **Dependencies**: Python file system access
- **Output**: Fixed import statements

#### `verify_use_case_config.py`

- **Purpose**: Verify UseCaseConfig schema implementation (B1-F1)
- **Usage**: `python ops/testing/verify_use_case_config.py`
- **Dependencies**: Database connection, Pydantic, SQLAlchemy
- **Output**: Comprehensive verification report for UseCaseConfig

#### `verify_output_contract.py`

- **Purpose**: Verify output contract validation implementation (B3-F4)
- **Usage**: `python ops/testing/verify_output_contract.py`
- **Dependencies**: jsonschema, pyyaml, ResponseFormatter
- **Output**: 10 comprehensive tests for JSON/YAML/TEXT validation, schema validation, best-effort/strict modes
- **Tests**: All validation formats (TEXT, JSON, YAML), schema validation, error handling modes

#### `verify_config_loader.py`

- **Purpose**: Verify UseCaseConfigLoader service implementation (B1-F2)
- **Usage**: `python ops/testing/verify_config_loader.py`
- **Dependencies**: Database connection, UseCaseConfigLoader, SQLAlchemy
- **Output**: Verification of config loading, caching, and intent-based lookup

#### `verify_rag_defaults.py`

- **Purpose**: Verify RAG defaults fix and config application (B1-F3)
- **Usage**: `python ops/testing/verify_rag_defaults.py`
- **Dependencies**: Retrieval service, UseCaseConfig
- **Output**: Verification that top_k defaults to 10 and config overrides work

#### `verify_use_case_menu.py`

- **Purpose**: Verify use case menu endpoint with RBAC filtering (B2-F1)
- **Usage**: `python ops/testing/verify_use_case_menu.py`
- **Dependencies**: FastAPI client, JWT authentication, database
- **Output**: Verification of RBAC-filtered use case list endpoint

#### `verify_enhanced_metrics.py`

- **Purpose**: Verify enhanced metrics in response (B2-F2)
- **Usage**: `python ops/testing/verify_enhanced_metrics.py`
- **Dependencies**: Orchestrator, ResponseFormatter, metrics components
- **Output**: Verification of comprehensive metrics (retrieval, guard, model, confidence)

#### `verify_template_model_selection.py`

- **Purpose**: Verify template-driven model selection (B3-F1)
- **Usage**: `python ops/testing/verify_template_model_selection.py`
- **Dependencies**: LLMRouter, UseCaseConfig
- **Output**: Verification that config overrides model selection and generation params

#### `verify_template_rag_config.py`

- **Purpose**: Verify template-driven RAG configuration (B3-F2)
- **Usage**: `python ops/testing/verify_template_rag_config.py`
- **Dependencies**: Orchestrator, RAG service, UseCaseConfig
- **Output**: Verification of RAG config application (enabled, top_k, filters)

#### `verify_template_streaming.py`

- **Purpose**: Verify streaming per template configuration (B3-F3)
- **Usage**: `python ops/testing/verify_template_streaming.py`
- **Dependencies**: Orchestrator, UseCaseConfig
- **Output**: Verification of streaming precedence rules (request > template > intent > global)

#### `verify_framework.py`

- **Purpose**: General framework verification utility
- **Usage**: `python ops/testing/verify_framework.py`
- **Dependencies**: Core framework components
- **Output**: Framework validation report

#### `verify_metrics_simple.py`

- **Purpose**: Simple metrics verification utility
- **Usage**: `python ops/testing/verify_metrics_simple.py`
- **Dependencies**: Metrics components
- **Output**: Basic metrics validation

#### `verify_test_database.py`

- **Purpose**: Verify test database setup and connectivity
- **Usage**: `python ops/testing/verify_test_database.py`
- **Dependencies**: PostgreSQL, test database
- **Output**: Database connectivity and schema verification

#### `run_service_tests.py`

- **Purpose**: Run tests for a specific service
- **Usage**: `python ops/testing/run_service_tests.py <service_name>`
- **Dependencies**: pytest, service-specific dependencies
- **Options**: Service name (backend, retrieval, embedding, etc.)

#### `manage_test_database.py`

- **Purpose**: Manage test database operations (create, drop, reset)
- **Usage**: `python ops/testing/manage_test_database.py [action]`
- **Dependencies**: PostgreSQL, SQLAlchemy
- **Actions**: create, drop, reset, migrate

#### `setup_test_database.py`

- **Purpose**: Set up test database with schema and seed data
- **Usage**: `python ops/testing/setup_test_database.py`
- **Dependencies**: PostgreSQL, migration scripts
- **Output**: Initialized test database

#### `setup_test_user.py`

- **Purpose**: Create test users and roles for authentication testing
- **Usage**: `python ops/testing/setup_test_user.py`
- **Dependencies**: Database connection, auth system
- **Output**: Test users created

#### `load_test_env.py`

- **Purpose**: Load test environment variables
- **Usage**: `python ops/testing/load_test_env.py`
- **Dependencies**: python-dotenv
- **Output**: Test environment variables loaded

#### `integrate_test_improvements.py`

- **Purpose**: Integration script for test improvements
- **Usage**: `python ops/testing/integrate_test_improvements.py`
- **Dependencies**: Test framework components
- **Output**: Integrated test improvements

#### `fix_db_connection.py`

- **Purpose**: Fix database connection issues in tests
- **Usage**: `python ops/testing/fix_db_connection.py`
- **Dependencies**: Database configuration
- **Output**: Fixed database connections

### 6. Database (`/ops/database/`)

Database init, migrations, and seed (SQL only). Apply in order: init → migrations → seed.

- **Init**: `ops/database/init/000_complete_init.sql` — base schema
- **Migrations**: `ops/database/migrations/*.sql` and `ops/database/migrations/rbac_v2/` — apply via psql or `run_migrations.sh` in rbac_v2
- **Seed**: `ops/database/seed/*.sql` (e.g. `001_seed_users.sql`, `002_seed_intents.sql`, …) — users, intents, use cases, models, etc. Apply after init; order is lexicographic (001, 002, …).
- **Reference**: [ops/database/README.md](../../ops/database/README.md) for full Quick Start and copy-paste commands.

### 7. Service-Specific Test Runners

Individual service test execution scripts.

#### `src/orchestrator/run_tests.sh`

- **Purpose**: Run backend service tests
- **Usage**: `bash src/orchestrator/run_tests.sh [pytest_options]`
- **Dependencies**: pytest, backend dependencies
- **Example**: `bash src/orchestrator/run_tests.sh --cov=app --cov-report=term-missing`

#### `src/corpus_svc/run_tests.sh`

- **Purpose**: Run retrieval service tests
- **Usage**: `bash src/corpus_svc/run_tests.sh [pytest_options]`
- **Dependencies**: pytest, retrieval dependencies
- **Example**: `bash src/corpus_svc/run_tests.sh --cov=app --cov-report=term-missing`

#### `src/shared/run_tests.sh`

- **Purpose**: Run shared module tests
- **Usage**: `bash src/shared/run_tests.sh [pytest_options]`
- **Dependencies**: pytest, shared dependencies
- **Example**: `bash src/shared/run_tests.sh --cov=shared/auth --cov-report=term-missing`

## Usage Examples

### Running All Tests

```bash
# Using centralized runner
python ops/testing/run_all_tests.py --coverage

# Using individual service runners
bash src/orchestrator/run_tests.sh --cov=app --cov-report=term-missing
bash src/corpus_svc/run_tests.sh --cov=app --cov-report=term-missing
bash src/shared/run_tests.sh --cov=shared/auth --cov-report=term-missing
```

### Setting Up Development Environment

```bash
# Download models
python ops/bootstrap/download_embedding_models.py
python ops/bootstrap/download_llm_guard_models.py

# Build services
bash ops/ci/build_images.sh

# Seed database (run from project root with POSTGRES_* env set; init first: ops/database/init/000_complete_init.sql)
for seed_file in ops/database/seed/*.sql; do
  PGPASSWORD=$POSTGRES_PASSWORD psql-17 -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -f "$seed_file"
done
```

### Running Integration Tests

```bash
# Start all services
bash ops/operations/run_rag_services.sh

# Run integration tests
bash ops/cli/run_integration_tests.sh
```

### Database Management

```bash
# Reset test database
bash ops/operations/reset_and_migrate_test_db.sh

# Apply migrations (SQL in ops/database/migrations/; see ops/database/README.md)
# Or use: ./ops/testing/reset_test_database.sh for test DB
```

## Script Dependencies

### Common Dependencies

- **Python 3.12+**: Required for all Python scripts
- **Docker**: Required for containerized services
- **PostgreSQL**: Required for database operations
- **pytest**: Required for test execution

### Service-Specific Dependencies

- **Backend**: FastAPI, SQLAlchemy, JWT
- **Retrieval**: Qdrant, sentence-transformers
- **Embedding**: sentence-transformers, numpy
- **LLM Guard**: LLM Guard library
- **Frontend**: Angular, Node.js

## Troubleshooting Scripts

### Common Issues

#### Permission Denied

```bash
# Make scripts executable
chmod +x ops/**/*.sh
```

#### Import Errors

```bash
# Fix import paths
python ops/testing/fix_imports.py
```

#### Database Connection Issues

```bash
# Reset test database
bash ops/operations/reset_and_migrate_test_db.sh
```

#### Service Startup Issues

```bash
# Rebuild services
bash ops/ci/build_images.sh
bash ops/operations/run_rag_services.sh
```

### Debug Mode

```bash
# Run with verbose output
bash -x ops/operations/run_rag_services.sh

# Run Python scripts with debug
python -u ops/testing/run_all_tests.py --verbose
```

## Script Maintenance

### Adding New Scripts

1. Place in appropriate category directory
2. Add to this index with full documentation
3. Include usage examples and dependencies
4. Test thoroughly before committing

### Updating Existing Scripts

1. Update documentation in this index
2. Test changes thoroughly
3. Update related scripts if needed
4. Document breaking changes

### Deprecating Scripts

1. Add deprecation notice to script
2. Update this index with deprecation status
3. Provide migration path to replacement
4. Remove after grace period

## Related Documentation

- [Testing Guide](TESTING_GUIDE.md) - Comprehensive testing practices
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
- [Developer Guide](../development/DEVELOPER_GUIDE.md) - General development practices
- [API Documentation](../api/) - API reference and examples

## Conclusion

This script index provides a comprehensive reference for all scripts in the AI Operations Platform project. Use this as your primary reference for understanding script purposes, usage, and dependencies.

For questions about specific scripts or to request new scripts, consult the project documentation or contact the development team.
