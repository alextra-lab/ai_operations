"""ONNX text-classification machinery — direct onnxruntime.InferenceSession.

Replaces the previous ``optimum[onnxruntime]`` / ``ORTModelForSequenceClassification``
dependency (removed to close CVE-2026-1839, AIO-77). The heavy ``optimum`` stack
introduced transitive vulnerabilities and unnecessary bloat; a raw
``onnxruntime.InferenceSession`` achieves the same forward pass with no extra
abstraction layer.

Architecture
------------
``get_tokenizer_and_model_for_classification`` loads a ``transformers``
tokenizer and builds an ``_OnnxClassifierModel`` (InferenceSession + id→label map
read from the model's ``config.json``). ``pipeline()`` wraps both into an
``_OnnxTextClassifier`` that is callable with the same input/output shapes as
``transformers.pipeline("text-classification")``:

* Without ``top_k`` (or ``top_k=1``) → ``list[dict]`` — one dict per input string.
* With ``top_k=None``               → ``list[list[dict]]`` — one list per input string.

Output parity is verified by ``tests/parity/`` rather than enforced by sharing
library code with llm-guard.

Public API (unchanged)
----------------------
* ``Model`` dataclass
* ``calculate_risk_score(score, threshold) -> float``
* ``truncate_tokens_head_tail(tokens, ...) -> list``
* ``get_tokenizer_and_model_for_classification(model) -> (tokenizer, _OnnxClassifierModel)``
* ``pipeline(model, tokenizer, **kwargs) -> _OnnxTextClassifier``
"""

from __future__ import annotations

import dataclasses
import logging
import os
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


# --- private helpers (replace optimum.onnxruntime.ORTModelForSequenceClassification) ---


@dataclasses.dataclass
class _OnnxClassifierModel:
    """Holds an onnxruntime InferenceSession + the id→label map from config.json."""

    session: Any  # onnxruntime.InferenceSession
    id2label: dict[int, str]


class _OnnxTextClassifier:
    """Callable that replaces ``transformers.pipeline("text-classification")``.

    Accepts ``list[str]`` or bare ``str`` input and returns the same shapes as the
    HuggingFace pipeline:
    * top_k=1 (default) → ``list[dict]``
    * top_k=None        → ``list[list[dict]]``
    """

    def __init__(
        self,
        model: _OnnxClassifierModel,
        tokenizer: Any,
        *,
        max_length: int,
        truncation: bool,
        top_k: int | None,
        return_token_type_ids: bool,
    ) -> None:
        self._model = model
        self._tokenizer = tokenizer
        self._max_length = max_length
        self._truncation = truncation
        self._top_k = top_k
        self._return_token_type_ids = return_token_type_ids

    def __call__(self, inputs: list[str] | str) -> list[Any]:
        import numpy as np

        if isinstance(inputs, str):
            inputs = [inputs]

        session = self._model.session
        id2label = self._model.id2label
        results: list[Any] = []

        for text in inputs:
            enc = self._tokenizer(
                text,
                return_tensors="np",
                truncation=self._truncation,
                max_length=self._max_length,
                return_token_type_ids=self._return_token_type_ids,
            )

            # Only pass input names the ONNX graph actually declares.
            feed = {inp.name: enc[inp.name] for inp in session.get_inputs() if inp.name in enc}
            logits = session.run(None, feed)[0][0]  # shape: (num_labels,)

            # Numerically-stable softmax.
            e = np.exp(logits - logits.max())
            scores = e / e.sum()

            if self._top_k is None:
                pairs: list[tuple[str, float]] = [
                    (id2label[i], float(scores[i])) for i in range(len(scores))
                ]
                pairs.sort(key=lambda t: t[1], reverse=True)
                results.append([{"label": lbl, "score": sc} for lbl, sc in pairs])
            else:
                best = int(np.argmax(scores))
                results.append({"label": id2label[best], "score": float(scores[best])})

        return results


# --- public API: loader and pipeline factory ----------------------------------


def get_tokenizer_and_model_for_classification(model: Model) -> tuple[Any, Any]:
    """Load the tokenizer + ONNX sequence-classification model for ``model``.

    Returns ``(tokenizer, _OnnxClassifierModel)`` — the same tuple shape as before,
    but the second element is now an ``_OnnxClassifierModel`` instead of an
    ``ORTModelForSequenceClassification``. Callers pass it straight to ``pipeline()``,
    so the change is transparent.
    """
    import onnxruntime
    import transformers

    tf_tokenizer = transformers.AutoTokenizer.from_pretrained(
        model.path, revision=model.revision, **model.tokenizer_kwargs
    )

    # Load id→label from config.json — same source the old pipeline used.
    tf_config = transformers.AutoConfig.from_pretrained(
        model.path, revision=model.revision, **model.kwargs
    )
    id2label: dict[int, str] = {int(k): v for k, v in tf_config.id2label.items()}

    # Resolve the .onnx file path.
    base = model.onnx_path or model.path
    onnx_file = (
        os.path.join(base, model.onnx_subfolder, model.onnx_filename)
        if model.onnx_subfolder
        else os.path.join(base, model.onnx_filename)
    )

    provider = "CUDAExecutionProvider" if device().type == "cuda" else "CPUExecutionProvider"
    session = onnxruntime.InferenceSession(onnx_file, providers=[provider])

    LOGGER.debug("Initialized classification ONNX model: %s", model)
    return tf_tokenizer, _OnnxClassifierModel(session=session, id2label=id2label)


def pipeline(model: Any, tokenizer: Any, **kwargs: Any) -> Any:
    """Return an ``_OnnxTextClassifier`` with ``transformers.pipeline`` output shapes.

    ``batch_size`` and ``device`` (injected by ``Model.__post_init__``) are accepted
    in ``**kwargs`` for API compatibility but are intentionally ignored — the
    ``InferenceSession`` handles execution context internally.
    """
    max_length: int = kwargs.get("max_length") or tokenizer.model_max_length
    truncation: bool = bool(kwargs.get("truncation", True))
    top_k: int | None = kwargs.get("top_k", 1)
    return_token_type_ids: bool = bool(kwargs.get("return_token_type_ids", True))
    return _OnnxTextClassifier(
        model=model,
        tokenizer=tokenizer,
        max_length=max_length,
        truncation=truncation,
        top_k=top_k,
        return_token_type_ids=return_token_type_ids,
    )
