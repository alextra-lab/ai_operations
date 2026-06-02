"""Native port of llm-guard's Gibberish input scanner (MIT).

Verbatim from ``llm_guard.input_scanners.gibberish`` (llm-guard==0.3.16), with
the dependency swaps from ``_onnx_classifier``. Model config matches what
``guard.py::configure_models`` applies to the gibberish ``DEFAULT_MODEL`` (onnx
subfolder, ``model.onnx``, local files only). Only MatchType.FULL is ported --
the production config and the only nltk-free branch.
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

_GIBBERISH_LABELS = ["word salad", "noise", "mild gibberish"]


def build_model(model_path: str) -> Model:
    return Model(
        path=model_path,
        onnx_path=f"{model_path}/onnx",
        onnx_subfolder="",
        onnx_filename="model.onnx",
        pipeline_kwargs={
            "return_token_type_ids": False,
            "max_length": 512,
            "truncation": True,
        },
        kwargs={"local_files_only": True, "trust_remote_code": False},
    )


class GibberishScanner:
    """Detects gibberish text via a HuggingFace classifier (MatchType.FULL)."""

    def __init__(self, model_path: str, *, threshold: float = 0.97) -> None:
        self._threshold = threshold
        model = build_model(model_path)
        tf_tokenizer, tf_model = get_tokenizer_and_model_for_classification(model)
        self._classifier = pipeline(model=tf_model, tokenizer=tf_tokenizer, **model.pipeline_kwargs)

    def scan(self, prompt: str) -> tuple[str, bool, float]:
        if prompt.strip() == "":
            return prompt, True, -1.0

        highest_score = 0.0
        results_all = self._classifier([prompt])
        for result in results_all:
            score = round(
                result["score"] if result["label"] in _GIBBERISH_LABELS else 1 - result["score"],
                2,
            )
            if score > highest_score:
                highest_score = score

        if highest_score > self._threshold:
            LOGGER.warning("Detected gibberish text (score=%s)", highest_score)
            return prompt, False, calculate_risk_score(highest_score, self._threshold)

        LOGGER.debug("No gibberish in the text (highest_score=%s)", highest_score)
        return prompt, True, calculate_risk_score(highest_score, self._threshold)
