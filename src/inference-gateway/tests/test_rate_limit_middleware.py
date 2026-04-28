"""
Integration tests for rate limiting middleware.

Tests:
- Middleware integration with FastAPI
- 429 responses with OpenAI format
- Retry-After headers
- Rate limit headers (X-RateLimit-*)
- Skip paths
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from shared.auth.models import TokenPayload  # type: ignore

from app.middleware.rate_limit_middleware import RateLimitMiddleware
from app.services.rate_limiter import RateLimitResult


class TestRateLimitMiddleware:
    """Tests for rate limiting middleware."""

    @pytest.mark.asyncio
    async def test_middleware_allows_request_within_limit(self):
        """Test that middleware allows request when within rate limit."""
        # Create test app
        app = FastAPI()

        @app.get("/v1/test")
        async def test_endpoint():
            return JSONResponse(status_code=200, content={"message": "success"})

        # Add middleware
        app.add_middleware(RateLimitMiddleware)

        # Mock rate limiter to allow
        with patch("app.services.rate_limiter.get_rate_limiter") as mock_get_limiter:
            mock_limiter = MagicMock()
            mock_limiter.check_all_limits = AsyncMock(return_value=RateLimitResult(allowed=True))
            mock_get_limiter.return_value = mock_limiter

            # Create test client
            from fastapi.testclient import TestClient

            client = TestClient(app)

            # Mock token in request state
            def mock_request_factory(*args, **kwargs):
                request = Request(*args, **kwargs)
                request.state.token = TokenPayload(
                    sub="user-123",
                    user_id="user-123",
                    roles=["user"],
                    exp=0,
                    iat=0,
                    iss="test",
                    token_type="access",
                )
                return request

            # Send request
            response = client.get("/v1/test")

            assert response.status_code == 200
            assert response.json() == {"message": "success"}

    @pytest.mark.asyncio
    async def test_middleware_denies_request_at_limit(self):
        """Test that middleware returns 429 when rate limit exceeded."""
        # Create test app
        app = FastAPI()

        @app.get("/v1/test")
        async def test_endpoint():
            return JSONResponse(status_code=200, content={"message": "success"})

        # Add middleware
        middleware = RateLimitMiddleware(app)

        # Mock rate limiter to deny
        with patch.object(middleware, "rate_limiter") as mock_limiter:
            mock_limiter.check_all_limits = AsyncMock(
                return_value=RateLimitResult(
                    allowed=False,
                    retry_after_seconds=30,
                    limit_type="global",
                    current_count=550,
                    limit=550,
                )
            )

            # Create mock request with token
            request = MagicMock()
            request.url.path = "/v1/test"
            request.state.token = TokenPayload(
                sub="user-123",
                user_id="user-123",
                roles=["user"],
                exp=0,
                iat=0,
                iss="test",
                token_type="access",
            )

            # Create mock call_next
            async def mock_call_next(req):
                return JSONResponse(status_code=200, content={"message": "success"})

            # Call middleware
            response = await middleware.dispatch(request, mock_call_next)

            assert response.status_code == 429
            assert "Retry-After" in response.headers
            assert response.headers["Retry-After"] == "30"
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers

    @pytest.mark.asyncio
    async def test_middleware_skips_health_endpoint(self):
        """Test that middleware skips rate limiting for /health."""
        app = FastAPI()

        @app.get("/health")
        async def health():
            return JSONResponse(status_code=200, content={"status": "healthy"})

        middleware = RateLimitMiddleware(app)

        # Mock rate limiter (should not be called)
        with patch.object(middleware, "rate_limiter") as mock_limiter:
            mock_limiter.check_all_limits = AsyncMock(side_effect=Exception("Should not be called"))

            # Create mock request
            request = MagicMock()
            request.url.path = "/health"
            request.state.token = None

            # Create mock call_next
            async def mock_call_next(req):
                return JSONResponse(status_code=200, content={"status": "healthy"})

            # Call middleware
            response = await middleware.dispatch(request, mock_call_next)

            # Should skip rate limiting
            assert response.status_code == 200
            mock_limiter.check_all_limits.assert_not_called()

    @pytest.mark.asyncio
    async def test_middleware_skips_admin_endpoints(self):
        """Test that middleware skips rate limiting for /admin/*."""
        app = FastAPI()

        @app.get("/admin/rate-limits")
        async def admin_endpoint():
            return JSONResponse(status_code=200, content={"limits": []})

        middleware = RateLimitMiddleware(app)

        # Mock rate limiter (should not be called)
        with patch.object(middleware, "rate_limiter") as mock_limiter:
            mock_limiter.check_all_limits = AsyncMock(side_effect=Exception("Should not be called"))

            # Create mock request
            request = MagicMock()
            request.url.path = "/admin/rate-limits"
            request.state.token = None

            # Create mock call_next
            async def mock_call_next(req):
                return JSONResponse(status_code=200, content={"limits": []})

            # Call middleware
            response = await middleware.dispatch(request, mock_call_next)

            # Should skip rate limiting
            assert response.status_code == 200
            mock_limiter.check_all_limits.assert_not_called()

    @pytest.mark.asyncio
    async def test_middleware_no_token_passes_through(self):
        """Test that middleware passes through when no token (for 401 from auth)."""
        app = FastAPI()

        @app.get("/v1/test")
        async def test_endpoint():
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})

        middleware = RateLimitMiddleware(app)

        # Mock rate limiter (should not be called)
        with patch.object(middleware, "rate_limiter") as mock_limiter:
            mock_limiter.check_all_limits = AsyncMock(side_effect=Exception("Should not be called"))

            # Create mock request WITHOUT token
            request = MagicMock()
            request.url.path = "/v1/test"
            request.state.token = None

            # Create mock call_next that returns 401
            async def mock_call_next(req):
                return JSONResponse(status_code=401, content={"error": "Unauthorized"})

            # Call middleware
            response = await middleware.dispatch(request, mock_call_next)

            # Should pass through to get 401 from auth
            assert response.status_code == 401
            mock_limiter.check_all_limits.assert_not_called()

    @pytest.mark.asyncio
    async def test_middleware_error_response_format(self):
        """Test that 429 response follows OpenAI error format."""
        app = FastAPI()
        middleware = RateLimitMiddleware(app)

        # Mock rate limiter to deny with specific details
        with patch.object(middleware, "rate_limiter") as mock_limiter:
            mock_limiter.check_all_limits = AsyncMock(
                return_value=RateLimitResult(
                    allowed=False,
                    retry_after_seconds=45,
                    limit_type="provider",
                    identifier="openai",
                    current_count=470,
                    limit=470,
                )
            )

            # Create mock request
            request = MagicMock()
            request.url.path = "/v1/chat/completions"
            request.state.token = TokenPayload(
                sub="user-123",
                user_id="user-123",
                roles=["user"],
                exp=0,
                iat=0,
                iss="test",
                token_type="access",
            )
            request.state.provider = "openai"

            # Create mock call_next
            async def mock_call_next(req):
                return JSONResponse(status_code=200, content={})

            # Call middleware
            response = await middleware.dispatch(request, mock_call_next)

            assert response.status_code == 429

            # Parse response body
            import json

            body = json.loads(
                response.body.decode() if isinstance(response.body, bytes) else response.body
            )

            # Check OpenAI error format
            assert "error" in body
            assert body["error"]["type"] == "rate_limit_exceeded"
            assert body["error"]["code"] == "rate_limit_exceeded"
            assert "provider" in body["error"]["message"]
            assert body["error"]["param"] == "openai"

    def test_should_skip_rate_limit_paths(self):
        """Test that skip paths are correctly identified."""
        app = FastAPI()
        middleware = RateLimitMiddleware(app)

        # Paths that should skip
        assert middleware._should_skip_rate_limit("/health") is True
        assert middleware._should_skip_rate_limit("/docs") is True
        assert middleware._should_skip_rate_limit("/redoc") is True
        assert middleware._should_skip_rate_limit("/openapi.json") is True
        assert middleware._should_skip_rate_limit("/admin/rate-limits") is True
        assert middleware._should_skip_rate_limit("/") is True

        # Paths that should NOT skip
        assert middleware._should_skip_rate_limit("/v1/chat/completions") is False
        assert middleware._should_skip_rate_limit("/v1/embeddings") is False
        assert middleware._should_skip_rate_limit("/v1/models") is False
