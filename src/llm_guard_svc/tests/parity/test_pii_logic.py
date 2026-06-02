"""Pure-logic unit tests for the native PII scanner (LLG-04 step 3).

These exercise the redaction grammar, overlap resolution, GLiNER label mapping,
the recall/precision metric, and the integrity of the labelled set — all WITHOUT
loading Presidio or GLiNER, so they run on the host venv. The model-backed metric
gate lives in test_pii_metrics_container.py.
"""

from __future__ import annotations

from src.llm_guard_svc.app.scanners._pii_common import (
    GLINER_LABEL_TO_ENTITY,
    GLINER_PII_LABELS,
    Span,
    build_redaction,
    map_gliner_label,
    resolve_overlaps,
)
from src.llm_guard_svc.tests.parity import pii_metrics
from src.llm_guard_svc.tests.parity.pii_labelled import PII_CASES
from src.llm_guard_svc.tests.parity.pii_metrics import Metrics, aggregate_by_group, score_case


class TestRedactionGrammar:
    @staticmethod
    def _span(text: str, surface: str, entity: str, score: float = 1.0) -> Span:
        start = text.index(surface)
        return Span(start, start + len(surface), entity, score)

    def test_per_entity_counter(self):
        text = "a jane@x.io b ops@x.io c"
        spans = [
            self._span(text, "jane@x.io", "EMAIL_ADDRESS"),
            self._span(text, "ops@x.io", "EMAIL_ADDRESS"),
        ]
        out, n = build_redaction(text, spans)
        assert out == "a [REDACTED_EMAIL_ADDRESS_1] b [REDACTED_EMAIL_ADDRESS_2] c"
        assert n == 2

    def test_distinct_entities_number_independently(self):
        text = "x 123-45-6789 y bob@x.io"
        spans = [
            self._span(text, "123-45-6789", "US_SSN", 0.5),
            self._span(text, "bob@x.io", "EMAIL_ADDRESS"),
        ]
        out, _ = build_redaction(text, spans)
        assert out == "x [REDACTED_US_SSN_1] y [REDACTED_EMAIL_ADDRESS_1]"

    def test_empty_and_no_spans(self):
        assert build_redaction("", []) == ("", 0)
        assert build_redaction("clean text", []) == ("clean text", 0)


class TestOverlapResolution:
    def test_keeps_higher_score(self):
        kept = resolve_overlaps([Span(0, 10, "PERSON", 0.6), Span(3, 8, "LOCATION", 0.9)])
        assert [(s.entity, s.score) for s in kept] == [("LOCATION", 0.9)]

    def test_disjoint_spans_all_kept(self):
        kept = resolve_overlaps([Span(0, 3, "PERSON", 0.6), Span(5, 9, "LOCATION", 0.6)])
        assert len(kept) == 2

    def test_redaction_resolves_overlaps(self):
        # An email span fully covering a stray PERSON sub-span -> only the email.
        text = "mail bob@acme.com here"
        spans = [Span(5, 17, "EMAIL_ADDRESS", 1.0), Span(5, 8, "PERSON", 0.7)]
        out, n = build_redaction(text, spans)
        assert out == "mail [REDACTED_EMAIL_ADDRESS_1] here"
        assert n == 1


class TestGlinerLabelMap:
    def test_mapping_is_total(self):
        # Every prompted label must map -> an unmapped label silently drops recall.
        assert all(map_gliner_label(label) is not None for label in GLINER_PII_LABELS)

    def test_case_insensitive(self):
        assert map_gliner_label("PERSON") == "PERSON"
        assert map_gliner_label(" Person ") == "PERSON"

    def test_unknown_label_is_none(self):
        assert map_gliner_label("spaceship") is None

    def test_canonical_entities_are_known(self):
        assert set(GLINER_LABEL_TO_ENTITY.values()) <= pii_metrics.FREE_TEXT_ENTITIES


class TestMetrics:
    def test_exact_match(self):
        gold = [Span(0, 5, "PERSON", 1.0)]
        pred = [Span(0, 5, "PERSON", 1.0)]
        assert score_case(gold, pred) == Metrics(1, 0, 0)

    def test_partial_overlap_is_tp(self):
        gold = [Span(0, 10, "PERSON", 1.0)]
        pred = [Span(2, 7, "PERSON", 1.0)]
        assert score_case(gold, pred).tp == 1

    def test_wrong_type_is_not_tp(self):
        gold = [Span(0, 10, "PERSON", 1.0)]
        pred = [Span(0, 10, "LOCATION", 1.0)]
        m = score_case(gold, pred)
        assert (m.tp, m.fp, m.fn) == (0, 1, 1)

    def test_false_positive_on_benign(self):
        assert score_case([], [Span(0, 4, "PERSON", 1.0)]) == Metrics(0, 1, 0)

    def test_recall_precision_f1_math(self):
        m = Metrics(tp=8, fp=2, fn=2)
        assert m.precision == 0.8
        assert m.recall == 0.8
        assert round(m.f1, 3) == 0.8

    def test_empty_is_perfect(self):
        m = score_case([], [])
        assert m.recall == 1.0 and m.precision == 1.0

    def test_aggregate_routes_by_group(self):
        gold = [Span(0, 5, "PERSON", 1.0), Span(6, 17, "US_SSN", 1.0)]
        pred = [Span(0, 5, "PERSON", 1.0), Span(6, 17, "US_SSN", 1.0)]
        groups = aggregate_by_group([(gold, pred)])
        assert groups["structured"] == Metrics(1, 0, 0)
        assert groups["free_text"] == Metrics(1, 0, 0)
        assert groups["overall"] == Metrics(2, 0, 0)


class TestLabelledSetIntegrity:
    def test_spans_align_with_text(self):
        for case in PII_CASES:
            for span in case.spans:
                assert 0 <= span.start < span.end <= len(case.text)
                assert case.text[span.start : span.end].strip() != ""

    def test_languages_are_en_or_fr(self):
        assert {c.lang for c in PII_CASES} <= {"en", "fr"}

    def test_entities_are_canonical(self):
        known = pii_metrics.STRUCTURED_ENTITIES | pii_metrics.FREE_TEXT_ENTITIES
        for case in PII_CASES:
            for span in case.spans:
                assert span.entity in known, f"{case.id}: unknown entity {span.entity}"

    def test_has_benign_and_bilingual_coverage(self):
        assert any(not c.spans for c in PII_CASES), "need >=1 benign (zero-PII) case"
        assert any(c.lang == "fr" for c in PII_CASES), "need French coverage"
        assert len(PII_CASES) >= 25
