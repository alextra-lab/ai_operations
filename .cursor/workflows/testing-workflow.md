# Testing Workflow for AI Operations Platform

## Overview

This workflow provides step-by-step guidance for testing in the AI Operations Platform project, following the reorganized testing structure.

## Quick Reference

### Test Execution Commands

```bash
# Run all tests (recommended)
python ops/testing/run_all_tests.py --coverage

# Run specific component
python ops/testing/run_all_tests.py --component backend --coverage

# Run service-specific tests
python ops/testing/run_service_tests.py backend --coverage

# Run integration tests
pytest tests/integration/

# Run E2E tests
pytest tests/e2e/
```

### Test Structure

```
/tests/                    # Cross-service tests
├── integration/          # Multi-service integration tests
├── e2e/                 # End-to-end tests
└── fixtures/            # Test data and fixtures

/src/<service>/tests/     # Service-specific tests
├── unit/                # Unit tests
└── integration/         # Service-internal integration tests
```

## Workflow Steps

### 1. Before Writing Tests

1. **Determine test type:**
   - Unit test → `src/<service>/tests/unit/`
   - Service integration → `src/<service>/tests/integration/`
   - Cross-service integration → `tests/integration/`
   - End-to-end → `tests/e2e/`

2. **Check existing patterns:**
   - Look at similar tests in the same directory
   - Follow naming conventions: `test_*.py`
   - Use existing fixtures when possible

3. **Set up test environment:**
   - Ensure services are running for integration/E2E tests
   - Check environment variables are set
   - Verify dependencies are installed

### 2. Writing Tests

1. **Use proper imports:**
   ```python
   # For service-specific tests
   from src.backend.app.models import User

   # For cross-service tests
   from tests.conftest import http_client, service_urls
   ```

2. **Follow test patterns:**
   ```python
   # Unit test pattern
   def test_function_name():
       # Arrange
       input_data = "test"

       # Act
       result = function_under_test(input_data)

       # Assert
       assert result == expected_output

   # Async test pattern
   @pytest.mark.asyncio
   async def test_async_function():
       result = await async_function()
       assert result is not None
   ```

3. **Use appropriate fixtures:**
   - Database sessions: `db_session`
   - HTTP clients: `http_client`
   - Mock objects: `mock_llm_client`
   - Test data: `test_user_credentials`

### 3. Running Tests

1. **Choose execution method:**
   - **Centralized (recommended):** `python ops/testing/run_all_tests.py`
   - **Service-specific:** `python ops/testing/run_service_tests.py <service>`
   - **Individual service:** `bash src/<service>/run_tests.sh`
   - **Direct pytest:** `pytest tests/integration/`

2. **Add coverage when needed:**
   ```bash
   python ops/testing/run_all_tests.py --coverage --html-report
   ```

3. **Debug failing tests:**
   ```bash
   python ops/testing/run_all_tests.py --component backend --verbose
   ```

### 4. Troubleshooting

1. **Common issues:**
   - Import errors → Check PYTHONPATH and import paths
   - Async issues → Add `@pytest.mark.asyncio` and `await`
   - Database errors → Check test database setup
   - Service not running → Start services with `ops/operations/run_rag_services.sh`

2. **Debug commands:**
   ```bash
   # Check test collection
   pytest --collect-only

   # Run with debug output
   pytest -vvv --log-cli-level=DEBUG

   # Run specific test
   pytest tests/integration/test_specific.py::test_function -v
   ```

3. **Reference documentation:**
   - [Testing Guide](../docs/testing/TESTING_GUIDE.md)
   - [Troubleshooting Guide](../docs/testing/TROUBLESHOOTING.md)
   - [Script Index](../docs/testing/SCRIPT_INDEX.md)

## Best Practices

### Test Organization
- Group related tests in the same file
- Use descriptive test names
- Keep tests focused and atomic
- Use fixtures for common setup

### Mocking Strategy
- Mock external services (OpenAI, etc.)
- Use real internal services when possible
- Mock database operations for unit tests
- Use real database for integration tests

### Error Handling
- Test both success and failure scenarios
- Verify error messages and status codes
- Test timeout and retry logic
- Handle async operations properly

### Performance
- Use parallel test execution when possible
- Clean up resources after tests
- Use appropriate timeouts
- Avoid long-running operations in tests

## Integration with Development

### Pre-commit
- Run tests before committing
- Use `python ops/testing/run_all_tests.py --fail-fast`

### CI/CD
- Use centralized runner in CI
- Generate coverage reports
- Run all test types

### Code Reviews
- Verify test coverage for new features
- Check test quality and patterns
- Ensure proper error handling

## Common Patterns

### Service Integration Test
```python
@pytest.mark.asyncio
async def test_service_integration(http_client, service_urls):
    """Test integration between services."""
    # Test service A
    async with http_client.get(f"{service_urls['backend']}/health") as response:
        assert response.status == 200

    # Test service B
    async with http_client.get(f"{service_urls['retrieval']}/health") as response:
        assert response.status == 200
```

### E2E Test
```python
@pytest.mark.asyncio
async def test_user_workflow(page, frontend_url):
    """Test complete user workflow."""
    await page.goto(frontend_url)
    await page.click("button[data-testid='login']")
    # ... perform user actions
    assert "Dashboard" in await page.text_content("h1")
```

### Unit Test with Mocking
```python
def test_function_with_mock(mock_database):
    """Test function with mocked dependencies."""
    mock_database.query.return_value.filter.return_value.first.return_value = mock_user
    result = function_under_test(mock_database)
    assert result is not None
    mock_database.commit.assert_called_once()
```

## Resources

- **Main Documentation:** `docs/testing/TESTING_GUIDE.md`
- **Troubleshooting:** `docs/testing/TROUBLESHOOTING.md`
- **Script Reference:** `docs/testing/SCRIPT_INDEX.md`
- **Reorganization Summary:** `docs/testing/REORGANIZATION_SUMMARY.md`
