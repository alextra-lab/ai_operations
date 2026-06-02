"""Entity-level recall/precision metrics for the native PII scanner (LLG-04 step 3).

Pure functions (stdlib only) so they unit-test on the host venv. Span matching is
**type-aware partial-overlap**: a predicted span counts as a true positive if it
overlaps a not-yet-matched gold span of the *same* canonical entity. This relaxes
off-by-one differences between Presidio/GLiNER offsets and the hand annotation
without rewarding wrong-type or spurious detections.

The acceptance bars below are the ratified gate (eval doc §8.4): the native
engine "matches/beats" the removed distilbert model when all of them hold on the
labelled set (``pii_labelled.PII_CASES``).
"""

from __future__ import annotations

from dataclasses import dataclass

# Canonical entity groups.
STRUCTURED_ENTITIES = frozenset(
    {"EMAIL_ADDRESS", "CREDIT_CARD", "US_SSN", "PHONE_NUMBER", "IBAN_CODE"}
)
FREE_TEXT_ENTITIES = frozenset({"PERSON", "LOCATION", "ORGANIZATION"})

# Ratified acceptance bars.
STRUCTURED_MIN_RECALL = 0.98
STRUCTURED_MIN_PRECISION = 0.98
FREE_TEXT_MIN_RECALL = 0.85
FREE_TEXT_MIN_PRECISION = 0.80
# Benign (zero-PII) cases must produce zero predictions: any redaction is a leak
# of non-PII and a hard failure.
BENIGN_MAX_FALSE_POSITIVES = 0


@dataclass(frozen=True)
class _SpanLike:
    start: int
    end: int
    entity: str


@dataclass(frozen=True)
class Metrics:
    """TP/FP/FN counts plus derived recall/precision/F1."""

    tp: int
    fp: int
    fn: int

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 1.0

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 1.0

    @property
    def f1(self) -> float:
        denom = self.precision + self.recall
        return 2 * self.precision * self.recall / denom if denom else 0.0

    def __add__(self, other: Metrics) -> Metrics:
        return Metrics(self.tp + other.tp, self.fp + other.fp, self.fn + other.fn)


def _overlap(a: _SpanLike, b: _SpanLike) -> bool:
    return not (a.end <= b.start or a.start >= b.end)


def score_case(gold: list, pred: list) -> Metrics:
    """Score one case's predicted spans against gold via type-aware overlap.

    ``gold``/``pred`` items need ``.start``, ``.end``, ``.entity`` attributes.
    """
    gold_used = [False] * len(gold)
    tp = 0
    for p in pred:
        for i, g in enumerate(gold):
            if gold_used[i] or p.entity != g.entity:
                continue
            if _overlap(p, g):
                gold_used[i] = True
                tp += 1
                break
    fp = len(pred) - tp
    fn = len(gold) - sum(gold_used)
    return Metrics(tp, fp, fn)


def aggregate_by_group(
    per_case: list[tuple[list, list]],
) -> dict[str, Metrics]:
    """Aggregate metrics across cases, partitioned by entity group.

    ``per_case`` is a list of ``(gold_spans, pred_spans)`` tuples. Returns a dict
    with ``"structured"``, ``"free_text"``, and ``"overall"`` Metrics. Spans are
    routed to a group by their entity type; benign false positives surface under
    whichever group the spurious entity belongs to (and in ``overall``).
    """
    groups: dict[str, Metrics] = {
        "structured": Metrics(0, 0, 0),
        "free_text": Metrics(0, 0, 0),
        "overall": Metrics(0, 0, 0),
    }
    for gold, pred in per_case:
        for group_name, members in (
            ("structured", STRUCTURED_ENTITIES),
            ("free_text", FREE_TEXT_ENTITIES),
        ):
            g = [s for s in gold if s.entity in members]
            p = [s for s in pred if s.entity in members]
            groups[group_name] = groups[group_name] + score_case(g, p)
        groups["overall"] = groups["overall"] + score_case(gold, pred)
    return groups
