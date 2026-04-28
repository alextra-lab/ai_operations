"""
Shared pytest configuration for cross-service tests.

This file provides common fixtures and configuration for integration and E2E tests
that span multiple services. Credentials and secrets must come from env only:
source config/env/env.test (copy from config/env/env.test.template) before running tests.
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add src directory to Python path for cross-service tests
_project_root = Path(__file__).resolve().parent.parent
src_dir = _project_root / "src"
sys.path.insert(0, str(src_dir))

# Load test env from canonical file (gitignored; no secrets in repo)
_env_test = _project_root / "config" / "env" / "env.test"
if _env_test.exists():
    with open(_env_test) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))
# Non-secret defaults only when env.test is missing (CI/convenience)
# Credentials (POSTGRES_PASSWORD, JWT_SECRET, DATABASE_URL, etc.) must come from config/env/env.test
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5433")
os.environ.setdefault("POSTGRES_DB", "aio-test")
os.environ.setdefault("INFERENCE_GATEWAY_URL", "http://inference-gateway-test:8002")


# Global patches for external services in integration tests
@pytest.fixture(scope="session", autouse=True)
def patch_external_services():
    """Patch external services globally for integration tests."""
    with patch(
        "src.orchestrator.app.orchestrator.llm_client.LLMClient", side_effect=create_mock_llm_client
    ):
        yield


def create_mock_llm_client(*args, **kwargs):
    """Create mock LLM client for integration tests."""
    mock = AsyncMock()
    mock.return_value = mock
    return mock


@pytest.fixture(scope="session")
def test_services_config():
    """Configuration for test services."""
    return {
        "backend_url": "http://localhost:8000",
        "retrieval_url": "http://localhost:8003",
        "embedding_url": "http://localhost:8002",
        "llm_guard_url": "http://localhost:8004",
        "frontend_url": "http://localhost:4200",
    }


@pytest.fixture
def test_user_credentials():
    """Test user credentials for authentication."""
    return {"username": "testuser", "password": "password", "email": "test@example.com"}


@pytest.fixture
def test_jwt_secret():
    """JWT secret for test tokens."""
    return "test_jwt_secret_for_integration_tests"
