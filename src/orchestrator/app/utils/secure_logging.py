"""
Secure Logging Utilities

Provides redaction capabilities for sensitive data in logs based on environment configuration.

v1: Simple environment flag (REDACT_LOGS=true/false)
v1.2: Granular field-level control via config file

Environment Variables:
    REDACT_LOGS: Enable/disable log redaction (default: false for backward compatibility)
    LOG_REDACTION_LEVEL: none|partial|full (default: partial)
        - none: No redaction (dev/test)
        - partial: Redact query/response content, keep metadata
        - full: Redact everything except request_id, timestamp
"""

import hashlib
from typing import Any

from shared.config import config_manager
from shared.config.loader import load_logging_config
from shared.config.schemas import LoggingConfig


def _load_redaction_settings() -> tuple[bool, str]:
    """Load redaction settings from shared logging configuration."""
    config = config_manager.get_config("logging")
    if isinstance(config, LoggingConfig):
        return config.redact_logs, config.redaction_level

    logging_config = load_logging_config()
    return logging_config.redact_logs, logging_config.redaction_level


# Configuration sourced from shared logging config
REDACT_LOGS, REDACTION_LEVEL = _load_redaction_settings()


def _hash_value(value: str, length: int = 8) -> str:
    """
    Create a short hash of a value for audit purposes.

    Args:
        value: Value to hash
        length: Hash length (default: 8 chars)

    Returns:
        Short hash (e.g., "a3b4c5d6")
    """
    if not value:
        return "[empty]"
    return hashlib.sha256(value.encode()).hexdigest()[:length]


def redact_query(query: str) -> str:
    """
    Redact query text for logging.

    Args:
        query: Original query text

    Returns:
        Redacted version based on REDACT_LOGS setting
    """
    if not REDACT_LOGS:
        return query

    if REDACTION_LEVEL == "none":
        return query

    if REDACTION_LEVEL == "full":
        return "[REDACTED]"

    # partial: Show length + hash
    return f"[REDACTED:{len(query)}chars:hash={_hash_value(query)}]"


def redact_response(response: str) -> str:
    """
    Redact response text for logging.

    Args:
        response: Original response text

    Returns:
        Redacted version based on REDACT_LOGS setting
    """
    if not REDACT_LOGS:
        return response

    if REDACTION_LEVEL == "none":
        return response

    if REDACTION_LEVEL == "full":
        return "[REDACTED]"

    # partial: Show length + hash
    return f"[REDACTED:{len(response)}chars:hash={_hash_value(response)}]"


def redact_session_id(session_id: str | None) -> str:
    """
    Redact session ID for logging.

    Args:
        session_id: Original session ID

    Returns:
        Redacted version based on REDACT_LOGS setting
    """
    if not session_id:
        return "none"

    if not REDACT_LOGS:
        return session_id

    if REDACTION_LEVEL == "full":
        return "[REDACTED]"

    # partial: Show prefix + hash
    prefix = session_id.split("_")[0] if "_" in session_id else "session"
    return f"{prefix}_[hash={_hash_value(session_id)}]"


def redact_request_body(body: dict[str, Any]) -> dict[str, Any]:
    """
    Redact sensitive fields in request body for logging.

    Args:
        body: Original request body dict

    Returns:
        Redacted copy based on REDACT_LOGS setting
    """
    if not REDACT_LOGS or REDACTION_LEVEL == "none":
        return body

    redacted = body.copy()

    # Always redact these fields if present
    sensitive_fields = ["query", "response", "content", "message", "context"]

    for field in sensitive_fields:
        if redacted.get(field):
            original = str(redacted[field])
            if REDACTION_LEVEL == "full":
                redacted[field] = "[REDACTED]"
            else:  # partial
                redacted[field] = f"[REDACTED:{len(original)}chars:hash={_hash_value(original)}]"

    # Optionally redact session_id
    if redacted.get("session_id"):
        redacted["session_id"] = redact_session_id(redacted["session_id"])

    return redacted


def get_redaction_status() -> dict[str, Any]:
    """
    Get current redaction configuration status.

    Returns:
        Dictionary with redaction settings
    """
    return {
        "redaction_enabled": REDACT_LOGS,
        "redaction_level": REDACTION_LEVEL,
    }
