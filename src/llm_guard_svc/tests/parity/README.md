# LLG-04 Parity Harness

Regression guard for replacing the `llm-guard` library with a direct
`onnxruntime`/`optimum` + `presidio` pipeline
(see `docs/development/analysis/llm-guard-replacement-evaluation.md` §5).

It snapshots the behaviour of the **current** `llm-guard`-backed service into a
golden baseline, then checks any candidate implementation against it on
**schema + semantic parity + latency budget**. Stdlib-only — it runs anywhere
the service runs, without the heavy model stack.

## Layout

| File | Role |
|---|---|
| `corpus.py` | Categorized inputs: benign, secrets (regex + detect-secrets), prompt-injection, gibberish, language, PII, and boundary/edge cases. |
| `schema.py` | Hand-rolled response-contract validator (no `jsonschema` dep). |
| `compare.py` | Layered comparator: schema / semantic (verdicts + `sanitized_text`) / score (tolerant). |
| `client.py` | Minimal `urllib` client for `POST /api/validate`. |
| `capture.py` | CLI that snapshots `golden/baseline.json` + `golden/latency.json`. |
| `test_parity.py` | Golden integrity, harness self-check, and opt-in candidate parity. |
| `golden/` | Committed baseline captured from the current service. |

## Capturing / refreshing the golden baseline

The current service only runs inside its Docker image (the host cannot import
`llm-guard`), so capture talks to the running container over HTTP.

```bash
# bring up the current (llm-guard) service, then:
python -m src.llm_guard_svc.tests.parity.capture \
    --url http://localhost:18081 \
    --latency-reps 15
```

This writes `golden/baseline.json` (one full response per case + provenance:
source URL, git HEAD) and `golden/latency.json` (p50/p95/p99/max). Re-capture
only when intentionally rebaselining; commit the result.

## Running the tests

```bash
# Layers 1-2 (golden integrity + harness self-check) — no service needed:
pytest src/llm_guard_svc/tests/parity/

# Layer 3 (candidate parity) — point at a running candidate service:
PARITY_CANDIDATE_URL=http://localhost:18082 \
    pytest src/llm_guard_svc/tests/parity/test_parity.py
```

Env knobs: `PARITY_CANDIDATE_URL` (enables candidate parity),
`PARITY_LATENCY_BUDGET_FACTOR` (default `1.5` × golden p99).

## Parity gates (what "matching" means)

- **schema** — field names / nesting / types of the `/api/validate` response.
- **semantic** — same scanner set, identical `passed` verdicts, identical
  `sanitized_text`, identical `modified`. This is the behavioural gate.
- **score** — per-scanner `score` and `risk_score` within tolerance; reported
  and gated separately, since scores come from different engines post-migration.

Parity means reproducing the current behaviour **verbatim, quirks included**
(e.g. the current PII model redacting `Bonjour`/`gggg` as `PERSON`, and
`llm-guard`'s signed score convention where `-1.0` means "passed with margin").
Do not "fix" the corpus or golden to look cleaner.
