"""
RLS (Row-Level Security) middleware for PostgreSQL session variables.

This middleware sets PostgreSQL session variables that are used by RLS policies
to enforce user isolation and role-based access control.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

from shared.logging_utils.fastapi import configure_logging

from ..db.database import AsyncSessionLocal
from ..utils.auth import jwt_validator

if TYPE_CHECKING:
    from fastapi import Request, Response

logger = configure_logging(service_name="rls_middleware", log_level="INFO", log_format="json")


async def rls_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    Set PostgreSQL session variables for RLS policies.

    This middleware:
    1. Extracts user info from JWT token
    2. Sets aio.user_id and aio.user_roles session variables
    3. Ensures all database queries in this request respect RLS policies

    Args:
        request: The incoming request
        call_next: The next middleware or endpoint handler

    Returns:
        Response: The response from the next middleware or endpoint
    """
    # Extract token payload
    token_payload = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            token_payload = jwt_validator.verify_token(token)
        except Exception as exc:
            logger.debug(
                "Failed to verify token for RLS",
                extra={"error": str(exc), "path": request.url.path},
            )

    # Set RLS session variables if we have a valid token
    if token_payload:
        user_id = token_payload.get("user_id") or token_payload.get("sub")
        # Note: TokenPayload has 'role' (singular), not 'roles' (plural)
        role = token_payload.get("role") or token_payload.get("roles")

        # Ensure roles is a list
        if isinstance(role, str):
            roles = [role]
        elif isinstance(role, list):
            roles = role
        else:
            roles = []

        # Format roles as comma-separated string for PostgreSQL array parsing
        roles_str = ",".join(str(r) for r in roles) if roles else ""

        # Set session variables in all database sessions created during this request
        # We'll do this by patching the AsyncSessionLocal temporarily
        # AsyncSessionLocal() returns an async context manager, so we need to wrap it
        original_call = AsyncSessionLocal.__call__

        def patched_call(*args: object, **kwargs: object) -> AbstractAsyncContextManager[Any]:
            """Create async session context manager that sets RLS variables."""

            @asynccontextmanager
            async def session_with_rls() -> AsyncGenerator[Any, None]:
                async with original_call(*args, **kwargs) as session:
                    try:
                        # Set RLS session variables
                        await session.execute(
                            text("SET LOCAL aio.user_id = :user_id"),
                            {"user_id": str(user_id)},
                        )
                        await session.execute(
                            text("SET LOCAL aio.user_roles = :roles"),
                            {"roles": f"{{{roles_str}}}" if roles_str else "{}"},
                        )
                        logger.debug(
                            "Set RLS session variables",
                            extra={
                                "user_id": str(user_id),
                                "roles": roles,
                                "path": request.url.path,
                            },
                        )
                    except Exception as exc:
                        logger.error(
                            "Failed to set RLS session variables",
                            extra={
                                "error": str(exc),
                                "user_id": str(user_id),
                                "path": request.url.path,
                            },
                        )
                    yield session

            return session_with_rls()

        # Temporarily patch AsyncSessionLocal
        AsyncSessionLocal.__call__ = patched_call  # type: ignore
        try:
            response = await call_next(request)
        finally:
            # Restore original AsyncSessionLocal
            AsyncSessionLocal.__call__ = original_call  # type: ignore
    else:
        # No token, proceed without setting RLS variables
        response = await call_next(request)

    return response
