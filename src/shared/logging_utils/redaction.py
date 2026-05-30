"""Utilities for redacting sensitive values before logging or client responses."""

from __future__ import annotations

import hashlib
import re
from typing import Any

REDACTED = "[REDACTED]"
GENERIC_CLIENT_ERROR = "An internal error occurred. Please try again later."

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|secret|token|api[_-]?key|authorization|credential)",
    re.IGNORECASE,
)


def redact_value(value: str | None) -> str:
    """Replace a sensitive string value with a redaction marker."""
    if not value:
        return REDACTED
    return REDACTED


def mask_identifier(value: str) -> str:
    """Return a stable opaque identifier suitable for audit logs."""
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"ref:{digest[:12]}"


def redact_mapping(data: dict[str, Any]) -> dict[str, Any]:
    """Redact values for keys that look sensitive."""
    redacted: dict[str, Any] = {}
    for key, inner_value in data.items():
        if _SENSITIVE_KEY_PATTERN.search(key):
            redacted[key] = REDACTED
        elif isinstance(inner_value, dict):
            redacted[key] = redact_mapping(inner_value)
        else:
            redacted[key] = inner_value
    return redacted


def safe_config_summary(config: dict[str, Any] | None) -> dict[str, Any]:
    """Log-safe summary of a configuration mapping (keys only)."""
    if not config:
        return {"keys": []}
    return {"keys": sorted(str(key) for key in config)}


def client_safe_error_message(
    detail: str | None = None,
    *,
    generic: str = GENERIC_CLIENT_ERROR,
) -> str:
    """Return a generic client-facing error message."""
    return generic if detail is None else generic
