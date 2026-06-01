"""Per-scanner parity for the native regex + secrets scanners (LLG-04 step 1).

Validates the native ports against the golden baseline WITHOUT the heavy model
stack: native scanners import only detect_secrets + presidio_anonymizer.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.llm_guard_svc.app.scanners.regex_scanner import RegexScanner
from src.llm_guard_svc.app.scanners.secrets_scanner import SecretsScanner
from src.llm_guard_svc.tests.parity.corpus import CORPUS

GOLDEN_PATH = Path(__file__).parent / "golden" / "baseline.json"

# Exact-string redaction is asserted ONLY for deterministic single-match cases
# (regex). These are no-op upstream, so the golden final sanitized_text equals
# the regex scanner's own output.
#
# The `secrets` scanner's redaction for MULTI-secret inputs is non-deterministic
# in llm-guard itself: Secrets.scan() iterates an unordered SecretsCollection and
# does prompt.find(value) + index-shifting replacement, so the exact mask layout
# varies run-to-run and can even re-leak a secret. The native port reproduces
# this faithfully. Therefore secrets parity is contracted at the VERDICT level
# (passed/score — fully deterministic, asserted in test_secrets_verdict_matches_golden),
# NOT on the redacted string. See the spec for the cutover implication.
REGEX_REDACTION = {
    "regex_password_assignment": "[REDACTED]",
    "regex_api_key_colon": "[REDACTED]",
    "regex_ssh_rsa_key": "Deploy key: [REDACTED] admin@host",
}


@pytest.fixture(scope="module")
def golden():
    if not GOLDEN_PATH.exists():
        pytest.skip("no golden baseline; run the parity capture CLI")
    return json.loads(GOLDEN_PATH.read_text())["cases"]


@pytest.fixture(scope="module")
def regex_scanner():
    return RegexScanner()


@pytest.mark.parametrize("case", CORPUS, ids=[c.id for c in CORPUS])
def test_regex_verdict_matches_golden(case, regex_scanner, golden):
    g = golden[case.id]["response"]["details"]["regex"]
    sanitized, passed, score = regex_scanner.scan(case.text)
    assert passed == g["passed"]
    assert score == g["score"]
    if passed:
        assert sanitized == case.text  # passed -> no redaction


@pytest.fixture(scope="module")
def secrets_scanner():
    return SecretsScanner()


@pytest.mark.parametrize("case", CORPUS, ids=[c.id for c in CORPUS])
def test_secrets_verdict_matches_golden(case, secrets_scanner, golden):
    g = golden[case.id]["response"]["details"]["secrets"]
    sanitized, passed, score = secrets_scanner.scan(case.text)
    assert passed == g["passed"]
    assert score == g["score"]
    if passed:
        assert sanitized == case.text


@pytest.mark.parametrize(
    ("case_id", "expected_text"), list(REGEX_REDACTION.items()), ids=list(REGEX_REDACTION)
)
def test_regex_redaction_matches_golden(case_id, expected_text, regex_scanner, golden):
    text = golden[case_id]["input_text"]
    sanitized, passed, _ = regex_scanner.scan(text)
    assert not passed
    assert sanitized == expected_text
    # Upstream scanners are no-ops for these inputs, so this equals the golden
    # final sanitized_text too.
    assert sanitized == golden[case_id]["response"]["sanitized_text"]
