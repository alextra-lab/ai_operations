"""Documented divergence of native PII from the frozen llm-guard golden (LLG-04 step 3).

The golden baseline (``golden/baseline.json``) is captured from the llm-guard
engine backed by the cc-by-nc distilbert PII model. The native engine is a
deliberate MODEL SWAP (Presidio + GLiNER), so it will NOT reproduce these
redactions verbatim — it is gated on the labelled recall/precision set instead
(``pii_metrics``), not on this golden.

These tests pin the *distilbert* quirks that the native engine intentionally
diverges from, so that:
  1. the divergence is a checked invariant, not a silent break, and
  2. nobody re-baselines the golden to native output (which would conflate the two
     engines and erase the llm_guard reference). The golden stays authoritative
     for ``anonymize_engine=llm_guard`` only.

Runs on the host venv (reads JSON only; no model stack).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_GOLDEN = Path(__file__).parent / "golden" / "baseline.json"


@pytest.fixture(scope="module")
def golden_cases() -> dict:
    data = json.loads(_GOLDEN.read_text())
    return data.get("cases", data)


def _anonymized(golden_cases: dict, case_id: str) -> str:
    return golden_cases[case_id]["response"]["sanitized_text"]


def test_golden_redacts_bonjour_as_person(golden_cases):
    """distilbert redacts the greeting 'Bonjour' as a PERSON (false positive).

    The native Presidio+GLiNER engine intentionally does NOT — 'Bonjour' is a
    greeting, not a name. This asserts the golden still carries the distilbert
    quirk (i.e. the golden has not been re-baselined to native).
    """
    sanitized = _anonymized(golden_cases, "pii_french_greeting")
    assert "Bonjour" not in sanitized
    assert "[REDACTED_PERSON" in sanitized


def test_golden_uses_distilbert_softmax_score(golden_cases):
    """The french-greeting anonymize score is the distilbert softmax artifact 0.6.

    The native engine emits only the cosmetic signed flag (1.0 redacted / -1.0
    clean), never a partial-confidence value — anonymize has weight 0 so the
    number never affects risk_score either way.
    """
    detail = golden_cases["pii_french_greeting"]["response"]["details"]["anonymize"]
    assert detail["passed"] is False
    assert detail["score"] == pytest.approx(0.6)


def test_golden_structured_redactions_present(golden_cases):
    """Structured PII cases remain redacted in the golden (llm_guard reference).

    The native engine also redacts these, but with its own placeholder grammar
    (e.g. ``[REDACTED_US_SSN_1]`` vs the golden ``[REDACTED_US_SSN_RE_1]``) — the
    grammar is not load-bearing, so only the verdict matters.
    """
    for case_id in ("pii_ssn_email", "pii_name_phone_email", "pii_credit_card"):
        assert "[REDACTED_" in _anonymized(golden_cases, case_id)
