"""
Test configuration and fixtures for Inference Gateway.

Configures Python path and environment variables for testing.
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import AsyncGenerator

import pytest


# Prevent pytest from collecting route handlers with test_ prefix as tests
# (e.g., test_provider in admin.py is a route handler, not a test)
def pytest_collection_modifyitems(session, config, items):
    """Filter out route handlers that start with 'test_' from app modules."""
    filtered_items = []
    for item in items:
        # Skip functions from app.* modules (route handlers, not tests)
        if hasattr(item, "obj") and hasattr(item.obj, "__module__"):
            if item.obj.__module__.startswith("app."):
                continue
        filtered_items.append(item)
    items[:] = filtered_items


from httpx import ASGITransport, AsyncClient

try:
    import jwt as pyjwt  # PyJWT library
except ImportError:
    import jose.jwt as pyjwt  # python-jose as fallback

try:
    from pytest_httpx import HTTPXMock
except ImportError:
    HTTPXMock = None  # Optional for unit tests

# Add parent directory to sys.path to make shared module importable
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Set required environment variables for testing
os.environ.setdefault("JWT_SECRET", "test_secret_key_minimum_32_chars_long_for_security")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_ISSUER", "test-gateway")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("TESTING", "true")

# Database configuration (test database on port 5433)
os.environ.setdefault(
    "DATABASE_URL", "postgresql://testuser:test_password_123@localhost:5433/aio-test"
)

# Redis configuration (test Redis on port 6380)
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6380")
os.environ.setdefault("REDIS_URL", "redis://localhost:6380")


@pytest.fixture(scope="session", autouse=True)
def _configure_gateway_services():
    """
    Configure Redis, circuit breaker, and rate limiter singletons for tests.
    Runs before any test that imports these services.
    """
    from shared.config.loader import load_inference_gateway_config

    from app.services.circuit_breaker import configure_circuit_breaker
    from app.services.rate_limiter import configure_rate_limiter
    from app.services.redis_client import configure_redis

    config = load_inference_gateway_config()
    configure_redis(config.redis)
    configure_circuit_breaker(config.circuit_breaker)
    configure_rate_limiter(config.rate_limiter)


def create_test_token(
    user_id: str = "test_user",
    role: str = "user",
    scopes: list[str] | None = None,
) -> str:
    """
    Create a test JWT token with specified scopes.

    Args:
        user_id: User ID for the token
        role: User role
        scopes: List of scopes (e.g., ["inference:chat"])

    Returns:
        JWT token string
    """
    if scopes is None:
        scopes = []

    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "user_id": user_id,
        "role": role,
        "scopes": scopes,
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iat": int(now.timestamp()),
        "iss": "test-gateway",
        "token_type": "access",
    }

    return pyjwt.encode(
        payload,
        os.environ["JWT_SECRET"],
        algorithm=os.environ["JWT_ALGORITHM"],
    )


@pytest.fixture
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Create test client for Inference Gateway.

    Yields:
        AsyncClient configured for testing
    """
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


if HTTPXMock is not None:

    @pytest.fixture
    def mock_openai_stream(httpx_mock):
        """
        Mock OpenAI streaming API responses.

        Simulates SSE streaming with multiple chunks.
        """

        def stream_response(request):
            """Generate streaming response chunks."""
            # Simulate streaming chat completion chunks
            chunks = [
                {
                    "id": "chatcmpl-test123",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "gpt-4o-mini",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"role": "assistant", "content": ""},
                            "finish_reason": None,
                        }
                    ],
                },
                {
                    "id": "chatcmpl-test123",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "gpt-4o-mini",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": "Hello"},
                            "finish_reason": None,
                        }
                    ],
                },
                {
                    "id": "chatcmpl-test123",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "gpt-4o-mini",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": " there"},
                            "finish_reason": None,
                        }
                    ],
                },
                {
                    "id": "chatcmpl-test123",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "gpt-4o-mini",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": "!"},
                            "finish_reason": "stop",
                        }
                    ],
                },
            ]

            # Format as SSE stream
            stream_data = ""
            for chunk in chunks:
                stream_data += f"data: {json.dumps(chunk)}\n\n"
            stream_data += "data: [DONE]\n\n"

            return stream_data

        # Mock OpenAI chat completions endpoint
        httpx_mock.add_callback(
            stream_response,
            url="https://api.openai.com/v1/chat/completions",
            method="POST",
        )

        return httpx_mock
