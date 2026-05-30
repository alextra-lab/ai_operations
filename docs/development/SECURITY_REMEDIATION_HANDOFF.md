# Security Remediation - Context Handoff

Date: 2026-05-30
Author: Cursor agent (handoff to a fresh session in this repo)
Repo this applies to: `github.com/alextra-lab/ai_operations` (local: `~/Dev/github/ai_operations`)

> Purpose: This is a complete context dump so a new agent opened in THIS repo can continue
> without re-deriving anything. The companion plan is at
> `docs/development/plans/SECURITY_REMEDIATION_PLAN.md`.

---

## 0. Repo situation (important)

Two local clones of the same code exist; they are **byte-identical** for all dependency/CI
files but have different remotes and commit history:

- `~/Dev/ai_operations` -> remote `git@gitlab.com:frenchforest/ai_operations.git` (GitLab). NOT the target.
- `~/Dev/github/ai_operations` -> remote `git@github.com:alextra-lab/ai_operations.git` (GitHub). **THIS is the target** - all alerts/PRs live here.

All analysis below was performed against the live GitHub repo via `gh` CLI (authenticated as
`alextra-lab`, token scopes include `repo`). The local source files used for code locations are
identical across both clones.

---

## CURRENT STATE (live, verified 2026-05-30)

| Category | Count | Notes |
|----------|-------|-------|
| Dependency vulnerabilities (Dependabot) | **1** | `webpack-dev-server` (medium, dev-only) in `src/frontend-angular/package-lock.json` |
| Code scanning (CodeQL) | **61** | UNTOUCHED - this is the remaining work |
| Open PRs | **13** | All deferred "risky major" bumps - see section 2 |

### Progress already made this session
The safe Dependabot security PRs were reviewed and merged, taking dependency alerts from
**98 -> 1** and open PRs from **48 -> 13**. The merged PRs covered all the runtime npm advisories
(dompurify, mermaid, lodash, @angular/core+compiler, ajv, fast-uri, uuid) and the bulk of the dev
tooling, plus the pip fixes (python-dotenv, black).

**The single remaining dependency alert** is `webpack-dev-server` (dev-only, medium). It likely
needs an `@angular-devkit/build-angular` bump or an override; confirm whether a Dependabot PR will
cover it or hand-fix.

## 1. Historical starting point (for reference)

The work began at ~160 total = 98 Dependabot dependency vulnerabilities + 61 CodeQL findings.

### A. 98 Dependabot dependency vulnerabilities (now 1 - see Current State above)
Severity at start: 2 critical, 40 high, 51 medium, 5 low. 95 npm + 3 pip. Resolved by merging the
safe Dependabot PRs.

### B. 61 open CodeQL code-scanning findings (51 high, 10 medium)
These need MANUAL source code fixes. No PRs exist for them. Tool = CodeQL.

| Rule | Count | Severity | Locations |
|------|-------|----------|-----------|
| py/sql-injection | 10 | high | `src/corpus_svc/app/routers/analytics.py` lines 63,117,170,186,206,234 (6); `src/inference-gateway/app/routers/admin.py` lines 1140,1235,1303,1357 (4) |
| py/clear-text-logging-sensitive-data | 23 | high/med | `src/orchestrator/app/services/secrets_manager.py` (7); `ops/testing/setup_test_database.py` (6); `src/orchestrator/app/orchestrator/response_formatter.py` (2); `ops/test_openai_key.py` (2); `src/shared/config/secrets.py` (1); `src/orchestrator/app/services/tool_service.py` (1); `src/orchestrator/app/orchestrator/llm_router.py` (1); `src/orchestrator/app/orchestrator/intent_parser.py` (1); `src/embedding/app/security.py` (1); `src/embedding/app/providers/openai.py` (1) |
| py/stack-trace-exposure | 9 | high | `src/orchestrator/app/routers/tools_testing.py` (4); `src/orchestrator/app/routers/orchestrator.py` (1); `src/inference-gateway/app/routers/admin.py` (1); `src/inference-gateway/app/main.py` (1); `src/embedding/app/main.py` (1); `src/corpus_svc/app/routers/analytics.py` (1) |
| py/path-injection | 2 | high | `src/embedding/app/config/models.py` lines 181, 183 |
| py/clear-text-storage-sensitive-data | 2 | med | (locations not yet pulled - query CodeQL alerts API) |
| py/incomplete-url-substring-sanitization | 1 | med | (locations not yet pulled) |
| js/insecure-randomness | 7 | high | `src/frontend-angular/src/app/services/session-storage.service.ts` (4); `src/frontend-angular/src/app/pages/conversations/conversation.component.ts` (2); `src/frontend-angular/src/app/pages/use-case-execution/use-case-execution.component.ts` (1) |
| js/incomplete-multi-character-sanitization | 3 | med | `src/frontend-angular/src/app/core/security/xss-protection.service.ts` lines 183, 263, 271 |
| js/incomplete-url-scheme-check | 2 | med | `src/frontend-angular/src/app/core/security/xss-protection.service.ts` lines 224, 256 |
| js/incomplete-html-attribute-sanitization | 1 | med | `src/frontend-angular/src/app/components/llm-content-renderer/llm-content-renderer.component.ts` line 765 |
| js/bad-tag-filter | 1 | med | `src/frontend-angular/src/app/core/security/xss-protection.service.ts` line 18 |

**P0 (true exploitable vulns): the 10 SQL-injection + 2 path-injection findings.**

---

## 2. The 13 remaining open PRs (all deferred risky majors - decide per-PR, do NOT blind-merge)

These are NOT security fixes; they are major/risky bumps Dependabot raised. Each needs a build/test
before merging, or should be closed if unwanted.

- Docker base image `python -> 3.14-slim`: #36 (llm_guard), #33 (embedding), #32 (orchestrator),
  #30 (corpus_svc), #23 (inference-gateway). Big jump (services on 3.11/3.12); verify wheelhouse +
  all deps build on 3.14 first.
- #35 @testing-library/angular 17 -> 19 (major, dev/test)
- #29 fastapi >=0.117.1 -> >=0.136.1 (orchestrator)
- #27 ng2-charts 5 -> 10 (major, frontend runtime)
- #26 redis >=5.0.0 -> >=7.4.0 (inference-gateway)
- #24 starlette >=0.48.0 -> >=1.0.0
- #21 numpy <2.0.0 -> <3.0.0 (orchestrator)
- #7 packaging >=23.0,<24.0 -> >=26.2,<27.0 (llm_guard)
- #1 node 24-alpine -> 25-alpine (frontend Docker)

### Remaining dependency alert (1) - separate from the PRs above
`webpack-dev-server` (medium, dev-only). Check for/await a Dependabot PR, or bump
`@angular-devkit/build-angular` / add an npm `override`.

---

## 3. Decisions already made with the user

- Scope: TACTICAL first. Keep current structure (per-service `requirements.txt`, root aggregators).
- Air-gapped deployment: nice-to-have, not mandatory -> KEEP the wheelhouse + npm cache; regenerate
  after bumps; do NOT re-architect.
- Dependency automation: KEEP Dependabot (add `groups` config). Do NOT switch to Renovate.
- Explicitly OUT OF SCOPE: uv-workspace migration across the 6 services; removing/replacing the
  wheelhouse. (The original proposal to do these would have addressed ~1 of 159 alerts.)
- Sequencing: Dependabot PR triage is DONE (98 -> 1 alert, 48 -> 13 PRs). **NEXT WORK = the 61
  CodeQL fixes, P0 injection first** (10 SQL-injection + 2 path-injection). The 13 leftover PRs are
  deferred majors to decide on separately.

---

## 4. Repo facts relevant to fixes

- 6 services under `src/`: `orchestrator`, `corpus_svc`, `embedding`, `llm_guard_svc`,
  `inference-gateway` (FastAPI) + `frontend-angular` (Angular 21). Shared lib: `src/shared`.
- DB access uses SQLAlchemy. SQL-injection fixes -> use bound params / `text()` with `:params`.
- DOMPurify is already a frontend dependency -> use it (plus Angular `DomSanitizer`) to replace the
  hand-rolled regex sanitizer in `xss-protection.service.ts`.
- CI: GitHub Actions only (`.github/workflows/ci.yml`, `license-scan.yml`). Lint/test steps use
  `|| true` (non-gating). No vuln scanning in CI today. CodeQL scanning IS enabled (alerts exist).
- Dependabot config: `.github/dependabot.yml` (pip per-service, npm, docker, github-actions; no `groups` yet).
- Dockerfiles install only each service's own `requirements.txt` from the wheelhouse then delete it,
  so image scanners only see installed deps (the wheelhouse does NOT inflate per-image alert counts).

---

## 5. Useful commands for the next agent

```bash
# Open dependency alerts (98)
gh api -X GET "repos/alextra-lab/ai_operations/dependabot/alerts?state=open&per_page=100" --paginate > /tmp/dbalerts.json

# Open code-scanning alerts (61) - pull missing locations for clear-text-storage / url-substring
gh api -X GET "repos/alextra-lab/ai_operations/code-scanning/alerts?state=open&per_page=100" --paginate > /tmp/csalerts.json

# Open Dependabot PRs (48)
gh pr list --repo alextra-lab/ai_operations --state open --limit 200 --json number,title,headRefName,mergeable,mergeStateStatus

# Per-PR CI status
gh pr checks <number> --repo alextra-lab/ai_operations
```
