"""Native anonymize/PII scanner: Presidio + GLiNER (LLG-04 step 3).

Replaces the llm-guard ``Anonymize`` scanner, which relied on
``Isotonic/distilbert_finetuned_ai4privacy_v2`` — a ``cc-by-nc-4.0``
(non-commercial) model unusable in a commercial product. This native engine uses
permissively-licensed components only:

  * Presidio pattern recognizers (MIT) for structured PII — email, credit card,
    US SSN, phone, IBAN. Language-agnostic regex/checksum matching; invoked
    directly (no spaCy ``NlpEngine``), so en+fr text is handled without a French
    spaCy model.
  * GLiNER ``urchade/gliner_multi_pii-v1`` (Apache-2.0, en+fr) for free-text
    PERSON/LOCATION/ORGANIZATION, wrapped as a Presidio recognizer.

Because this is a deliberate MODEL SWAP (not a verbatim port), it does NOT
reproduce the old distilbert redactions byte-for-byte. It is validated against a
labelled PII recall/precision set, not golden/differential parity. ``anonymize``
has weight 0 in ``_calculate_risk_score``: it redacts text but never moves the
overall ``risk_score``.

Heavy imports (Presidio recognizers, GLiNER) are deferred to ``__init__`` /
first use to preserve lazy model loading (eval doc §3a.1). Original code — linted
and type-checked normally.
"""

from __future__ import annotations

import logging
from typing import Any

from ._pii_common import Span, build_redaction, resolve_overlaps

LOGGER = logging.getLogger(__name__)

# Structured-PII entities handled by Presidio pattern recognizers (high
# precision, model-free). Free-text PERSON/LOCATION/ORGANIZATION come from GLiNER.
_DEFAULT_REGIONS = ("US", "GB", "FR")


class AnonymizeScanner:
    """Detects and redacts PII via Presidio pattern recognizers + GLiNER."""

    def __init__(
        self,
        gliner_model_path: str,
        *,
        score_threshold: float = 0.4,
        gliner_threshold: float = 0.5,
        regions: tuple[str, ...] = _DEFAULT_REGIONS,
    ) -> None:
        self._score_threshold = score_threshold

        # Deferred heavy imports: presidio predefined recognizers + GLiNER wrapper.
        from presidio_analyzer.predefined_recognizers import (
            CreditCardRecognizer,
            EmailRecognizer,
            IbanRecognizer,
            PhoneRecognizer,
            UsSsnRecognizer,
        )

        from ._gliner_recognizer import GlinerRecognizer

        self._pattern_recognizers: list[Any] = [
            EmailRecognizer(),
            CreditCardRecognizer(),
            UsSsnRecognizer(),
            PhoneRecognizer(supported_regions=list(regions)),
            IbanRecognizer(),
        ]
        self._gliner = GlinerRecognizer(gliner_model_path, threshold=gliner_threshold)

    def detect(self, prompt: str) -> list[Span]:
        """Return the resolved, thresholded PII spans for ``prompt``.

        Merges Presidio pattern recognizers + GLiNER, filters by the score
        threshold, and resolves overlaps. Exposed so the labelled-set metric test
        can score entity spans directly (``scan`` only returns redacted text).
        """
        spans: list[Span] = []
        for recognizer in self._pattern_recognizers:
            results = (
                recognizer.analyze(
                    text=prompt,
                    entities=recognizer.supported_entities,
                    nlp_artifacts=None,
                )
                or []
            )
            spans.extend(
                Span(r.start, r.end, r.entity_type, float(r.score))
                for r in results
                if r.score >= self._score_threshold
            )

        gliner_results = self._gliner.analyze(prompt, self._gliner.supported_entities) or []
        spans.extend(
            Span(r.start, r.end, r.entity_type, float(r.score))
            for r in gliner_results
            if r.score >= self._score_threshold
        )
        return resolve_overlaps(spans)

    def scan(self, prompt: str) -> tuple[str, bool, float]:
        """Return ``(sanitized_text, passed, score)``.

        ``passed`` is False when any PII was redacted (drives ``modified=True``);
        ``score`` is cosmetic here (weight 0): ``1.0`` on redaction, ``-1.0``
        clean.
        """
        if prompt.strip() == "":
            return prompt, True, -1.0

        spans = self.detect(prompt)
        if not spans:
            return prompt, True, -1.0
        sanitized, redacted_count = build_redaction(prompt, spans)
        LOGGER.warning("Redacted %d PII span(s)", redacted_count)
        return sanitized, False, 1.0
