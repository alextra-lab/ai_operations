"""Differential parity for the native ONNX classifiers vs the llm-guard ones.

For each classifier (prompt_injection, gibberish, language), build BOTH engines
through ``guard.py``'s own dispatch (``LLMGuard._build_*("llm_guard"|"native")``)
and assert they return identical ``(sanitized, passed, score)`` on every corpus
case. This is the faithful unit gate for LLG-04 step 2:

  * It compares native directly against the real llm-guard scanner on the SAME
    raw input, so it cannot be fooled by a shared bug (unlike a golden baseline)
    and is immune to pipeline ordering -- the full-service golden runs each
    scanner on text already sanitized by upstream scanners, so per-scanner golden
    comparison on raw text only holds for cases with no upstream modification.
  * It exercises the real ``_build_*`` dispatch + model-path wiring this PR adds.

Needs the model stack (transformers + optimum) AND ``llm_guard`` installed, so it
runs inside the llm-guard-svc container and skips on the bare host venv. Run via:

    docker run -d --name llg-verify --entrypoint sleep \\
        -v "$PWD/data/llm-guard-models:/app/models:ro" aio-llm-guard-svc infinity
    docker cp src/llm_guard_svc/app/. llg-verify:/app/app/
    docker cp src/llm_guard_svc/tests/. llg-verify:/app/tests/
    docker exec -u root llg-verify python -m pip install -q pytest
    docker exec -e PYTHONPATH=/app:/app/app -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \\
        llg-verify python -m pytest tests/parity/test_onnx_parity.py -q

Once llm_guard is removed at the end of LLG-04 this differential test no longer
applies (the llm-guard side is gone); the full service-level harness covers
parity from then on.
"""

from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec

import pytest

# Dual-path: the rest of the parity suite imports `src.llm_guard_svc.*` on the
# host venv; this test also runs in the flat container layout (`tests.parity.*`).
try:  # pragma: no cover - import shim
    from src.llm_guard_svc.tests.parity.corpus import CORPUS
except ModuleNotFoundError:  # pragma: no cover - container layout
    from tests.parity.corpus import CORPUS  # type: ignore[no-redef]

_HAS_OPTIMUM = find_spec("optimum.onnxruntime") is not None
_HAS_LLM_GUARD = find_spec("llm_guard") is not None


def _guard_module():
    try:
        return import_module("src.llm_guard_svc.app.guard")
    except ModuleNotFoundError:  # container flat layout
        return import_module("app.guard")


@pytest.fixture(scope="module")
def guard():
    if not (_HAS_OPTIMUM and _HAS_LLM_GUARD):
        pytest.skip("needs optimum + llm_guard + models (run inside llm-guard-svc container)")
    mod = _guard_module()
    mod.configure_models()  # set the llm-guard *_MODEL global paths, as the service does
    return mod


@pytest.fixture(scope="module")
def prompt_injection_pair(guard):
    return (
        guard.LLMGuard._build_prompt_injection("llm_guard"),
        guard.LLMGuard._build_prompt_injection("native"),
    )


@pytest.fixture(scope="module")
def gibberish_pair(guard):
    return (
        guard.LLMGuard._build_gibberish("llm_guard"),
        guard.LLMGuard._build_gibberish("native"),
    )


@pytest.fixture(scope="module")
def language_pair(guard):
    return (
        guard.LLMGuard._build_language("llm_guard"),
        guard.LLMGuard._build_language("native"),
    )


def _assert_same(base, native, text):
    """Native (sanitized, passed, score) must equal the llm-guard scanner's."""
    b = base.scan(text)
    n = native.scan(text)
    assert n == b, f"native {n} != llm_guard {b} for text={text!r}"


@pytest.mark.parametrize("case", CORPUS, ids=[c.id for c in CORPUS])
def test_prompt_injection_differential(case, prompt_injection_pair):
    base, native = prompt_injection_pair
    _assert_same(base, native, case.text)


@pytest.mark.parametrize("case", CORPUS, ids=[c.id for c in CORPUS])
def test_gibberish_differential(case, gibberish_pair):
    base, native = gibberish_pair
    _assert_same(base, native, case.text)


@pytest.mark.parametrize("case", CORPUS, ids=[c.id for c in CORPUS])
def test_language_differential(case, language_pair):
    base, native = language_pair
    _assert_same(base, native, case.text)
