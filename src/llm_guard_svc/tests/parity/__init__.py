"""LLG-04 parity harness.

Regression guard for the llm-guard -> onnxruntime/optimum + presidio migration
(see ``docs/development/analysis/llm-guard-replacement-evaluation.md`` §5).

The harness snapshots the behaviour of the *current* ``llm-guard``-backed service
(``POST /api/validate``) into a golden baseline, then compares any candidate
implementation against it on schema + semantic parity + latency budget.

Stdlib-only on purpose: it must run anywhere the service runs without pulling in
the heavy model stack.
"""
