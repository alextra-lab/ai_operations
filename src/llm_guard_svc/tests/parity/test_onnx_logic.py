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


class TestOnnxTextClassifier:
    """_OnnxTextClassifier forward-pass logic with a mocked session and tokenizer."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_classifier(id2label: dict, logits: list[float], top_k: int | None = 1):
        from unittest.mock import MagicMock

        import numpy as np

        from src.llm_guard_svc.app.scanners._onnx_classifier import (
            _OnnxClassifierModel,
            _OnnxTextClassifier,
        )

        # Mock tokenizer: returns numpy arrays for input_ids and attention_mask.
        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {
            "input_ids": np.array([[1, 2, 3]]),
            "attention_mask": np.array([[1, 1, 1]]),
        }
        mock_tokenizer.model_max_length = 512

        # Mock session inputs: two named inputs.
        inp_ids = MagicMock()
        inp_ids.name = "input_ids"
        attn_mask = MagicMock()
        attn_mask.name = "attention_mask"

        mock_session = MagicMock()
        mock_session.get_inputs.return_value = [inp_ids, attn_mask]
        # session.run(None, feed)[0][0] must yield a 1-D array of logits.
        mock_session.run.return_value = [np.array([logits])]

        ort_model = _OnnxClassifierModel(session=mock_session, id2label=id2label)
        return _OnnxTextClassifier(
            model=ort_model,
            tokenizer=mock_tokenizer,
            max_length=512,
            truncation=True,
            top_k=top_k,
            return_token_type_ids=False,
        )

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_top1_returns_single_dict(self):
        import math

        id2label = {0: "SAFE", 1: "INJECTION"}
        clf = self._make_classifier(id2label, logits=[0.1, 2.5], top_k=1)
        result = clf(["hello"])

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0]["label"] == "INJECTION"
        assert isinstance(result[0]["score"], float)

        # Expected softmax score for class 1.
        e0, e1 = math.exp(0.1), math.exp(2.5)
        expected = e1 / (e0 + e1)
        assert abs(result[0]["score"] - expected) < 1e-6
        assert result[0]["score"] > 0.9

    def test_top_k_none_returns_list_of_dicts(self):
        id2label = {0: "SAFE", 1: "INJECTION"}
        clf = self._make_classifier(id2label, logits=[2.0, 0.5], top_k=None)
        result = clf(["hello"])

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], list)
        assert len(result[0]) == 2
        # Sorted descending by score — class 0 (SAFE) wins.
        assert result[0][0]["label"] == "SAFE"
        assert result[0][1]["label"] == "INJECTION"
        assert result[0][0]["score"] > result[0][1]["score"]

    def test_multiple_inputs_returns_one_result_per_input(self):
        id2label = {0: "SAFE", 1: "INJECTION"}
        clf = self._make_classifier(id2label, logits=[1.0, 0.0], top_k=1)
        result = clf(["text1", "text2", "text3"])

        assert len(result) == 3
        for item in result:
            assert isinstance(item, dict)
            assert "label" in item
            assert "score" in item

    def test_bare_string_input_wrapped(self):
        id2label = {0: "SAFE", 1: "INJECTION"}
        clf = self._make_classifier(id2label, logits=[0.5, 1.5], top_k=1)
        result = clf("bare string")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)

    def test_softmax_scores_sum_to_one(self):
        id2label = {0: "A", 1: "B", 2: "C"}
        clf = self._make_classifier(id2label, logits=[1.0, 2.0, 3.0], top_k=None)
        result = clf(["hello"])

        total = sum(r["score"] for r in result[0])
        assert abs(total - 1.0) < 1e-6
