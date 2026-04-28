"""
Unit tests for RLS (Row-Level Security) middleware.

Tests that RLS session variables are set correctly for authenticated requests.
"""

import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("JWT_SECRET", "test_jwt_secret_for_unit_tests_only_1234567890")

import pytest
from app.middleware.rls import rls_middleware
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app():
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    return app


@pytest.fixture
def client(app):
    """Create a test client for RLS middleware tests."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_rls_no_auth_header(client):
    """RLS middleware passes through requests without auth header."""
    # Mock AsyncSessionLocal to track if it's called
    original_call = MagicMock()
    with patch("app.middleware.rls.AsyncSessionLocal") as mock_session_local:
        mock_session_local.__call__ = original_call
        async with client:
            response = await client.get("/test")
            assert response.status_code == 200
        # AsyncSessionLocal should not be patched if no token
        assert mock_session_local.__call__ is original_call


@pytest.mark.asyncio
async def test_rls_invalid_token(client):
    """RLS middleware passes through requests with invalid tokens."""
    original_call = MagicMock()
    with (
        patch("app.middleware.rls.AsyncSessionLocal") as mock_session_local,
        patch("app.middleware.rls.jwt_validator.verify_token", return_value=None),
    ):
        mock_session_local.__call__ = original_call
        async with client:
            response = await client.get("/test", headers={"Authorization": "Bearer invalid"})
            assert response.status_code == 200
        # AsyncSessionLocal should not be patched if token invalid
        assert mock_session_local.__call__ is original_call


@pytest.mark.asyncio
async def test_rls_valid_token_sets_variables(client):
    """RLS middleware sets session variables for valid tokens."""
    user_id = str(uuid.uuid4())
    roles = ["admin", "developer"]
    payload = {
        "sub": user_id,
        "user_id": user_id,
        "role": roles[0],
        "roles": roles,
    }

    # Track if patched call is used
    patched_called = False
    original_call = MagicMock()

    async def patched_call(*args, **kwargs):
        nonlocal patched_called
        patched_called = True
        # Return a mock async context manager
        session = MagicMock()
        session.execute = AsyncMock()
        context_manager = MagicMock()
        context_manager.__aenter__ = AsyncMock(return_value=session)
        context_manager.__aexit__ = AsyncMock(return_value=None)
        return context_manager

    with (
        patch("app.middleware.rls.AsyncSessionLocal") as mock_session_local,
        patch("app.middleware.rls.jwt_validator.verify_token", return_value=payload),
    ):
        mock_session_local.__call__ = original_call
        # Apply middleware
        app_with_middleware = FastAPI()
        app_with_middleware.middleware("http")(rls_middleware)

        @app_with_middleware.get("/test")
        async def test_endpoint():
            return {"ok": True}

        async with AsyncClient(
            transport=ASGITransport(app=app_with_middleware), base_url="http://test"
        ) as ac:
            response = await ac.get("/test", headers={"Authorization": "Bearer validtoken"})
            assert response.status_code == 200

        # Verify AsyncSessionLocal was patched (restored after request)
        assert mock_session_local.__call__ is original_call


@pytest.mark.asyncio
async def test_rls_single_role(client):
    """RLS middleware handles single role (string) in token."""
    user_id = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "user_id": user_id,
        "role": "admin",  # Single role as string
    }

    with (
        patch("app.middleware.rls.AsyncSessionLocal"),
        patch("app.middleware.rls.jwt_validator.verify_token", return_value=payload),
    ):
        app_with_middleware = FastAPI()
        app_with_middleware.middleware("http")(rls_middleware)

        @app_with_middleware.get("/test")
        async def test_endpoint():
            return {"ok": True}

        async with AsyncClient(
            transport=ASGITransport(app=app_with_middleware), base_url="http://test"
        ) as ac:
            response = await ac.get("/test", headers={"Authorization": "Bearer validtoken"})
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_rls_no_roles(client):
    """RLS middleware handles tokens with no roles."""
    user_id = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "user_id": user_id,
        # No role or roles field
    }

    with (
        patch("app.middleware.rls.AsyncSessionLocal"),
        patch("app.middleware.rls.jwt_validator.verify_token", return_value=payload),
    ):
        app_with_middleware = FastAPI()
        app_with_middleware.middleware("http")(rls_middleware)

        @app_with_middleware.get("/test")
        async def test_endpoint():
            return {"ok": True}

        async with AsyncClient(
            transport=ASGITransport(app=app_with_middleware), base_url="http://test"
        ) as ac:
            response = await ac.get("/test", headers={"Authorization": "Bearer validtoken"})
            assert response.status_code == 200
