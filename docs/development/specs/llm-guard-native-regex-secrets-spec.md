# Spec — Native `regex` + `secrets` scanners (LLG-04 cutover step 1)

**Status:** Implemented (2026-06-01) — native regex+secrets behind flags (default `llm_guard`), unit parity green
**Date:** 2026-06-01
**Linear:** AIO-1 (LLG-04)
**Related:** `docs/development/analysis/llm-guard-replacement-evaluation.md` (§3, §4.1–4.2, §6, §10.2), `src/llm_guard_svc/tests/parity/` (parity harness, PR #92), `src/llm_guard_svc/app/guard.py`

---

## 1. Goal

Replace the `llm-guard`-backed `regex` and `secrets` scanners with native
implementations that depend on `detect-secrets` + `presidio-anonymizer`
directly (not `llm_guard`), as the first per-scanner cutover of the LLG-04
migration. **Byte-exact behavioural parity** with the current service, validated
by the parity harness. `llm-guard` stays installed and remains the default
engine; nothing switches automatically.

This is the lowest-risk pair (evaluation §4.1–4.2, §10.2) and proves the
cutover pattern — engine switch + per-scanner parity — that the remaining
scanners (3 ONNX classifiers, then PII) will reuse.

## 2. Non-goals

- No change to the 3 ONNX classifiers (`prompt_injection`, `gibberish`,
  `language`) or `anonymize` (PII).
- No `transformers` version change; `llm-guard` is **not** removed. (The 7
  Dependabot CVEs close only at the end of LLG-04 — see eval §9a.)
- No container/compose changes; validation is unit-level per-scanner (decided
  during design). The service-level harness (`PARITY_CANDIDATE_URL`) remains the
  later end-to-end gate.
- No flipping of the default engine in this increment — native code ships
  **dormant** behind a flag defaulting to `llm_guard`.

## 3. Approach (decided): verbatim port

Both scanners are small, MIT-licensed llm-guard modules whose exact behaviour
depends on machinery that is impractical to recreate faithfully:

- `regex` redacts via presidio's `TextReplaceBuilder` and returns llm-guard's
  signed score convention (`-1.0` clean / `1.0` blocked) directly.
- `secrets` is `detect-secrets` + **95 bundled custom plugins** + `REDACT_ALL`
  (each detected secret → literal `"******"`) + `TextReplaceBuilder`. Observed
  artifacts like `export GH_TOKEN=************AB` are *emergent* from this exact
  stack (overlapping detections each masked to `******`, trailing chars
  uncovered) and are **not** reproducible by a clean reimplementation.

**Therefore: port llm-guard's `regex.py` / `secrets.py` logic verbatim and
vendor the 95 `secrets_plugins/` files**, depending on `detect-secrets` +
`presidio-anonymizer` directly. Parity is guaranteed by construction (same code
path). Rejected alternatives: reimplement on detect-secrets defaults (drops the
95 plugins → recall regression, diverges on redaction); thin shim still importing
`llm_guard` (reduces no dependency).

License: `llm-guard` is MIT — vendoring is permitted with attribution.

## 4. Behaviour to reproduce (from golden baseline)

Scanner contract: `.scan(text) -> tuple[sanitized_text: str, passed: bool, score: float]`.

`regex` (SEARCH match type, our two patterns, `redact=True`):
| Input | sanitized | passed | score |
|---|---|---|---|
| `password=hunter2supersecret` | `[REDACTED]` | False | 1.0 |
| `api_key: ABCD1234EFGH5678` | `[REDACTED]` | False | 1.0 |
| `Deploy key: ssh-rsa AAAAB3…== admin@host` | `Deploy key: [REDACTED] admin@host` | False | 1.0 |
| clean text | unchanged | True | -1.0 |

`secrets` (`REDACT_ALL`, llm-guard plugin config):
| Input | sanitized | passed | score |
|---|---|---|---|
| `aws_access_key_id=AKIA… aws_secret_access_key=wJal…` | `aws_access_key_id=****** aws_secret_access_key=******` | False | 1.0 |
| `export GH_TOKEN=ghp_…AB` | `export GH_TOKEN=************AB` | False | 1.0 |
| clean text | unchanged | True | -1.0 |

Note: only one pattern path fires per `regex.scan` (it returns on the first
matching pattern); `MatchType.SEARCH` redacts the first match only.

## 5. Components

### 5.1 `src/llm_guard_svc/app/scanners/` (new package)
- `__init__.py` — exports the native scanner classes.
- `regex_scanner.py` — port of llm-guard `Regex` + the `MatchType.SEARCH`
  subset; constructed with the two existing credential/SSH patterns.
- `secrets_scanner.py` — port of llm-guard `Secrets`: the `plugins_used`
  config, `redact_value` (`REDACT_ALL` → `"******"`), and `scan()`.
- `secrets_plugins/` — the 95 vendored custom plugin modules, unchanged.
- `secrets_plugins/README.md` — provenance (llm-guard version, source path) +
  MIT attribution.

Native scanners must produce the identical `(str, bool, float)` tuple shape, so
they slot into the existing `LLMGuard.validate_input` scan loop with no loop
changes.

### 5.2 Engine switch — `LLMGuardConfig` (`src/shared/config/schemas.py` + `loader.py`)
- New fields: `regex_engine: str = "llm_guard"`, `secrets_engine: str = "llm_guard"`
  (allowed: `"llm_guard"`, `"native"`).
- Env: `LLM_GUARD_REGEX_ENGINE`, `LLM_GUARD_SECRETS_ENGINE` (read in `loader.py`
  alongside the existing `*_model_dir` vars).

### 5.3 `LLMGuard.__init__` (`src/llm_guard_svc/app/guard.py`)
- Build the `regex` and `secrets` entries of `self.scanners` from the selected
  engine (native class vs current llm-guard class). All other scanners
  unchanged. No change to the scan loop, risk-score weights, or response shape.

### 5.4 Dependencies — `src/llm_guard_svc/requirements.txt`
- Add explicit `detect-secrets` and `presidio-anonymizer`, pinned to the
  versions `llm-guard==0.3.16` currently resolves (so the vendored plugins
  behave identically). These are presently transitive.

## 6. Parity validation

New `src/llm_guard_svc/tests/parity/test_scanner_parity.py`:
- Instantiate the **native** `Regex` and `Secrets` directly (no service, no
  `llm_guard` import).
- For every one of the 22 corpus cases, run `native.scan(input_text)` and assert
  `(passed, score)` equals the golden `details.regex` / `details.secrets`.
- For the deterministic `regex_*` cases, additionally assert the redacted
  `output_text` equals the golden `sanitized_text`. (Valid as a per-scanner
  oracle: for these inputs the earlier scanners are no-ops, so the golden
  `sanitized_text` reflects this scanner on ~raw input.) Secrets redaction is
  **not** asserted as an exact string — see §6a.
- For non-secret cases, assert native passes unchanged (`True`, `-1.0`, text
  unmodified).

The existing harness self-check + golden-integrity tests continue to guard the
overall contract. The opt-in service-level harness is unchanged and will gate the
eventual end-to-end cutover.

### 6a. Parity finding (implementation, 2026-06-01)

While building the secrets parity test, the `secrets` redaction proved
**non-deterministic for multi-secret inputs** — this is a property of llm-guard's
`Secrets.scan()` itself, not the port: it iterates an unordered
`SecretsCollection` and redacts via `prompt.find(value)` + index-shifting
replacement, so for overlapping/multiple secrets the exact mask layout varies
run-to-run and can even **re-leak a secret** (observed: an AWS keypair input
whose "redacted" output duplicated the secret value verbatim). The live service
now even returns a different `secret_github_pat` redaction than the golden
captured hours earlier.

Consequences:
- **Verdict is the contract.** `secrets` parity is asserted at `(passed, score)`
  only (deterministic; 22/22 green). Exact-string redaction is asserted only for
  the deterministic single-match `regex` cases. The native port reproduces the
  current (quirky) behaviour faithfully.
- **Cutover implication (for the "make native default" step):** we should decide
  whether to keep the non-deterministic redaction (pure parity) or **fix it**
  (deterministic, non-leaking redaction) as an intentional, documented
  improvement. The verdict — what the orchestrator gates on — is unaffected
  either way.
- **Harness follow-up:** the merged service-level harness (`compare.py`, PR #92)
  asserts `sanitized_text` exact-equality, which is therefore flaky for these two
  multi-secret cases when comparing any candidate. Relax that comparison (verdict
  + secret-absence rather than exact string) before the end-to-end cutover gate.

## 7. Acceptance criteria

1. `app/scanners/{regex_scanner,secrets_scanner}.py` + vendored `secrets_plugins/`
   exist; neither imports `llm_guard`.
2. `LLM_GUARD_REGEX_ENGINE` / `LLM_GUARD_SECRETS_ENGINE` select the engine;
   default (`llm_guard`) leaves behaviour and the golden baseline unchanged.
3. `test_scanner_parity.py` passes: native `regex` + `secrets` match golden
   `(passed, score)` for all 22 cases and redaction for the secret/regex cases.
4. Existing `src/llm_guard_svc/tests/` pass; ruff + black + mypy (pre-commit)
   clean.
5. `detect-secrets` + `presidio-anonymizer` declared explicitly; image still
   builds.

## 8. Rollback

Per-scanner: revert `LLM_GUARD_REGEX_ENGINE` / `LLM_GUARD_SECRETS_ENGINE` to
`llm_guard` (the default) — no redeploy of code needed. Native code is inert
until a flag is flipped.
