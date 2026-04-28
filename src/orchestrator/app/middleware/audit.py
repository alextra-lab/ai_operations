"""Audit middleware providing security guardrails and observability."""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import TYPE_CHECKING

from shared.logging_utils.fastapi import configure_logging

from ..db.database import AsyncSessionLocal
from ..db.models import AuditLog
from ..utils.auth import jwt_validator

if TYPE_CHECKING:
    from fastapi import Request, Response

# Use a descriptive service name for audit logging
logger = configure_logging(service_name="audit_middleware", log_level="INFO", log_format="json")


def _extract_roles(payload: dict[str, object]) -> list[str]:
    """Normalize role information from a token payload."""
    raw_roles = payload.get("roles")
    if isinstance(raw_roles, list):
        return [str(role) for role in raw_roles]
    role = payload.get("role")
    return [str(role)] if isinstance(role, str) else []


def _safe_uuid(value: str | None) -> uuid.UUID | None:
    """Convert a string to UUID if possible."""
    if not value:
        return None
    with suppress(ValueError, TypeError):
        return uuid.UUID(str(value))
    return None


async def audit_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Record structured audit information and persist it for observability."""

    start_time = time.perf_counter()
    response: Response = await call_next(request)

    duration_ms = round((time.perf_counter() - start_time) * 1000, 4)
    client_host = request.client.host if request.client else "unknown"
    request_id = (
        response.headers.get("X-Request-ID")
        or request.headers.get("X-Request-ID")
        or str(uuid.uuid4())
    )

    token_payload: dict[str, object] | None = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            token_payload = jwt_validator.verify_token(token)
        except Exception as exc:  # - ensure audit logging never fails
            logger.warning(
                "Failed to verify token for audit logging",
                extra={"error": str(exc), "path": request.url.path},
            )

    roles = _extract_roles(token_payload or {})
    user_id_value = (token_payload or {}).get("user_id") or (token_payload or {}).get("sub")
    actor_user_id = _safe_uuid(str(user_id_value) if user_id_value else None)

    # Ensure we never log secrets in context; only metadata
    log_context = {
        "method": request.method,
        "path": request.url.path,
        "client": client_host,
        "status_code": response.status_code,
        "duration_ms": duration_ms,
    }

    if token_payload:
        log_context.update(
            {
                "user": token_payload.get("sub"),
                "user_roles": roles,
                "token_id": token_payload.get("jti"),
            }
        )

    # Persist audit event into database (async)
    try:
        async with AsyncSessionLocal() as session:
            audit_entry = AuditLog(
                actor_user_id=actor_user_id,
                actor_roles=roles,
                action=f"{request.method} {request.url.path}",
                resource_type="http_request",
                resource_id=str(request.url.path),
                request_id=request_id,
                client_ip=client_host,
                user_agent=request.headers.get("user-agent"),
                success=bool(response.status_code < 400),
                details={
                    "status_code": response.status_code,
                    "query_params": dict(request.query_params),
                    "duration_ms": duration_ms,
                },
            )
            session.add(audit_entry)
            await session.commit()
    except Exception as exc:  # - audit persistence must be best-effort
        logger.error(
            "Failed to persist audit log entry",
            extra={"error": str(exc), "path": request.url.path},
            exc_info=True,
        )

    # Note: request_id is already set by RequestIDLoggerMiddleware on the LogRecord,
    # so we don't include it in extra to avoid KeyError: "Attempt to overwrite 'request_id' in LogRecord"
    logger.info("Audit log", extra=log_context)
    return response
