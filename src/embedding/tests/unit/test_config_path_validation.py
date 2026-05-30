"""Unit tests for embedding configuration path validation."""

import os
from pathlib import Path

import pytest

from app.config.models import _BUILTIN_CONFIG_PATH, _load_user_yaml_mapping, load_config


def test_builtin_config_path_exists_in_package() -> None:
    """Package default config path should exist in the repository."""
    assert os.path.isfile(_BUILTIN_CONFIG_PATH)


def test_load_user_yaml_mapping_accepts_basename() -> None:
    """Basename-only config paths load from the package config directory."""
    loaded = _load_user_yaml_mapping("models.yaml")
    assert isinstance(loaded, dict)


def test_load_user_yaml_mapping_rejects_traversal() -> None:
    """Path traversal attempts must be rejected."""
    with pytest.raises(ValueError, match="simple filename"):
        _load_user_yaml_mapping("../outside.yaml")


def test_load_config_rejects_explicit_traversal_path(tmp_path: Path) -> None:
    """Explicit config_path outside allowlist must fail fast."""
    outside = tmp_path / "outside.yaml"
    outside.write_text("providers: []\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid configuration path"):
        load_config(str(outside))
