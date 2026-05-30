"""Unit tests for embedding configuration path validation."""

import os
from pathlib import Path

import pytest

from app.config.models import _resolve_allowed_config_path, load_config


def test_resolve_allowed_config_path_accepts_package_default() -> None:
    """Package default config path should resolve within allowed base."""
    package_default = os.path.join(os.path.dirname(__file__), "..", "..", "app", "config", "models.yaml")
    resolved = _resolve_allowed_config_path(package_default)
    assert os.path.isabs(resolved)


def test_resolve_allowed_config_path_rejects_traversal() -> None:
    """Paths outside allowed directories must be rejected."""
    with pytest.raises(ValueError, match="not allowed"):
        _resolve_allowed_config_path("/etc/passwd")


def test_load_config_rejects_explicit_traversal_path(tmp_path: Path) -> None:
    """Explicit config_path outside allowlist must fail fast."""
    outside = tmp_path / "outside.yaml"
    outside.write_text("providers: []\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid configuration path"):
        load_config(str(outside))
