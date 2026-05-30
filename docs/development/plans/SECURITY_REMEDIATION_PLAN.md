# Security Remediation Plan (Dependencies + CodeQL)

Status: COMPLETED locally — pending push + GitHub CodeQL rescan
Date: 2026-05-30
Repo: `github.com/alextra-lab/ai_operations` (local: `~/Dev/github/ai_operations`)
Companion context: `docs/development/SECURITY_REMEDIATION_HANDOFF.md`

## Goal
Clear the security backlog on the GitHub repo: dependency vulnerabilities (Dependabot) and code
scanning findings (CodeQL), keeping the current per-service structure and the wheelhouse.

## Current state (live)
- Dependency vulnerabilities: 1 (`webpack-dev-server`, medium, dev-only).
- CodeQL findings: 61 (51 high, 10 medium) - NOT YET ADDRESSED.
- Open PRs: 13 (all deferred risky majors).

## Scope decisions (confirmed with user)
- Tactical; keep per-service `requirements.txt` + root aggregators + wheelhouse.
- Air-gapped = nice-to-have: keep + regenerate caches, do not re-architect.
- Keep Dependabot (add `groups`); no Renovate; no uv-workspace migration.

---

## DONE - Dependency phase (Dependabot PR triage)
- Merged the safe security PRs (mermaid, dompurify, fast-uri, lodash, @angular/core+compiler, ajv,
  uuid, python-dotenv, black, dev-dep chain). Dep alerts 98 -> 1, PRs 48 -> 13.

## REMAINING

### Step 1 - CodeQL P0: injection vulns (12 high) [DO FIRST]
- SQL injection (10): parameterize SQL (SQLAlchemy bound params / `text()` with `:params`) in:
  - `src/corpus_svc/app/routers/analytics.py` lines 63, 117, 170, 186, 206, 234
  - `src/inference-gateway/app/routers/admin.py` lines 1140, 1235, 1303, 1357
  - Add a regression test per fixed endpoint where feasible.
- Path injection (2): validate/normalize path in `src/embedding/app/config/models.py` lines 181-183;
  restrict to an allowlisted base dir; reject `..`/absolute traversal.

### Step 2 - CodeQL: log redaction + error handling
- Clear-text logging (23) + storage (2): redact secrets/tokens/PII before logging (mask values, log
  keys only) - `src/orchestrator/app/services/secrets_manager.py` (7), `ops/testing/setup_test_database.py`
  (6), `src/orchestrator/app/orchestrator/response_formatter.py` (2), `ops/test_openai_key.py` (2),
  `src/shared/config/secrets.py`, `src/orchestrator/app/services/tool_service.py`,
  `src/orchestrator/app/orchestrator/llm_router.py`, `src/orchestrator/app/orchestrator/intent_parser.py`,
  `src/embedding/app/security.py`, `src/embedding/app/providers/openai.py`.
- Stack-trace exposure (9): catch exceptions, return generic client errors, log detail server-side
  only - `src/orchestrator/app/routers/tools_testing.py` (4), `.../routers/orchestrator.py`,
  `src/inference-gateway/app/routers/admin.py`, `src/inference-gateway/app/main.py`,
  `src/embedding/app/main.py`, `src/corpus_svc/app/routers/analytics.py`.
- Note: `ops/` test-script logging may be acceptable to dismiss as false-positive with rationale.

### Step 3 - CodeQL: frontend
- Insecure randomness (7): replace `Math.random()` with `crypto.getRandomValues()` /
  `crypto.randomUUID()` in `src/frontend-angular/src/app/services/session-storage.service.ts` (4),
  `.../pages/conversations/conversation.component.ts` (2),
  `.../pages/use-case-execution/use-case-execution.component.ts` (1).
- Incomplete sanitization (8): replace the hand-rolled regex sanitizer in
  `src/frontend-angular/src/app/core/security/xss-protection.service.ts` (lines 18, 183, 224, 256,
  263, 271) with DOMPurify (already a dep) + Angular `DomSanitizer`; fix the URL-scheme allowlist.
  Also `src/frontend-angular/src/app/components/llm-content-renderer/llm-content-renderer.component.ts`
  line 765.

### Step 4 - Remaining dependency alert
- Resolve `webpack-dev-server` (dev-only): await/trigger Dependabot PR or bump
  `@angular-devkit/build-angular` / add npm `override`.

### Step 5 - Decide the 13 deferred PRs
- Per-PR: build + test, then merge or close. Risky majors: python 3.14 base images
  (#23/30/32/33/36), @testing-library/angular 17->19 (#35), fastapi (#29), ng2-charts 5->10 (#27),
  redis (#26), starlette 1.0 (#24), numpy (#21), packaging (#7), node 25-alpine (#1).

### Step 6 - Prevent regression (CI + Dependabot)
- Add CI `security` job (`pip-audit` + `npm audit --audit-level=high`); ensure CodeQL runs on PRs.
- Add `groups` to `.github/dependabot.yml` (npm dev / npm prod / Angular; pip) to stop PR sprawl.
- Optional: fix stale paths in `ops/ci/*.sh` and wire Trivy image scan into CI.

### Step 7 - Verify + document
- Re-check `gh api .../dependabot/alerts?state=open` and `.../code-scanning/alerts?state=open` -> ~0.
- Run frontend build/tests + Python tests for touched services (corpus_svc, inference-gateway,
  embedding, orchestrator).
- Session log in `docs/development/sessions/`; record any CodeQL alerts dismissed as false-positive.

## Out of scope
- uv workspace migration; removing/replacing the wheelhouse; switching to Renovate.
