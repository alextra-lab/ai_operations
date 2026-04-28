# Testing Rules for AI Operations Platform

## Test Organization Rules

### Directory Structure
- **Unit tests**: Place in `src/<service>/tests/unit/`
- **Service integration tests**: Place in `src/<service>/tests/integration/`
- **Cross-service integration tests**: Place in `tests/integration/`
- **End-to-end tests**: Place in `tests/e2e/`
- **Test fixtures**: Place in `tests/fixtures/`

### Naming Conventions
- **Test files**: Use `test_*.py` or `*_test.py`
- **Test functions**: Use `test_*` prefix
- **Test classes**: Use `Test*` prefix
- **Fixtures**: Use descriptive names (e.g., `db_session`, `mock_llm_client`)

## Test Execution Rules

### Preferred Execution Methods
1. **Centralized runner** (recommended): `python ops/testing/run_all_tests.py`
2. **Service-specific runner**: `python ops/testing/run_service_tests.py <service>`
3. **Individual service runners**: `bash src/<service>/run_tests.sh` (backward compatible)
4. **Direct pytest**: `pytest tests/integration/` or `pytest tests/e2e/`

### Coverage Requirements
- **Minimum coverage**: 80% for critical components
- **Coverage reports**: Generate with `--coverage` flag
- **HTML reports**: Use `--html-report` for detailed analysis

## Test Writing Rules

### Import Rules
- **Service-specific tests**: Use `from src.<service>.app.X import Y`
- **Cross-service tests**: Use `from tests.conftest import http_client, service_urls`
- **Absolute imports**: Always use absolute imports, never relative

### Async Test Rules
- **Async functions**: Must use `@pytest.mark.asyncio` decorator
- **Async calls**: Always use `await` for async function calls
- **Async fixtures**: Use `AsyncMock` for async database sessions

### Mocking Rules
- **External services**: Always mock (OpenAI, external APIs)
- **Internal services**: Use real services when possible
- **Database operations**: Mock for unit tests, real for integration tests
- **Async mocks**: Use `AsyncMock(spec=AsyncSession)` for database sessions

### Assertion Rules
- **Descriptive assertions**: Use clear, specific assertion messages
- **Error testing**: Test both success and failure scenarios
- **Edge cases**: Test boundary conditions and error states
- **Async assertions**: Use `assert_awaited_once()` for async mock verification

## Test Data Rules

### Fixture Usage
- **Reuse fixtures**: Use existing fixtures when possible
- **Fixture scope**: Use appropriate scope (function, class, module, session)
- **Fixture cleanup**: Ensure proper cleanup in fixtures
- **Test isolation**: Each test should be independent

### Test Data Management
- **Test data**: Use `tests/fixtures/` for shared test data
- **Mock data**: Create realistic mock data
- **Data cleanup**: Clean up test data after tests
- **Data isolation**: Use unique data for each test

## Documentation Rules

### Test Documentation
- **Docstrings**: Write clear docstrings for test functions
- **Comments**: Add comments for complex test logic
- **Examples**: Include usage examples in test documentation
- **Troubleshooting**: Document common issues and solutions

### Script Documentation
- **Script index**: All scripts must be documented in `docs/testing/SCRIPT_INDEX.md`
- **Usage examples**: Include usage examples and dependencies
- **Parameter documentation**: Document all script parameters
- **Error handling**: Document error conditions and solutions

## Quality Rules

### Test Quality
- **Single responsibility**: Each test should test one thing
- **Clear naming**: Test names should describe what is being tested
- **Proper setup**: Use fixtures for test setup and teardown
- **Clean assertions**: Use specific, meaningful assertions

### Code Quality
- **Type hints**: Use type hints in test functions
- **Error handling**: Handle errors gracefully in tests
- **Performance**: Avoid long-running operations in tests
- **Maintainability**: Keep tests simple and maintainable

## Integration Rules

### Service Integration
- **Service boundaries**: Respect service boundaries in tests
- **API contracts**: Test API contracts between services
- **Error propagation**: Test error handling across services
- **Data flow**: Test data flow between services

### End-to-End Testing
- **User workflows**: Test complete user workflows
- **Browser automation**: Use Playwright for E2E tests
- **Real interactions**: Test real user interactions
- **Full system**: Test full system functionality

## Troubleshooting Rules

### Common Issues
- **Import errors**: Check PYTHONPATH and import paths
- **Async issues**: Ensure proper async/await usage
- **Database errors**: Check test database setup
- **Service errors**: Verify services are running

### Debug Procedures
- **Verbose output**: Use `-v` or `--verbose` for detailed output
- **Debug logging**: Use `--log-cli-level=DEBUG` for debug information
- **Test isolation**: Run individual tests to isolate issues
- **Service status**: Check service health before running tests

## Maintenance Rules

### Regular Maintenance
- **Test review**: Regularly review and update tests
- **Coverage monitoring**: Monitor test coverage trends
- **Performance monitoring**: Monitor test execution time
- **Documentation updates**: Keep test documentation current

### Adding New Tests
- **Follow patterns**: Follow existing test patterns
- **Update documentation**: Update relevant documentation
- **Test thoroughly**: Test new tests thoroughly
- **Review process**: Include tests in code review process

## Script Rules

### Script Organization
- **Categorization**: Place scripts in appropriate category directories
- **Naming**: Use descriptive names for scripts
- **Documentation**: Document all scripts in script index
- **Error handling**: Include proper error handling in scripts

### Script Usage
- **Centralized runners**: Prefer centralized test runners
- **Service management**: Use operations scripts for service control
- **Development setup**: Use bootstrap scripts for environment setup
- **Temporary work**: Use temp_scripts for throwaway scripts

## Compliance Rules

### Standards Compliance
- **PEP 8**: Follow PEP 8 style guidelines
- **Type hints**: Use type hints throughout
- **Error handling**: Implement proper error handling
- **Logging**: Use structured logging with context

### Security Compliance
- **No secrets**: Never include secrets in test code
- **Mock external**: Mock all external service calls
- **Test data**: Use test-specific data, not production data
- **Access control**: Test access control and authorization
