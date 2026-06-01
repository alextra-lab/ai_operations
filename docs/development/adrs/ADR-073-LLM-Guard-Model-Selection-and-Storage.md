# ADR-073: LLM Guard Model Selection and Storage Strategy

**Status:** Accepted
**Date:** 2026-03-03
**Deciders:** Platform Team
**Tags:** llm-guard, security, onnx, models, storage, configuration

---

## Context

**What is the issue we're addressing?**

The `llm-guard-svc` container bundles four classification models for input
validation: PII detection, prompt injection, gibberish detection, and language
filtering. A review of the model storage layout and service configuration
revealed five problems requiring decisions:

1. **Duplicate storage.** The download script (`ops/bootstrap/download_llm_guard_models.py`)
   called `snapshot_download` twice per model — once to a flat `org-model` path
   and once to a model-id-only path — creating full duplicates. Only one copy
   per model is ever used; the other is dead weight. The total wasted storage
   across three models was approximately 2.35 GB.

2. **PyTorch weights stored alongside ONNX models.** Every scanner is
   initialized with `use_onnx=True`. ONNX Runtime loads `model.onnx` from the
   `onnx/` subdirectory; `model.safetensors` and `pytorch_model.bin` at the
   repo root are never read. These files consumed approximately 1.3 GB across
   active model directories.

3. **Wrong config constants in `guard.py`.** Two Python import aliases were
   incorrect:
   - `DEBERTA_AI4PRIVACY_v2_CONF` was imported and used for the PII
     (Anonymize) scanner, but the model on disk is
     `Isotonic/distilbert_finetuned_ai4privacy_v2` (DistilBERT). The correct
     constant is `DISTILBERT_AI4PRIVACY_v2_CONF`, which carries identical
     entity label mappings but the correct model path defaults.
   - `V2_MODEL` was imported as `PI_MODEL` for prompt injection. The model on
     disk (`protectai/deberta-v3-small-prompt-injection-v2`) is the *small*
     variant, not the base V2. The correct constant is `V2_SMALL_MODEL`.

4. **Quantized language model unused.** The
   `protectai/xlm-roberta-base-language-detection-onnx` repo contains three
   ONNX files: `model.onnx` (1.0 GB), `model_optimized.onnx` (1.0 GB), and
   `model_quantized.onnx` (266 MB INT8). The service was defaulting to
   `model.onnx`. The quantized model is ~4× smaller with negligible accuracy
   loss for language detection.

5. **Model directory names hardcoded in Python source.** All four model
   directory names are string literals in `guard.py`'s `configure_models()`
   function. There is no env-var mechanism to override them without editing
   source code. The `LLMGuardConfig` schema only exposes the base directory
   path (`LLM_GUARD_MODELS_PATH`).

6. **Dependency maintenance risk.** `llm-guard==0.3.16` requires
   `transformers>=4.51.3`, which carries known CVEs. The llm-guard project
   shows reduced upstream maintenance activity. Replacing the library with a
   direct `onnxruntime` + `presidio` pipeline is a potential future path.

---

## Decision

**Six decisions are made here:**

### D1 — ONNX-only storage
Store only the ONNX model files on disk. Do not retain PyTorch weights
(`model.safetensors`, `pytorch_model.bin`) alongside ONNX models. Since the
service always sets `use_onnx=True`, PyTorch weights are never loaded. The
download script must be updated to exclude these files via `ignore_patterns`.

### D2 — Single copy per model, flat `org-model` naming convention
Eliminate the duplicate download. Each model is downloaded once to a
`org-model` flat path (e.g., `protectai-deberta-v3-small-prompt-injection-v2`).
The second `snapshot_download` call targeting the model-id-only path (e.g.,
`deberta-v3-small-prompt-injection-v2`) is removed.

Exception: `distilbert_finetuned_ai4privacy_v2` retains the id-only name as
its canonical path since `guard.py` already references it that way. This is
resolved by LLG-03 (config externalization), which normalizes all four names.

### D3 — Correct config constants for active models
Use the correct llm-guard constant for each model:
- PII scanner: `DISTILBERT_AI4PRIVACY_v2_CONF` (not `DEBERTA_AI4PRIVACY_v2_CONF`)
- Prompt injection scanner: `V2_SMALL_MODEL` imported as `PI_MODEL` (not `V2_MODEL`)

These are bug fixes with no behavioral impact since `guard.py` overrides the
model paths in `configure_models()` regardless, but using the correct constants
avoids confusion for future maintainers and aligns with the actual model on disk.

### D4 — Use quantized language model
Set `LANG_MODEL.onnx_filename = "model_quantized.onnx"` in `configure_models()`
to load the INT8 quantized XLM-RoBERTa model (266 MB) instead of the full
float32 model (1.0 GB). Language detection is a low-complexity classification
task; INT8 quantization has negligible accuracy impact. Also delete
`model_optimized.onnx` (graph-optimized but same size as full model, providing
no meaningful benefit without hardware-specific optimizations).

### D5 — Externalize model directory names to configuration
Model directory names are extracted from hardcoded strings in `guard.py` into
four new fields on `LLMGuardConfig` in `src/shared/config/schemas.py`, each
backed by an environment variable. This is tracked as Linear task LLG-03 and
is not part of the immediate Phase 0 execution. Hardcoded names in `guard.py`
are accepted as technical debt until LLG-03 is complete.

### D6 — llm-guard dependency: replacement required (was: deferred)
`llm-guard==0.3.16` was accepted as-is for the MVP release.

**Update (2026-06-01): this is no longer a deferrable trade-off.** `0.3.16` is
the final published release (no newer version exists on PyPI) and it hard-pins
`transformers==4.51.3`. The open `transformers` CVEs are fixed in `>=4.52.1` /
`>=4.53.0`, which the pin structurally forbids — so **there is no upstream fix
path**, and the CVE exposure is permanent for as long as the service depends on
llm-guard. The two Dependabot bumps that tried to raise `transformers` (PRs #84,
#87) were closed because they conflict with this pin (and with
`zh-core-web-sm`'s `spacy-pkuseg<0.1.0` requirement).

The earlier mitigation ("no external-facing model inference surface") is
inaccurate as written: `/api/validate` processes untrusted user input through
the scanners. Whether any open `transformers` CVE is reachable via the inference
path (vs. model-download/deserialisation only) is an **open question LLG-04 must
resolve** via advisory review + `pip-audit` reachability. Interim posture until
LLG-04 lands: keep `llm-guard-svc` network-isolated (reachable only from
`orchestrator-api` on the internal `observability` network, never externally).

The replacement — a direct `onnxruntime`/`optimum` + `presidio_analyzer` /
`presidio_anonymizer` pipeline that drops the llm-guard wrapper and un-pins
`transformers` (→ patched `>=4.53`) — is therefore **committed**, tracked as
LLG-04. A separate, newly-surfaced blocker scopes into the same work: the PII
model `Isotonic/distilbert_finetuned_ai4privacy_v2` is licensed
**`cc-by-nc-4.0` (non-commercial)**, which is incompatible with commercial
enterprise deployment and likely requires swapping the PII model for a
permissively-licensed alternative. The detailed evaluation, per-scanner design,
parity-harness plan, phased cutover, rollback strategy, licensing audit, and
acceptance-gate criteria live in
`docs/development/analysis/llm-guard-replacement-evaluation.md`.

---

## Alternatives Considered

### Option A — Upgrade to DeBERTa-base models for PII and prompt injection

**Description:** Replace the current DistilBERT PII model with
`Isotonic/deberta-v3-base_finetuned_ai4privacy_v2` and the small prompt
injection model with `protectai/deberta-v3-base-prompt-injection-v2`.

**Pros:**
- Meaningfully higher accuracy on PII entity detection
- Full DeBERTa-v3-base prompt injection model is the intended default in
  `V2_MODEL` within llm-guard

**Cons:**
- DeBERTa-v3-base models are ~4× larger than the DistilBERT/small variants
- No ONNX version of `protectai/deberta-v3-base-prompt-injection-v2` is
  published; would require `use_onnx=False` and PyTorch inference
- Inference latency increases significantly on CPU-only containers
- Air-gapped deployment requires re-downloading and re-packaging larger models

**Why Deferred:** Current models are sufficient for MVP validation use case.
Upgrade is tracked as a post-MVP consideration.

**Update (2026-06-01): Option A is licensing-dead.** Both
`Isotonic/deberta-v3-base_finetuned_ai4privacy_v2` and the currently-used
`Isotonic/distilbert_finetuned_ai4privacy_v2` are `cc-by-nc-4.0` (non-commercial),
as is the entire ai4privacy lineage (and `iiiorg/piiranha-v1` is `cc-by-nc-nd`).
The PII model must move to a permissively-licensed option — see LLG-04, which
selects Presidio (MIT) + GLiNER `gliner_multi_pii-v1` (Apache-2.0).

### Option B — Replace llm-guard now with direct onnxruntime pipeline

**Description:** Remove the `llm-guard` package entirely; implement scanners
directly using `onnxruntime`, `optimum`, and `presidio_analyzer` /
`presidio_anonymizer`.

**Pros:**
- Eliminates the pinned `transformers` CVE constraint
- Full control over inference code path
- Can target specific `onnxruntime` execution providers (CoreML, CPU) without
  llm-guard's abstraction layer

**Cons:**
- Significant implementation effort (re-implement 4 scanner pipelines)
- Loses llm-guard's tested scanner contract (threshold logic, match types,
  result normalization)
- Presidio and spaCy are already direct dependencies, so dep footprint reduction
  is partial

**Why Deferred:** Risk-to-benefit ratio is unfavorable pre-MVP. Tracked as
LLG-04 for formal evaluation.

---

## Consequences

### Positive Consequences

- Approximately 4.65 GB freed from the model storage volume immediately
  (3 duplicate dirs + PyTorch weights + `model_optimized.onnx`)
- Language detection model load time and memory footprint reduced by ~75%
  (1.0 GB → 266 MB)
- Correct config constants make `guard.py` consistent with the actual models on
  disk and with llm-guard's own API surface
- Container image size reduction: ONNX-only download eliminates ~1.3 GB of
  PyTorch weights from future builds
- Clearer audit trail via ADR for future model upgrade or replacement decisions

### Negative Consequences

- `model.onnx` (1.0 GB full-precision language model) remains on disk until
  LLG-02 (download script update) is complete and models are re-downloaded in
  clean state. It is no longer loaded but occupies disk.
- PII detection accuracy is lower than with the DeBERTa-base model; this is an
  accepted trade-off for MVP.
- `llm-guard`'s `transformers` CVE remains unresolved until LLG-04 decision is
  made.

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Quantized language model has lower accuracy in edge cases | Low | Language detection is a coarse filter (EN/FR); INT8 loss is negligible for this task |
| `V2_SMALL_MODEL` constant path assumptions differ from `V2_MODEL` | Low | `guard.py` overrides all Model paths in `configure_models()`; constant choice only affects fallback defaults |
| llm-guard CVE in `transformers` | Medium | Pinned version, no external-facing model inference surface; mitigated by LLG-04 timeline |
| ONNX quantization accuracy regression on adversarial prompt injection inputs | Medium | Monitor false-negative rate post-deploy; threshold (0.92) provides buffer |

---

## Implementation Notes

**Phase 0 — Immediate (no Linear tracking, executed on 2026-03-03):**
- Deleted from `data/llm-guard-models/`:
  - `Isotonic-distilbert_finetuned_ai4privacy_v2/` (duplicate, ~507 MB)
  - `autonlp-Gibberish-Detector-492513457/` (duplicate, ~766 MB)
  - `deberta-v3-small-prompt-injection-v2/` (duplicate, ~1.08 GB)
  - `distilbert_finetuned_ai4privacy_v2/model.safetensors` (253 MB)
  - `madhurjindal-autonlp-Gibberish-Detector-492513457/model.safetensors` (255 MB)
  - `madhurjindal-autonlp-Gibberish-Detector-492513457/pytorch_model.bin` (255 MB)
  - `protectai-deberta-v3-small-prompt-injection-v2/model.safetensors` (541 MB)
  - `protectai-xlm-roberta-base-language-detection-onnx/model_optimized.onnx` (1.0 GB)
- Modified `src/llm_guard_svc/app/guard.py`:
  - Import: `DEBERTA_AI4PRIVACY_v2_CONF` → `DISTILBERT_AI4PRIVACY_v2_CONF`
  - Import: `V2_MODEL as PI_MODEL` → `V2_SMALL_MODEL as PI_MODEL`
  - Added: `LANG_MODEL.onnx_filename = "model_quantized.onnx"` in `configure_models()`

**Remaining tracked work (Linear project: AIO - LLM Guard Hardening):**
- LLG-01: Write this ADR (complete)
- LLG-02: Simplify `ops/bootstrap/download_llm_guard_models.py` (single copy, ONNX-only, no duplicates) — **complete** (AIO-3, merged in PR #85, 2026-06-01)
- LLG-03: Externalize model directory names to `LLMGuardConfig` in `schemas.py` and `loader.py` — **complete** (AIO-2, merged in PR #85, 2026-06-01)
- LLG-04: Replace `llm-guard` with a direct `onnxruntime`/`optimum` + `presidio` pipeline — **committed** (was "evaluate"; see `docs/development/analysis/llm-guard-replacement-evaluation.md`)

---

## References

- `src/llm_guard_svc/app/guard.py` — scanner initialization and model path configuration
- `src/shared/config/schemas.py` — `LLMGuardConfig` schema
- `src/shared/config/loader.py` — `load_llm_guard_config()` function
- `ops/bootstrap/download_llm_guard_models.py` — model download script
- `src/llm_guard_svc/README.md` — service documentation
- ADR-071: Centralized Configuration Gateway (parent pattern for LLG-03)
- [llm-guard GitHub](https://github.com/protectai/llm-guard) — upstream library
- [ProtectAI HuggingFace org](https://huggingface.co/ProtectAI) — model source

---

## Status Updates

### 2026-03-03 - Accepted
**Changed By:** Platform Team
**Reason:** Phase 0 immediate actions executed. Architectural decisions
documented and accepted. Linear tasks LLG-02 through LLG-04 created for
remaining work.

### 2026-06-01 - Updated (LLG-02/03 complete; D6 reframed; new licensing blocker)
**Changed By:** Platform Team
**Reason:** LLG-02 (AIO-3) and LLG-03 (AIO-2) shipped in PR #85. An independent
review of this ADR surfaced that D6's "deferred/accepted" framing is no longer
valid: `llm-guard==0.3.16` is the final release and pins `transformers==4.51.3`,
so the open `transformers` CVEs have no upstream fix path and are permanent
until the library is replaced — D6 reframed to "replacement required" and LLG-04
promoted from optional decision-gate to committed work. Verification during this
update also found that the PII model
`Isotonic/distilbert_finetuned_ai4privacy_v2` is licensed `cc-by-nc-4.0`
(non-commercial), a separate blocker for commercial deployment that LLG-04 must
address (likely a PII-model swap). Corrected the Decision section header
("Five" → "Six decisions"). Full Option B evaluation and execution plan:
`docs/development/analysis/llm-guard-replacement-evaluation.md`.

---

**Template Version:** 1.0
**Based On:** [Michael Nygard's ADR pattern](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
