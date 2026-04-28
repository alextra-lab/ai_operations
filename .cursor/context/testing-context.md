# Testing Context for Cursor AI

## Quick Reference

### Test Execution Commands
```bash
# Centralized (recommended)
python ops/testing/run_all_tests.py --coverage
python ops/testing/run_all_tests.py --component backend
python ops/testing/run_all_tests.py --component integration

# Service-specific
python ops/testing/run_service_tests.py backend --coverage
python ops/testing/run_service_tests.py retrieval --type unit

# Individual service (backward compatible)
bash src/backend/run_tests.sh --cov=app --cov-report=term-missing
bash src/retrieval/run_tests.sh --cov=app --cov-report=term-missing
bash src/shared/run_tests.sh --cov=shared/auth --cov-report=term-missing

# Direct pytest
pytest tests/integration/
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

/temp_ops/            # Temporary scripts (gitignored)
```

### Scripts Organization
```
/ops/
├── bootstrap/          # System initialization
├── ci/                # CI/CD scripts
├── cli/               # Command-line utilities
├── operations/        # Operational scripts
├── testing/           # Test execution utilities
└── migrations/        # Database migrations
```

## Key Files

### Test Configuration
- `tests/conftest.py` - Shared test configuration
- `tests/integration/conftest.py` - Integration test fixtures
- `tests/e2e/conftest.py` - E2E test fixtures
- `src/<service>/tests/conftest.py` - Service-specific fixtures

### Test Runners
- `ops/testing/run_all_tests.py` - Master test runner
- `ops/testing/run_service_tests.py` - Service-specific runner
- `src/<service>/run_tests.sh` - Individual service runners

### Documentation
- `docs/testing/TESTING_GUIDE.md` - Main testing guide
- `docs/testing/TROUBLESHOOTING.md` - Troubleshooting guide
- `docs/testing/SCRIPT_INDEX.md` - Script reference
- `docs/testing/REORGANIZATION_SUMMARY.md` - Change summary

## Common Patterns

### Unit Test
```python
def test_function_name():
    # Arrange
    input_data = "test"

    # Act
    result = function_under_test(input_data)

    # Assert
    assert result == expected_output
```

### Async Test
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### Integration Test
```python
@pytest.mark.asyncio
async def test_service_integration(http_client, service_urls):
    async with http_client.get(f"{service_urls['backend']}/health") as response:
        assert response.status == 200
```

### E2E Test
```python
@pytest.mark.asyncio
async def test_user_workflow(page, frontend_url):
    await page.goto(frontend_url)
    await page.click("button[data-testid='login']")
    # ... perform user actions
    assert "Dashboard" in await page.text_content("h1")
```

## Troubleshooting

### Common Issues
- **Import errors** → Check PYTHONPATH and import paths
- **Async issues** → Add `@pytest.mark.asyncio` and `await`
- **Database errors** → Check test database setup
- **Service not running** → Start with `ops/operations/run_rag_services.sh`

### Debug Commands
```bash
# Check test collection
pytest --collect-only

# Run with debug output
pytest -vvv --log-cli-level=DEBUG

# Run specific test
pytest tests/integration/test_specific.py::test_function -v
```

## Best Practices

1. **Test Organization**: Group related tests, use descriptive names
2. **Mocking**: Mock external services, use real internal services
3. **Error Handling**: Test success and failure scenarios
4. **Performance**: Use parallel execution, clean up resources
5. **Documentation**: Update test docs when adding new tests

## Service URLs (for integration tests)
- Backend: `http://localhost:8000`
- Retrieval: `http://localhost:8003`
- Embedding: `http://localhost:8002`
- LLM Guard: `http://localhost:8004`
- Frontend: `http://localhost:4200`
