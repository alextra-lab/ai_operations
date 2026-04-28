"""
Secret provider abstractions for centralized configuration.

Current implementation supports environment-backed secrets. The abstraction
enables future Vault or alternative secret stores via ADR-061 without forcing
services to change how they request sensitive values.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from typing import Protocol

logger = logging.getLogger(__name__)


class SecretProvider(Protocol):
    """Protocol for retrieving named secrets."""

    def get_secret(self, key: str, default: str | None = None) -> str | None: ...


class EnvSecretProvider:
    """Secret provider that resolves secrets from process environment variables."""

    def __init__(self, environment: Mapping[str, str] | None = None) -> None:
        self._environment = environment or os.environ

    def get_secret(self, key: str, default: str | None = None) -> str | None:
        return self._environment.get(key, default)


_secret_provider: SecretProvider | None = None


def _create_provider() -> SecretProvider:
    provider_name = os.environ.get("SECRET_PROVIDER", "env").lower()
    if provider_name == "env":
        return EnvSecretProvider()

    logger.warning(
        "Unknown SECRET_PROVIDER '%s'; falling back to environment provider",
        provider_name,
    )
    return EnvSecretProvider()


def get_secret_provider() -> SecretProvider:
    """Get the configured secret provider (singleton)."""
    global _secret_provider
    if _secret_provider is None:
        _secret_provider = _create_provider()
    return _secret_provider


def set_secret_provider(provider: SecretProvider | None) -> None:
    """Override the global secret provider (useful for tests)."""
    global _secret_provider
    _secret_provider = provider


def resolve_secret(key: str, default: str | None = None) -> str | None:
    """Resolve a secret by key using the configured provider."""
    provider = get_secret_provider()
    return provider.get_secret(key, default)
