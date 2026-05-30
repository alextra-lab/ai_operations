"""Unit tests for embedding configuration path validation."""

import os
from pathlib import Path

import pytest

from app.config.models import (
    _KNOWN_CONFIG_PATHS,
    _resolve_user_config_path,
    load_config,
)


def test_known_config_paths_include_package_default() -> None:
    """Built-in config path should be part of the allowlist."""
    package_default = os.path.join(
        os.path.dirname(__file__), "..", "..", "app", "config", "models.yaml"
    )
    resolved = os.path.realpath(package_default)
    assert resolved in _KNOWN_CONFIG_PATHS


def test_resolve_user_config_path_accepts_basename() -> None:
    """Basename-only config paths resolve under the package config directory."""
    resolved = _resolve_user_config_path("models.yaml")
    assert os.path.isabs(resolved)
    assert resolved.endswith("models.yaml")


def test_resolve_user_config_path_rejects_traversal() -> None:
    """Path traversal attempts must be rejected."""
    with pytest.raises(ValueError, match="not allowed|simple filename"):
        _resolve_user_config_path("../outside.yaml")


def test_load_config_rejects_explicit_traversal_path(tmp_path: Path) -> None:
    """Explicit config_path outside allowlist must fail fast."""
    outside = tmp_path / "outside.yaml"
    outside.write_text("providers: []\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid configuration path"):
        load_config(str(outside))
