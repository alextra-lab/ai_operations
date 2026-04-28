import os
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

# Add the backend directory to Python path so 'app' module can be imported
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Also add src directory for shared modules
src_dir = backend_dir.parent
sys.path.insert(0, str(src_dir))

# Set environment variables for testing
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("POSTGRES_USER", "testuser")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password_123")
# Load test environment variables from env.test.local
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "ops" / "testing"))
from load_test_env import load_test_env  # type: ignore[import-not-found]

load_test_env()

# Override with unit test specific values
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5433")
os.environ.setdefault("POSTGRES_DB", "aio-test")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://testuser:test_password_123@localhost:5433/aio-test",
)
os.environ.setdefault("OPENAI_API_KEY", "test_openai_api_key_for_backend_tests")
os.environ.setdefault("INFERENCE_GATEWAY_URL", "http://inference-gateway-test:8002")
os.environ.setdefault("JWT_SECRET", "test_jwt_secret_for_testing_only_32_chars")

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession


# Patch LLMClient globally before any orchestrator code is imported
# Create a mock that doesn't interfere with async operations
def create_mock_llm_client(*_args, **_kwargs):
    from unittest.mock import MagicMock

    mock = MagicMock()
    # Ensure the mock doesn't break when used in async contexts
    mock.return_value = mock
    return mock


llmclient_patch = patch("app.orchestrator.llm_client.LLMClient", side_effect=create_mock_llm_client)
llmclient_patch.start()

# Patch init_database globally to prevent lifespan issues
init_database_patch = patch("shared.auth.init_database", new_callable=AsyncMock)
init_database_patch.start()


@pytest.fixture(scope="session", autouse=True)
def stop_global_patches():
    yield
    llmclient_patch.stop()
    init_database_patch.stop()


# =============================================================================
# ASYNC DATABASE FIXTURES (ADR-022 - P5-A23: All sync patterns removed)
# =============================================================================


@pytest_asyncio.fixture
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async database session fixture for tests.

    Provides an async session that rolls back after each test.
    Use this for migrated async tests (ADR-022).
    """
    from app.db.database import AsyncSessionLocal, init_db

    # Initialize tables (idempotent)
    await init_db()

    async with AsyncSessionLocal() as session:
        yield session
        # Rollback any uncommitted changes after test
        await session.rollback()


@pytest_asyncio.fixture
async def clean_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async database session fixture that commits changes.

    Use this when you need changes to persist for the test.
    """
    from app.db.database import AsyncSessionLocal, init_db

    await init_db()

    async with AsyncSessionLocal() as session:
        yield session
        await session.commit()
