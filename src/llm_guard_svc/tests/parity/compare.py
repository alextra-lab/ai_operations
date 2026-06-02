"""Parity comparison between a golden baseline response and a candidate.

Comparison is layered so the migration can tighten gates over time:

* **schema**   — both payloads satisfy the response contract (always required).
* **semantic** — same scanner set, same ``passed`` verdicts, identical
  ``sanitized_text`` and ``modified`` flag. This is the behavioural gate: a
  reimplemented scanner must reach the same accept/redact decision.
* **score**    — per-scanner ``score`` and top-level ``risk_score`` within a
  tolerance. Scores come from different engines post-migration, so this is
  reported and gated separately with a configurable tolerance.

See ``docs/development/analysis/llm-guard-replacement-evaluation.md`` §5.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .schema import scanner_names, validate_response_schema


@dataclass
class Diff:
    """One parity discrepancy."""

    field: str
    golden: object
    candidate: object
    kind: str  # "schema" | "semantic" | "score"

    def __str__(self) -> str:
        return f"[{self.kind}] {self.field}: golden={self.golden!r} candidate={self.candidate!r}"


@dataclass
class ParityResult:
    case_id: str
    diffs: list[Diff] = field(default_factory=list)

    @property
    def schema_diffs(self) -> list[Diff]:
        return [d for d in self.diffs if d.kind == "schema"]

    @property
    def semantic_diffs(self) -> list[Diff]:
        return [d for d in self.diffs if d.kind == "semantic"]

    @property
    def score_diffs(self) -> list[Diff]:
        return [d for d in self.diffs if d.kind == "score"]

    def passed(self, *, include_scores: bool) -> bool:
        kinds = {"schema", "semantic"} | ({"score"} if include_scores else set())
        return not any(d.kind in kinds for d in self.diffs)


def compare(
    case_id: str,
    golden: dict,
    candidate: dict,
    *,
    score_tol: float = 0.05,
    risk_tol: float = 0.05,
    ignore_scanners: frozenset[str] = frozenset(),
    compare_text: bool = True,
) -> ParityResult:
    """Compare a candidate response against the golden baseline for one case.

    ``ignore_scanners`` drops those scanners from the scanner-set and per-scanner
    verdict/score comparison — used for ``anonymize`` after the LLG-04 finale,
    whose native engine is a deliberate model swap (Presidio+GLiNER) that diverges
    from the distilbert golden by design (gated instead by the labelled PII metric
    set). ``compare_text=False`` skips the ``sanitized_text``/``modified`` equality
    for cases where the golden ``anonymize`` redacted (so its text diverges too).
    """
    result = ParityResult(case_id=case_id)

    # --- schema (both sides) ---
    for label, payload in (("golden", golden), ("candidate", candidate)):
        for err in validate_response_schema(payload):
            result.diffs.append(Diff(f"{label}.schema", err, None, "schema"))
    if result.schema_diffs:
        return result  # can't meaningfully compare malformed payloads

    g_scanners = scanner_names(golden) - ignore_scanners
    c_scanners = scanner_names(candidate) - ignore_scanners
    if g_scanners != c_scanners:
        result.diffs.append(
            Diff("details.scanners", sorted(g_scanners), sorted(c_scanners), "semantic")
        )

    # --- semantic: sanitized_text + modified ---
    if compare_text:
        if golden.get("sanitized_text") != candidate.get("sanitized_text"):
            result.diffs.append(
                Diff(
                    "sanitized_text",
                    golden.get("sanitized_text"),
                    candidate.get("sanitized_text"),
                    "semantic",
                )
            )
        if golden.get("modified") != candidate.get("modified"):
            result.diffs.append(
                Diff("modified", golden.get("modified"), candidate.get("modified"), "semantic")
            )

    # --- per-scanner passed (semantic) + score (score) ---
    g_details = golden.get("details", {})
    c_details = candidate.get("details", {})
    for scanner in sorted(g_scanners & c_scanners):
        g_res, c_res = g_details[scanner], c_details[scanner]
        if g_res.get("passed") != c_res.get("passed"):
            result.diffs.append(
                Diff(
                    f"details.{scanner}.passed",
                    g_res.get("passed"),
                    c_res.get("passed"),
                    "semantic",
                )
            )
        g_score, c_score = g_res.get("score"), c_res.get("score")
        if g_score is not None and c_score is not None:
            if abs(float(g_score) - float(c_score)) > score_tol:
                result.diffs.append(Diff(f"details.{scanner}.score", g_score, c_score, "score"))
        elif (g_score is None) != (c_score is None):
            result.diffs.append(Diff(f"details.{scanner}.score", g_score, c_score, "score"))

    # --- top-level risk_score (score) ---
    g_risk, c_risk = golden.get("risk_score"), candidate.get("risk_score")
    if abs(float(g_risk) - float(c_risk)) > risk_tol:
        result.diffs.append(Diff("risk_score", g_risk, c_risk, "score"))

    return result
