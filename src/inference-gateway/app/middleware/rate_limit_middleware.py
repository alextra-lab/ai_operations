"""
Rate limiting middleware for Inference Gateway.

Checks rate limits before processing requests and returns 429 errors
when limits are exceeded.

Features:
- Pre-request rate limit checking
- OpenAI-compatible 429 responses
- Retry-After header injection
- Minimal overhead (<1ms Redis, <20ms PostgreSQL)

VERIFICATION:
- Returns 429 with OpenAI error format (ADR-054)
- Includes Retry-After header
- Fast-fail when limits exceeded
- Zero impact when limits not reached
"""

import time
from typing import Callable, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from shared.auth.models import TokenPayload  # type: ignore[import-untyped]
from shared.logging_utils.fastapi import configure_logging  # type: ignore[import-untyped]
from starlette.middleware.base import BaseHTTPMiddleware

from ..models.errors import build_error_response
from ..services.rate_limiter import get_rate_limiter

logger = configure_logging(service_name="rate_limit_middleware")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware.

    Checks rate limits before processing requests.
    Returns 429 Too Many Requests when limits exceeded.

    Applies to:
    - /v1/chat/completions
    - /v1/embeddings
    - /v1/responses

    Skips:
    - /health
    - /docs
    - /admin/* (rate limits managed separately)
    """

    def __init__(self, app, **kwargs):
        """
        Initialize rate limit middleware.

        Args:
            app: FastAPI application instance
            **kwargs: Additional middleware configuration
        """
        super().__init__(app, **kwargs)
        self.rate_limiter = get_rate_limiter()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limit check.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response (429 if rate limited, otherwise normal response)
        """
        # Skip rate limiting for non-API endpoints
        if self._should_skip_rate_limit(request.url.path):
            return await call_next(request)

        # Extract token from request (added by auth middleware)
        token: Optional[TokenPayload] = getattr(request.state, "token", None)

        if not token:
            # No token - auth middleware should have rejected already
            # Allow through for proper 401 error
            return await call_next(request)

        # Extract provider and model from request
        provider = self._extract_provider(request)
        model = self._extract_model(request)

        # Check rate limits
        start_time = time.time()
        result = await self.rate_limiter.check_all_limits(
            token=token,
            model=model,
            provider=provider,
        )
        check_latency_ms = int((time.time() - start_time) * 1000)

        if not result.allowed:
            # Rate limited - return 429
            logger.warning(
                "Request rate limited",
                extra={
                    "user_id": token.user_id if hasattr(token, "user_id") else None,
                    "service_id": token.sub if token.has_role("service") else None,
                    "roles": token.roles if hasattr(token, "roles") else [],
                    "limit_type": result.limit_type,
                    "identifier": result.identifier,
                    "current_count": result.current_count,
                    "limit": result.limit,
                    "retry_after": result.retry_after_seconds,
                    "check_latency_ms": check_latency_ms,
                    "path": request.url.path,
                },
            )

            # Build OpenAI-compatible error response
            error_response = build_error_response(
                message=f"Rate limit exceeded for {result.limit_type or 'requests'}. Please retry after {result.retry_after_seconds} seconds.",
                error_type="rate_limit_exceeded",
                error_code="rate_limit_exceeded",
                param=result.identifier,
            )

            # Add Retry-After header
            headers = {
                "Retry-After": str(result.retry_after_seconds),
                "X-RateLimit-Limit": str(result.limit) if result.limit else "unknown",
                "X-RateLimit-Remaining": str(
                    max(0, (result.limit or 0) - (result.current_count or 0))
                ),
                "X-RateLimit-Reset": str(int(time.time()) + result.retry_after_seconds),
            }

            return JSONResponse(
                status_code=429,
                content=error_response.model_dump(),
                headers=headers,
            )

        # Rate limit passed - continue to handler
        # Log if check was slow
        if check_latency_ms > 50:
            logger.warning(
                "Slow rate limit check",
                extra={"check_latency_ms": check_latency_ms, "path": request.url.path},
            )

        return await call_next(request)

    def _should_skip_rate_limit(self, path: str) -> bool:
        """
        Determine if rate limiting should be skipped for this path.

        Args:
            path: Request path

        Returns:
            True if rate limiting should be skipped
        """
        skip_paths = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/",
        ]

        # Skip admin endpoints (they have separate rate limits)
        if path.startswith("/admin"):
            return True

        # Skip non-API paths
        for skip_path in skip_paths:
            if path == skip_path or path.startswith(skip_path + "/"):
                return True

        return False

    def _extract_provider(self, request: Request) -> Optional[str]:
        """
        Extract provider from request state.

        Provider is set by router after model resolution.

        Args:
            request: FastAPI request

        Returns:
            Provider name or None
        """
        return getattr(request.state, "provider", None)

    def _extract_model(self, request: Request) -> Optional[str]:
        """
        Extract model from request body.

        Args:
            request: FastAPI request

        Returns:
            Model name or None
        """
        # Try to get model from request state (set by router)
        model: Optional[str] = getattr(request.state, "model", None)
        if model is not None:
            return model

        # Fallback: try to parse from request body (limited, as body may not be read yet)
        # This is best-effort - actual model extraction happens in router
        return None
