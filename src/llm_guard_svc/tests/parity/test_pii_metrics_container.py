"""Model-backed metric gate for the native PII scanner (LLG-04 step 3).

Unlike the other scanners, PII is a deliberate MODEL SWAP (cc-by-nc distilbert ->
Presidio + GLiNER), so there is NO differential ``_assert_same`` vs llm-guard —
comparing a swapped model to the old one is meaningless. Instead this builds the
real native scanner through ``guard.py``'s dispatch
(``LLMGuard._build_anonymize("native")``) and asserts entity-level
recall/precision on the labelled set (``pii_labelled.PII_CASES``) clears the
ratified acceptance bars (``pii_metrics``).

Needs ``gliner`` + ``presidio_analyzer`` + the staged GLiNER model, so it runs
inside the llm-guard-svc container and skips on the bare host venv. Run via:

    docker run -d --name llg-verify --entrypoint sleep \\
        -v "$PWD/data/llm-guard-models:/app/models:ro" aio-llm-guard-svc infinity
    docker cp src/llm_guard_svc/app/. llg-verify:/app/app/
    docker cp src/llm_guard_svc/tests/. llg-verify:/app/tests/
    docker exec -u root llg-verify python -m pip install -q pytest
    docker exec -e PYTHONPATH=/app:/app/app -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \\
        llg-verify python -m pytest tests/parity/test_pii_metrics_container.py -q -s

If a bar misses, tune ``AnonymizeScanner`` (``score_threshold`` /
``gliner_threshold`` / the GLiNER label set) — the bars define "match/beat the
removed distilbert", not the implementation.
"""

from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec

import pytest

# Dual-path: host venv imports `src.llm_guard_svc.*`; the container uses the flat
# `tests.parity.*` / `app.*` layout.
try:  # pragma: no cover - import shim
    from src.llm_guard_svc.tests.parity import pii_metrics
    from src.llm_guard_svc.tests.parity.pii_labelled import PII_CASES
except ModuleNotFoundError:  # pragma: no cover - container layout
    from tests.parity import pii_metrics  # type: ignore[no-redef]
    from tests.parity.pii_labelled import PII_CASES  # type: ignore[no-redef]

_HAS_GLINER = find_spec("gliner") is not None
_HAS_PRESIDIO = find_spec("presidio_analyzer") is not None


def _guard_module():
    try:
        return import_module("src.llm_guard_svc.app.guard")
    except ModuleNotFoundError:  # container flat layout
        return import_module("app.guard")


@pytest.fixture(scope="module")
def groups():
    """Build the native scanner once, score every labelled case, aggregate."""
    if not (_HAS_GLINER and _HAS_PRESIDIO):
        pytest.skip("needs gliner + presidio_analyzer + GLiNER model (run in container)")
    guard = _guard_module()
    scanner = guard.LLMGuard._build_anonymize("native")

    per_case: list[tuple[list, list]] = []
    for case in PII_CASES:
        predicted = scanner.detect(case.text)
        per_case.append((list(case.spans), predicted))
    result = pii_metrics.aggregate_by_group(per_case)
    # Surface the numbers when run with -s; cheap and invaluable for tuning.
    for name, m in result.items():
        print(
            f"[pii-metrics] {name:10s} "
            f"recall={m.recall:.3f} precision={m.precision:.3f} f1={m.f1:.3f} "
            f"(tp={m.tp} fp={m.fp} fn={m.fn})"
        )
    return result


def test_structured_recall(groups):
    assert groups["structured"].recall >= pii_metrics.STRUCTURED_MIN_RECALL


def test_structured_precision(groups):
    assert groups["structured"].precision >= pii_metrics.STRUCTURED_MIN_PRECISION


def test_free_text_recall(groups):
    assert groups["free_text"].recall >= pii_metrics.FREE_TEXT_MIN_RECALL


def test_free_text_precision(groups):
    assert groups["free_text"].precision >= pii_metrics.FREE_TEXT_MIN_PRECISION


def test_no_leak_on_benign(groups):
    """Benign (zero-PII) cases must yield zero predictions (no non-PII redaction)."""
    if not (_HAS_GLINER and _HAS_PRESIDIO):
        pytest.skip("needs gliner + presidio_analyzer + GLiNER model (run in container)")
    guard = _guard_module()
    scanner = guard.LLMGuard._build_anonymize("native")
    leaks = []
    for case in PII_CASES:
        if case.spans:
            continue
        predicted = scanner.detect(case.text)
        if predicted:
            leaks.append((case.id, [(s.entity, case.text[s.start : s.end]) for s in predicted]))
    assert len(leaks) <= pii_metrics.BENIGN_MAX_FALSE_POSITIVES, f"PII leaked on benign: {leaks}"


def test_weight_zero_invariant(groups):
    """anonymize must not contribute to risk_score (sanitization, not a verdict)."""
    guard = _guard_module()
    # The weights map lives inside _calculate_risk_score; assert anonymize is absent
    # (weight 0) so a redaction never moves the overall risk_score.
    instance = guard.LLMGuard.__new__(guard.LLMGuard)
    score = guard.LLMGuard._calculate_risk_score(
        instance, {"anonymize": {"passed": False, "score": 1.0}}
    )
    assert score == 0.0
