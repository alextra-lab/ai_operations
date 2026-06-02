# Spec — Native PII / `anonymize` (Presidio + GLiNER) — LLG-04 cutover step 3

**Status:** Implemented (2026-06-02) — native code dormant behind `LLM_GUARD_ANONYMIZE_ENGINE` (default `llm_guard`); gated on a labelled PII recall/precision set (not golden parity)
**Date:** 2026-06-02
**Linear:** AIO-72 (sub-issue of AIO-1 / LLG-04)
**Related:** `docs/development/analysis/llm-guard-replacement-evaluation.md` (§3a, §4.4, §8), `docs/development/specs/llm-guard-native-regex-secrets-spec.md` (step 1), `docs/development/specs/llm-guard-native-onnx-classifiers-spec.md` (step 2), `src/llm_guard_svc/app/scanners/anonymize_scanner.py`, `src/llm_guard_svc/tests/parity/`

---

## 1. Goal

Replace the `llm_guard` `Anonymize`/PII scanner — which relies on
`Isotonic/distilbert_finetuned_ai4privacy_v2` — with a native, permissively
licensed pipeline: **Presidio pattern recognizers (MIT) + GLiNER
`urchade/gliner_multi_pii-v1` (Apache-2.0, en+fr)**. This is the fourth and final
per-scanner cutover of LLG-04, reusing the established **engine switch + dormant
flag** pattern: native code ships behind `LLM_GUARD_ANONYMIZE_ENGINE` defaulting
to `llm_guard`; nothing switches automatically.

## 2. Non-goals

- **No `transformers` version change.** `llm-guard==0.3.16` stays installed and
  keeps the `transformers==4.51.3` pin. The 7 Dependabot CVEs close only at the
  LLG-04 finale (AIO-73), when `llm_guard` is removed and `transformers` is
  unpinned (eval §9a). Verified: GLiNER 0.2.26 requires
  `transformers>=4.51.3,<5.2.0`, so it is compatible with the current pin and
  adds no conflict with `optimum==1.25.2`.
- No change to the four already-ported scanners (`regex`/`secrets`, the three
  ONNX classifiers).
- No flipping of the default engine. `anonymize_engine` defaults to `llm_guard`.
- No removal of the distilbert model dir / `pii_model_dir` config (the
  `llm_guard` branch still uses them until the finale).

## 3. Why this step is different (parity is NOT by construction)

Steps 1–2 were verbatim wrapper ports validated by **differential parity**
(`native.scan(text) == llm_guard.scan(text)`, byte-identical). That is
**structurally impossible** here, because this is a deliberate **model swap**, not
a wrapper substitution:

- The entire **ai4privacy lineage is `cc-by-nc-4.0` (non-commercial)** — the
  current distilbert PII model, the ADR-073 "Option A" deberta, and Piiranha
  (NC-ND). Unusable in a commercial product, so the model **must** change (eval
  §4.4). A swapped model produces deliberately different redactions.
- The golden baseline proves the divergence: `pii_french_greeting` is redacted by
  distilbert as `[REDACTED_PERSON_1], comment allez-vous…` (it tags the greeting
  "Bonjour" as a PERSON — a false positive); the native engine will not reproduce
  that quirk.

The acceptance gate therefore moves from "byte-identical" to **entity-level
recall/precision on a hand-labelled PII set** (eval §8.4). Almost all code here is
**original** (not a vendored port) and is linted/type-checked normally.

## 4. Approach (decided): Presidio pattern recognizers + GLiNER

Licenses verified from HF model cards (eval §4.4):
`presidio-analyzer`/`presidio-anonymizer` MIT, `gliner` Apache-2.0,
`gliner_multi_pii-v1` Apache-2.0.

- **Structured PII (floor):** Presidio predefined pattern recognizers —
  `EmailRecognizer`, `CreditCardRecognizer` (Luhn), `UsSsnRecognizer`,
  `PhoneRecognizer` (regions `US/GB/FR`), `IbanRecognizer`. Model-free regex/checksum
  matching, high precision.
- **Free-text PII (NER):** GLiNER `gliner_multi_pii-v1` wrapped as a Presidio
  `EntityRecognizer`, carrying `PERSON`/`LOCATION`/`ORGANIZATION` in **both** en
  and fr (the load-bearing rung for the French half of the requirement).
- **Runtime decision (locked):** GLiNER runs **eager torch** (no ONNX export this
  step). Latency is dormant-only; ONNX export is deferred to the AIO-73 finale if
  p99 needs it.

**French NLP refinement (decided):** the container ships only `en`/`zh` spaCy
models, no `fr_core_news_*`. Rather than add a French spaCy model (image growth)
or wire a blank French `NlpEngine`, the native scanner **invokes the Presidio
pattern recognizers directly** (`recognizer.analyze(text, entities,
nlp_artifacts=None)`) — they are language-agnostic regex/checksum matchers that
need no `NlpEngine` — and lets GLiNER (which does its own tokenization) carry FR
NER. The native PII path therefore never loads spaCy. Optional spaCy `en` NER
remains a future booster lever if English name recall falls short.

Rejected: keep the cc-by-nc distilbert (licensing); ai4privacy "Option A" deberta
(same NC license); Piiranha (NC-ND).

## 5. Behaviour to reproduce (the contract)

Drop-in behind `POST /api/validate`. Scanner contract unchanged:
`AnonymizeScanner.scan(text) -> tuple[sanitized_text, passed, score]`.

| Aspect | Native behaviour |
|---|---|
| Redaction placeholder | `[REDACTED_<ENTITY>_<n>]`, numbered per entity type. Grammar mirrors the Vault style **for tidiness only** — verified no downstream consumer parses it; the orchestrator treats `sanitized_text` as opaque. |
| `passed` | `False` when any PII is redacted (drives `modified=True`); `True` when clean. |
| `score` | `1.0` on redaction, `-1.0` clean. **Cosmetic** — `anonymize` has **weight 0** in `_calculate_risk_score`, so PII redaction never moves `risk_score`. The old `0.6` distilbert-softmax value is intentionally not reproduced. |
| Empty/whitespace input | `(prompt, True, -1.0)`. |
| Overlapping detections | Resolved (highest score, then longest) before redaction. |

### 5a. Hard operational requirements (preserved verbatim, eval §3a)

1. **Lazy model loading.** Heavy imports (Presidio recognizers, GLiNER) live in
   `AnonymizeScanner.__init__`; the GLiNER model loads on first `analyze()`. No
   model loads at import/startup/`/health` — only when the lazy `LLMGuard` is
   first built on `/api/validate`.
2. **Bypass.** `LLM_GUARD_ENABLED=false` short-circuits both the service
   (`get_llm_guard()` → `None`) and the orchestrator
   (`controller._is_guard_enabled()`). Untouched.

## 6. Components

```
src/llm_guard_svc/app/scanners/
  _pii_common.py          # NEW: Span, GLINER_LABEL_TO_ENTITY map, resolve_overlaps,
                          #      build_redaction — stdlib only (host-venv testable)
  _gliner_recognizer.py   # NEW: GlinerRecognizer(EntityRecognizer); lazy GLiNER load
  anonymize_scanner.py    # NEW: AnonymizeScanner; pattern recognizers + GLiNER;
                          #      .detect() (spans) + .scan() ((str,bool,float))
```

Wiring (mirrors steps 1–2):
- `shared/config/schemas.py` — add `anonymize_engine` (default `llm_guard`) and
  `gliner_model_dir` (default `gliner_multi_pii-v1`) to `LLMGuardConfig`.
- `shared/config/loader.py` — map `LLM_GUARD_ANONYMIZE_ENGINE` /
  `LLM_GUARD_GLINER_MODEL_DIR`.
- `llm_guard_svc/app/guard.py::LLMGuard` — add `anonymize_engine` param +
  `_build_anonymize(engine)` (native → `AnonymizeScanner(_native_model_path(
  "gliner_model_dir"))`, else the existing `Anonymize(Vault(), …)`); replace the
  hardcoded `anonymize` dict entry. `Vault()` now lives only on the `llm_guard`
  branch.
- `llm_guard_svc/app/main.py` — pass `anonymize_engine` into `LLMGuard(...)`.
- `config/env/env.template` — add the two vars.
- `src/llm_guard_svc/requirements.txt` — add `gliner==0.2.26` and explicit
  `presidio-analyzer==2.2.358` (was only transitive via llm-guard).
- `ops/bootstrap/download_llm_guard_models.py` — add the GLiNER repo→dir mapping
  with a per-model `ignore_patterns` override that **keeps** the PyTorch weights
  (eager torch), unlike the ONNX-only default.

## 7. Verification (decided: labelled-set metric gate, not parity)

**(a) Pure-logic unit tests** (`tests/parity/test_pii_logic.py`, no model stack,
host venv): placeholder grammar + per-entity counters, overlap resolution,
GLiNER label→entity map totality (an unmapped label silently drops recall),
empty/no-span redaction, the recall/precision metric math, and labelled-set
integrity (span offsets, en+fr coverage, canonical entity names, benign cases).

**(b) Model-backed metric gate** (`tests/parity/test_pii_metrics_container.py`,
skip-if-`gliner`/`presidio_analyzer`-absent): build the native scanner via
`LLMGuard._build_anonymize("native")`, run the labelled set
(`tests/parity/pii_labelled.py`) through `.detect()`, compute entity-level
recall/precision (`tests/parity/pii_metrics.py`), and assert the ratified bars:

| Group | Recall | Precision |
|---|---|---|
| Structured (email/card/SSN/IBAN/phone) | ≥ 0.98 | ≥ 0.98 |
| Free-text (PERSON/LOCATION/ORGANIZATION) | ≥ 0.85 | ≥ 0.80 |
| Benign (zero-PII) cases | — | **zero false positives (hard fail on any leak)** |

There is **no differential `_assert_same` vs llm-guard** — comparing a swapped
model to the old one is meaningless. Runs in the `llm-guard-svc` container
(`docker cp` + `docker exec … pytest`, models mounted at `/app/models`).

**(c) Documented divergence** (`tests/parity/test_pii_golden_divergence.py`, host
venv): pins the distilbert golden quirks the native engine intentionally diverges
from (e.g. "Bonjour" redacted as PERSON; the `0.6` softmax score) so the
divergence is a checked invariant and the golden is **not** re-baselined to native
(it stays authoritative for `anonymize_engine=llm_guard` only).

## 7a. Finding — model swap reshapes the verification (implementation, 2026-06-02)

Unlike steps 1–2, parity-by-construction does not exist here: the licensing-forced
model swap means native output legitimately differs from the distilbert golden.
The verification was therefore restructured around a **new hand-labelled PII set +
recall/precision gate** (§7b), with the golden retained only as the frozen
`llm_guard` reference. The placeholder grammar was confirmed **not** load-bearing
(no consumer parses `[REDACTED_<ENTITY>_<n>]`), so exact-string parity was
explicitly dropped as a goal — only the redaction *verdict* and the metric bars
matter.

## 8. Cutover sequencing

Ships behind `LLM_GUARD_ANONYMIZE_ENGINE` (default `llm_guard`). The default flip
to `native`, `llm_guard` removal, `transformers` unpin, distilbert-dir removal,
and CVE closure all happen together at the **LLG-04 finale (AIO-73)**, re-validated
by the full parity harness + this labelled metric gate.

## 9. Rollback

Set `LLM_GUARD_ANONYMIZE_ENGINE=llm_guard` (the default) — reverts the
`anonymize` scanner to the llm-guard distilbert path with no redeploy. No other
scanner is affected.
