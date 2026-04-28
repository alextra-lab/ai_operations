# Testing Guide

## Overview

This document provides comprehensive guidelines for creating, maintaining, and troubleshooting tests in the AI Operations Platform project. It serves as the single source of truth for testing practices and patterns.

## Current Test Status

### Test Statistics (Latest)

- **Total Tests**: 363
- **Passing Tests**: 318 (87.6%)
- **Failing Tests**: 39 (10.7%)
- **Skipped Tests**: 6 (1.7%)

### Fixed Issues

✅ **Database Schema Issues**: Fixed PromptTemplate field name mismatch (`active` → `is_active_version`)
✅ **Template Loader Tests**: Fixed database query field references
✅ **Import Path Issues**: Fixed module import paths in test files
✅ **Missing Assertions**: Fixed tests returning boolean values instead of using assertions
✅ **Test Collection Conflicts**: Resolved duplicate test module names
✅ **Test Database Setup**: Complete isolated test database with dedicated environment
✅ **Database Seeding**: Comprehensive test data including users, templates, and sample data
✅ **Environment Configuration**: Dedicated test environment file to avoid production conflicts

### Remaining Issues

🔄 **Async Authentication Tests**: 30+ tests still need async/await fixes
🔄 **Database Connection Tests**: Some shared database tests need configuration
🔄 **LLM Guard Service Tests**: Import and validation issues remain

## Test Environment Setup

### Quick Start

```bash
# Complete test environment setup (one command)
./ops/testing/start_test_services.sh

# Run tests
python ops/testing/run_all_tests.py

# Clean up
./ops/testing/clean_test_environment.sh
```

### Detailed Setup Guide

For comprehensive setup instructions, troubleshooting, and environment management, see:
**[TEST_ENVIRONMENT_SETUP.md](TEST_ENVIRONMENT_SETUP.md)**

### Test Database Configuration

The project uses a dedicated test database (`aio-test`) with separate environment configurations for different test types:

#### Environment Files

- **`config/env/env.test`**: Docker services (internal container communication)
- **`config/env/env.test.local`**: Unit tests (direct database access)

#### Database Seeding

The test database is automatically seeded with:

- **Users**: 3 test users (admin, analyst, testuser) with proper roles
- **Templates**: 4 prompt templates (query, rule generation, summarization, enrichment)
- **Use Cases**: 2 sample use cases (threat hunting, rule generation)
- **Documents**: 1 sample security policy document

#### Test Environment Loading

All test scripts automatically load the test environment configuration:

```python
# Test scripts automatically load test environment
from load_test_env import load_test_env
load_test_env()
```

## Frontend Testing (Angular)

### Node.js Requirements

| Environment | Version | Notes |
|-------------|---------|-------|
| Local development | Node.js 24 LTS | Required for Jest test coverage |
| Docker builds | `node:24-alpine` | Production image build |
| npm cache | `node:24-alpine` | Built inside Docker container |

**Important**: Node.js 25 (odd-numbered, non-LTS) has compatibility issues with test coverage tools. Always use an LTS version (22 or 24).

### Frontend Testing Flow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Lint &    │ →  │    Unit     │ →  │   Build     │ →  │   E2E       │
│   Type Check│    │    Tests    │    │   Docker    │    │   Tests     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     Node 24           Node 24          node:24-alpine      Cypress vs
   (local/CI)        (local/CI)        (production)      running container
```

### Running Frontend Tests

```bash
cd src/frontend-angular

# Linting
npm run lint

# Unit tests
npm run test

# Unit tests with coverage
npm run test -- --coverage

# Build (production)
npm run build -- --configuration=production
```

### Why Cypress Isn't in Docker Builds

Cypress is intentionally excluded from production Docker images:

1. **Production images should be lean** - No test tools in production
2. **Tests validate code before build** - Unit tests and linting run first
3. **E2E tests run externally** - Cypress tests the deployed container, not inside it

For E2E testing, run Cypress against a deployed container:

```bash
# Start the application
docker-compose up -d frontend

# Run Cypress E2E tests against it
npx cypress run --config baseUrl=http://localhost:80
```

## Test Architecture Patterns

### 1. Test Structure and Organization

#### Directory Structure

```
/tests/                    # Cross-service integration and E2E tests
├── integration/          # Multi-service integration tests
├── e2e/                 # End-to-end tests
└── fixtures/            # Test data and fixtures

/src/<service>/tests/     # Service-specific tests
├── unit/                # Unit tests
└── integration/         # Service-internal integration tests
```

#### Naming Conventions

- **Test Files**: `test_*.py` or `*_test.py`
- **Test Functions**: `test_*`
- **Test Classes**: `Test*`
- **Fixtures**: Descriptive names (e.g., `db_session`, `mock_llm_client`)

### 2. Database Testing Patterns

#### Phase 7 Strategy: Mock vs. Real DB

- **Unit Tests (`src/*/tests/unit/`)**: MUST use pure mocks (`AsyncMock`). NO real database connection.
- **Integration Tests (`src/*/tests/integration/`)**: MAY use real PostgreSQL database (via `async_engine`).

#### Async Database Testing (Unit Test Pattern)

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_database_operation():
    """Example of proper async database testing (UNIT)."""
    # Mock database session
    db_session = AsyncMock(spec=AsyncSession)

    # Set up mock return values (Modern SQLAlchemy 2.0 style)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [expected_result]
    db_session.execute.return_value = mock_result

    # Call async method with await
    result = await manager.async_method(db_session, params)

    # Assert results
    assert result is not None
    db_session.commit.assert_awaited_once()
```

#### Database Model Testing

```python
@pytest.fixture
def db_session():
    """Provide a mock database session for testing."""
    return AsyncMock(spec=AsyncSession)

@pytest.fixture
def sample_user():
    """Provide sample user data for testing."""
    return {
        "username": "testuser",
        "password": "password123",
        "email": "test@example.com",
        "role": UserRole.USER
    }
```

### 3. Authentication Testing Patterns

#### JWT Token Testing

```python
@pytest.fixture
def auth_manager():
    """Provide authentication manager for testing."""
    return UnifiedAuthManager(secret="test_secret")

@pytest.fixture
def valid_token(auth_manager):
    """Generate a valid JWT token for testing."""
    user_data = {"sub": "testuser", "roles": ["user"]}
    return auth_manager.create_access_token(data=user_data)
```

#### Async Authentication Testing

```python
@pytest.mark.asyncio
async def test_authenticate_user_success(auth_manager, db_session, sample_user):
    """Test successful user authentication."""
    # Mock database response
    db_session.query().filter().first.return_value = mock_user

    # Call async method
    result = await auth_manager.authenticate_user(
        db_session,
        sample_user["username"],
        sample_user["password"]
    )

    # Assert results
    assert result is not None
    assert result.username == sample_user["username"]
```

### 4. Service Integration Testing

#### Mock External Services

```python
@pytest.fixture
def mock_llm_client():
    """Mock LLM client to avoid external API calls."""
    mock_client = AsyncMock()
    mock_client.generate_response.return_value = {
        "content": "Mock response",
        "usage": {"tokens": 100}
    }
    return mock_client

@pytest.fixture(autouse=True)
def patch_llm_client(mock_llm_client):
    """Automatically patch LLM client in all tests."""
    with patch("app.orchestrator.llm_client.LLMClient", return_value=mock_llm_client):
        yield
```

### 5. Error Handling and Edge Cases

#### Exception Testing

```python
@pytest.mark.asyncio
async def test_database_error_handling(auth_manager, db_session):
    """Test proper error handling for database failures."""
    # Simulate database error
    db_session.query().filter().first.side_effect = SQLAlchemyError("Connection failed")

    # Test that exception is properly handled
    with pytest.raises(HTTPException) as exc_info:
        await auth_manager.authenticate_user(db_session, "user", "pass")

    assert exc_info.value.status_code == 500
    assert "Database error" in str(exc_info.value.detail)
```

#### Input Validation Testing

```python
@pytest.mark.parametrize("invalid_input", [
    None,
    "",
    "   ",
    "invalid@",
    "x" * 256  # Too long
])
async def test_input_validation(invalid_input, auth_manager, db_session):
    """Test input validation with various invalid inputs."""
    with pytest.raises(ValidationError):
        await auth_manager.create_user(db_session, username=invalid_input, ...)
```

## Common Test Issues and Solutions

### 1. Async/Await Issues

#### Problem: Coroutines Never Awaited

```
RuntimeWarning: coroutine 'UnifiedAuthManager.authenticate_user' was never awaited
```

#### Solution

```python
# ❌ Wrong - missing await
result = manager.authenticate_user(db_session, username, password)

# ✅ Correct - proper await
result = await manager.authenticate_user(db_session, username, password)

# ❌ Wrong - missing @pytest.mark.asyncio
def test_async_method():
    result = await manager.async_method()

# ✅ Correct - proper async test decorator
@pytest.mark.asyncio
async def test_async_method():
    result = await manager.async_method()
```

### 2. Database Field Mismatches

#### Problem: AttributeError for Missing Fields

```
AttributeError: type object 'PromptTemplate' has no attribute 'active'
```

#### Solution

```python
# ❌ Wrong - using non-existent field
templates = db.query(PromptTemplate).filter(PromptTemplate.active == True).all()

# ✅ Correct - using actual field name
templates = db.query(PromptTemplate).filter(PromptTemplate.is_active_version == True).all()
```

**Prevention**: Always check model definitions before writing tests:

```bash
# Check model fields
grep -n "Mapped\[" src/orchestrator/app/db/models.py
```

### 3. Import Path Issues

#### Problem: ModuleNotFoundError

```
ModuleNotFoundError: No module named 'shared'
```

#### Solution

**Use absolute imports** starting from `src.{service}.app`:

```python
# ❌ Wrong - relative imports or old service names
from backend.app.db.models import PromptTemplate  # 'backend' was renamed
from app.db.models import PromptTemplate  # Relative (deprecated)
from db.models import PromptTemplate  # Missing path prefix

# ✅ Correct - absolute imports from src root
from src.orchestrator.app.db.models import PromptTemplate
from src.orchestrator.app.routers.health import router as health_router
from src.orchestrator.app.main import create_app
from src.shared.auth import auth_router
```

**Prevention**: The conftest.py adds the `src` directory to `sys.path`:

```python
# In conftest.py (e.g., src/orchestrator/tests/conftest.py)
import sys
from pathlib import Path

# Add src directory to Python path for absolute imports
src_dir = Path(__file__).resolve().parent.parent.parent  # Points to src/
sys.path.insert(0, str(src_dir))
```

**Note**: Per project rules, tests MUST use absolute imports: `from src.{service}.app.X import Y`

### 4. Mock Configuration Issues

#### Problem: Mock Not Working as Expected

#### Solution

```python
# ❌ Wrong - incomplete mock setup
db_session.query().filter().first.return_value = mock_user

# ✅ Correct - complete mock chain
db_session.query.return_value.filter.return_value.first.return_value = mock_user

# Or use side_effect for multiple calls
db_session.query().filter().first.side_effect = [None, mock_user]
```

### 5. Database Session Management

#### Problem: Database Connection Issues in Tests

#### Solution

```python
@pytest.fixture
async def db_session():
    """Provide isolated database session for testing."""
    # Use in-memory SQLite for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_sessionmaker(engine)() as session:
        yield session

    await engine.dispose()
```

## Test Configuration Best Practices

### 1. Pytest Configuration (pytest.ini)

```ini
[tool:pytest]
testpaths = src scripts
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*

# Async test configuration
asyncio_mode = auto

# Logging configuration
log_cli = true
log_cli_level = INFO
log_cli_format = %(asctime)s [%(levelname)8s] %(name)s: %(message)s

# Warnings configuration
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
    ignore::RuntimeWarning:asyncio

# Exclude problematic temporary scripts
ignore =
    temp_ops/test_*.py
```

### 2. Test Fixtures (conftest.py)

```python
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock
import pytest

# Add src directory to Python path
src_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_dir))

# Set test environment variables
import os
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

# Global patches for external services
@pytest.fixture(scope="session", autouse=True)
def patch_external_services():
    """Patch external services globally."""
    with patch("app.orchestrator.llm_client.LLMClient", side_effect=create_mock_llm_client):
        yield

def create_mock_llm_client(*args, **kwargs):
    """Create mock LLM client."""
    mock = AsyncMock()
    mock.return_value = mock
    return mock
```

### 3. Test Database Setup

```python
@pytest.fixture(scope="session")
async def test_db():
    """Set up test database using the configured test database."""
    # Use the test database configuration
    from load_test_env import load_test_env
    load_test_env()

    # Create engine using test database URL
    engine = create_async_engine(os.environ["DATABASE_URL"])

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()
```

#### Test Database Management

The project provides comprehensive test database management tools:

```python
# Database setup and verification
from scripts.testing.setup_test_database import setup_test_database
from scripts.testing.verify_test_database import verify_database

# Set up test database
await setup_test_database()

# Verify database is ready
await verify_database()
```

## Test Execution

### Running Tests

#### Individual Service Tests

```bash
# Backend tests
bash src/orchestrator/run_tests.sh --cov=app --cov-report=term-missing

# Retrieval tests
bash src/corpus_svc/run_tests.sh --cov=app --cov-report=term-missing

# Shared tests
bash src/shared/run_tests.sh --cov=shared/auth --cov-report=term-missing
```

#### Centralized Test Runner

```bash
# Set up test database first (if not already done)
python ops/testing/setup_test_database.py

# Run all tests (automatically loads test environment)
python ops/testing/run_all_tests.py

# Run specific component
python ops/testing/run_all_tests.py --component backend

# Run with coverage
python ops/testing/run_all_tests.py --coverage

# Verify test database before running tests
python ops/testing/verify_test_database.py
```

#### Specific Test Execution

```bash
# Run specific test file
pytest src/shared/tests/unit/auth/test_manager_db.py -v

# Run specific test
pytest src/shared/tests/unit/auth/test_manager_db.py::test_create_user_duplicate_username -v

# Run tests matching pattern
pytest -k "test_authenticate" -v
```

### Coverage Analysis

```bash
# Generate coverage report
python ops/testing/run_coverage.py --component all

# Generate HTML coverage report
python ops/testing/run_coverage.py --component backend --format html

# View coverage report
open coverage_reports/backend/index.html
```

## Performance and Maintenance

### 1. Test Performance

- Use in-memory databases for unit tests
- Mock external services to avoid network calls
- Run tests in parallel when possible
- Use fixtures for expensive setup operations

### 2. Performance Benchmarks

Performance benchmarks validate async database migration (ADR-022) and establish baseline metrics for regression detection.

#### Location and Structure

- **Script Location**: `tests/benchmarks/benchmark_async_db.py`
- **Utilities**: `tests/benchmarks/benchmark_utils.py`
- **Results Storage**: `tests/benchmarks/results/`
- **Naming Convention**: `benchmark_YYYYMMDD_HHMMSS.json` (auto-generated) or custom via `--output`

#### Running Benchmarks

```bash
# Load test environment
source <(grep -Ev '^(#|$)' config/env/env.test | sed 's/^/export /')
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5433

# Run all benchmarks (default: 50 iterations, 10 concurrent)
python tests/benchmarks/benchmark_async_db.py

# Custom configuration
python tests/benchmarks/benchmark_async_db.py \
  --iterations 100 \
  --concurrency 20 \
  --output results/my_benchmark.json

# Database only (skip API)
python tests/benchmarks/benchmark_async_db.py --skip-api
```

#### What Gets Benchmarked

**Direct Database Operations:**
- Simple query (SELECT with LIMIT)
- Count query (COUNT aggregation)
- Filtered query (SELECT with WHERE)
- Join query (SELECT with JOIN)
- Transaction (read + write)

**API Endpoints (End-to-End):**
- GET /api/v1/use-cases/available
- GET /api/v1/tools/available
- GET /api/v1/query-history

#### Performance Targets

| Operation | Target p95 Latency | Notes |
|-----------|-------------------|-------|
| Simple Query | < 10ms | Primary key lookup |
| Count Query | < 50ms | Aggregation |
| Filtered Query | < 20ms | Indexed WHERE clause |
| Join Query | < 30ms | Foreign key indexes |
| Transaction | < 50ms | Read + Write |
| API: Use Cases | < 200ms | Includes RBAC checks |
| API: Tools | < 200ms | Includes permission checks |
| API: Query History | < 300ms | Includes filters |

#### Interpreting Results

- **Success Rate**: Should be 100% (no failures)
- **p95 Latency**: Should meet or exceed targets
- **Throughput**: Should scale with concurrency
- **No Regressions**: Compare against baseline (>20% increase is concerning)

#### Documentation

- **Main Guide**: `tests/benchmarks/README.md`
- **Session Log**: `docs/development/sessions/2025-12-01-p5-a21-performance-benchmarks.md`
- **ADR Reference**: ADR-022 (Backend Async Database Migration)

### 3. Test Maintenance

- Keep tests simple and focused
- Use descriptive test names
- Add comments for complex test logic
- Regularly review and update test data

### 4. Test Coverage

- Aim for 80%+ coverage on critical components
- Focus on business logic and error paths
- Use coverage reports to identify gaps
- Exclude test files from coverage reports

## Continuous Integration

### 1. Pre-commit Hooks

The repo root includes [.pre-commit-config.yaml](../../.pre-commit-config.yaml) for Ruff (lint) and Black (format). Install so checks run on every commit:

```bash
pip install pre-commit
pre-commit install
```

Run manually: `pre-commit run --all-files`. Tests are not run in the pre-commit hook (use CI or run tests locally before pushing).

### 2. CI Pipeline

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.12
      - name: Install dependencies
        run: pip install -r requirements-dev-all.txt
      - name: Run tests
        run: python ops/testing/run_all_tests.py --coverage
```

## Troubleshooting

### Common Issues and Quick Fixes

#### 1. Test Collection Errors

```bash
# Check for import errors
pytest --collect-only 2>&1 | grep ImportError

# Check Python path
python -c "import sys; print('\\n'.join(sys.path))"
```

#### 2. Async Test Failures

```bash
# Find async methods that need await
grep -r "async def" src/shared/auth/manager.py

# Find test functions calling async methods
grep -r "manager\." src/shared/tests/unit/auth/test_manager_db.py | grep -v "await"
```

#### 3. Database Test Failures

```bash
# Check database model fields
grep -n "Mapped\[" src/orchestrator/app/db/models.py

# Check database URL configuration
grep -r "DATABASE_URL" src/
```

#### 4. Test Database Issues

```bash
# Check test database status
python ops/testing/verify_test_database.py

# Reset test database if corrupted
python ops/testing/manage_test_database.py reset

# Check test environment variables
python ops/testing/load_test_env.py

# Verify database connection
psql-17 -U testuser -d aio-test -c "SELECT 1;"
```

#### 5. Debug Mode

```bash
# Run with verbose output
pytest -vvv

# Run with debug logging
pytest --log-cli-level=DEBUG

# Run tests in isolation
pytest --forked
```

## Conclusion

This guide provides comprehensive patterns and practices for creating reliable, maintainable tests in the AI Operations Platform project. Following these guidelines will help prevent test failures and ensure consistent test quality across the codebase.

For specific issues not covered in this guide, refer to the [Troubleshooting Guide](TROUBLESHOOTING.md) or consult the project's test infrastructure documentation.

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [SQLAlchemy Testing Guide](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [Async Testing with Pytest](https://pytest-asyncio.readthedocs.io/)
- [Test Database Setup Guide](TEST_DATABASE_SETUP.md) - Comprehensive guide for test database configuration
