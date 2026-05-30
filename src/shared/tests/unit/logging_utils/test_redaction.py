"""Unit tests for logging redaction utilities."""

from shared.logging_utils.redaction import (
    GENERIC_CLIENT_ERROR,
    REDACTED,
    mask_identifier,
    redact_mapping,
    redact_value,
    safe_config_summary,
)


def test_redact_value_masks_content() -> None:
    assert redact_value("super-secret") == REDACTED


def test_mask_identifier_is_stable() -> None:
    first = mask_identifier("api_key_prod")
    second = mask_identifier("api_key_prod")
    assert first == second
    assert first.startswith("ref:")


def test_redact_mapping_redacts_sensitive_keys() -> None:
    result = redact_mapping({"password": "abc", "username": "alice"})
    assert result["password"] == REDACTED
    assert result["username"] == "alice"


def test_safe_config_summary_lists_keys_only() -> None:
    summary = safe_config_summary({"timeout": 30, "token": "secret"})
    assert summary == {"keys": ["timeout", "token"]}


def test_generic_client_error_constant() -> None:
    assert "internal error" in GENERIC_CLIENT_ERROR.lower()
