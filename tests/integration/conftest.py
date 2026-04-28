"""
Integration test configuration.

This file provides fixtures and configuration specific to integration tests
that test interactions between services.

P5-A20: Migrated to async database patterns (ADR-022).
All integration tests now use async_db_session.
"""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import aiohttp
import pytest
import pytest_asyncio

# Import FastAPI test client
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import admin_required, get_current_user

# Import database and models
from src.orchestrator.app.db.database import AsyncSessionLocal, init_db
from src.orchestrator.app.main import app
from src.shared.auth.models import TokenPayload, User, UserRole


@pytest_asyncio.fixture
async def http_client():
    """HTTP client for making requests to services."""
    async with aiohttp.ClientSession() as client:
        yield client


@pytest.fixture
def service_urls():
    """URLs for all services in integration tests."""
    return {
        "backend": "http://localhost:8000",
        "retrieval": "http://localhost:8003",
        "embedding": "http://localhost:8002",
        "llm_guard": "http://localhost:8004",
    }


@pytest.fixture
def test_document_data():
    """Sample document data for testing."""
    return {
        "filename": "test_document.pdf",
        "content": "This is a test document for integration testing.",
        "metadata": {
            "title": "Test Document",
            "author": "Test Author",
            "created_date": "2024-01-01",
        },
    }


@pytest.fixture
def mock_database_session():
    """Mock database session for integration tests."""
    return AsyncMock()


@pytest.fixture
def test_query_data():
    """Sample query data for testing."""
    return {"query": "What is the main topic of this document?", "filters": {}, "limit": 10}


# =============================================================================
# ASYNC DATABASE FIXTURES (ADR-022 - P5-A20)
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


# Backward compatibility: db_session is now async
@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an async database session (alias for async_db_session)."""
    await init_db()

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture
async def test_user(async_db_session: AsyncSession):
    """Create a test user for integration tests."""
    # Use timestamp to ensure unique username
    timestamp = int(datetime.now(UTC).timestamp() * 1000000)
    username = f"testuser_{timestamp}"
    email = f"test_{timestamp}@example.com"

    user = User(
        id=uuid.uuid4(),
        username=username,
        full_name="Test User",
        email=email,
        hashed_password="hashed_password_123",
        role=UserRole.USER,
        is_active=True,
        center_id="test-center",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)

    yield user

    # Cleanup: rollback in fixture handles cleanup automatically


@pytest_asyncio.fixture
async def admin_user(async_db_session: AsyncSession):
    """Create an admin user for integration tests."""
    # Use timestamp to ensure unique username
    timestamp = int(datetime.now(UTC).timestamp() * 1000000)
    username = f"adminuser_{timestamp}"
    email = f"admin_{timestamp}@example.com"

    user = User(
        id=uuid.uuid4(),
        username=username,
        full_name="Admin User",
        email=email,
        hashed_password="hashed_password_123",
        role=UserRole.ADMIN,
        is_active=True,
        center_id="admin-center",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)

    yield user

    # Cleanup: rollback in fixture handles cleanup automatically


@pytest_asyncio.fixture
async def async_client():
    """Create an async HTTP client for API testing."""
    async with AsyncClient(base_url="http://test") as client:
        yield client


@pytest.fixture
def admin_token():
    """Create a mock admin JWT token."""
    # In a real test, this would be a properly signed JWT token
    # For now, we'll use a mock token that the auth system can recognize
    return "mock_admin_token_for_testing"


@pytest.fixture
def user_token():
    """Create a mock user JWT token."""
    # In a real test, this would be a properly signed JWT token
    # For now, we'll use a mock token that the auth system can recognize
    return "mock_user_token_for_testing"


@pytest.fixture
def mock_admin_user():
    """Mock admin user for authentication."""
    return TokenPayload(
        sub="admin_user",
        user_id=str(uuid.uuid4()),
        role=UserRole.ADMIN,
        exp=int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        iat=int(datetime.now(UTC).timestamp()),
        iss="test",
        token_type="access",
    )


@pytest.fixture
def mock_regular_user():
    """Mock regular user for authentication."""
    return TokenPayload(
        sub="regular_user",
        user_id=str(uuid.uuid4()),
        role=UserRole.USER,
        exp=int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        iat=int(datetime.now(UTC).timestamp()),
        iss="test",
        token_type="access",
    )


@pytest.fixture
def authenticated_admin_client(mock_admin_user):
    """Create a test client with admin authentication."""
    from fastapi.testclient import TestClient

    def mock_get_current_user():
        return mock_admin_user

    def mock_admin_required():
        return mock_admin_user

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[admin_required] = mock_admin_required

    with TestClient(app) as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_user_client(mock_regular_user):
    """Create a test client with regular user authentication."""
    from fastapi import HTTPException, status
    from fastapi.testclient import TestClient

    def mock_get_current_user():
        return mock_regular_user

    def mock_admin_required():
        # This should raise 403 for non-admin users
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient role. Required: ['admin'], got: {mock_regular_user.role}",
        )

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[admin_required] = mock_admin_required

    with TestClient(app) as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()
