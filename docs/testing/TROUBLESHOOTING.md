# Test Troubleshooting Guide

## Quick Reference

### Current Test Status

- **Total Tests**: 363
- **Passing**: 318 (87.6%)
- **Failing**: 39 (10.7%)
- **Skipped**: 6 (1.7%)

### Most Common Issues

1. **Async/Await Problems** (30+ failures)
2. **Database Field Mismatches** (Fixed)
3. **Import Path Issues** (Fixed)
4. **Mock Configuration** (5+ failures)

## Issue-Specific Solutions

### 1. Async/Await Issues (30+ failures)

#### Symptoms

```text
RuntimeWarning: coroutine 'UnifiedAuthManager.authenticate_user' was never awaited
SyntaxError: 'await' outside async function
```

#### Root Cause

Authentication manager methods are async but tests are calling them synchronously.

#### Solution

```python
# ❌ Wrong
def test_authenticate_user():
    result = manager.authenticate_user(db, username, password)

# ✅ Correct
@pytest.mark.asyncio
async def test_authenticate_user():
    result = await manager.authenticate_user(db, username, password)
```

#### Quick Fix Script

```bash
# Run this script to fix async issues in auth tests
python temp_ops/fix_async_tests.py
```

### 2. Database Field Mismatches (Fixed ✅)

#### Symptoms

```text
AttributeError: type object 'PromptTemplate' has no attribute 'active'
```

#### Root Cause

Tests were using old field names that don't exist in the current model.

#### Solution Applied

- Changed `PromptTemplate.active` to `PromptTemplate.is_active_version`
- Updated `template.template` to `template.template_content`

### 3. Import Path Issues (Fixed ✅)

#### Symptoms

```text
ModuleNotFoundError: No module named 'shared'
ImportError: No module named 'db'
```

#### Root Cause

Incorrect import paths in test files.

#### Solution Applied

```python
# ❌ Wrong
from db.models import PromptTemplate
from backend.app.db.models import PromptTemplate  # old service name

# ✅ Correct - use absolute imports
from src.orchestrator.app.db.models import PromptTemplate
```

### 4. Mock Configuration Issues (5+ failures)

#### Symptoms

```text
AssertionError: Expected call not made
TypeError: 'AsyncMock' object is not callable
```

#### Root Cause

Improper mock setup for async database sessions.

#### Solution

```python
# ❌ Wrong
db_session = MagicMock()

# ✅ Correct
db_session = AsyncMock(spec=AsyncSession)
```

### 5. Model Management / Gateway Admin 404 (Provider Management, Gateway Metrics)

#### Symptoms

- Browser: `GET http://localhost:4201/api/admin/gateway/providers 404 (Not Found)` or similar for `/api/admin/gateway/metrics/*`.
- UI: "Loading providers..." spinner never finishes; "0 providers total".

#### Root Cause

- Orchestrator proxies these requests to the **inference-gateway** service. If `INFERENCE_GATEWAY_URL` includes `/v1` (e.g. in Docker), the orchestrator was calling `.../v1/admin/providers`, but the gateway serves admin at `/admin/...` (no `/v1`), so the gateway returns 404.
- Code fix: orchestrator now strips a trailing `/v1` from the gateway base URL for admin routes (see `admin_gateway_providers.py` and `admin_gateway_metrics.py`).

#### What to do

1. **Restart the orchestrator** so it loads the fix (strip `/v1` for admin gateway calls).
2. **Ensure the inference-gateway service is running** and reachable from the orchestrator (e.g. `http://inference-gateway:8002` in Docker, or `http://localhost:8002` for local dev).
3. **Local dev only:** set `INFERENCE_GATEWAY_URL` to the gateway root (no `/v1`), e.g. `export INFERENCE_GATEWAY_URL=http://localhost:8002`.
4. **Dev server:** Angular proxy in `proxy.conf.json` forwards `/api/admin/gateway` to the orchestrator; ensure the orchestrator is running on port 8006.

## Step-by-Step Fix Process

### Step 1: Fix Async Authentication Tests

1. **Identify async methods**:

   ```bash
   grep -n "async def" src/shared/auth/manager.py
   ```

2. **Update test functions**:

   ```python
   # Add @pytest.mark.asyncio decorator
   @pytest.mark.asyncio
   async def test_method_name():
       # Add await before method calls
       result = await manager.async_method()
   ```

3. **Fix mock setup**:

   ```python
   # Use AsyncMock for async database sessions
   db_session = AsyncMock(spec=AsyncSession)
   ```

### Step 2: Fix Database Connection Tests

1. **Check database configuration**:

   ```python
   # Ensure test database URL is set
   TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
   ```

2. **Fix async database operations**:

   ```python
   @pytest.mark.asyncio
   async def test_database_operation():
       async with db_manager.get_session() as session:
           result = await session.execute(query)
   ```

### Step 3: Fix LLM Guard Service Tests

1. **Check import paths**:

   ```python
   # Ensure proper imports
   from llm_guard_svc.app.main import app
   ```

2. **Fix validation endpoint tests**:

   ```python
   # Use proper test client
   from fastapi.testclient import TestClient
   client = TestClient(app)
   ```

## Diagnostic Commands

### Check Test Status

```bash
# Run all tests and see summary
bash src/orchestrator/run_tests.sh --cov=app --cov-report=term-missing | tail -20

# Run specific test file
bash src/orchestrator/run_tests.sh src/shared/tests/unit/auth/test_manager_db.py -v

# Run specific test
bash src/orchestrator/run_tests.sh src/shared/tests/unit/auth/test_manager_db.py::test_create_user_duplicate_username -v
```

### Check Async Issues

```bash
# Find async methods that need await
grep -r "async def" src/shared/auth/manager.py

# Find test functions calling async methods
grep -r "manager\." src/shared/tests/unit/auth/test_manager_db.py | grep -v "await"
```

### Check Import Issues

```bash
# Check for import errors
bash src/orchestrator/run_tests.sh --collect-only 2>&1 | grep ImportError

# Check Python path
python -c "import sys; print('\\n'.join(sys.path))"
```

### Check Database Issues

```bash
# Check database model fields
grep -n "Mapped\[" src/orchestrator/app/db/models.py

# Check database URL configuration
grep -r "DATABASE_URL" src/
```

## Automated Fix Scripts

### Fix Async Tests

```python
#!/usr/bin/env python3
# temp_ops/fix_async_tests.py
import re
from pathlib import Path

def fix_async_tests(file_path: Path):
    with open(file_path, 'r') as f:
        content = f.read()

    # Convert def to async def for tests calling async methods
    async_methods = ['authenticate_user', 'create_user', 'store_refresh_token',
                    'validate_refresh_token', 'revoke_refresh_token']

    for method in async_methods:
        # Add @pytest.mark.asyncio and async def
        pattern = rf'def (test_\w+.*?manager\.{method})'
        content = re.sub(pattern, r'@pytest.mark.asyncio\nasync def \1', content)

        # Add await to method calls
        content = re.sub(f'manager\.{method}\\(', f'await manager.{method}(', content)

    with open(file_path, 'w') as f:
        f.write(content)

if __name__ == "__main__":
    fix_async_tests(Path("src/shared/tests/unit/auth/test_manager_db.py"))
```

### Fix Import Paths

```python
#!/usr/bin/env python3
# temp_ops/fix_imports.py
import re
from pathlib import Path

def fix_imports(file_path: Path):
    with open(file_path, 'r') as f:
        content = f.read()

    # Fix common import issues (use absolute imports from src root)
    replacements = {
        'from db.models import': 'from src.orchestrator.app.db.models import',
        'from db.database import': 'from src.orchestrator.app.db.database import',
        'from shared.models import': 'from src.shared.auth.models import',
        'from backend.app.': 'from src.orchestrator.app.',  # Phase 5 rename
    }

    for old, new in replacements.items():
        content = content.replace(old, new)

    with open(file_path, 'w') as f:
        f.write(content)

if __name__ == "__main__":
    fix_imports(Path("test_db_templates.py"))
```

## Prevention Strategies

### 1. Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: test-check
        name: Check test syntax
        entry: bash -c "python -m py_compile src/**/test_*.py"
        language: system
        files: ^src/.*test_.*\.py$
```

### 2. Test Template

```python
# Template for new async tests
import pytest
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_async_method():
    """Test async method with proper mocking."""
    # Setup
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.query().filter().first.return_value = expected_result

    # Execute
    result = await manager.async_method(mock_session, params)

    # Assert
    assert result is not None
    mock_session.commit.assert_awaited_once()
```

### 3. Validation Scripts

```bash
#!/bin/bash
# ops/validate_tests.sh

echo "Checking test syntax..."
find src -name "test_*.py" -exec python -m py_compile {} \;

echo "Checking for async issues..."
grep -r "def test_" src/ | grep -v "@pytest.mark.asyncio" | grep -E "(async def|await)"

echo "Checking import paths..."
grep -r "from [a-z]" src/ | grep -v "from [a-z]" | head -10
```

## Emergency Fixes

### If All Tests Are Failing

1. Check Python path configuration
2. Verify all dependencies are installed
3. Check database connection
4. Review conftest.py files

### If Specific Test File Is Failing

1. Run individual test to isolate issue
2. Check imports and dependencies
3. Verify mock configurations
4. Review test data setup

### If Tests Are Slow

1. Use in-memory databases
2. Mock external services
3. Reduce test data volume
4. Run tests in parallel

## Getting Help

### Debug Mode

```bash
# Run with verbose output
bash src/orchestrator/run_tests.sh -vvv

# Run with debug logging
PYTHONPATH=$PROJECT_ROOT/src bash src/orchestrator/run_tests.sh --log-cli-level=DEBUG
```

### Test Isolation

```bash
# Run tests in isolation
bash src/orchestrator/run_tests.sh --forked

# Run specific test categories
bash src/orchestrator/run_tests.sh -k "not integration"
```

### Coverage Analysis

```bash
# Generate coverage report
bash src/orchestrator/run_tests.sh --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Conclusion

This troubleshooting guide provides quick solutions for the most common test issues in the AI Operations Platform project. Following these patterns will help resolve test failures efficiently and prevent similar issues in the future.

For issues not covered in this guide, refer to the comprehensive [Testing Guide](TESTING_GUIDE.md) or consult the project's test infrastructure documentation.
