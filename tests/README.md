# Cross-Service Tests

## Overview

This directory contains integration and end-to-end tests that span multiple services in the AI Operations Platform project.

## Directory Structure

```
/tests/
├── integration/       # Multi-service integration tests
├── e2e/              # End-to-end tests
├── fixtures/         # Test data and fixtures
├── conftest.py       # Shared test configuration
└── README.md         # This file
```

## Test Categories

### Integration Tests (`integration/`)

Tests that verify interactions between multiple services without involving the full user interface.

**Examples:**
- `test_retrieval_endpoints.py` - Test corpus service API endpoints
- `test_document_upload.py` - Test document upload flow across services
- `test_document_processing_embedding.py` - Test document processing pipeline

**Characteristics:**
- Test service-to-service communication
- Use HTTP clients to make API calls
- Mock external dependencies
- Focus on data flow and API contracts

### End-to-End Tests (`e2e/`)

Tests that verify complete user workflows from frontend to backend.

**Examples:**
- `test_security_e2e.py` - Test security features across frontend and backend
- `verify_endtoend_ingestion_flow.py` - Test complete document ingestion workflow

**Characteristics:**
- Test complete user workflows
- Use browser automation (Playwright)
- Test real user interactions
- Verify full system functionality

### Test Fixtures (`fixtures/`)

Shared test data, mock objects, and utilities used across tests.

**Examples:**
- Sample documents for testing
- Mock API responses
- Test user credentials
- Database test data

## Running Tests

### Integration Tests
```bash
# Run all integration tests
pytest tests/integration/

# Run specific integration test
pytest tests/integration/test_retrieval_endpoints.py

# Run with verbose output
pytest tests/integration/ -v
```

### End-to-End Tests
```bash
# Run all E2E tests
pytest tests/e2e/

# Run specific E2E test
pytest tests/e2e/test_security_e2e.py

# Run with browser visible (for debugging)
pytest tests/e2e/ --headed
```

### All Cross-Service Tests
```bash
# Run all tests in this directory
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Test Configuration

### Prerequisites

1. **Services Running**: All required services must be running
   ```bash
   # Start all services
   bash ops/operations/run_rag_services.sh
   ```

2. **Dependencies Installed**: Install test dependencies
   ```bash
   pip install pytest playwright aiohttp
   ```

3. **Browser Setup**: Install Playwright browsers
   ```bash
   playwright install
   ```

### Environment Variables

Tests use the following environment variables:
- `TESTING=true` - Enables test mode
- `DATABASE_URL` - Test database connection
- `OPENAI_API_KEY` - Mock API key for testing

### Service URLs

Tests expect services to be running on these ports:
- Backend: `http://localhost:8000`
- Corpus: `http://localhost:8003`
- Embedding: `http://localhost:8002`
- LLM Guard: `http://localhost:8004`
- Frontend: `http://localhost:4200`

## Writing Tests

### Integration Test Template
```python
import pytest
import aiohttp
from tests.integration.conftest import http_client, service_urls

@pytest.mark.asyncio
async def test_service_integration(http_client, service_urls):
    """Test integration between services."""
    # Make API call to service A
    async with http_client.get(f"{service_urls['backend']}/health") as response:
        assert response.status == 200

    # Make API call to service B
    async with http_client.get(f"{service_urls['retrieval']}/health") as response:
        assert response.status == 200
```

### E2E Test Template
```python
import pytest
from tests.e2e.conftest import page, frontend_url

@pytest.mark.asyncio
async def test_user_workflow(page, frontend_url):
    """Test complete user workflow."""
    # Navigate to frontend
    await page.goto(frontend_url)

    # Perform user actions
    await page.click("button[data-testid='login']")
    await page.fill("input[name='username']", "testuser")
    await page.fill("input[name='password']", "password")
    await page.click("button[type='submit']")

    # Verify results
    await page.wait_for_selector("h1")
    assert "Dashboard" in await page.text_content("h1")
```

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

## Troubleshooting

### Common Issues

#### Services Not Running
```bash
# Check if services are running
docker ps

# Start services
bash ops/operations/run_rag_services.sh
```

#### Database Connection Issues
```bash
# Reset test database
bash ops/testing/reset_test_database.sh
```

#### Browser Issues
```bash
# Install Playwright browsers
playwright install

# Run with visible browser for debugging
pytest tests/e2e/ --headed
```

#### Import Errors
```bash
# Check Python path
python -c "import sys; print('\\n'.join(sys.path))"

# Run from project root
cd /path/to/project
pytest tests/
```

### Debug Mode
```bash
# Run with verbose output
pytest tests/ -vvv

# Run with debug logging
pytest tests/ --log-cli-level=DEBUG

# Run specific test with debugging
pytest tests/integration/test_retrieval_endpoints.py::test_specific_function -vvv
```

## Related Documentation

- [Testing Guide](../docs/testing/TESTING_GUIDE.md) - Comprehensive testing practices
- [Script Index](../docs/testing/SCRIPT_INDEX.md) - Test execution scripts
- [Developer Guide](../docs/development/DEVELOPER_GUIDE.md) - Development practices

## Maintenance

### Regular Tasks
- Update test data and fixtures
- Review and update test coverage
- Clean up obsolete tests
- Update documentation

### Adding New Tests
1. Place in appropriate directory (integration/ or e2e/)
2. Use existing fixtures when possible
3. Follow naming conventions
4. Add to test documentation
5. Test thoroughly before committing

### Updating Tests
1. Update when APIs change
2. Maintain backward compatibility when possible
3. Update documentation
4. Test changes thoroughly
