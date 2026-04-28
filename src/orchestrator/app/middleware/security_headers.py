"""Middleware enforcing baseline security headers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from shared.logging_utils.fastapi import configure_logging

if TYPE_CHECKING:
    from fastapi import Request, Response

logger = configure_logging(
    service_name="security_headers_middleware", log_level="INFO", log_format="json"
)


DEFAULT_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-XSS-Protection": "1; mode=block",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=(), usb=()",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' ws: wss:; "
        "frame-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'self'; "
        "report-uri /api/security/csp-report"
    ),
}


async def security_headers_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Apply opinionated security headers to every response."""

    response = await call_next(request)

    for header, value in DEFAULT_HEADERS.items():
        if header not in response.headers:
            response.headers[header] = value

    logger.debug(
        "Applied security headers",
        extra={
            "path": request.url.path,
            "headers": list(DEFAULT_HEADERS.keys()),
        },
    )

    return response
