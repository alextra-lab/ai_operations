"""
End-to-end test configuration.

This file provides fixtures and configuration for E2E tests that test
the complete user workflow from frontend to backend.
"""

import asyncio
from unittest.mock import patch

import pytest
from playwright.async_api import async_playwright


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def browser():
    """Playwright browser instance for E2E tests."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser):
    """Playwright page instance for E2E tests."""
    page = await browser.new_page()
    yield page
    await page.close()


@pytest.fixture
def frontend_url():
    """Frontend URL for E2E tests."""
    return "http://localhost:4200"


@pytest.fixture
def backend_url():
    """Backend URL for E2E tests."""
    return "http://localhost:8000"


@pytest.fixture
def test_user_data():
    """Test user data for E2E authentication."""
    return {
        "username": "e2e_test_user",
        "password": "e2e_test_password",
        "email": "e2e@example.com",
    }


@pytest.fixture
def mock_external_services():
    """Mock external services for E2E tests."""
    with patch("app.orchestrator.llm_client.LLMClient") as mock_llm:
        mock_llm.return_value.generate_response.return_value = {
            "content": "Mock E2E response",
            "usage": {"tokens": 100},
        }
        yield mock_llm
