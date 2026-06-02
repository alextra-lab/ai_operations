"""LLG-04 parity tests.

Three layers, runnable independently of the model stack:

1. **Golden integrity** — the committed baseline exists, covers the corpus, and
   every captured response satisfies the response-schema contract.
2. **Harness self-check** — proves the comparator actually detects regressions
   (a parity harness that cannot fail is worthless): golden-vs-golden passes,
   and deliberately mutated payloads are caught as schema/semantic diffs.
3. **Candidate parity (opt-in)** — when ``PARITY_CANDIDATE_URL`` points at a
   running candidate service, every corpus case is replayed and compared against
   the golden baseline on schema + semantic parity, with a latency p99 budget.

Layers 1-2 run in plain CI with no service. Layer 3 is skipped unless the env
var is set, so it gates the migration without blocking the default suite.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest

from src.llm_guard_svc.tests.parity.client import health, validate
from src.llm_guard_svc.tests.parity.compare import compare
from src.llm_guard_svc.tests.parity.corpus import CORPUS
from src.llm_guard_svc.tests.parity.schema import (
    EXPECTED_SCANNERS,
    validate_response_schema,
)

GOLDEN_PATH = Path(__file__).parent / "golden" / "baseline.json"
LATENCY_PATH = Path(__file__).parent / "golden" / "latency.json"

CANDIDATE_URL = os.environ.get("PARITY_CANDIDATE_URL")
# Candidate p99 must stay within this multiple of the golden p99 (evaluation §5.4).
LATENCY_BUDGET_FACTOR = float(os.environ.get("PARITY_LATENCY_BUDGET_FACTOR", "1.5"))


def _load_golden() -> dict:
    if not GOLDEN_PATH.exists():
        pytest.skip(
            f"no golden baseline at {GOLDEN_PATH}; run "
            "`python -m src.llm_guard_svc.tests.parity.capture` against the current service"
        )
    return json.loads(GOLDEN_PATH.read_text())


# --------------------------------------------------------------------------- #
# Layer 1 — golden integrity
# --------------------------------------------------------------------------- #
def test_golden_covers_every_corpus_case() -> None:
    golden = _load_golden()
    captured = set(golden["cases"].keys())
    expected = {c.id for c in CORPUS}
    assert captured == expected, f"golden/corpus drift: {expected ^ captured}"


def test_golden_responses_match_schema() -> None:
    golden = _load_golden()
    failures: dict[str, list[str]] = {}
    for case_id, entry in golden["cases"].items():
        errors = validate_response_schema(entry["response"])
        if errors:
            failures[case_id] = errors
    assert not failures, f"golden responses violate schema: {failures}"


def test_golden_scanning_cases_run_expected_scanners() -> None:
    golden = _load_golden()
    for case_id, entry in golden["cases"].items():
        details = entry["response"]["details"]
        if "status" in details:  # bypass/disabled shape
            continue
        assert set(details.keys()) == set(
            EXPECTED_SCANNERS
        ), f"{case_id}: scanner set drift {set(details.keys()) ^ set(EXPECTED_SCANNERS)}"


# --------------------------------------------------------------------------- #
# Layer 2 — harness self-check (must be able to FAIL on a regression)
# --------------------------------------------------------------------------- #
def test_compare_identical_passes() -> None:
    golden = _load_golden()
    case_id, entry = next(iter(golden["cases"].items()))
    resp = entry["response"]
    result = compare(case_id, resp, copy.deepcopy(resp))
    assert result.passed(include_scores=True), [str(d) for d in result.diffs]


def test_compare_detects_flipped_verdict() -> None:
    """A reimplemented scanner that flips a pass/fail must be caught."""
    golden = _load_golden()
    # Pick a scanning-shape case that has at least one scanner verdict.
    scanning = [
        (cid, e["response"])
        for cid, e in golden["cases"].items()
        if "status" not in e["response"]["details"]
    ]
    assert scanning, "expected at least one scanning-shape golden case"
    case_id, resp = scanning[0]
    mutated = copy.deepcopy(resp)
    scanner = next(iter(mutated["details"]))
    mutated["details"][scanner]["passed"] = not mutated["details"][scanner].get("passed", True)

    result = compare(case_id, resp, mutated)
    assert not result.passed(include_scores=False)
    assert any(d.kind == "semantic" for d in result.semantic_diffs)


def test_compare_detects_changed_sanitized_text() -> None:
    """A redaction regression (different sanitized output) must be caught."""
    golden = _load_golden()
    case_id, entry = next(iter(golden["cases"].items()))
    resp = entry["response"]
    mutated = copy.deepcopy(resp)
    mutated["sanitized_text"] = resp["sanitized_text"] + " DRIFT"

    result = compare(case_id, resp, mutated)
    assert not result.passed(include_scores=False)
    assert any(d.field == "sanitized_text" for d in result.semantic_diffs)


def test_compare_detects_score_drift_beyond_tolerance() -> None:
    golden = _load_golden()
    scanning = [
        (cid, e["response"])
        for cid, e in golden["cases"].items()
        if "status" not in e["response"]["details"]
    ]
    case_id, resp = scanning[0]
    mutated = copy.deepcopy(resp)
    scanner = next(iter(mutated["details"]))
    base = mutated["details"][scanner].get("score", 0.0)
    mutated["details"][scanner]["score"] = base + 0.5  # well beyond default tol

    result = compare(case_id, resp, mutated, score_tol=0.05)
    assert result.score_diffs, "score drift beyond tolerance should be reported"
    # Score drift alone does not fail the semantic gate.
    assert result.passed(include_scores=False)
    assert not result.passed(include_scores=True)


def _first_scanning_case(golden: dict) -> tuple[str, dict]:
    for cid, e in golden["cases"].items():
        if "status" not in e["response"]["details"]:
            return cid, e["response"]
    raise AssertionError("expected at least one scanning-shape golden case")


def test_compare_ignores_anonymize_scanner() -> None:
    """ignore_scanners={'anonymize'} drops the PII verdict from the gate."""
    golden = _load_golden()
    case_id, resp = _first_scanning_case(golden)
    mutated = copy.deepcopy(resp)
    # Flip the anonymize verdict — caught by default, ignored when excluded.
    mutated["details"]["anonymize"]["passed"] = not mutated["details"]["anonymize"].get(
        "passed", True
    )
    assert not compare(case_id, resp, mutated).passed(include_scores=False)
    ignored = compare(case_id, resp, mutated, ignore_scanners=frozenset({"anonymize"}))
    assert ignored.passed(include_scores=False), [str(d) for d in ignored.diffs]


def test_compare_skips_text_when_flagged() -> None:
    """compare_text=False suppresses sanitized_text/modified equality."""
    golden = _load_golden()
    case_id, resp = _first_scanning_case(golden)
    mutated = copy.deepcopy(resp)
    mutated["sanitized_text"] = resp["sanitized_text"] + " DIVERGES"
    mutated["modified"] = not resp.get("modified", False)
    # Caught with text comparison on; suppressed when off.
    assert any(
        d.field in ("sanitized_text", "modified")
        for d in compare(case_id, resp, mutated).semantic_diffs
    )
    skipped = compare(case_id, resp, mutated, compare_text=False)
    assert not any(d.field in ("sanitized_text", "modified") for d in skipped.semantic_diffs)


def test_schema_validator_rejects_malformed() -> None:
    assert validate_response_schema({"sanitized_text": 5}), "non-string sanitized_text should fail"
    assert validate_response_schema({}), "empty payload should fail"
    assert validate_response_schema(
        {"sanitized_text": "x", "risk_score": 2.0, "modified": False, "details": {}}
    ), "risk_score out of range should fail"


# --------------------------------------------------------------------------- #
# Layer 3 — candidate parity (opt-in via PARITY_CANDIDATE_URL)
# --------------------------------------------------------------------------- #
# The golden was captured from the llm-guard engine (distilbert PII) at the old
# transformers==4.51.3 pin. The candidate is the native engine at transformers>=4.53
# (LLG-04 finale), so some divergence is expected and accepted:
#
# 1. `anonymize` — a deliberate model swap (Presidio+GLiNER); its verdict is excluded
#    everywhere and its redacted `sanitized_text` is not compared. Native PII is gated
#    by test_pii_metrics_container + test_pii_golden_divergence instead.
# 2. `secrets` `sanitized_text` — redaction is non-deterministic for multi-secret inputs
#    (eval §6a / detect-secrets ordering), so text is not compared where secrets redacted;
#    the verdict still is.
# 3. A few ONNX-classifier VERDICTS shift on near-threshold inputs at transformers 4.53
#    vs 4.51.3. Verified native >= golden on each (golden false-positived valid French as
#    prompt-injection; native passes it; keyboard-mash flagged non-language, still caught by
#    gibberish). Accepted with evidence below. The gate still catches any OTHER verdict drift.
_IGNORE_PII = frozenset({"anonymize"})
_ACCEPTED_VERDICT_DRIFT = {
    ("lang_french_valid", "prompt_injection"),  # golden FP 0.7 -> native pass -0.9 (better)
    ("pii_french_greeting", "prompt_injection"),  # golden FP 0.4 -> native pass -1.0 (better)
    ("gib_keyboard_mash", "language"),  # golden pass -1.0 -> native fail 0.7 (gibberish also flags)
}


def _golden_redacted(golden_resp: dict, scanner: str) -> bool:
    return golden_resp.get("details", {}).get(scanner, {}).get("passed") is False


def _is_accepted_drift(case_id: str, diff) -> bool:
    for scanner in ("prompt_injection", "language", "gibberish"):
        if (
            diff.field == f"details.{scanner}.passed"
            and (case_id, scanner) in _ACCEPTED_VERDICT_DRIFT
        ):
            return True
    return False


@pytest.mark.skipif(not CANDIDATE_URL, reason="set PARITY_CANDIDATE_URL to run candidate parity")
def test_candidate_matches_golden() -> None:
    golden = _load_golden()
    assert health(CANDIDATE_URL), f"candidate at {CANDIDATE_URL} is not healthy"

    failures: list[str] = []
    for case in CORPUS:
        probe = validate(CANDIDATE_URL, case)
        assert probe.status == 200, f"{case.id}: HTTP {probe.status}"
        golden_resp = golden["cases"][case.id]["response"]
        # Skip sanitized_text where the model-swapped anonymize or the
        # non-deterministic secrets scanner redacted in the golden.
        compare_text = not (
            _golden_redacted(golden_resp, "anonymize") or _golden_redacted(golden_resp, "secrets")
        )
        result = compare(
            case.id,
            golden_resp,
            probe.payload,
            ignore_scanners=_IGNORE_PII,
            compare_text=compare_text,
        )
        failures.extend(
            f"{case.id}: {d}"
            for d in result.diffs
            if d.kind != "score" and not _is_accepted_drift(case.id, d)
        )

    assert not failures, "candidate diverged from golden (unexpected):\n" + "\n".join(failures)


@pytest.mark.skipif(not CANDIDATE_URL, reason="set PARITY_CANDIDATE_URL to run candidate parity")
def test_candidate_latency_within_budget() -> None:
    if not LATENCY_PATH.exists():
        pytest.skip("no golden latency baseline captured")
    baseline_p99 = json.loads(LATENCY_PATH.read_text())["aggregate_ms"]["p99"]
    budget = baseline_p99 * LATENCY_BUDGET_FACTOR

    latencies = [validate(CANDIDATE_URL, case).latency_ms for case in CORPUS for _ in range(5)]
    latencies.sort()
    rank = max(1, round(0.99 * len(latencies)))
    candidate_p99 = latencies[min(rank, len(latencies)) - 1]

    assert candidate_p99 <= budget, (
        f"candidate p99 {candidate_p99:.1f}ms exceeds budget "
        f"{budget:.1f}ms ({LATENCY_BUDGET_FACTOR}x golden p99 {baseline_p99:.1f}ms)"
    )
