"""GLiNER-backed Presidio recognizer for free-text PII (LLG-04 step 3).

Wraps the GLiNER zero-shot NER model (``urchade/gliner_multi_pii-v1``,
Apache-2.0, en+fr) as a Presidio ``EntityRecognizer`` so it composes with the
Presidio pattern recognizers. The model is loaded lazily on first ``load()`` (the
heavy ``gliner``/``torch`` import lives inside the method), preserving the
service's lazy-model-loading requirement (eval doc §3a.1).

Original code (not a vendored port) — linted and type-checked normally.
"""

from __future__ import annotations

import logging
from typing import Any

from presidio_analyzer import EntityRecognizer, RecognizerResult

from ._pii_common import GLINER_PII_LABELS, map_gliner_label

LOGGER = logging.getLogger(__name__)


class GlinerRecognizer(EntityRecognizer):
    """Presidio recognizer that delegates free-text NER to GLiNER."""

    def __init__(
        self,
        model_path: str,
        *,
        threshold: float = 0.5,
        supported_language: str = "en",
    ) -> None:
        self._model_path = model_path
        self._threshold = threshold
        self._model: Any = None
        # Canonical Presidio entity types GLiNER contributes (PERSON/LOCATION/...).
        supported_entities = sorted(
            {entity for label in GLINER_PII_LABELS if (entity := map_gliner_label(label))}
        )
        super().__init__(
            supported_entities=supported_entities,
            supported_language=supported_language,
            name="GlinerRecognizer",
        )

    def load(self) -> None:
        """Lazily load the GLiNER model from the local model dir (offline)."""
        if self._model is not None:
            return
        from gliner import GLiNER  # heavy import deferred to first use

        LOGGER.info("Loading GLiNER PII model from %s", self._model_path)
        self._model = GLiNER.from_pretrained(self._model_path, local_files_only=True)

    def analyze(
        self,
        text: str,
        entities: list[str],
        nlp_artifacts: Any = None,  # noqa: ARG002 — required by EntityRecognizer interface
    ) -> list[RecognizerResult]:
        """Run GLiNER and return Presidio results for the requested entities."""
        if self._model is None:
            self.load()
        model = self._model
        assert model is not None  # loaded above

        predictions = model.predict_entities(text, GLINER_PII_LABELS, threshold=self._threshold)
        results: list[RecognizerResult] = []
        for pred in predictions:
            entity = map_gliner_label(pred["label"])
            if entity is None or (entities and entity not in entities):
                continue
            results.append(
                RecognizerResult(
                    entity_type=entity,
                    start=pred["start"],
                    end=pred["end"],
                    score=float(pred["score"]),
                )
            )
        return results
