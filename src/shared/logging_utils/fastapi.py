"""
FastAPI-Specific Logging Utilities

Provides middleware for request ID propagation and context logging.
Intended for use in FastAPI-based services only.
"""

import json
import logging
import time
import uuid
from collections.abc import Callable
from typing import Any, cast
from urllib.parse import parse_qsl

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from shared.config.loader import load_logging_config

from .base import (
    JsonFormatter,
    LoggingContextAdapter,
    TextFormatter,
    configure_logging,
    get_logger,
)

MAX_BODY_BYTES = 2048
SENSITIVE_HEADERS = {"authorization", "x-api-key", "cookie"}
SENSITIVE_FIELDS = {
    "password",
    "token",
    "secret",
    "key",
    "authorization",
    "refresh_token",
    "access_token",
}


class RequestIDLoggerMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID to logger context."""

    # Store the original factory at class level to avoid recursion
    _original_factory = None
    _factory_initialized = False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Initialize the original factory only once
        if not self._factory_initialized:
            self._original_factory = logging.getLogRecordFactory()
            self._factory_initialized = True

        def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
            # Always call the original factory to avoid recursion
            if self._original_factory is None:
                raise RuntimeError("Original factory not initialized")
            record = self._original_factory(*args, **kwargs)
            if not hasattr(record, "request_id"):
                record.request_id = request_id
            return record

        # Set our custom factory
        logging.setLogRecordFactory(record_factory)  # type: ignore[arg-type]

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return cast("Response", response)
        finally:
            # Restore the original factory
            if self._original_factory is not None:
                logging.setLogRecordFactory(self._original_factory)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log request/response metadata."""

    def __init__(
        self,
        app: Callable,
        logger: logging.Logger | LoggingContextAdapter,
        verbose: bool = False,
    ) -> None:
        super().__init__(app)
        self._logger = logger
        self._verbose = verbose

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.monotonic()
        path = request.url.path
        request_log: dict[str, Any] = {
            "method": request.method,
            "path": path,
        }

        if self._verbose:
            request_log["headers"] = _sanitize_headers(request.headers)
            body_info = await _build_body_info(request)
            request_log.update(body_info)

        self._logger.info("HTTP request", extra=request_log)
        response = await call_next(request)

        duration_ms = int((time.monotonic() - start_time) * 1000)
        response_log: dict[str, Any] = {
            "method": request.method,
            "path": path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        }
        if self._verbose:
            response_log["headers"] = _sanitize_headers(response.headers)

        self._logger.info("HTTP response", extra=response_log)
        return cast("Response", response)


def is_verbose_logging_enabled() -> bool:
    return load_logging_config().verbose


def _sanitize_headers(headers: Any) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() not in SENSITIVE_HEADERS:
            sanitized[key] = value
    return sanitized


async def _build_body_info(
    request: Request,
) -> dict[str, Any]:
    body = await request.body()
    body_size = len(body)
    if body_size == 0:
        return {}

    content_type = request.headers.get("content-type")
    truncated = body_size > MAX_BODY_BYTES
    body_preview = body[:MAX_BODY_BYTES]
    return {
        "body_size_bytes": body_size,
        "body_truncated": truncated,
        "body": _sanitize_body(
            content_type,
            body_preview,
        ),
    }


def _sanitize_body(
    content_type: str | None,
    body: bytes,
) -> Any:
    if content_type and "multipart/form-data" in content_type:
        return "[multipart]"

    if content_type and "application/octet-stream" in content_type:
        return "[binary]"

    body_text = body.decode("utf-8", errors="replace")

    if content_type and "application/json" in content_type:
        try:
            data = json.loads(body_text)
            return _redact_json(data)
        except json.JSONDecodeError:
            return _truncate_string(body_text)

    if content_type and "application/x-www-form-urlencoded" in content_type:
        return _sanitize_form(body_text)

    return _truncate_string(body_text)


def _sanitize_form(body_text: str) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for key, value in parse_qsl(body_text, keep_blank_values=True):
        if _is_sensitive_field(key):
            sanitized[key] = "[REDACTED]"
        else:
            sanitized[key] = _truncate_string(value)
    return sanitized


def _redact_json(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, inner_value in value.items():
            if _is_sensitive_field(key):
                redacted[key] = "[REDACTED]"
            elif isinstance(inner_value, dict | list):
                redacted[key] = _redact_json(inner_value)
            else:
                redacted[key] = inner_value
        return redacted

    if isinstance(value, list):
        return {"arrayLength": len(value)}

    return value


def _truncate_string(value: str) -> str:
    if len(value) <= MAX_BODY_BYTES:
        return value
    preview = value[:MAX_BODY_BYTES]
    return f"{preview}...[truncated]"


def _is_sensitive_field(field_name: str) -> bool:
    return field_name.lower() in SENSITIVE_FIELDS


# Re-export for clean imports
__all__ = [
    "JsonFormatter",
    "LoggingContextAdapter",
    "RequestIDLoggerMiddleware",
    "RequestLoggingMiddleware",
    "TextFormatter",
    "configure_logging",
    "get_logger",
    "is_verbose_logging_enabled",
]
