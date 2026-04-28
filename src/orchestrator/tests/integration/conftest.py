"""
Shared fixtures for integration tests.

P5-A17: Migrated to async database patterns (ADR-022).
All integration tests now use async_db_session.
"""

import os
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

# Load test environment variables
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "ops" / "testing"))
from load_test_env import load_test_env  # type: ignore[import-not-found]

load_test_env()

# Override with integration test specific values only if not already set
# This allows env.test to provide values, but provides defaults for CI/local testing
if "POSTGRES_HOST" not in os.environ:
    os.environ["POSTGRES_HOST"] = "localhost"
if "POSTGRES_PORT" not in os.environ:
    os.environ["POSTGRES_PORT"] = "5433"
if "POSTGRES_DB" not in os.environ:
    os.environ["POSTGRES_DB"] = "aio-test"
if "POSTGRES_USER" not in os.environ:
    os.environ["POSTGRES_USER"] = os.environ.get("TEST_DB_USER", "testuser")
if "POSTGRES_PASSWORD" not in os.environ:
    os.environ["POSTGRES_PASSWORD"] = os.environ.get("TEST_DB_PASSWORD", "test_password_123")

# Construct DATABASE_URL from components if not explicitly set
if "DATABASE_URL" not in os.environ:
    db_user = os.environ["POSTGRES_USER"]
    db_password = os.environ["POSTGRES_PASSWORD"]
    db_host = os.environ["POSTGRES_HOST"]
    db_port = os.environ["POSTGRES_PORT"]
    db_name = os.environ["POSTGRES_DB"]
    os.environ["DATABASE_URL"] = (
        f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )

import pytest_asyncio
from app.db.database import AsyncSessionLocal, init_db
from sqlalchemy.ext.asyncio import AsyncSession

# =============================================================================
# ASYNC DATABASE FIXTURES (ADR-022)
# =============================================================================


@pytest_asyncio.fixture
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an async database session for integration testing."""
    await init_db()

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
