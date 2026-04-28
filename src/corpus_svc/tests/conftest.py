"""
Shared pytest fixtures for retrieval service tests.
"""

import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Set test environment variables
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("JWT_SECRET", "test_jwt_secret_for_testing_only_min_32_chars_long")
os.environ.setdefault("POSTGRES_USER", "testuser")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password_123")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5433")
os.environ.setdefault("POSTGRES_DB", "aio-test")

# Database URL for tests
TEST_DATABASE_URL = (
    f"postgresql+asyncpg://"
    f"{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}"
    f"/{os.environ['POSTGRES_DB']}"
)


@pytest_asyncio.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create an async database session for testing.
    Each test gets a fresh session with transaction rollback.
    """
    # Create async engine
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,  # Disable connection pooling for tests
        echo=False,  # Set to True for SQL debugging
    )

    # Create session factory
    async_session_factory = sessionmaker(
        bind=engine,  # type: ignore[arg-type]
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create session
    async with async_session_factory() as session:  # type: ignore[attr-defined]
        yield session
        # Rollback at end of test
        await session.rollback()

    # Dispose engine
    await engine.dispose()
