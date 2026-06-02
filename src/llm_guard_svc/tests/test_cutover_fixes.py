"""Unit tests for the LLG-04 finale cutover fixes (AIO-73).

Covers the salted-hash cache key (so raw user text is never a cache key) and the
``get_llm_guard`` process singleton (models load once, not per request). Both
import the service stack, so they run in the llm-guard-svc container and skip on
the bare host venv.
"""

from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec

import pytest

pytestmark = pytest.mark.skipif(
    find_spec("cachetools") is None or find_spec("fastapi") is None,
    reason="needs the service stack (cachetools/fastapi) — run in the llm-guard-svc container",
)


def _guard():
    try:
        return import_module("src.llm_guard_svc.app.guard")
    except ModuleNotFoundError:  # container flat layout
        return import_module("app.guard")


def _main():
    try:
        return import_module("src.llm_guard_svc.app.main")
    except ModuleNotFoundError:  # container flat layout
        return import_module("app.main")


def test_cache_key_is_salted_hash():
    guard = _guard()
    key = guard._cache_key("my-secret-token")
    assert key == guard._cache_key("my-secret-token")  # stable within a process
    assert len(key) == 64 and all(c in "0123456789abcdef" for c in key)
    assert "my-secret-token" not in key  # raw text is never the cache key


def test_get_llm_guard_builds_once(monkeypatch):
    main = _main()
    if not main.LLM_GUARD_SERVICE_ENABLED:
        pytest.skip("service disabled in this env")
    builds: list[int] = []
    monkeypatch.setattr(main, "LLMGuard", lambda **kwargs: builds.append(1) or object())
    main.get_llm_guard.cache_clear()
    try:
        first = main.get_llm_guard()
        second = main.get_llm_guard()
        assert first is second  # singleton reused across requests
        assert len(builds) == 1  # constructed once, not per call
    finally:
        main.get_llm_guard.cache_clear()
