"""Pure-logic helpers for the native anonymize/PII scanner (LLG-04 step 3).

Original code (not a vendored port) — linted and type-checked normally. Kept
free of the heavy ``presidio_analyzer`` / ``gliner`` stack so the placeholder
grammar, overlap resolution, and GLiNER label mapping can be unit-tested on the
host venv without loading any model. ``anonymize_scanner`` and
``_gliner_recognizer`` import these helpers.
"""

from __future__ import annotations

from dataclasses import dataclass

# GLiNER is a zero-shot NER model: it returns whichever label strings it is
# prompted with. We prompt it only for the free-text entities it handles well
# (structured PII like email/card/SSN is covered far more precisely by the
# Presidio pattern recognizers) and map each prompt label to its canonical
# Presidio entity type. The mapping MUST be total over ``GLINER_PII_LABELS`` —
# an unmapped label silently drops recall (eval doc §4.4). ``test_pii_logic``
# asserts totality.
# ORGANIZATION is intentionally excluded: it is the noisiest GLiNER label (it
# confidently tags common phrases like "downtown hotel"/"pipeline run"/"We") and
# company names are generally not personal data. The ratified PII bar covers
# PERSON/LOCATION only (LLG-04 / AIO-72).
GLINER_LABEL_TO_ENTITY: dict[str, str] = {
    "person": "PERSON",
    "location": "LOCATION",
}

# The label set handed to ``GLiNER.predict_entities``.
GLINER_PII_LABELS: list[str] = list(GLINER_LABEL_TO_ENTITY)


@dataclass(frozen=True)
class Span:
    """A detected PII span over the original text."""

    start: int
    end: int
    entity: str
    score: float


def map_gliner_label(label: str) -> str | None:
    """Map a GLiNER prompt label to a canonical Presidio entity, or None."""
    return GLINER_LABEL_TO_ENTITY.get(label.strip().lower())


def resolve_overlaps(spans: list[Span]) -> list[Span]:
    """Drop overlapping spans, keeping the highest-scoring (then longest).

    Presidio's AnalyzerEngine performs equivalent conflict resolution internally;
    we reimplement it here because the native scanner merges results from several
    recognizers without going through ``AnalyzerEngine``.
    """
    # Highest score first; on a tie prefer the longer span, then the earlier one.
    ordered = sorted(spans, key=lambda s: (-s.score, -(s.end - s.start), s.start))
    kept: list[Span] = []
    for span in ordered:
        if any(not (span.end <= k.start or span.start >= k.end) for k in kept):
            continue
        kept.append(span)
    return kept


def build_redaction(text: str, spans: list[Span]) -> tuple[str, int]:
    """Redact ``spans`` to ``[REDACTED_<ENTITY>_<n>]`` placeholders.

    Overlaps are resolved first; placeholders are numbered per entity type in
    reading order. Returns the redacted text and the number of spans redacted.

    The placeholder *grammar* mirrors the llm-guard Vault style for tidiness, but
    carries no downstream contract weight (no consumer parses it; the orchestrator
    treats ``sanitized_text`` as opaque).
    """
    kept = sorted(resolve_overlaps(spans), key=lambda s: s.start)
    counters: dict[str, int] = {}
    out: list[str] = []
    cursor = 0
    for span in kept:
        counters[span.entity] = counters.get(span.entity, 0) + 1
        out.append(text[cursor : span.start])
        out.append(f"[REDACTED_{span.entity}_{counters[span.entity]}]")
        cursor = span.end
    out.append(text[cursor:])
    return "".join(out), len(kept)
