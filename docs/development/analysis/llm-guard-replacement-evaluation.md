# LLM-Guard Replacement Evaluation (LLG-04)

**Status:** Committed (Option B) — execution in progress. Done: parity harness (PR #92),
native regex+secrets (PR #93), native ONNX classifiers (PR #94). Remaining: PII
(`anonymize`) cutover via Presidio + GLiNER, then remove llm-guard + unpin
`transformers>=4.53` + close the 7 CVEs (the acceptance gate in §8).
**Date:** 2026-06-01 (updated 2026-06-02)
**Linear:** AIO-1 (LLG-04)
**Related:** ADR-073 (D6), `src/llm_guard_svc/app/guard.py`, `src/llm_guard_svc/app/main.py`
**Supersedes the "post-MVP decision gate" framing in ADR-073 D6.**

---

## 1. Why now (forcing function)

`llm-guard-svc` depends on `llm-guard==0.3.16`, which **hard-pins
`transformers==4.51.3`** (confirmed via package metadata). `0.3.16` is the
**final published release** on PyPI — there is no newer llm-guard to upgrade to.

All **7 open Dependabot alerts** target `transformers` (1 low, 6 medium), fixed
in `>=4.52.1` / `>=4.53.0`. The pin structurally forbids those versions, so the
CVEs **cannot be resolved while we depend on llm-guard**. Two Dependabot PRs that
tried to raise `transformers` (#84 → 5.0.0rc3, #87 → 5.9.0) were closed: both
conflict with the pin, and #87 additionally violated `zh-core-web-sm`'s
`spacy-pkuseg<0.1.0` requirement and bumped `optimum` to a major version.

**A second, independent blocker surfaced during this evaluation:** the PII model
`Isotonic/distilbert_finetuned_ai4privacy_v2` is licensed **`cc-by-nc-4.0`
(non-commercial)** — incompatible with a commercial enterprise product. This is
true of the *current* deployment, not just the replacement, and means LLG-04 is
not a pure "keep the models, drop the wrapper" exercise for PII.

---

## 2. Recommendation

**Adopt Option B:** remove the `llm-guard` wrapper and run the scanners directly
on `onnxruntime`/`optimum` + `presidio`. This un-pins `transformers` (→ patched
`>=4.53`), closing all 7 CVEs, and shrinks the dependency tree. It reuses the
already-staged ONNX models for 3 of 4 classifiers and keeps the `/api/validate`
contract unchanged.

The PII scanner is carved out as its own workstream because of (a) the
presidio/ONNX integration complexity and (b) the non-commercial license, which
likely forces a **PII model swap** regardless of the wrapper decision.

### Alternatives weighed

| Option | Verdict |
|---|---|
| **A. Stay on llm-guard, accept CVEs** | Rejected — CVEs permanent, no upstream path; non-commercial PII license unaddressed. |
| **B. Direct onnxruntime/optimum + presidio (this doc)** | **Recommended** — surgical, reuses models/thresholds/contract, closes CVEs. |
| C. Fork/patch llm-guard to relax the pin | Rejected — unsupported maintenance burden; doesn't fix licensing. |
| D. Guardrails AI / NeMo Guardrails | Rejected for now — heavier, opinionated, own dep/CVE surface; overkill for a fixed 6-scanner contract. |

---

## 3. Behaviour to preserve (the contract)

The replacement must be a drop-in behind `POST /api/validate`
(`ValidationRequest{input_text, context, strict_mode}` →
`{sanitized_text, risk_score, modified, details{<scanner>:{passed, score}}}`).

Current scanners and the values that **must** be carried over verbatim
(from `guard.py`):

| Scanner | Engine today | Key params to preserve |
|---|---|---|
| `anonymize` (PII) | llm-guard `Anonymize` + presidio + distilbert ONNX | entity set per `DISTILBERT_AI4PRIVACY_v2_CONF`, `use_onnx=True` |
| `prompt_injection` | llm-guard `PromptInjection` (deberta ONNX) | threshold **0.92**, `MatchType.TRUNCATE_HEAD_TAIL` |
| `gibberish` | llm-guard `Gibberish` (ONNX) | threshold **0.97**, `MatchType.FULL` |
| `language` | llm-guard `Language` (xlm-roberta ONNX) | `valid_languages=[en, fr]`, `MatchType.FULL`, `onnx_filename=model_quantized.onnx` |
| `secrets` | llm-guard `Secrets` (**detect-secrets** under the hood) | default plugin set |
| `regex` | llm-guard `Regex` | the two credential/SSH patterns, `MatchType.SEARCH` |

Risk-score weights in `_calculate_risk_score` (PI 0.3, secrets 0.2, others 0)
must also be preserved.

### 3a. Hard operational requirements (must carry over verbatim)

These existing behaviours are **requirements**, not nice-to-haves, and apply to
the replacement and to the new PII model exactly as they do today:

1. **Full lazy model loading.** Models must NOT load at container startup. Today
   `initialize_models()` only resolves/validates model *paths* at import
   (`main.py:26`); the ONNX models load on the **first `/api/validate`** call,
   via the `get_llm_guard()` dependency constructing the scanners. This keeps
   startup and `/health` instant. The replacement (presidio/GLiNER/ONNX sessions)
   must defer all heavy model construction to first use the same way — no eager
   loading at import or in the healthcheck path.
2. **llm-guard bypass (two levels).** Setting `LLM_GUARD_ENABLED=false` must fully
   bypass scanning:
   - **Service-side:** `get_llm_guard()` returns `None` → the validate route
     short-circuits to a pass-through response (no scanners run).
   - **Orchestrator-side:** `controller._is_guard_enabled()` /
     `middleware/sanitization.py` skip the call to `llm-guard-svc` entirely.
   The replacement must preserve both the env flag and both short-circuit paths,
   with identical pass-through semantics.

---

## 4. Per-scanner replacement design + risks

### 4.1 regex — trivial
Stdlib `re.search` over the existing patterns. Exact parity.

### 4.2 secrets — near-exact
llm-guard's `Secrets` scanner is **built on `detect-secrets`** (`bc-detect-secrets`
is already a dependency). Re-implementing directly on `detect-secrets` is
near-identical behaviour, not a new engine. Codex's generic detect-secrets
caveats (no context, prefix-less tokens) apply equally to today's behaviour, so
they are **not a regression**. Parity validated by diffing against golden output.

### 4.3 prompt_injection / gibberish / language — ONNX classification
Use `optimum.onnxruntime.ORTModelForSequenceClassification.from_pretrained(<dir>)`
+ `AutoTokenizer`, pointing at the staged models. **Verified:** every model dir
contains `config.json` where `ORTModel` needs it (each `onnx/` for PI+gibberish;
the root for language), so `ORTModel` will load — Codex's "may lack config.json"
uncertainty is resolved.

Open parity risks to control:
- **Opset / runtime compat** — confirm each staged `.onnx` opset loads on the
  target `onnxruntime` (current working build: 1.26.0; quantized INT8 language
  model loads there). Record the minimum supported `onnxruntime`.
- **Tokenizer alignment** — match padding/truncation/`max_length` (512) exactly;
  logits diverge silently otherwise. Harness must include boundary-length inputs.
- **Threshold parity** — apply the exact thresholds above; emit the same
  `{passed, score}` shape.

### 4.4 PII / anonymize — highest risk + licensing blocker
Two coupled problems:

1. **License:** `distilbert_finetuned_ai4privacy_v2` is `cc-by-nc-4.0`
   (non-commercial). For commercial enterprise use this likely must be
   **replaced** with a permissively-licensed PII/NER model (e.g. a presidio-
   native spaCy/transformers recognizer, or an Apache/MIT PII model). This is a
   model-selection decision, separate from the wrapper.
2. **Integration:** presidio does not natively accept an ONNX session. Wiring an
   ONNX model requires an `optimum`-wrapped HF `pipeline` or a custom
   `EntityRecognizer`. The ai4privacy label schema (`FIRSTNAME`, `LASTNAME`, …)
   must be mapped to presidio entity types (`PERSON`, `EMAIL_ADDRESS`, …); any
   unmapped label silently drops recall. Presidio's default `score_threshold`
   (0.35) differs from llm-guard's single-softmax threshold and must be tuned.

**Decision (PII direction — locked):** **Presidio-native (MIT) baseline +
GLiNER (Apache-2.0) as the NER recognizer.** Licenses verified from HF model
cards on 2026-06-01:

| Model / engine | License | Commercial? |
|---|---|---|
| `presidio-analyzer` / `presidio-anonymizer` | MIT | ✅ already a dep |
| `en_core_web_*` (spaCy NER) | MIT | ✅ already installed |
| `urchade/gliner_multi_pii-v1` (PII NER, en+fr, synthetic data) | apache-2.0 | ✅ |
| `Isotonic/distilbert_finetuned_ai4privacy_v2` (current) | cc-by-nc-4.0 | ❌ NC |
| `Isotonic/deberta-v3-base_finetuned_ai4privacy_v2` (ADR Option A) | cc-by-nc-4.0 | ❌ NC |
| `iiiorg/piiranha-v1` | cc-by-nc-nd-4.0 | ❌ NC-ND |

The **entire ai4privacy lineage is non-commercial**, so the PII model swap is
unavoidable (this also kills ADR-073's "Option A"). Approach: presidio pattern
recognizers (email/card/SSN/phone/IBAN — strong, model-free) as the floor; add
spaCy NER (MIT) then GLiNER (Apache-2.0) for free-text name/location entities
**only as far up the ladder as the parity harness requires** to match/beat the
current distilbert on our entity set. GLiNER needs the `gliner` library
(Apache-2.0) and an ONNX export; it is loaded lazily per §3a. PII output is
validated against a **labelled PII test set**, not just golden diff.

---

## 5. Parity harness (regression guard — necessary, not sufficient)

1. **Snapshot golden outputs** from the *current* service at current `HEAD`
   (post-LLG-02/03, post-D3/D4 — Codex's "pre-D3 fixtures" concern does not
   apply; D3 shipped 2026-03-03). Capture full structured JSON, not raw bytes.
2. **Compare on schema**, not string equality — field names/nesting must match.
3. **Curated adversarial set** in addition to representative inputs — PII and
   prompt-injection edge cases are where parity matters most.
4. **Latency baseline** — record p99 of the current service; the replacement
   must stay within an agreed budget (presidio wrapping may add overhead).

---

## 6. Cutover, rollback, observability

- **Phased per-scanner cutover** (low → high risk): `secrets` → `language` →
  `gibberish` → `prompt_injection` → `PII` last. Each behind a feature flag so a
  single scanner can fall back independently.
- **Rollback** — keep the current `llm-guard` image tagged; the flag reverts any
  scanner to the llm-guard path without a redeploy. `llm-guard-svc` is a
  synchronous gate on `/api/validate`, so a silent regression blocks all queries.
- **Observability deltas** — removing llm-guard changes scanner log field names /
  `scanner_name` values and any metrics keyed on them. Audit dashboards/alerts
  before cutover so they don't silently stop firing.

---

## 7. Dependency outcome

- **Remove:** `llm-guard`.
- **Keep / unpin:** `transformers>=4.53` (patched), `optimum[onnxruntime]`,
  `onnxruntime` (record min version), `presidio-analyzer`, `presidio-anonymizer`,
  `detect-secrets`, `sentencepiece`, `spacy` + `en_core_web_sm`.
- **Result:** all 7 `transformers` CVEs close; transitive footprint shrinks.

---

## 8. Acceptance gate (LLG-04 is "done" only when all hold)

1. Parity harness passes on the agreed input set (functional + schema).
2. Dependabot `transformers` alerts → **0**.
3. p99 latency within the agreed budget vs. the current baseline.
4. PII model is **permissively licensed** (commercial-compatible) and meets a
   defined recall/precision bar on the labelled PII set.
5. Existing `src/llm_guard_svc/tests/` pass (via the CI harness).
6. **Lazy loading preserved** — startup + `/health` stay instant; models load on
   first `/api/validate` only (§3a.1).
7. **Bypass preserved** — `LLM_GUARD_ENABLED=false` short-circuits both the
   service and the orchestrator paths to pass-through (§3a.2).

---

## 9. Open items to resolve before/early in execution

- CVE **reachability** analysis — **RESOLVED 2026-06-01 (see §9a below).** All 7
  open `transformers` alerts are unreachable in our usage; urgency is low and
  LLG-04 remains the only fix. Alerts left **open** (not dismissed) as a visible
  reminder until the migration unpins `transformers>=4.53` and closes them.
- PII model selection (permissive license) — the gating decision for §4.4.
- Confirm ONNX opset vs. target `onnxruntime`; pin the minimum.
- Choose the patched `transformers` floor compatible with `optimum` + the models.

### 9a. CVE reachability analysis (resolved 2026-06-01)

All 7 open Dependabot alerts target `transformers` in
`src/llm_guard_svc/requirements.txt`. No patch is installable while
`llm-guard==0.3.16` hard-pins `transformers==4.51.3` (patches land at 4.52.1 /
4.53.0 / 5.0.0rc3), so **LLG-04 is the only fix path** — partial bumps just
re-break llm-guard (cf. closed PRs #84, #87).

Reachability was assessed against our actual usage: **inference only, ONNX
(`use_onnx=True`), `local_files_only=True`, no training**, and four text
classifiers (distilbert PII, madhurjindal gibberish, deberta-v3-small PI,
xlm-roberta language). A tree-wide grep found no use of `Trainer`, `from_tf`,
`Marian*`, `Donut*`, TTS/`EnglishNormalizer`, or `AdamWeightDecay`.

| # | Sev | Vulnerable component | Reachable? | Rationale |
|---|---|---|---|---|
| 138 | low | `image_utils.py` URL validation (URL username injection) | No | Text-only; no remote URL/image fetch; `local_files_only=True` |
| 139 | med | `DonutProcessor` ReDoS | No | Donut (vision-doc) not used |
| 140 | med | `convert_tf_weight_name_to_pt_weight_name()` (TF→PT) | No | ONNX models; no TF→PT conversion |
| 141 | med | `MarianTokenizer` ReDoS | No | Marian MT not used |
| 142 | med | `EnglishNormalizer.normalize_numbers()` (TTS) | No | No text-to-speech / number normalization |
| 143 | med | `AdamWeightDecay` optimizer ReDoS | No | Inference only; no training |
| 144 | med | `Trainer` arbitrary code execution | No | `Trainer` never instantiated |

**Conclusion:** none reachable → low urgency; proceed with LLG-04 at planned
pace (not as an emergency). Decision: keep alerts **open** until the migration
closes them, rather than dismissing as `not_used`.

---

## 10. Suggested sequencing

1. Stand up the **parity harness** + capture golden outputs (no behaviour change).
   **DONE (2026-06-01)** — `src/llm_guard_svc/tests/parity/`, PR #92.
2. Replace `regex` + `secrets` (lowest risk) → validate.
   **DONE (2026-06-01)** — native ports in `app/scanners/` (95 detect-secrets
   plugins vendored) behind `LLM_GUARD_REGEX_ENGINE` / `LLM_GUARD_SECRETS_ENGINE`
   (default `llm_guard`). Verdict parity green. Finding: secrets redaction is
   non-deterministic in llm-guard for multi-secret inputs — see the spec §6a.
3. Replace the 3 ONNX classifiers → validate (tokenizer/threshold parity).
4. PII workstream: pick a permissive model → wire via presidio → validate on the
   labelled set.
5. Drop `llm-guard`, set the patched `transformers`, rebuild, confirm alerts → 0,
   run the full suite.
6. Update ADR-073 (record the final decision + chosen versions/model) and ship.
