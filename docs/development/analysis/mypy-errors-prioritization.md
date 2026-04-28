# Mypy Errors — Prioritization and Config Options

**Generated:** 2025-02-07
**Last updated:** 2025-02-07 (current run)
**Total:** **98 errors** in **22 files** (582 source files checked)
**Config:** `mypy.ini` (strict for `src/`, relaxed for `tests/` and `ops/`)

This document categorizes current Mypy errors by priority and calls out which ones are good candidates to fix in code vs. address by loosening or disabling rules.

## Current snapshot (what remains)

| Priority | Category | Count | Status |
|----------|----------|-------|--------|
| **P1** | Real bugs (arg-type, assignment, operator) | 0 | ✅ Fixed (loader.py, openai.py, use_case_management.py) |
| **P2** | no-untyped-def (missing return/param annotations) | ~81 | **Remaining** — see file list below |
| **P3** | var-annotated (variable annotations) | 8 | **Remaining** |
| **Notes** | annotation-unchecked (tests/ops) | 34 | Optional: suppress in `mypy.ini` |

**Remaining error locations (98 total):**

- **ops/** (7): `validate_configuration.py` (3× `results`), `demonstrate_stateless_core_v1.py` (1× `headers`), `verify_template_streaming.py` (3× `headers`)
- **src/orchestrator:** routers `token_analytics.py`, `admin_pricing.py`, `websocket.py`, `corpus.py`, `chunking.py`, `tools_admin.py`, `use_cases.py` (1); `app/middleware/rls.py`; `app/orchestrator/controller.py`
- **src/corpus_svc:** routers `usage.py`, `analytics.py`, `query.py`, `documents.py`; tests `test_multi_collection_search.py` (1× `metadata_`)
- **src/llm_guard_svc:** `app/main.py`
- **src/embedding:** `app/routers/embedding.py`, `app/routers/admin.py`, `app/main.py`
- **src/inference-gateway:** `app/routers/chat.py`

## Related documentation

- **Project coding standards:** `.cursorrules` and backend standards (e.g. `.cursor/skills/backend-standards/`) require **type hints for all function signatures, parameters, return types, and class attributes** in production code. Fixing annotations (Option A below) is the preferred long-term approach; loosening (Option B) is a pragmatic exception for high-churn areas only.
- **Mypy config:** `mypy.ini` at repo root — defines ERROR PRIORITY, per-module strictness (`src/` strict, `tests/` and `ops/` relaxed), and which checks are on/off.
- **Development guidelines:** `docs/development/guidelines/` — Developer_Guide.md (workflows, structure), DOCUMENTATION_GUIDELINES.md (docs as single source of truth), DOCUMENT_ORGANIZATION_GUIDE.md (where to put analysis vs plans vs guidelines).
- **Earlier analysis:** `docs/development/analysis/mypy-error-classification.md` — older Mypy run (different error mix); this document reflects the current config and error set.

---

## Summary by category

| Priority | Category | Count | Action |
|----------|----------|-------|--------|
| **P1** | Real bugs / type safety | 0 (was 4) | ✅ Fixed |
| **P2** | Strictness (no-untyped-def) | ~81 | Fix gradually or loosen config |
| **P3** | Variable annotations | 8 | Fix opportunistically or disable |
| **Notes** | annotation-unchecked | 34 | Suppress or ignore (tests/ops) |

---

## P1 — Fix first (real bugs / type safety)

These can indicate wrong types at runtime. Fix in code; do not silence with config.

### 1. `arg-type` (2 errors)

**File:** `src/shared/config/loader.py`

- **Line 52:** `password=resolve_secret("POSTGRES_PASSWORD") or os.environ.get("POSTGRES_PASSWORD", "test_password_123")` → type is `str | None`; `DatabaseConfig.password` expects `str`.
- **Line 93:** `secret=resolve_secret("JWT_SECRET") or os.environ.get("JWT_SECRET", "CHANGE_ME")` → type is `str | None`; `JWTConfig.secret` expects `str`.

**Cause:** If both `resolve_secret()` and `os.environ.get()` can return `None`, the expression is still `str | None`.
**Fix:** Use a guaranteed default (e.g. `... or ""`) and document why empty is acceptable, or assert/narrow after a runtime check and then pass a `str`. Prefer aligning the model with reality (`str | None`) only if the app truly allows missing password/secret in some environments.

---

### 2. `assignment` (1 error)

**File:** `src/embedding/app/providers/openai.py:86`

- `api_key = os.environ.get(api_key_env)` → expression is `str | None`, but the variable is inferred as `str` from the `if self._api_key_override` branch. The `if not api_key: raise ...` narrows for runtime but not for the initial assignment in the `else` branch.

**Fix:** Annotate explicitly, e.g. `api_key: str | None = os.environ.get(api_key_env)`, then after the `if not api_key: raise ...` use `api_key` (mypy will treat it as `str`), or assign in both branches so the type is clear.

---

### 3. `operator` (1 error)

**File:** `src/orchestrator/app/routers/use_case_management.py:720`

- `if target_state not in allowed_states:` — “Unsupported right operand type for in ("object")”.
  `allowed_states` comes from `valid_transitions.get(current_state, [])`; the dict values are likely typed as `list` of something generic (e.g. `object`), so the right-hand side of `in` is inferred as involving `object`.

**Fix:** Type `valid_transitions` so values are e.g. `list[str]` (or the actual state type), so `allowed_states` has a concrete type and the `in` check is valid.

---

## P2 — Annotation strictness (consider loosening or gradual fix)

**~81 errors** (current run) — almost all are **`no-untyped-def`**: “Function is missing a return type annotation” or “missing type annotation for one or more arguments”.

These come from **`disallow_untyped_defs = True`** for `[mypy-src.*]`. They are not proof of runtime bugs; they enforce that all functions in `src/` are fully annotated. **Project coding standards** (see Related documentation above) require type hints for all function signatures and parameters in production code; addressing these by adding annotations is the standard-compliant approach.

### Option A — Fix gradually (recommended; aligns with project standards)

- Add `-> None` or the correct return type for every function that currently has none.
- Add argument types for every parameter (including FastAPI dependency injection and route handlers).
- Aligns with `.cursorrules` and backend standards (“type hints mandatory”). Your existing `mypy.ini` already says: *“no-untyped-def - Gradual, fix when touching code”*.

### Option B — Loosen for specific modules (temporary exception)

If you need **short-term relief** without fixing all call sites (e.g. unblocking CI or pre-commit), you can relax only for narrow module patterns. This conflicts with the project’s “type hints mandatory” standard; treat as temporary and revert once annotations are added.

1. **FastAPI route handlers** (routers): many errors are in `src/*/app/routers/*.py` and `src/*/app/main.py` (lifespan, startup). You can add a more specific section and turn off strict defs for those modules only, for example:

   ```ini
   [mypy-src.*.app.routers]
   disallow_untyped_defs = False

   [mypy-src.*.app.main]
   disallow_untyped_defs = False
   ```

   Then fix annotations gradually when you work in those files.

2. **Pydantic / schema validators**: errors in `src/orchestrator/app/schemas/*.py` (e.g. `pricing.py`, `token_usage.py`, `tool_registration.py`) are often validators or `@field_validator`. You can either add correct annotations (e.g. `classmethod` + proper args) or relax for `src.*.schemas` if you prefer.

3. **MCP and middleware**: a few errors in `stdio_client.py`, `http_client.py`, `rls.py`. Same choice: fix when touching, or add a small `[mypy-src.*.mcp]` / `[mypy-src.*.middleware]` block with `disallow_untyped_defs = False` and clean up later.

### Option C — Do not loosen globally

Keeping **`disallow_untyped_defs = True`** for `src/` and fixing over time is the most consistent with your stated philosophy (“Require annotations on all functions” in production code). Use Option B only for narrow, high-churn areas (e.g. routers) if you need quick relief.

---

## P3 — Variable annotations (low priority / optional disable)

**8 errors** (current run) — **`var-annotated`**: “Need type annotation for variable”. Project standards (`.cursorrules`) also require type hints for variables; adding annotations is the standard-compliant approach.

| Location | Variable |
|----------|----------|
| `ops/validate_configuration.py` | `results` (×3) |
| `ops/demonstrate_stateless_core_v1.py` | `headers` |
| `ops/testing/verify_template_streaming.py` | `headers` (×3) |
| `src/orchestrator/.../chunking_service.py` | `current_chunk` |
| `src/corpus_svc/.../chunking_service.py` | `current_chunk` |
| `src/corpus_svc/.../text_extractor_base.py` | `_importers` |
| `src/orchestrator/.../response_formatter.py` | `validation_metadata` |
| `src/corpus_svc/tests/unit/services/test_multi_collection_search.py` | `metadata_` |

*(Some previously listed src/ locations may have been fixed; re-run mypy to confirm.)*

- **ops/** already has relaxed rules; these still appear because mypy requires an annotation when it can’t infer the type (e.g. empty list `[]`). Fix by adding explicit types (e.g. `results: list[SomeResult] = []`) or leave as-is if you’re okay with ops being loosely typed.
- For **src/** prefer adding the missing variable annotations (quick in most cases). Disabling **`var-annotated`** in `mypy.ini` would conflict with project standards (“type hints mandatory” for variables); use only if the team explicitly decides to allow unannotated variables in certain areas.

---

## Notes (not errors) — `annotation-unchecked`

**34 notes** in `tests/` and `ops/`: “By default the bodies of untyped functions are not checked, consider using --check-untyped-defs”.

- These are **informational**. They refer to code in **tests** and **ops**, where you already have `disallow_untyped_defs = False` and `check_untyped_defs = False`.
- You can **ignore** them (no config change), or suppress the note so mypy doesn’t report them:

  ```ini
  [mypy-tests.*]
  disable_error_code = annotation-unchecked

  [mypy-ops.*]
  disable_error_code = annotation-unchecked
  ```

  That keeps behavior the same but removes the note from the report.

---

## Config changes summary (if you want to loosen)

| Goal | Change in `mypy.ini` |
|------|----------------------|
| Fix only real type bugs | No config change; P1 already fixed. |
| Fewer router/main errors (temporary) | Add `[mypy-src.*.app.routers]` and optionally `[mypy-src.*.app.main]` with `disallow_untyped_defs = False`. Revert when annotations are added. |
| Allow unannotated variables in src | Not recommended (conflicts with project standards). If needed: `disable_error_code = var-annotated` under `[mypy-src.*]`. |
| Silence annotation-unchecked in tests/ops | Add `disable_error_code = annotation-unchecked` under `[mypy-tests.*]` and `[mypy-ops.*]`. |

---

## Recommended order of work

1. **P1:** ✅ Done — no remaining real type-safety errors.
2. **P2:** Per project coding standards, prefer **Option A** (add return/param annotations when you touch a file). Use Option B (temporary `disallow_untyped_defs = False` for `[mypy-src.*.app.routers]` and `[mypy-src.*.app.main]`) only if you need immediate CI/pre-commit relief.
3. **P3:** Add the 8 variable annotations (ops + 1 test); quick wins in `src/` are the single `metadata_` in corpus_svc tests.
4. **Notes:** Optionally add `disable_error_code = annotation-unchecked` under `[mypy-tests.*]` and `[mypy-ops.*]` to quiet the 34 notes.

Re-run to confirm after any changes:

```bash
uv run mypy --config-file mypy.ini src tests ops
```

and use the same command after any config or annotation changes to confirm the desired balance of strictness vs. noise.

---

## What remains (quick reference)

- **98 errors** in **22 files** as of last run.
- **P1:** None — arg-type, assignment, operator issues in `loader.py`, `openai.py`, `use_case_management.py` are fixed.
- **P2 (~81):** Add return type and parameter annotations to route handlers and main/lifespan in:
  - **orchestrator:** `token_analytics`, `admin_pricing`, `websocket`, `corpus`, `chunking`, `tools_admin`, `use_cases`; `middleware/rls`; `controller`
  - **corpus_svc:** `usage`, `analytics`, `query`, `documents`
  - **embedding:** `embedding`, `admin` routers; `main`
  - **llm_guard_svc:** `main`
  - **inference-gateway:** `chat` router
- **P3 (8):** Add variable annotations: `ops/validate_configuration.py` (3× `results`), `ops/demonstrate_stateless_core_v1.py` (1× `headers`), `ops/testing/verify_template_streaming.py` (3× `headers`), `src/corpus_svc/tests/.../test_multi_collection_search.py` (1× `metadata_`).
- **Optional:** Suppress 34 `annotation-unchecked` notes in tests/ops via `disable_error_code = annotation-unchecked` in `mypy.ini`.
