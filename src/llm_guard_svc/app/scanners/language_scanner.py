"""Native port of llm-guard's Language input scanner (MIT).

Verbatim from ``llm_guard.input_scanners.language`` (llm-guard==0.3.16), with the
dependency swaps from ``_onnx_classifier``. Model config matches what
``guard.py::configure_models`` applies to the language ``DEFAULT_MODEL``: the
ONNX model lives at the model dir root (no ``onnx`` subfolder) under
``model_quantized.onnx``. ``top_k=None`` makes the pipeline return every label's
score per input. Only MatchType.FULL is ported (the production config).
"""

from __future__ import annotations

import logging

from ._onnx_classifier import (
    Model,
    calculate_risk_score,
    get_tokenizer_and_model_for_classification,
    pipeline,
)

LOGGER = logging.getLogger(__name__)


def build_model(model_path: str) -> Model:
    return Model(
        path=model_path,
        onnx_path=model_path,
        onnx_subfolder="",
        onnx_filename="model_quantized.onnx",
        pipeline_kwargs={
            "top_k": None,
            "return_token_type_ids": False,
            "max_length": 512,
            "truncation": True,
        },
        kwargs={"local_files_only": True, "trust_remote_code": False},
    )


class LanguageScanner:
    """Verifies detected languages are within ``valid_languages`` (MatchType.FULL).

    When no language scores above the threshold, the prompt is considered valid.
    """

    def __init__(
        self,
        model_path: str,
        valid_languages: list[str],
        *,
        threshold: float = 0.6,
    ) -> None:
        self._threshold = threshold
        self._valid_languages = valid_languages
        model = build_model(model_path)
        tf_tokenizer, tf_model = get_tokenizer_and_model_for_classification(model)
        self._pipeline = pipeline(model=tf_model, tokenizer=tf_tokenizer, **model.pipeline_kwargs)

    def scan(self, prompt: str) -> tuple[str, bool, float]:
        if prompt.strip() == "":
            return prompt, True, -1.0

        results_all = self._pipeline([prompt])
        for result_chunk in results_all:
            languages_above_threshold = [
                result["label"] for result in result_chunk if result["score"] > self._threshold
            ]
            highest_score = max(result["score"] for result in result_chunk)

            if len(set(languages_above_threshold) - set(self._valid_languages)) > 0:
                LOGGER.warning(
                    "Languages found with high confidence: %s", languages_above_threshold
                )
                return prompt, False, calculate_risk_score(highest_score, self._threshold)

        LOGGER.debug("Only valid languages found in the text.")
        return prompt, True, -1.0
