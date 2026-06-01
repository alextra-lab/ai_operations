"""Per-scanner parity for the native regex + secrets scanners (LLG-04 step 1).

Validates the native ports against the golden baseline WITHOUT the heavy model
stack: native scanners import only detect_secrets + presidio_anonymizer.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.llm_guard_svc.app.scanners.regex_scanner import RegexScanner
from src.llm_guard_svc.tests.parity.corpus import CORPUS

GOLDEN_PATH = Path(__file__).parent / "golden" / "baseline.json"

# Cases where exactly one of {regex, secrets} redacts and upstream scanners are
# no-ops, so the golden final sanitized_text equals that scanner's own output.
EXPECTED_REDACTION = {
    "regex_password_assignment": ("regex", "[REDACTED]"),
    "regex_api_key_colon": ("regex", "[REDACTED]"),
    "regex_ssh_rsa_key": ("regex", "Deploy key: [REDACTED] admin@host"),
    "secret_aws_keypair": ("secrets", "aws_access_key_id=****** aws_secret_access_key=******"),
    "secret_github_pat": ("secrets", "export GH_TOKEN=************AB"),
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
