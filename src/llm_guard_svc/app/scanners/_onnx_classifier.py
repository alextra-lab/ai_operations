"""Native port of llm-guard's ONNX text-classification machinery (MIT).

Verbatim from llm-guard==0.3.16 (``llm_guard/model.py``,
``llm_guard/transformers_helpers.py``, ``llm_guard/util.py``), with only the
dependency swaps needed to drop the ``llm_guard`` import:
  * ``llm_guard.util.get_logger``      -> stdlib logging
  * ``lazy_load_dep(...)``             -> direct ``transformers`` / ``optimum`` imports
    (both are hard dependencies of this service, so the lazy wrapper is moot)
  * the structural ``Scanner`` Protocol base is dropped (not needed at runtime)

The ``Model`` dataclass, ``calculate_risk_score`` convention,
``truncate_tokens_head_tail`` splitting, the tokenizer/ONNX loading, and the
HuggingFace ``text-classification`` pipeline construction are unchanged -- so at
the pinned ``transformers==4.51.3`` + ``optimum[onnxruntime]==1.25.2`` the native
scanners call the identical tokenizer + ONNX graph + pipeline as llm-guard, and
their output matches the current service by construction (LLG-04 step 2).
"""

from __future__ import annotations

import dataclasses
import logging
from functools import cache
from typing import Any

LOGGER = logging.getLogger(__name__)


# --- llm_guard.util.device (verbatim; torch ships via transformers[torch]) ----
@cache
def device() -> Any:
    import torch

    if torch.cuda.is_available():
        return torch.device("cuda:0")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


# --- llm_guard.model.Model (verbatim) -----------------------------------------
@dataclasses.dataclass
class Model:
    """Stores model information (path + ONNX layout + transformers kwargs)."""

    path: str
    subfolder: str = ""
    revision: str | None = None
    onnx_path: str | None = None
    onnx_revision: str | None = None
    onnx_subfolder: str = ""
    onnx_filename: str = "model.onnx"
    kwargs: dict = dataclasses.field(default_factory=dict)
    pipeline_kwargs: dict = dataclasses.field(default_factory=dict)
    tokenizer_kwargs: dict = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        default_pipeline_kwargs = {
            "batch_size": 1,
            "device": device(),
        }
        self.pipeline_kwargs = {**default_pipeline_kwargs, **self.pipeline_kwargs}

    def __str__(self) -> str:
        return self.path


# --- llm_guard.util.calculate_risk_score (verbatim) ---------------------------
def calculate_risk_score(score: float, threshold: float) -> float:
    """Risk score in [-1, 1]; negative below the threshold, positive above."""
    if score > threshold:
        risk_score = round((score - threshold) / (1 - threshold), 1)
    else:
        risk_score = round((score - threshold) / threshold, 1)

    return min(max(risk_score, -1), 1)


# --- llm_guard.util.truncate_tokens_head_tail (verbatim) ----------------------
def truncate_tokens_head_tail(
    tokens: list[Any],
    max_length: int = 512,
    head_length: int = 128,
    tail_length: int = 382,
) -> list[Any]:
    if len(tokens) > max_length:
        head_tokens = tokens[:head_length]
        tail_tokens = tokens[-tail_length:]
        tokens = head_tokens + tail_tokens
    return tokens


# --- llm_guard.transformers_helpers (ONNX path, verbatim minus lazy_load_dep) -
def get_tokenizer_and_model_for_classification(model: Model) -> tuple[Any, Any]:
    """Load the tokenizer + ONNX sequence-classification model for ``model``.

    Mirrors llm-guard's ``get_tokenizer_and_model_for_classification(..., use_onnx=True)``
    -- the only path this service uses.
    """
    import transformers

    tf_tokenizer = transformers.AutoTokenizer.from_pretrained(
        model.path, revision=model.revision, **model.tokenizer_kwargs
    )

    from optimum.onnxruntime import ORTModelForSequenceClassification

    provider = "CUDAExecutionProvider" if device().type == "cuda" else "CPUExecutionProvider"
    tf_model = ORTModelForSequenceClassification.from_pretrained(
        model.onnx_path or model.path,
        export=model.onnx_path is None,
        file_name=model.onnx_filename,
        subfolder=model.onnx_subfolder,
        revision=model.onnx_revision,
        provider=provider,
        **model.kwargs,
    )
    LOGGER.debug("Initialized classification ONNX model: %s", model)
    return tf_tokenizer, tf_model


def pipeline(model: Any, tokenizer: Any, **kwargs: Any) -> Any:
    """HuggingFace ``text-classification`` pipeline (verbatim factory)."""
    import transformers

    if kwargs.get("max_length") is None:
        kwargs["max_length"] = tokenizer.model_max_length

    return transformers.pipeline(
        "text-classification",
        model=model,
        tokenizer=tokenizer,
        **kwargs,
    )
