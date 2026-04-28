# Publication Audit Plan — GitHub Public Release

**Purpose:** Systematic, phase-by-phase review of the codebase before publishing as a public GitHub repository.
**Focus:** Personal information exposure, over-logging, and missing or incorrect information.
**Approach:** One phase per scope; same audit instructions applied in each phase (“fine-tooth comb”).

---

**Status:** Phases 1–12 complete (2026-02-04). (Test failures/segfault are out of scope for this plan; tracked separately.)

**For agents:** All phases complete. Each phase has its own **Status** in Section 4 (Phase Definitions) and in the Phase Overview table (Section 3). When maintaining or re-auditing, use the same instructions (Section 2) and Phase Log (Section 7).

---

## 1. Audit Objectives

For every file in scope, verify:

| Objective | What to check |
|-----------|----------------|
| **No PII exposure** | No real names, emails, internal hostnames, IPs, org-specific identifiers, or other personally identifiable data in committed files. Replace with placeholders (e.g. `user@example.com`, `internal-host.example.com`) where examples are needed. |
| **No over-logging** | No logging of secrets, API keys, tokens, passwords, full request/response bodies with user content, or other sensitive data. Logs use redaction where required (see ADR-048). No debug dumps of PII or credentials. |
| **No missing/incorrect information** | READMEs, docstrings, and docs accurately describe behavior. No stale references (old paths, renamed services, outdated env vars). Config examples and templates are correct and safe. |

**Out of scope for this plan:** Functional correctness, performance, or feature completeness — only publication-readiness (safety and accuracy of what is exposed).

---

## 2. Standard Phase Instructions

**Apply these steps in every phase.**

1. **List all files** in the phase scope (by directory and file type).
2. **PII sweep:** Search for patterns that may indicate PII or internal-only data:
   - Real-looking emails, names, phone numbers.
   - Internal hostnames, VPNs, or org-specific URLs.
   - Real IP addresses (except documented examples like `127.0.0.1`).
   - Company/product names that should be generic in public docs.
3. **Secrets and logging sweep:**
   - Hardcoded secrets, API keys, passwords, tokens (including in comments or examples).
   - `logger.*` / `logging.*` / `print()` that log request/response bodies, headers, or user input without redaction.
   - Logging of env vars that may hold secrets.
4. **Accuracy sweep:**
   - Cross-check docstrings, READMEs, and docs against current code paths and config.
   - Verify env var names, service names, and file paths in documentation.
   - Ensure code comments and TODOs do not reference internal-only systems.
5. **Record findings** in the phase log (see Phase Log template below). Fix or document before marking phase complete.
6. **When editing code in scope:** Remove unnecessary `cast()` that were added only to satisfy mypy (e.g. `return cast(...)`). Prefer fixing real types or leaving code as-is per `mypy.ini`; avoid “cast theater” (adding/removing casts that add no real type safety).
   - **Remove cast:** For `return cast(SomeType, x)` where `x` comes from JSON/API (e.g. `response.json()`), replace with a typed variable and return it: `data: SomeType = response.json()` then `return data`. Remove the `cast` import if no longer used. Only keep `cast` when it is truly required (e.g. narrowing a union after a runtime check).

**Phase log template (use per phase):**

```markdown
## Phase N: [Scope Name]
- **Scope:** [list directories/files]
- **Completed (date):** ___________
- **PII findings:** [none / list and resolution]
- **Over-logging findings:** [none / list and resolution]
- **Accuracy findings:** [none / list and resolution]
- **Sign-off:** ___________
```

---

## 3. Phase Overview and Directory Map

Every project directory is assigned to exactly one phase. Phases are ordered so that shared/config and dependencies are audited before service-specific code.

| Phase | Status | Scope | Directories / contents |
|-------|--------|--------|------------------------|
| **1** | ✅ Complete (2026-01-28) | Root and config | Root files, `config/`, `deploy/` |
| **2** | ✅ Complete (2026-01-28) | Shared library | `src/shared/` |
| **3** | ✅ Complete (2026-01-28) | Corpus service | `src/corpus_svc/` |
| **4** | ✅ Complete (2026-01-29) | Embedding service | `src/embedding/` |
| **5** | ✅ Complete (2026-01-30) | Inference gateway | `src/inference-gateway/` |
| **6** | ✅ Complete (2026-02-02) | LLM Guard service | `src/llm_guard_svc/` |
| **7** | ✅ Complete (2026-02-02) | Orchestrator | `src/orchestrator/` |
| **8** | ✅ Complete (2026-02-03) | Frontend (Angular) | `src/frontend-angular/` |
| **9** | ✅ Complete (2026-02-03) | Ops and scripts | `ops/` (all subdirs and root-level scripts) |
| **10** | ✅ Complete (2026-02-03) | Tests | `tests/` (all subdirs) |
| **11** | ✅ Complete (2026-02-04) | Documentation | `docs/` (11a, 11b, 11c) |
| **12** | ✅ Complete (2026-02-04) | IDE and tooling config | `.cursor/`, root dotfiles and config files |

---

## 4. Phase Definitions (Detailed)

### Phase 1: Root and config

- **Status:** ✅ Complete (2026-01-28).
- **Scope:**
  - **Root:** `README.md`, `README_NPM_CACHE.md`, `pyproject.toml`, `pytest.ini`, `mypy.ini`, `conftest.py`, `constraints.txt`, `requirements-all.txt`, `env_setup`, `ai_operations.code-workspace`
  - **config/**
    - `config/env/` — only tracked files (e.g. `env.template`, `env.test.template`; do not read actual `.env` or secrets)
    - `config/models/` — `model_metadata.template.yaml`, `model_metadata.yaml`
  - **deploy/** — `docker-compose.yml`, `docker-compose.test.yml`
- **Notes:** Env templates must use placeholders only; no real keys or internal URLs. Compose files must not embed secrets; document any required env vars.

---

### Phase 2: Shared library

- **Status:** ✅ Complete (2026-01-28).
- **Scope:** `src/shared/` (all subdirectories and files).
- **Notes:** Shared logging and redaction (ADR-048) are critical here. Check that no sensitive fields are logged without redaction and that shared config/docs match actual behavior. After fixes: update tests for touched code (e.g. `TokenPayload` `roles` vs `role`, mocks) and resolve linter errors in modified files (type hints, ORM `Column` access, etc.).

---

### Phase 3: Corpus service

- **Status:** ✅ Complete (2026-01-28).
- **Scope:** `src/corpus_svc/` (all subdirectories and files).
- **Notes:** Include app code, tests under this tree, and any service-specific README or config. Check logging in document/ingestion paths.

---

### Phase 4: Embedding service

- **Status:** ✅ Complete (2026-01-29).
- **Scope:** `src/embedding/` (all subdirectories and files).
- **Notes:** Check for model paths, external API references, and any logging of input text or keys.

---

### Phase 5: Inference gateway

- **Status:** ✅ Complete (2026-01-30).
- **Scope:** `src/inference-gateway/` (all subdirectories and files).
- **Notes:** Gateway touches provider keys and request/response payloads; verify no secrets or full prompts/responses in logs.

---

### Phase 6: LLM Guard service

- **Status:** ✅ Complete (2026-02-02).
- **Scope:** `src/llm_guard_svc/` (all subdirectories and files).
- **Notes:** Content may be sensitive; ensure logging is redacted or minimal per ADR-048.

---

### Phase 7: Orchestrator

- **Status:** ✅ Complete (2026-02-02).
- **Scope:** `src/orchestrator/` (all subdirectories and files).
- **Notes:** Central routing and use-case execution; check logging of user input, session IDs, and external calls.

---

### Phase 8: Frontend (Angular)

- **Status:** ✅ Complete (2026-02-03).
- **Scope:** `src/frontend-angular/` (all subdirectories and files: TS, HTML, SCSS, config, specs).
- **Notes:** No API keys or secrets in frontend code. Check for internal URLs, analytics IDs, or PII in comments or mock data.

---

### Phase 9: Ops and scripts

- **Status:** ✅ Complete (2026-02-03).
- **Scope:** Entire `ops/` tree:
  - `ops/bootstrap/`
  - `ops/ci/`
  - `ops/cli/`
  - `ops/database/`
  - `ops/operations/`
  - `ops/testing/`
  - All root-level scripts in `ops/` (e.g. `*.py`, `*.sh`, `*.md`)
- **Notes:** Scripts may load env or config; must not log secrets or assume internal-only paths without documenting. Check for credentials in comments or example commands.

---

### Phase 10: Tests

- **Status:** ✅ Complete (2026-02-03).
- **Scope:** Entire `tests/` tree:
  - `tests/benchmarks/` (including `results/` for committed files)
  - `tests/e2e/`
  - `tests/fixtures/`
  - `tests/integration/`
  - `tests/load/` (including `results/` for committed files)
  - `tests/mcp_compliance/`
  - `tests/unit/`
  - Root: `tests/conftest.py`, `tests/README.md`
- **Notes:** Fixtures and test data must not contain real PII or secrets. Test env vars and URLs should be placeholders or clearly test-only.

---

### Phase 11: Documentation

- **Status:** ✅ Complete (2026-02-04) (11a, 11b, 11c).
- **Scope:** Entire `docs/` tree. Use sub-phases for execution; all are part of Phase 11.

| Sub-phase | Scope |
|-----------|--------|
| **11a** | **docs/** root: `README.md`, `PROJECT_OVERVIEW.md` (designated overview), and any other root-level `.md`. **docs/admin/**, **docs/api/** (and **docs/api/admin/**), **docs/architecture/** (and **docs/architecture/database/**), **docs/demo/** (includes `CISO_PRESENTATION*.md`), **docs/deployment/**, **docs/operations/**, **docs/testing/**, **docs/user-guides/** (includes `GLOSSARY.md`). |
| **11b** | **docs/development/** — **adrs/**, **analysis/**, **architecture/**, **guidelines/**, **guides/**, **migration/**, **plans/** (including subdirs: active, archive, completed, features, future), **specs/**, **templates/**, **testing/**. Plus **docs/development/** root-level `.md` (e.g. `FEATURE_IMPLEMENTATION_PROMPT_V1.md`). |
| **11c** | **docs/development/sessions/**, **docs/development/completed/**, **docs/development/tasks/**, **docs/development/reports/**, **docs/development/archive/**. **docs/archive/** (all subdirs: e.g. backend-audit-sept2025, bootstrap-scripts, documentation-review-oct2025, outdated_guides, p4-f10-refactor, plan-reorganization-oct2025, qodo-troubleshooting-oct2025, streamlit-frontend, temp_orchestrator_refactoring_2025-10-25). |

**Notes:** Sessions and completed docs often contain internal context or names; sanitize or redact. Ensure no real hostnames, credentials, or customer data. CISO and demo docs must be safe for public viewing.

---

### Phase 12: IDE and tooling config

- **Status:** ✅ Complete (2026-02-04).
- **Scope:**
  - **.cursor/** — `agents/`, `commands/`, `context/`, `memory/`, `rules/`, `skills/`, `workflows/`, `README.md`. (Exclude `.cursor/sessions/`, `cache/`, `logs/`, `settings/` per .gitignore.)
  - **Root dotfiles and config:** `.cursorignore`, `.cursorrules`, `.clinerules`, `.dockerignore`, `.editorconfig`, `.eslintrc.json`, `.gitignore`, `.htmlhintrc`, `.htmlhintignore`, `.prettierignore`, `.prettierrc`, `.qodo/`.
- **Notes:** Ensure no internal URLs, names, or secrets in rules or command docs. `.cursorrules` and rules in `.cursor/rules/` may reference internal processes — make them generic if needed for public repo.

---

## 5. Excluded from Audit (Verify .gitignore)

These are not audited as part of this plan because they are (or should be) ignored and not published:

- `.env`, `config/env/env.test`, `config/env/env.test.local`, `config/env/*.bak`
- `data/`, `temp_scripts/`, `backups/`, `corpus_docs/`
- `.cursor/sessions/`, `.cursor/cache/`, `.cursor/logs/`, `.cursor/settings/`
- `venv/`, `node_modules/`, build/cache dirs, coverage reports

**Pre-audit step:** Confirm `.gitignore` (and any `.cursorignore` usage for publishing) excludes the above so they never enter the public repo.

---

## 6. Execution Order and Sign-off

1. Complete **Phase 1** first (root and config).
2. Then **Phase 2** (shared), then services **3–8** in order.
3. Then **Phase 9** (ops), **Phase 10** (tests).
4. Then **Phase 11** (docs) — 11a → 11b → 11c.
5. Finally **Phase 12** (IDE and tooling).

Each phase is **complete** only when:

- All files in scope have been reviewed per Section 2.
- Findings are recorded in the phase log.
- Issues are fixed or explicitly accepted (with rationale) and documented.
- Phase sign-off is dated and recorded.

---

## 7. Phase Log (To Be Filled During Audit)

Fill each block as the phase is completed.

### Phase 1: Root and config

- **Scope:** Root files, `config/`, `deploy/`
- **Completed (date):** 2026-01-28
- **PII findings:** Fixed hardcoded path in docker-compose.test.yml (now PROJECT_ROOT/relative); model_metadata.yaml gitignored.
- **Over-logging findings:** None.
- **Accuracy findings:** Fixed pytest.ini (backend→orchestrator, retrieval→corpus_svc); requirements-all.txt same; env_setup and test env standardized on config/env/env.test; credentials removed from compose/test conftest (env-only).
- **Sign-off:** Phase 1 complete (2026-01-28). Test failures/segfault (OpenBLAS) out of scope; tracked in separate thread.

### Phase 2: Shared library

- **Scope:** `src/shared/` (all subdirectories and files: auth/, config/, db/, logging_utils/, providers/, telemetry_utils/, tests/, database.py, requirements.txt, run_tests.sh)
- **Completed (date):** 2026-01-28
- **PII findings:** Auth router and manager logged `username` in login, refresh, revoke, user management, and JWT validation paths. JWT validation also logged `sub` (often username). **Fixed:** Use `user_id` only in log extra; removed `username` and `sub` from all auth logs. Router imported `orchestrator.app.db.models` for roles (service-boundary violation). **Fixed:** Use raw SQL `SELECT role FROM user_roles WHERE user_id = :user_id` in router, matching manager pattern; removed orchestrator import.
- **Over-logging findings:** `config/base.py` used `print()` for validation and env-file write errors (could leak config details or paths). **Fixed:** Switched to logging; log only `type(e).__name__` and `filepath`, not full exception messages. `telemetry_utils/telemetry.py` logged OTLP endpoint URL (internal). **Fixed:** Log "OpenTelemetry OTLP exporter configured" only, no URL. JWT loader default `myTopsecretkey` was key-like. **Fixed:** Default set to `CHANGE_ME`. No passwords, tokens, or request/response bodies logged.
- **Accuracy findings:** Config loader JWT default and config base error reporting updated as above. `logging_utils` does not implement redaction; ADR-048 redaction lives in orchestrator middleware. Shared logging provides JSON formatter, request-id propagation, and context adapters only—documented via phase audit. localhost / 0.0.0.0 in config and tests are documented examples only.
- **Sign-off:** Phase 2 complete (2026-01-28). **Tests:** Auth unit tests updated—`TokenPayload` uses `roles` (not `role`); `test_requires_roles_forbidden` mock provides `has_any_role`; lambda args `_self`/`_required_roles` for Ruff. All 201 shared tests pass. **Linter:** `validate_token` return type `dict[str, str | list[str]]`; `get_sessions` where-clause uses `RefreshToken.revoked.is_(False)`; `getattr` for ORM `Column` access in conditionals (router/manager); `# type: ignore[assignment]` for ORM attribute writes where needed.

### Phase 3: Corpus service

- **Scope:** `src/corpus_svc/` (all subdirectories and files: app/, tests/, README.md, Dockerfile, requirements.txt, run_tests.sh)
- **Completed (date):** 2026-01-28
- **PII findings:** Logging of file names, document titles, collection names, query text, and telemetry endpoint could expose PII or internal data. **Fixed:** main.py no longer logs OTLP endpoint URL (log "OpenTelemetry OTLP exporter configured" only). Documents router no longer logs file_name in upload/preflight messages. Document and collection repositories log document_id/collection_id only, not title/name. Query service logs query length and result count only; collection names and query text removed from log messages. Ingestion service logs collection id only for Qdrant collection.
- **Over-logging findings:** main.py used print() for startup; switched to logger.info. PDF extraction had [DEBUG] in error message; removed. Test file had debug print(response.json()); removed.
- **Accuracy findings:** README referenced src/retrieval/, utils/logging.py, utils/telemetry.py, storage/, and SECRET_KEY. **Fixed:** Paths updated to src/corpus_svc/; observability described as shared.logging_utils and shared.telemetry_utils; storage → repositories; SECRET_KEY → JWT_SECRET. Development and deployment paths updated to corpus_svc.
- **Sign-off:** Phase 3 complete (2026-01-28). Tests: DummyDoc in test_multi_collection_search given file_type, classification, created_at; removed print from test_documents_router. All 106 corpus_svc tests pass. Linter: lazy % formatting in collection_repository; getattr for ORM Column in query_service; type: ignore[assignment] for ORM attribute writes in collection_repository.

### Phase 4: Embedding service

- **Scope:** `src/embedding/` (all subdirectories and files: app/, Dockerfile, README.md, requirements.txt, etc.)
- **Completed (date):** 2026-01-29
- **PII findings:** Admin router logged `current_user.get("sub")` in log extra (sub is often username). **Fixed:** Use `user_id` only in log extra for all admin endpoints. Default config `app/config/models.yaml` used internal hostname `host.docker.internal`. **Fixed:** Replaced with `http://localhost:8000/v1` and generic comment.
- **Over-logging findings:** main.py logged telemetry endpoint URL. **Fixed:** Log "OpenTelemetry OTLP exporter configured" only. security.py logged received API key on auth failure. **Fixed:** Log "Invalid or missing Client API Key" only, no key value. local.py logged full model path when loading. **Fixed:** Log model name only. config/models.py logged config file path. **Fixed:** Log "Configuration loaded successfully" only.
- **Accuracy findings:** README stated Python 3.11+ and referenced non-existent requirements-dev.txt. **Fixed:** Python 3.12+; removed requirements-dev.txt from installation steps. security.py docstring referenced "Retrieval Service". **Fixed:** "trusted internal clients (e.g. corpus service, orchestrator)".
- **Sign-off:** Phase 4 complete (2026-01-29).

### Phase 5: Inference gateway

- **Scope:** `src/inference-gateway/` (app/, tests/, Dockerfile, README.md, requirements.txt, run_tests.sh, etc.)
- **Completed (date):** 2026-01-30
- **PII findings:** None. Logs use `user_id` or `integration_id` (service) only; no real names, emails, or hostnames in committed files. Test fixtures use placeholders (e.g. test-key, fake_token).
- **Over-logging findings:** Redis client logged Redis URL on init, connect success, and connection failures (URL can contain credentials). **Fixed:** Removed `url` from all log extra; connection failures log `error_type` only. OpenAI provider docstring example showed `print(chunk...)` for streamed content (could encourage logging user/assistant text). **Fixed:** Example now uses variable assignment and comment "do not log or print user/assistant text". Database connection logged full exception in rollback and connection-check failure. **Fixed:** Log `type(e).__name__` only. No provider API keys, prompts, or full responses logged.
- **Accuracy findings:** README project structure was minimal (main.py only). **Fixed:** Updated to reflect app/database, middleware, models, providers, routers, services, utils and tests/unit, integration. README referenced `.env.example` (not present). **Fixed:** "See config/env/env.template or config/env/env.test.template". Last Updated set to 2026-01-30.
- **Sign-off:** Phase 5 complete (2026-01-30).

### Phase 6: LLM Guard service

- **Scope:** `src/llm_guard_svc/` (app/, tests/, Dockerfile, Dockerfile.pipBuild, README.md, requirements.txt, app.py)
- **Completed (date):** 2026-02-02
- **PII findings:** None. Logs use user_id only; no real names, emails, or hostnames in committed files.
- **Over-logging findings:** guard.py logged input_text, sanitized_text, and input_text[:50] in validation events, cache hits, fail-fast, and result cached messages (ADR-048 violation). Exception messages and str(e) could leak sensitive content. **Fixed:** Removed all user content from logs; log only input_length, risk_score, modified, request_id, user_id. Replaced print() in configure_models with _logger; log model name only for success, no paths for warnings. Scanner error log and API response "error" field changed to type(exc).**name** and "Scanner failed". main.py validation exception handler and generic handler no longer log or return exception message to client; use type(e).**name** only.
- **Accuracy findings:** README listed wrong model names (deberta-v3-base vs distilbert, base vs small for prompt-injection). **Fixed:** Updated to Isotonic/distilbert_finetuned_ai4privacy_v2, protectai/deberta-v3-small-prompt-injection-v2; added bootstrap script reference; corrected git clone target directory names to match guard.py. Removed unnecessary cast in guard.py (typed variable instead). Removed debug print from test_validation_endpoint.py.
- **Sign-off:** Phase 6 complete (2026-02-02).

### Phase 7: Orchestrator

- **Scope:** `src/orchestrator/` (all subdirectories and files: app/, tests/, run_tests.sh)
- **Completed (date):** 2026-02-02
- **PII findings:** Orchestrator router logged `username` (current_user.sub) and `client` (request.client.host) in request log extra. **Fixed:** Removed username and client from log extra; use user_id only. DEBUG log with session_id in message simplified to debug-level "Session context" with has_session only.
- **Over-logging findings:** collection_management: logged auth header prefix, header keys, full URL/Headers/Params/Data, response status/headers/content, and full exception. **Fixed:** Log method only for proxy; response status only; exception as type(e).\_\_name\_\_. llm_client: logged API key suffix and in test mode actual/expected key. **Fixed:** "LLMClient initialized" only; test diagnostic logs redact key (API key mismatch / matches expected test key). retrieval_client: logged base_url, "First result sample" (user content), str(e). **Fixed:** "RetrievalClient initialized" only; removed first-result log; type(e).\_\_name\_\_ for errors. controller: logged extracted search query text, response.json() for usage stats, e.response.text and str(e). **Fixed:** Log query length only; no response body; type(e).\_\_name\_\_ for errors. llm_guard_client: logged base_url, str(e). **Fixed:** "LLMGuardClient initialized" only; type(e).\_\_name\_\_. llm_router: logged base_url. **Fixed:** "LLMRouter: Using Inference Gateway" only. response_formatter: logged exception message and match content. **Fixed:** type(e).\_\_name\_\_; "Unexpected match format (skipped)". prompt schema: logged variables list and template content. **Fixed:** "variables validated" / "template validated" only. admin_gateway_providers and admin_gateway_metrics: logged url, response_text, str(e). **Fixed:** type(e).\_\_name\_\_ only; no URL or response body in logs.
- **Accuracy findings:** No README at src/orchestrator root; app-level READMEs (orchestrator/steps, README_INTENT_BASED_ROUTING.md) and MODELS.md exist. No stale paths or incorrect env names found in reviewed files.
- **Sign-off:** Phase 7 complete (2026-02-02). Cast removal: replaced cast with typed variables for response.json() / JSON-derived values in collection_management, retrieval_client, llm_guard_client, corpus, admin_gateway_providers, controller (prompts). Orchestrator unit tests (36) pass; one integration test error (POSTGRES_PORT env) is pre-existing and out of scope.

### Phase 8: Frontend (Angular)

- **Scope:** `src/frontend-angular/`
- **Completed (date):** 2026-02-03
- **PII findings:** Test data used non-example domains and private IPs. **Fixed:** Swapped emails to `example.com` placeholders and replaced `192.168.1.1` with `192.0.2.1` (TEST-NET-1). Cypress fixture email updated to `hello@example.com`.
- **Over-logging findings:** Frontend had console logs of tokens, session IDs, request bodies, file names, template/use-case configs, and WebSocket payload data. Logging interceptor emitted request/response bodies and headers. **Fixed:** Removed sensitive console logs, reduced logging interceptor to request metadata only (no bodies/headers), and removed event payloads from WebSocket parse errors. API integration README examples no longer log tokens or response content.
- **Accuracy findings:** API README environment example and logging guidance did not match current `environment.ts`. **Fixed:** Updated `apiBaseUrl`/`wsBaseUrl` to `/api/v1` and `/ws`, removed unused debug config example, and clarified interceptor as metadata-only logging.
- **Sign-off:** Phase 8 complete (2026-02-03).
- **Dependencies (npm audit):** Frontend upgraded to **Angular 21** (2026-02-03); `npm audit fix` and `npm audit fix --force` were applied. **0 vulnerabilities** reported. TypeScript 5.9, zone.js 0.16, marked 17; overrides in place for ngx-graph and jest-preset-angular peer deps.

### Phase 9: Ops and scripts

- **Scope:** `ops/` (all subdirs and root-level scripts)
- **Completed (date):** 2026-02-03
- **PII findings:** Seed emails in 001_seed_users.sql used @aio.local. **Fixed:** Replaced with @example.com. SAMPLE_CONTEXT in external_demo.py used real-looking IP ranges (175.45.176.0/22, 210.52.109.0/24) and enrichment example (185.193.141.248, Selectel/Moscow). **Fixed:** Use 192.0.2.0/24 and 192.0.2.1 with generic org/city. Placeholder IPs in 003_seed_use_cases.sql (192.168.1.100) replaced with 192.0.2.1 and example.com.
- **Over-logging findings:** external_demo.py logged username, response.text, request body prefix, and str(e). **Fixed:** Log "Authenticating with API" only; log status code only for auth/request/health failures; no request or response bodies; exception as type(e).**name**. verify_query_history.py printed token prefix. **Fixed:** "Authentication successful" only. verify_enhanced_metrics.py printed response.text on auth/API failure. **Fixed:** Status code and type(e).**name** only. verify_query_history HTTP error handler printed response.text. **Fixed:** Status only. reset_datastores.py hardcoded POSTGRES_PASSWORD. **Fixed:** Use os.environ.get with defaults; docstring notes env for production. Test-only passwords (adminpassword, test_password_123) in verify_* and init_test_environment.sh left as clearly test defaults; docs use <test-password> in examples.
- **Accuracy findings:** Many references to scripts/ (scripts/bootstrap/seed_users.py, scripts/migrations/runner.py, scripts/testing/*). **Fixed:** Updated to ops/ in external_demo, README, init_test_database.sh, reset_test_database.sh, init_test_environment.sh, demonstrate_enhanced_pipeline_fixed.py, rebuild_retrieval_service.sh. ops/README.md listed migrations/ and seed_phase1.py; actual layout is database/ with init/migrations/seed/. **Fixed:** Directory structure and key paths; seed via ops/database/seed/; migration runner/seed Python scripts may not exist under ops (fallback to SQL or doc). MIGRATION_SUMMARY.md stated password admin123; seed uses adminpassword. **Fixed:** "(test default, see seed)". rebuild_retrieval_service.sh referred to "Retrieval Service"; service is corpus_svc. **Fixed:** "Corpus service (corpus_svc)" and usage path ops/operations/.
- **Sign-off:** Phase 9 complete (2026-02-03).

### Phase 10: Tests

- **Scope:** `tests/` (all subdirs)
- **Completed (date):** 2026-02-03
- **PII findings:** Fixed example_threat_triage.yaml (<jdoe@corp.local>, <helpdesk@corp.local> → example.com). Fixed test_export_workflow.py and load_test.py (192.168.1.x → 192.0.2.1 TEST-NET-1).
- **Over-logging findings:** Replaced JWT secret "myTopsecretkey" with test placeholder in test_retrieval_endpoints, test_document_upload, test_document_processing_embedding. Removed prints of full response bodies, request payloads, error text, and exception messages; use status/counts and type(e).**name** only. Removed upload data dump from verify_endtoend_ingestion_flow.
- **Accuracy findings:** Updated README: "Retrieval" → "Corpus" for service name; reset_and_migrate_test_db.sh → reset_test_database.sh. Updated docstrings and print messages: "retrieval service" → "corpus service". Removed unnecessary cast() in benchmark_async_db and load/utils (typed variables instead).
- **Sign-off:** Phase 10 complete (2026-02-03).

### Phase 11a: Documentation — root, api, architecture, user-facing

- **Scope:** `docs/` root, admin, api, architecture, demo, deployment, operations, testing, user-guides
- **Completed (date):** 2026-02-04
- **PII findings:** PROJECT_OVERVIEW had "Document Owner: Alex". **Fixed:** "Project maintainer". Demo credentials (DEMO_CREDENTIALS.md) used @aio.local for all emails. **Fixed:** Replaced with @example.com. PRICING_MANAGEMENT audit example used admin@company.com. **Fixed:** admin@example.com. CISO presentation docs had "Presenter/Presented by: Alex" and "Role Split: Alex as Architect". **Fixed:** "Project team" and "Architect, AI as Developer". TEST_DATABASE_SETUP used PostgreSQL user "Alex". **Fixed:** Generic user "aio". Private/example IPs in api, user-guides, demo: 192.168.1.100, 192.168.45.123, 192.168.1.1, 45.123.45.67, 172.66.146.119, 10.0.1.50. **Fixed:** 192.0.2.x (TEST-NET-1) or 192.0.2.2/192.0.2.3 where multiple examples needed. STRUCTURED_OUTPUT_GUIDE had phishing@apt-group.ru. **Fixed:** phishing@example.com. Deployment and troubleshooting docs had absolute path /Users/Alex/Dev/ai_operations. **Fixed:** $PROJECT_ROOT.
- **Over-logging findings:** None (documentation only; no code logging in 11a scope).
- **Accuracy findings:** docs/README "configuration/" folder referenced but not present. **Fixed:** "deployment/ and operations/ - Setup and deployment guides".
- **Sign-off:** Phase 11a complete (2026-02-04). **Verification:** Two remaining items in 11a scope fixed: docs/api/template-management.md (path → $PROJECT_ROOT); docs/README.md folder diagram (configuration/ → deployment/, operations/; removed qodo/).

### Phase 11b: Documentation — development (adrs, plans, specs, guidelines)

- **Scope:** `docs/development/` adrs, analysis, architecture, guidelines, guides, migration, plans, specs, templates, testing, root .md
- **Completed (date):** 2026-02-04
- **PII findings:** Personal name "Alex" in Document Owner, Maintained By, Deciders, Changed By, Accepted By, Proposed By, Authors, Owner, and Participants. Absolute path `/Users/Alex/Dev/ai_operations` in analysis, guidelines, plans, and guides. Private IP examples 192.168.1.x in analysis, migration, plans. **Fixed:** All "Alex" → "Project team", "Development Team", "Architecture Team", "Product Owner", or "User" as appropriate. Paths → `$PROJECT_ROOT`. IPs → 192.0.2.x (TEST-NET-1). STYLING_GUIDE user-name placeholder "Alex" → "User". DOCUMENTATION_SYNC_REPORT Participants → "User, Assistant". iptables example 10.0.0.0/8 → 192.0.2.0/24.
- **Over-logging findings:** None (documentation only).
- **Accuracy findings:** None. Env vars, service names, and paths in reviewed docs match current code/config.
- **Sign-off:** Phase 11b complete (2026-02-04).

### Phase 11c: Documentation — sessions, completed, tasks, archive

- **Scope:** `docs/development/sessions/`, `docs/development/completed/`, `docs/development/tasks/`, `docs/development/reports/`, `docs/development/archive/`; `docs/archive/` (all subdirs).
- **Completed (date):** 2026-02-04
- **PII findings:** Personal name "Alex" in Document Owner, Session Owner, Author, Participants in sessions, completed, and tasks. Absolute paths `/Users/Alex/Dev/ai_operations` and `/Users/Alex/Dev/dfs_fusioncenter_assist` in sessions, reports, and docs/archive. **Fixed:** All "Alex" → "Project team", "User", or "project maintainer" as appropriate. Paths → `$PROJECT_ROOT`. Placeholder IP 192.168.1.100 in one session example → 192.0.2.1. **docs/archive:** "Alex" in documentation-review-oct2025/README (By), plan-reorganization-oct2025 (Approved By, Document Owner, REVIEW_THIS_FIRST title); internal path in qodo-troubleshooting-oct2025/rag_qa_fix_documentation. **Fixed:** Same substitutions; path → `$PROJECT_ROOT`. **docs/development/reports:** Two files had cd /Users/Alex/Dev/ai_operations paths. **Fixed:** `$PROJECT_ROOT`.
- **Over-logging findings:** None (documentation only).
- **Accuracy findings:** None. Env vars and service names in scope are consistent with code.
- **Sign-off:** Phase 11c complete (2026-02-04).

### Phase 12: IDE and tooling config

- **Scope:** `.cursor/` (agents, commands, context, memory, rules, skills, workflows, README), root dotfiles (`.cursorignore`, `.cursorrules`, `.clinerules`, `.dockerignore`, `.editorconfig`, `.eslintrc.json`, `.gitignore`, `.htmlhintrc`, `.htmlhintignore`, `.prettierignore`, `.prettierrc`), `.qodo/`
- **Completed (date):** 2026-02-04
- **PII findings:** reminders.md used absolute path `~/Dev/ai_operations/config/env/env.test`. **Fixed:** Use `source config/env/env.test` (run from project root). execute-task.md and reminders.md listed test passwords (adminpassword, analystpassword, password). **Fixed:** Replaced with placeholders and reference to config/env templates and ops/database/seed.
- **Over-logging findings:** None. No logging code in IDE/config scope. References to "no secrets" in rules/skills are guidance only.
- **Accuracy findings:** .clinerules referred to "Cline", Streamlit, /src/backend/, /scripts/migrations. **Fixed:** Title → "IDE / Assistant rules"; frontend → Angular and src/frontend-angular/; schemas/auth/LLM paths → generic src/{service}/app/ and shared/auth; migrations → ops/database/. .cursorrules referenced docs/UI_DEVELOPMENT_PLAN.md (missing). **Fixed:** docs/development/plans/ and MASTER_ROADMAP_V2.md or active phase. .cursor/README.md omitted agents/, commands/, skills/. **Fixed:** Directory structure and overview updated. production-ready.md referenced src/backend and run_tests.sh. **Fixed:** Backend steps made generic; tests → ops/testing/run_all_tests.py. documentation-organization.mdc and documentation-drift agent had docs/configuration/. **Fixed:** docs/deployment/, docs/operations/ (per Phase 11a).
- **Sign-off:** Phase 12 complete (2026-02-04).

---

## 8. Quick-Reference Checklist (Per Phase)

Use this for every phase; check each item before sign-off.

- [ ] All files in phase scope listed and reviewed.
- [ ] **PII sweep:** No real emails, names, hostnames, IPs, or org-specific identifiers; examples use placeholders.
- [ ] **Secrets sweep:** No hardcoded API keys, passwords, tokens; no secrets in comments or example configs.
- [ ] **Logging sweep:** No logging of request/response bodies, user input, or secrets without redaction (ADR-048 where applicable).
- [ ] **Accuracy:** Docstrings, READMEs, and docs match current code and config; env var names and paths correct.
- [ ] **Cast removal:** Unnecessary `cast()` removed; use typed variables (e.g. `data: dict[str, Any] = response.json()`) or fix types instead of `return cast(...)`.
- [ ] Findings recorded in Phase Log; issues fixed or accepted with rationale.
- [ ] Tests for touched code pass; linter errors in modified files resolved.
- [ ] Phase sign-off dated.

---

## 9. References

- **ADR-048:** Secure Logging with Configurable Redaction — `docs/development/adrs/ADR-048-Secure-Logging-Redaction.md`
- **.gitignore** — ensure all sensitive paths are excluded before publication.
- **Documentation organization** — `.cursorrules` / `docs/development/guidelines/DOCUMENT_ORGANIZATION_GUIDE.md` (if present).

### Pre-commit and lint (out of scope for this plan)

Pre-commit may fail with many **pre-existing** ruff and mypy errors (e.g. 376+ ruff, hundreds of mypy in ops/tests). These are tracked separately from the publication audit. **Update (Feb 2025):** Mypy has been fixed and re-enabled in pre-commit; use `SKIP=ruff` only if ruff still fails.

- **Activate the venv** before running pre-commit, ruff, or mypy:

  ```bash
  source venv/bin/activate   # macOS/Linux
  ```

- **Prefer `SKIP` over `--no-verify`:** To skip only the hooks that currently fail (mypy, ruff), run:

  ```bash
  SKIP=mypy,ruff git commit -m "your message"
  ```

  Trailing-whitespace, end-of-file-fixer, black, check-yaml, and other hooks still run. Only mypy and ruff are skipped, so you keep most of the benefit. Use `--no-verify` only if you must skip all hooks.
- **To commit without running failing hooks:** Use `SKIP=mypy,ruff git commit ...` (above) or `git commit --no-verify` if you need to skip everything. Ensure your changes are correct; run `ruff check` / `mypy` on changed paths when you want to validate.
- **Config fixes already applied:** `mypy.ini` — single-line exclude regex; exclude `tests/(integration|e2e)/conftest.py` and `src/.../tests/conftest.py` to avoid duplicate-module "conftest"; `explicit_package_bases = True`. `pyproject.toml` — removed unknown rule `PT028` so ruff parses.
- **Long-term (hooks pass without SKIP):** Fix the remaining ruff (~214 in src) and mypy (~885 in src after test override) errors in a dedicated pass. Then pre-commit will pass and you won't need `SKIP` or `--no-verify`. A mypy override for `src.*.tests.*` (disallow_untyped_defs = False) is already in mypy.ini to reduce test-file noise.
- **If you have hundreds of modified files** (e.g. from pre-commit or editor touching the whole repo): stage **only** the Phase 4 and config files, then commit; leave the rest unstaged. After committing, to discard the other changes: `git checkout -- .` (or `git restore .`).
- **Example commit (with venv active, only Phase 4 files staged):**

  ```bash
  source venv/bin/activate
  git add docs/development/plans/PUBLICATION_AUDIT_PLAN.md mypy.ini pyproject.toml \
    src/embedding/README.md src/embedding/app/config/models.py src/embedding/app/config/models.yaml \
    src/embedding/app/main.py src/embedding/app/providers/local.py src/embedding/app/providers/openai.py \
    src/embedding/app/routers/admin.py src/embedding/app/security.py \
    src/embedding/requirements.txt src/embedding/PHASE2_COMPLETION.md
  git commit -m "Complete Publication Audit Phase 4 (embedding service)" -m "..." # (or SKIP=mypy,ruff git commit ... if hooks fail)
  ```

---

**Document status:** Phases 1–12 complete. Draft for use during publication preparation.
**Last updated:** 2026-02-04.

---

## Appendix A: Directory-to-Phase Map (Complete)

| Directory or area | Phase |
|-------------------|-------|
| Root (README, pyproject, workspace, env_setup, etc.) | 1 |
| config/env/ (templates only) | 1 |
| config/models/ | 1 |
| deploy/ | 1 |
| src/shared/ | 2 |
| src/corpus_svc/ | 3 |
| src/embedding/ | 4 |
| src/inference-gateway/ | 5 |
| src/llm_guard_svc/ | 6 |
| src/orchestrator/ | 7 |
| src/frontend-angular/ | 8 |
| ops/bootstrap/, ops/ci/, ops/cli/, ops/database/, ops/operations/, ops/testing/, ops/*.py, ops/*.sh, ops/*.md | 9 |
| tests/benchmarks/, tests/e2e/, tests/fixtures/, tests/integration/, tests/load/, tests/mcp_compliance/, tests/unit/, tests/conftest.py, tests/README.md | 10 |
| docs/ (root .md), docs/admin/, docs/api/, docs/architecture/, docs/demo/, docs/deployment/, docs/operations/, docs/testing/, docs/user-guides/ | 11a |
| docs/development/adrs/, analysis/, architecture/, guidelines/, guides/, migration/, plans/, specs/, templates/, testing/, root .md | 11b |
| docs/development/sessions/, completed/, tasks/, reports/, archive/; docs/archive/ | 11c |
| .cursor/ (commands, context, memory, rules, workflows, README), .cursorignore, .cursorrules, .clinerules, .dockerignore, .editorconfig, .eslintrc.json, .gitignore, .htmlhintrc, .htmlhintignore, .prettierignore, .prettierrc, .qodo/ | 12 |
