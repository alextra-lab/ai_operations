"""AIO-76 regression test: secrets scanner must not leak temp files on scan error.

SecretsScanner.scan() writes the raw prompt to a NamedTemporaryFile before calling
detect-secrets. If scan_file() raises the file was previously left on disk
(os.remove only on happy path). This test asserts the fix: the temp file is always
removed, even when scan_file() raises.

Only needs detect_secrets + presidio_anonymizer — no model stack required.
"""

from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

import pytest

from src.llm_guard_svc.app.scanners.secrets_scanner import SecretsScanner


def test_temp_file_removed_when_scan_file_raises():
    """
    When detect-secrets raises during scan_file(), the temp file containing
    the raw prompt must still be removed (ADR-048: no user content retained).

    Strategy:
    1. Intercept tempfile.NamedTemporaryFile to capture the path before the
       scanner creates it.
    2. Patch SecretsCollection.scan_file to raise RuntimeError.
    3. Assert SecretsScanner.scan() re-raises and the temp file no longer exists.
    """
    captured: list[str] = []
    real_named_temp = tempfile.NamedTemporaryFile

    def capturing_named_temp(**kwargs):
        f = real_named_temp(**kwargs)
        captured.append(f.name)
        return f

    with (
        patch(
            "src.llm_guard_svc.app.scanners.secrets_scanner.tempfile.NamedTemporaryFile",
            side_effect=capturing_named_temp,
        ),
        patch(
            "src.llm_guard_svc.app.scanners.secrets_scanner.SecretsCollection.scan_file",
            side_effect=RuntimeError("simulated scan failure"),
        ),
    ):
        scanner = SecretsScanner()
        with pytest.raises(RuntimeError, match="simulated scan failure"):
            scanner.scan("AKIAIOSFODNN7EXAMPLE my-super-secret-value")

    assert captured, "NamedTemporaryFile was never called — test setup is broken"
    temp_path = captured[0]
    assert not os.path.exists(temp_path), (
        f"Temp file {temp_path!r} was left on disk after scan_file() raised — "
        "AIO-76 fix is missing or broken"
    )


def test_temp_file_removed_on_successful_scan():
    """
    Sanity check: the temp file is also removed on the normal (non-raising) path.
    This was already true before AIO-76 but is included to prevent regression.
    """
    captured: list[str] = []
    real_named_temp = tempfile.NamedTemporaryFile

    def capturing_named_temp(**kwargs):
        f = real_named_temp(**kwargs)
        captured.append(f.name)
        return f

    with patch(
        "src.llm_guard_svc.app.scanners.secrets_scanner.tempfile.NamedTemporaryFile",
        side_effect=capturing_named_temp,
    ):
        scanner = SecretsScanner()
        scanner.scan("no secrets here just ordinary text")

    assert captured, "NamedTemporaryFile was never called — test setup is broken"
    temp_path = captured[0]
    assert not os.path.exists(
        temp_path
    ), f"Temp file {temp_path!r} was left on disk after a successful scan"
