"""Pure-logic unit tests for the native ONNX classifier ports (LLG-04 step 2).

These exercise the ported helpers and match-type input prep WITHOUT loading any
model, so they run anywhere (no transformers/optimum/model files needed). The
model-backed parity against the golden baseline lives in test_onnx_parity.py.
"""

from __future__ import annotations

from src.llm_guard_svc.app.scanners._onnx_classifier import (
    calculate_risk_score,
    truncate_tokens_head_tail,
)
from src.llm_guard_svc.app.scanners.prompt_injection_scanner import (
    PROMPT_CHARACTERS_LIMIT,
    MatchType,
)


class TestCalculateRiskScore:
    """Ported llm-guard signed-risk convention: negative below threshold, positive above."""

    def test_at_threshold_is_zero(self):
        assert calculate_risk_score(0.92, 0.92) == 0.0

    def test_above_threshold_positive(self):
        # (0.99 - 0.92) / (1 - 0.92) = 0.875 -> round(,1) = 0.9
        assert calculate_risk_score(0.99, 0.92) == 0.9

    def test_max_score_clamps_to_one(self):
        assert calculate_risk_score(1.0, 0.92) == 1.0

    def test_below_threshold_negative(self):
        # (0.0 - 0.92) / 0.92 = -1.0
        assert calculate_risk_score(0.0, 0.92) == -1.0

    def test_just_below_threshold(self):
        # (0.46 - 0.92) / 0.92 = -0.5
        assert calculate_risk_score(0.46, 0.92) == -0.5


class TestTruncateTokensHeadTail:
    def test_short_token_list_unchanged(self):
        tokens = list(range(100))
        assert truncate_tokens_head_tail(tokens) == tokens

    def test_long_token_list_keeps_head_and_tail(self):
        tokens = list(range(600))
        out = truncate_tokens_head_tail(tokens)
        assert len(out) == 128 + 382
        assert out[:128] == list(range(128))
        assert out[-382:] == list(range(600 - 382, 600))


class TestPromptInjectionMatchType:
    def test_full_returns_prompt_as_single_input(self):
        assert MatchType.FULL.get_inputs("hello world") == ["hello world"]

    def test_truncate_head_tail_short_prompt_unchanged(self):
        text = "a" * PROMPT_CHARACTERS_LIMIT  # not > limit
        assert MatchType.TRUNCATE_HEAD_TAIL.get_inputs(text) == [text]

    def test_truncate_head_tail_long_prompt_splits(self):
        part = (PROMPT_CHARACTERS_LIMIT - 3) // 2  # 126
        text = "H" * 200 + "T" * 200  # 400 chars > 256
        out = MatchType.TRUNCATE_HEAD_TAIL.get_inputs(text)
        assert len(out) == 1
        assert out[0] == f"{text[:part]}...{text[-part:]}"
        assert out[0].count("...") == 1
        assert len(out[0]) == part * 2 + 3
