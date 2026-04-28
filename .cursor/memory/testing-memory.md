# Testing Memory for Cursor AI

## Project Testing Status (December 2024)

### Reorganization Completed
- ✅ **Documentation consolidated**: 6 files → 3 comprehensive documents
- ✅ **Scripts reorganized**: Clear categorization by purpose
- ✅ **Integration tests moved**: From temp_scripts to proper locations
- ✅ **Centralized runners created**: New test execution options
- ✅ **Backward compatibility maintained**: All existing runners still work

### Current Test Structure
```
/tests/                    # Cross-service tests
├── integration/          # Multi-service integration tests
├── e2e/                 # End-to-end tests
└── fixtures/            # Test data and fixtures

/src/<service>/tests/     # Service-specific tests
├── unit/                # Unit tests
└── integration/         # Service-internal integration tests
```

### Scripts Organization
```
/ops/
├── bootstrap/          # System initialization
├── ci/                # CI/CD scripts
├── cli/               # Command-line utilities
├── operations/        # Operational scripts (moved from testing/)
├── testing/           # Test execution utilities
└── migrations/        # Database migrations
```

## Key Commands

### Test Execution
```bash
# Centralized (recommended)
python ops/testing/run_all_tests.py --coverage
python ops/testing/run_all_tests.py --component backend

# Service-specific
python ops/testing/run_service_tests.py backend --coverage

# Individual service (backward compatible)
bash src/backend/run_tests.sh --cov=app --cov-report=term-missing
bash src/retrieval/run_tests.sh --cov=app --cov-report=term-missing
bash src/shared/run_tests.sh --cov=shared/auth --cov-report=term-missing

# Direct pytest
pytest tests/integration/
pytest tests/e2e/
```

### Service Management
```bash
# Start all services
bash ops/operations/run_rag_services.sh

# Rebuild service
bash ops/operations/rebuild_retrieval_service.sh

# Reset test database
bash ops/operations/reset_and_migrate_test_db.sh
```

## Documentation Locations

### Primary Documentation
- **Main guide**: `docs/testing/TESTING_GUIDE.md`
- **Troubleshooting**: `docs/testing/TROUBLESHOOTING.md`
- **Script index**: `docs/testing/SCRIPT_INDEX.md`
- **Reorganization summary**: `docs/testing/REORGANIZATION_SUMMARY.md`

### Deprecated Documentation
- **Old location**: `docs/development/Testing/` (marked as deprecated)
- **Migration notice**: `docs/development/Testing/DEPRECATED.md`

## Common Patterns

### Unit Test Pattern
```python
def test_function_name():
    # Arrange
    input_data = "test"

    # Act
    result = function_under_test(input_data)

    # Assert
    assert result == expected_output
```

### Async Test Pattern
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### Integration Test Pattern
```python
@pytest.mark.asyncio
async def test_service_integration(http_client, service_urls):
    async with http_client.get(f"{service_urls['backend']}/health") as response:
        assert response.status == 200
```

## Service URLs (for integration tests)
- Backend: `http://localhost:8000`
- Retrieval: `http://localhost:8003`
- Embedding: `http://localhost:8002`
- LLM Guard: `http://localhost:8004`
- Frontend: `http://localhost:4200`

## Common Issues & Solutions

### Import Errors
- **Problem**: `ModuleNotFoundError: No module named 'shared'`
- **Solution**: Check PYTHONPATH and use absolute imports
- **Command**: `python -c "import sys; print('\\n'.join(sys.path))"`

### Async Issues
- **Problem**: `RuntimeWarning: coroutine was never awaited`
- **Solution**: Add `@pytest.mark.asyncio` and use `await`
- **Pattern**: `@pytest.mark.asyncio` + `async def` + `await`

### Database Errors
- **Problem**: Database connection failures
- **Solution**: Check test database setup and environment variables
- **Command**: `bash ops/operations/reset_and_migrate_test_db.sh`

### Service Not Running
- **Problem**: Integration tests fail with connection errors
- **Solution**: Start services with operations scripts
- **Command**: `bash ops/operations/run_rag_services.sh`

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

## Recent Changes

### December 2024 Reorganization
- Moved operational scripts from `ops/testing/` to `ops/operations/`
- Created new `temp_ops/` directory (gitignored) for temporary scripts
- Moved integration tests from `temp_ops/` to `tests/integration/` and `tests/e2e/`
- Created centralized test runners while preserving individual service runners
- Consolidated testing documentation from 6 files to 3 comprehensive documents

### Backward Compatibility
- All existing `run_tests.sh` scripts continue working unchanged
- All existing documentation references remain valid
- No breaking changes to current workflows
- Gradual adoption of new centralized runners

## Quick Reference

### When to Use What
- **Unit tests**: `src/<service>/tests/unit/` - Test individual functions/classes
- **Service integration**: `src/<service>/tests/integration/` - Test service-internal integration
- **Cross-service integration**: `tests/integration/` - Test interactions between services
- **End-to-end**: `tests/e2e/` - Test complete user workflows
- **Temporary scripts**: `temp_ops/` - Throwaway debug/test scripts

### Test Execution Priority
1. **Centralized runner**: `python ops/testing/run_all_tests.py` (recommended)
2. **Service-specific runner**: `python ops/testing/run_service_tests.py <service>`
3. **Individual service runners**: `bash src/<service>/run_tests.sh` (backward compatible)
4. **Direct pytest**: `pytest tests/integration/` or `pytest tests/e2e/`

### Documentation Priority
1. **Main guide**: `docs/testing/TESTING_GUIDE.md` (comprehensive practices)
2. **Troubleshooting**: `docs/testing/TROUBLESHOOTING.md` (issue resolution)
3. **Script index**: `docs/testing/SCRIPT_INDEX.md` (script reference)
4. **Reorganization summary**: `docs/testing/REORGANIZATION_SUMMARY.md` (change details)
