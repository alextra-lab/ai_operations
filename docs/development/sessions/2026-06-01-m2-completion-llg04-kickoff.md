# Development Session - 2026-06-01
**Focus:** Finish M2 (AIO-43) full local stack; close out Dependabot; scope LLG-04
**Status:** M2 complete; LLG-04 scoped (implementation pending)

## Work Completed
- **AIO-3 / AIO-2 / AIO-47** (PR #85, merged): ONNX-only download script (repo_id→dir
  map, ignore_patterns, no HF_HOME pollution); externalized 4 model dir names to
  `LLMGuardConfig`; staged models; added missing `sentencepiece` dep. llm-guard-svc
  healthy, `/api/validate` detects prompt injection across all 6 scanners.
- **AIO-50** (PR #88, merged): ui-webapp build + bring-up. Fixed ng2-charts v10
  migration (`NgChartsModule`→`BaseChartDirective`), registry npm build (npm_cache
  is gitignored/.dockerignored), and nginx `BACKEND_HOST=orchestrator-api`. Verified
  healthy, SPA renders (0 console errors), demo login + query 200 through the proxy.
- **Dependabot:** closed #84 + #87 (both break the llm-guard `transformers==4.51.3`
  pin); safe-bumps PR pending.
- **Docs:** ADR-073 updated (D6 reframed, Option A licensing-dead, status update);
  created `analysis/llm-guard-replacement-evaluation.md`.
- Local `.venv` recreated as Python 3.12 (was a stray 3.14) + repopulated.

## Key Decisions
- **LLG-04 committed (Option B):** drop llm-guard, run scanners directly on
  `onnxruntime`/`optimum` + `presidio`; un-pins `transformers`→`>=4.53`, closes all 7
  CVEs. `llm-guard==0.3.16` is final + pins `transformers==4.51.3` → no upstream path.
- **PII model must be swapped:** current `distilbert_finetuned_ai4privacy_v2` is
  `cc-by-nc-4.0` (non-commercial); entire ai4privacy lineage is NC. Selected
  **Presidio (MIT) + GLiNER `gliner_multi_pii-v1` (Apache-2.0)**.
- **Hard requirements for the replacement:** full lazy model loading (first
  `/api/validate`, not startup) + `LLM_GUARD_ENABLED=false` bypass (svc + orchestrator).

## Next Steps
- Open the safe-bumps PR (starlette/python-multipart/embedding-torch; non-llm-guard).
- Finish AIO-48 (restore `orchestrator → llm-guard: service_healthy` depends_on).
- Begin LLG-04 in a fresh thread: parity harness first (golden + schema + adversarial
  + p99), then per-scanner cutover (secrets→language→gibberish→PI→PII).
