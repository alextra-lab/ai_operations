# Security Remediation Plan (Dependencies + CodeQL)

Status: ✅ FULLY COMPLETE — 2026-05-30
Date: 2026-05-30
Repo: `github.com/alextra-lab/ai_operations` (local: `~/Dev/github/ai_operations`)
Companion context: `docs/development/SECURITY_REMEDIATION_HANDOFF.md`

## Goal
Clear the security backlog on the GitHub repo: dependency vulnerabilities (Dependabot) and code
scanning findings (CodeQL), keeping the current per-service structure and the wheelhouse.

## Final state (live, verified 2026-05-30)
- Dependency vulnerabilities: 0 ✅
- CodeQL findings: 0 open ✅ (2 auto-closed on scan after code fix; 9 dismissed via API)
- Open PRs: 0 ✅
- `webpack-dev-server` dev alert resolved via npm-prod group merge.

## Scope decisions (confirmed with user)
- Tactical; keep per-service `requirements.txt` + root aggregators + wheelhouse.
- Air-gapped = nice-to-have: keep + regenerate caches, do not re-architect.
- Keep Dependabot (add `groups`); no Renovate; no uv-workspace migration.

---

## DONE - Dependency phase (Dependabot PR triage)
- Merged the safe security PRs (mermaid, dompurify, fast-uri, lodash, @angular/core+compiler, ajv,
  uuid, python-dotenv, black, dev-dep chain). Dep alerts 98 -> 1, PRs 48 -> 13.

## COMPLETED STEPS

### Step 1 ✅ - CodeQL P0: injection vulns
- SQL injection (10): already parameterized via `text()` + bound params before this session (PR #55).
- Path injection (2): fixed in PR #55 (`src/embedding/app/config/models.py` basename-only allowlist).

### Step 2 ✅ - CodeQL: log redaction + error handling
- Code fixes (PR #76): `intent_parser.py` — removed config dict from log; `tools_testing.py` —
  `ValueError` handler now returns `GENERIC_CLIENT_ERROR` instead of raw `str(e)`.
- Dismissed via GitHub API (false-positive / won't-fix): `response_formatter.py` (non-sensitive
  config params), `setup_test_database.py` logging (DB name, not password), `setup_test_database.py`
  + `setup_test_user.py` env-file writes (intentional test setup), `test_tool_result_processor.py`
  (test assertion on hardcoded URL).

### Step 3 ✅ - CodeQL: frontend
- All JS findings (insecure randomness, incomplete sanitization) were resolved in PR #55.

### Step 4 ✅ - Remaining dependency alerts
- All dependency alerts cleared via Dependabot PR triage + merges.

### Step 5 ✅ - Deferred PRs
- All 20 open Dependabot PRs triaged: 15 merged, 4 closed as superseded, 2 closed pending
  TypeScript 6 support in Angular build tooling (will resurface automatically).

### Step 6 ✅ - Prevent regression
- `groups` already present in `.github/dependabot.yml` for npm; pip groups added.
- Per-service pip Dependabot entries removed — root entry handles all services via `-r` includes,
  preventing cross-service pin conflicts. See Dependency_Management.md for rationale.

## Out of scope
- uv workspace migration; removing/replacing the wheelhouse; switching to Renovate.
