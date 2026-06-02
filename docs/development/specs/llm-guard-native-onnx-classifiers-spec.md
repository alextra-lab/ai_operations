# Spec — Native ONNX classifiers (`prompt_injection`, `gibberish`, `language`) — LLG-04 cutover step 2

**Status:** Proposed (2026-06-02)
**Date:** 2026-06-02
**Linear:** AIO-1 (LLG-04)
**Related:** `docs/development/analysis/llm-guard-replacement-evaluation.md` (§3, §4.3, §6, §10.2), `docs/development/specs/llm-guard-native-regex-secrets-spec.md` (step 1, the pattern this reuses), `src/llm_guard_svc/tests/parity/` (parity harness, PR #92), `src/llm_guard_svc/app/guard.py`

---

## 1. Goal

Port the three ONNX text-classification scanners — `prompt_injection`,
`gibberish`, `language` — off the `llm_guard` library wrappers
(`llm_guard.input_scanners.*` + `llm_guard.transformers_helpers` +
`llm_guard.util`) to native implementations that call `transformers` +
`optimum.onnxruntime` **directly**. This is the second per-scanner cutover of
LLG-04, reusing the step-1 pattern: **engine switch + per-scanner parity**,
native code ships **dormant** behind per-scanner flags defaulting to
`llm_guard`, nothing switches automatically.

## 2. Non-goals

- **No `transformers` version change.** `llm-guard==0.3.16` stays installed and
  keeps the `transformers==4.51.3` pin. The 7 Dependabot CVEs close only at the
  end of LLG-04, when `llm_guard` is removed and `transformers` is unpinned
  (eval §9a). This step is pure wrapper substitution at the current pin.
- No change to `regex`/`secrets` (step 1, done) or `anonymize`/PII (step 3, the
  last and only model-licensing-sensitive cutover).
- No flipping of any default engine. All three flags default to `llm_guard`.
- No container/compose changes. Validation is per-scanner parity (§7).

## 3. Why this step is parity-safe by construction

At the pinned `transformers==4.51.3` + `optimum[onnxruntime]==1.25.2`, the native
scanner and the `llm_guard` scanner load **the same tokenizer, the same ONNX
graph, and the same HuggingFace `text-classification` pipeline** from the same
on-disk model directory. The only thing replaced is the thin Python wrapper that
wires them together. Output is therefore **byte-identical by construction** this
increment — the parity test confirms the *wrapper port is faithful*, not that a
new model behaves the same.

The genuine parity risk (tokenizer / pipeline post-processing drift across
`transformers` versions) materialises only when `transformers` is later
unpinned. Shipping the faithful native path now, dormant, isolates that risk:
the final LLG-04 step becomes flag-flips + dep changes with the same harness
re-run against the new `transformers`.

## 4. Approach (decided): verbatim wrapper port

`llm_guard`'s three scanners are thin: a `Model` dataclass, a
`get_tokenizer_and_model_for_classification` helper (AutoTokenizer +
`ORTModelForSequenceClassification`), a `pipeline` factory, `calculate_risk_score`,
and a `MatchType.get_inputs` input-prep step, then a small `scan()` loop. All are
MIT-licensed and small.

**Therefore: port the wrapper logic verbatim**, dropping only the `llm_guard.*`
imports (logger → stdlib, `Scanner` Protocol base dropped, `device()` /
`lazy_load_dep` inlined). Shared machinery lands once in
`scanners/_onnx_classifier.py`; each scanner gets its own module with its model
config + `scan()`. Parity is guaranteed by calling the identical underlying
`transformers` / `optimum` APIs. Rejected: reimplement inference on raw
`onnxruntime` (re-derives tokenizer/pipeline post-processing → drift risk for no
benefit); keep importing `llm_guard.transformers_helpers` (removes no dependency).

License: `llm-guard` is MIT — vendoring with attribution is permitted (see
`scanners/_onnx_classifier.py` header + PROVENANCE note).

## 5. Model configuration to reproduce (from `guard.py::configure_models`)

The current service mutates `llm_guard`'s global `Model` objects at startup. The
native scanners must construct an equivalent `Model` with **exactly** these final
values (paths from `LLMGuardConfig` model dirs via `get_model_path`):

| Scanner | `path` | `onnx_path` | `onnx_subfolder` | `onnx_filename` | extra |
|---|---|---|---|---|---|
| `prompt_injection` | `<dir>` | `<dir>/onnx` | `""` | `model.onnx` | `tokenizer_kwargs={use_fast:False}`; `threshold=0.92`; `MatchType.TRUNCATE_HEAD_TAIL` |
| `gibberish` | `<dir>` | `<dir>/onnx` | `""` | `model.onnx` | `threshold=0.97`; `MatchType.FULL` |
| `language` | `<dir>` | `<dir>` | `""` | `model_quantized.onnx` | `valid_languages=[en,fr]`; `threshold=0.6`(default); `MatchType.FULL`; `top_k=None` |

All three: `kwargs={local_files_only:True, trust_remote_code:False}` (PI also
keeps `token:True` from `V2_SMALL_MODEL`); `pipeline_kwargs` include
`return_token_type_ids:False, max_length:512, truncation:True` plus the
`Model.__post_init__` defaults `batch_size:1, device:cpu`.

Scanner contract (unchanged): `.scan(text) -> tuple[sanitized_text, passed, score]`.
The classifiers never modify text (`sanitized_text == prompt` always); they
return `passed` + signed risk score from `calculate_risk_score`.

## 6. Components

```
src/llm_guard_svc/app/scanners/
  _onnx_classifier.py          # NEW: ported Model dataclass, get_tokenizer_and_model_for_classification,
                               #      pipeline factory, calculate_risk_score, device(), truncate_tokens_head_tail
  prompt_injection_scanner.py  # NEW: PromptInjectionScanner + MatchType + model config
  gibberish_scanner.py         # NEW: GibberishScanner + model config
  language_scanner.py          # NEW: LanguageScanner + model config
```

Wiring (mirrors step 1):
- `shared/config/schemas.py` — add `prompt_injection_engine`, `gibberish_engine`,
  `language_engine` to `LLMGuardConfig` (default `llm_guard`).
- `shared/config/loader.py` — map `LLM_GUARD_{PROMPT_INJECTION,GIBBERISH,LANGUAGE}_ENGINE`.
- `llm_guard_svc/app/main.py` — pass the three flags into `LLMGuard(...)`.
- `llm_guard_svc/app/guard.py::LLMGuard.__init__` — add three params; dispatch
  `native` vs `llm_guard` per scanner, building native scanners from
  `get_model_path(config.<dir>)` (config loaded lazily inside `__init__`,
  preserving lazy model loading — models still load on first `/api/validate`).
- `config/env/env.template` — add the three vars (default `llm_guard`).

## 7. Verification (decided: unit parity, like step 1)

**(a) Pure-logic unit tests** (`tests/parity/test_onnx_logic.py`, no model stack,
run anywhere): `calculate_risk_score` boundary values, PI `TRUNCATE_HEAD_TAIL`
char-splitting (`>256` → `head...tail`), empty/whitespace input → `(prompt, True, -1.0)`,
label→score mapping (`INJECTION` / gibberish-label set / language threshold).

**(b) Model-backed parity** (`tests/parity/test_onnx_parity.py`, skip-if-stack-absent):
instantiate each native scanner against the configured model dir, run the
`prompt_injection` / `gibberish` / `language` corpus categories, assert
`passed` + `score` equal the committed golden baseline. Requires the model stack
+ model files, so it runs in the `llm-guard-svc` container (transformers 4.51.3,
models at `/app/models`) and is skipped on the bare host venv. Run via:
`docker cp` the new modules + test into the running container, then
`docker exec llm-guard-svc python -m pytest …`. Skips cleanly (like the existing
`golden` fixture) when `optimum`/models are unavailable.

Service-level harness (`PARITY_CANDIDATE_URL`, 1.5× p99 budget) stays the later
end-to-end gate before any default flip.

## 8. Cutover sequencing

Ships behind three independent flags so each scanner can be flipped to `native`
in production separately once confidence is high. Default flip + `llm_guard`
removal + `transformers` unpin happen together at the **end** of LLG-04, after
the PII cutover (step 3), re-validated by the full parity harness.
