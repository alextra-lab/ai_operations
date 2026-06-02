"""LLMGuard selects native vs llm-guard scanner engines per config (LLG-04).

Skipped where the full llm-guard stack is unavailable (runs in the service image
/ CI), since constructing LLMGuard imports llm_guard.
"""

import importlib.util
import logging

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("llm_guard") is None,
    reason="requires the full llm-guard stack (service image / CI)",
)


def _guard(**engines):
    from src.llm_guard_svc.app.guard import LLMGuard

    return LLMGuard(logger=logging.getLogger("test"), **engines)


def test_native_engines_select_native_classes():
    from src.llm_guard_svc.app.scanners import RegexScanner, SecretsScanner

    g = _guard(regex_engine="native", secrets_engine="native")
    assert isinstance(g.scanners["regex"], RegexScanner)
    assert isinstance(g.scanners["secrets"], SecretsScanner)


def test_default_engines_select_llm_guard():
    from src.llm_guard_svc.app.scanners import RegexScanner, SecretsScanner

    g = _guard()
    assert not isinstance(g.scanners["regex"], RegexScanner)
    assert not isinstance(g.scanners["secrets"], SecretsScanner)
