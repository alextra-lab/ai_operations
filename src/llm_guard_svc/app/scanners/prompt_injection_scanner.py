"""Native port of llm-guard's PromptInjection input scanner (MIT).

Verbatim from ``llm_guard.input_scanners.prompt_injection`` (llm-guard==0.3.16),
with only the dependency swaps from ``_onnx_classifier`` (stdlib logging, direct
transformers/onnxruntime imports via ``_onnx_classifier``, Scanner Protocol base
dropped). The model config matches what ``guard.py::configure_models`` applies to
``V2_SMALL_MODEL`` at runtime (onnx subfolder layout, ``use_fast=False`` tokenizer,
``local_files_only``), so detection is identical to the service at the pinned transformers.

Only the MatchType branches the service uses are ported (FULL,
TRUNCATE_HEAD_TAIL, TRUNCATE_TOKEN_HEAD_TAIL); SENTENCE/CHUNKS depended on nltk
and are unused (production config is TRUNCATE_HEAD_TAIL).
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from ._onnx_classifier import (
    Model,
    calculate_risk_score,
    get_tokenizer_and_model_for_classification,
    pipeline,
    truncate_tokens_head_tail,
)

LOGGER = logging.getLogger(__name__)

PROMPT_CHARACTERS_LIMIT = 256


def build_model(model_path: str) -> Model:
    """Construct the prompt-injection Model from a resolved local model dir.

    Mirrors ``V2_SMALL_MODEL`` after ``configure_models``: onnx in the ``onnx``
    subfolder, ``model.onnx`` file, slow tokenizer, local files only. ``revision``
    is left ``None`` -- a no-op for the local directory under ``local_files_only``.
    """
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
        tokenizer_kwargs={"use_fast": False},
        kwargs={"local_files_only": True, "trust_remote_code": False},
    )


class MatchType(Enum):
    FULL = "full"
    # Split the prompt into two parts (126 head and 382 tail tokens) and check.
    TRUNCATE_TOKEN_HEAD_TAIL = "truncate_token_head_tail"
    # Split the prompt into a head/tail of characters joined by "...".
    TRUNCATE_HEAD_TAIL = "truncate_head_tail"

    _tokenizer: Any

    def set_tokenizer(self, tokenizer: Any) -> None:
        self._tokenizer = tokenizer

    def get_inputs(self, prompt: str) -> list[str]:
        if self == MatchType.TRUNCATE_TOKEN_HEAD_TAIL and self._tokenizer is not None:
            tokenized_input = self._tokenizer.tokenize(prompt)
            return [
                self._tokenizer.convert_tokens_to_string(truncate_tokens_head_tail(tokenized_input))
            ]

        if self == MatchType.TRUNCATE_HEAD_TAIL and len(prompt) > PROMPT_CHARACTERS_LIMIT:
            part_length = (PROMPT_CHARACTERS_LIMIT - 3) // 2
            start = prompt[:part_length]
            end = prompt[-part_length:]
            return [f"{start}...{end}"]

        return [prompt]


class PromptInjectionScanner:
    """Detects prompt-injection attempts via a HuggingFace classifier."""

    def __init__(
        self,
        model_path: str,
        *,
        threshold: float = 0.92,
        match_type: MatchType = MatchType.TRUNCATE_HEAD_TAIL,
    ) -> None:
        self._threshold = threshold
        model = build_model(model_path)
        tf_tokenizer, tf_model = get_tokenizer_and_model_for_classification(model)
        self._pipeline = pipeline(model=tf_model, tokenizer=tf_tokenizer, **model.pipeline_kwargs)
        match_type.set_tokenizer(tf_tokenizer)
        self._match_type = match_type

    def scan(self, prompt: str) -> tuple[str, bool, float]:
        if prompt.strip() == "":
            return prompt, True, -1.0

        highest_score = 0.0
        results_all = self._pipeline(self._match_type.get_inputs(prompt))
        for result in results_all:
            injection_score = round(
                result["score"] if result["label"] == "INJECTION" else 1 - result["score"],
                2,
            )

            if injection_score > highest_score:
                highest_score = injection_score

            if injection_score > self._threshold:
                LOGGER.warning("Detected prompt injection (score=%s)", injection_score)
                return prompt, False, calculate_risk_score(injection_score, self._threshold)

        LOGGER.debug("No prompt injection detected (highest_score=%s)", highest_score)
        return prompt, True, calculate_risk_score(highest_score, self._threshold)
