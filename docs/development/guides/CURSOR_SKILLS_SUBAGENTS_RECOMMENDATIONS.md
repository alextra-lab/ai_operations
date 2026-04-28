# Cursor Skills, Subagents, and Standards Recommendations

**Purpose:** Improve development efficiency, resource use, and code quality by adopting Agent Skills, Subagents, and fixing gaps in coding standards. Aligns with [Cursor Rules](https://cursor.com/docs/context/rules), [Skills](https://cursor.com/docs/context/skills), [Subagents](https://cursor.com/docs/context/subagents), and [Commands](https://cursor.com/docs/context/commands).

**Status:** Recommendations only. Implement incrementally.

**Project stack:** Angular frontend, FastAPI backend (no Streamlit).

---

## 1. Current State Summary

### What You Have

| Area | Location | Notes |
|------|----------|--------|
| **Project rules** | `.cursor/rules/` | Strong: Angular (general, template, testing, accessibility, performance), documentation-organization, general-reasoning, testing-rules |
| **Commands** | `.cursor/commands/` | execute-task, find-next-task, production-ready, update-plans, commit-code, reminders |
| **Legacy rules** | `.cursorrules` | Full project overview, security, Python/Frontend standards, docs taxonomy, scripts layout |
| **Guidelines** | `docs/development/guidelines/` | ANGULAR_DEVELOPMENT_GUIDELINES.md, DOCUMENTATION_GUIDELINES.md, etc. |
| **Context/memory** | `.cursor/context/`, `.cursor/memory/` | testing-context, testing-memory, testing-workflow |

### What You're Missing

- **No Skills** — `.cursor/skills/` does not exist. Skills are ideal for single-purpose, on-demand workflows (run tests, where to put docs, backend standards).
- **No Subagents** — `.cursor/agents/` does not exist. Subagents give context isolation and specialized behavior (verifier, test-runner, security).
- **No AGENTS.md** — No project-root or nested agent instructions as a simple alternative to rules.
- **Backend rules** — Python/FastAPI standards live only in `.cursorrules`; no dedicated rule or skill for `**/*.py` or backend paths.
- **Path inconsistency** — `.cursorrules` references `scripts/bootstrap/`, `scripts/testing/` while the repo uses `ops/bootstrap/`, `ops/testing/`. Docs and `.cursor` context use `ops/` consistently.

---

## 2. Recommended Skills

Skills are loaded on demand and keep context small. Create `.cursor/skills/<name>/SKILL.md` with YAML frontmatter (`name`, `description`).

| Skill | Description | When to use |
|-------|-------------|-------------|
| **run-tests** | Run the correct test command for this project (frontend: `npm test` in frontend-angular; backend/integration: `python ops/testing/run_all_tests.py` with optional `--coverage`, `--component`, `--fail-fast`). | User asks to run tests, verify after changes, or before commit. |
| **docs-where** | Where to create or move documentation (BUILD vs USE; `docs/development/` vs `docs/api/`, `docs/architecture/`). References `docs/development/guidelines/DOCUMENT_ORGANIZATION_GUIDE.md` and documentation-organization rule. | Creating or moving docs, or deciding doc location. |
| **backend-standards** | Python 3.12, type hints, PEP 8, Black/Ruff, structured JSON logging, `src/{service}/app/` layout, no secrets, LLM-Guard for external APIs. | Working in `src/backend/`, `src/retrieval/`, or any `**/*.py` outside tests. |
| **security-check** | Never read/modify `.env`, `**/config/secrets.*`, or credentials; validate input; no sensitive data in logs; reference project security section. | Any auth, config, or security-sensitive change. |
| **task-complete** | Task completion workflow: set status COMPLETED, move task to `docs/development/completed/tasks/`, add brief session log; do not create extra summary docs. | When a development task is done and user wants to close it out. |
| **create-adr** | Create Architecture Decision Records: use template `docs/development/adrs/template.md`, sequential numbering (NNN-kebab-case-title), place in `docs/development/adrs/`. Only for significant decisions (tech choice, security pattern, major refactor). References documentation-organization rule. | When documenting an architecture or technology decision that needs an ADR. |

**Suggested first skill:** `backend-standards` (backend has no dedicated rule file). Optional: `run-tests` to standardize test commands; `create-adr` when you adopt ADRs regularly.

---

## 3. Recommended Subagents

Subagents run in a separate context and are good for verification, test runs, and security review. Create `.cursor/agents/<name>.md` with YAML frontmatter (`name`, `description`, optional `model`, `readonly`).

| Subagent | Description | When to use |
|----------|-------------|-------------|
| **verifier** | **Functional verification only:** Run tests, check that implementations exist (no stubs where behavior was promised), report pass/fail. Does *not* do design or style review. Use `model: fast`. | After a task is marked done; "did it actually work?" |
| **second-opinion** | **Independent code review:** Design, readability, maintainability, alignment with project standards (e.g. .cursorrules, backend-standards, Angular rules), potential bugs or edge cases. Gives a fresh, critical pass over delivered code. Use when you want a 2nd set of eyes before merge or sign-off. | After code is delivered; "review this like a colleague would." |
| **test-runner** | Proactively runs the appropriate test suite for changed code (frontend vs backend vs integration), analyzes failures, and suggests fixes. | After code changes; "run tests and fix failures." |
| **security-auditor** | Reviews auth, secrets handling, input validation, and LLM-Guard usage. Use when touching login, RBAC, or external APIs. | Auth/RBAC, config, or security-sensitive features. |
| **documentation-drift** | Run **after** documentation is updated: verify accuracy vs code/reality, correct location and naming (docs/ taxonomy), valid links. Ensures no doc drift. | After creating or updating docs (api, architecture, guides, ADRs, etc.). |
| **plans** | Run **after** plans, specs, or tasks are updated: verify accuracy (status vs reality), correct location (plans/active|completed|future, tasks vs completed/tasks), naming, task-completion workflow, cross-references. | After creating or updating plans, specs, or tasks. |

**Verifier vs second-opinion:** The **verifier** answers "does it work?" (tests pass, no obvious gaps). The **second-opinion** subagent answers "is this good code?" (design, standards, maintainability, potential issues). Use both for delivered code: verifier first, then second-opinion for review.

**Suggested first subagents:** `verifier` for functional check; add `second-opinion` when you want independent review of delivered code.

---

## 4. Commands

Current commands are strong. Optional additions:

- **run-tests** — Quick prompt: "Run the full test suite (or frontend/backend) per project conventions and report results." Complements a possible run-tests skill.
- **docs-check** — "Given this doc topic, which folder and naming should it use? (BUILD vs USE; exact path)." Complements docs-where skill.

Not required if you add the corresponding skills and invoke them via `/run-tests` or `/docs-where`.

---

## 5. Coding Standards: Are They Clearly Defined and Used?

### Defined

- **.cursorrules:** Python 3.12, type hints, PEP 8, Black/Ruff, logging, file layout, scripts layout, testing structure, docs taxonomy, security.
- **.cursor/rules:** Angular (components, templates, testing, accessibility, performance), documentation organization, testing rules (paths, pytest, mocks, coverage).
- **docs/development/guidelines/ANGULAR_DEVELOPMENT_GUIDELINES.md:** TypeScript, Angular 21, Jest, ESLint/Prettier/HTMLHint/EditorConfig, OnPush, 80% coverage.

### Gaps and Fixes

1. **scripts/ vs ops/**
   **Issue:** `.cursorrules` says `scripts/bootstrap/`, `scripts/testing/`, etc. The repo uses `ops/` (e.g. `ops/testing/run_all_tests.py`).
   **Fix:** Update `.cursorrules` to use `ops/` paths so agents and docs match reality.

2. **Angular testing stack in rules**
   **Issue:** `.cursor/rules/angular-testing-guidelines.mdc` says "Jasmine and Karma" and "Protractor or Cypress." The project uses **Jest** (`package.json`: `"test": "jest"`) and `jest-preset-angular`.
   **Fix:** Update angular-testing-guidelines.mdc to reference Jest (and E2E tooling you actually use, e.g. Playwright if applicable).

3. **Backend-specific rule**
   **Issue:** No rule with `globs: **/*.py` or scoped to `src/backend/`, so backend standards are only in the long .cursorrules.
   **Fix:** Add a `backend-standards.mdc` rule (or a `backend-standards` skill) that encodes Python/FastAPI standards and is applied when working on backend code.

4. **Single source of truth for test commands**
   **Issue:** Test runner paths appear in .cursorrules, testing-rules.md, execute-task, production-ready, and various docs; some say `scripts/testing/`, most use `ops/testing/`.
   **Fix:** Standardize on `ops/testing/` everywhere and add one skill or command that documents the canonical commands (e.g. `python ops/testing/run_all_tests.py`, `npm test` in frontend).

---

## 6. Implementation Priority

1. **Quick fixes (no new directories)**
   - Update `.cursorrules`: change `scripts/` → `ops/` for bootstrap, ci, cli, operations, testing, migrations.
   - Update `.cursor/rules/angular-testing-guidelines.mdc`: Jasmine/Karma → Jest; align E2E with actual tooling.

2. **First skill**
   - Add `.cursor/skills/backend-standards/SKILL.md` with project Python/FastAPI and security rules (extracted from .cursorrules).
   - Optional: add `run-tests` skill with exact commands for frontend and backend/integration.

3. **First subagent**
   - Add `.cursor/agents/verifier.md` to verify completed work (run tests, report pass/fail, note incomplete parts).

4. **Then**
   - Add `docs-where`, `task-complete`, and `create-adr` skills if you often create docs, close tasks, or record architecture decisions.
   - Add `second-opinion` subagent for independent code review of delivered code.
   - Add **`documentation-drift`** subagent: run after documentation updates to verify accuracy and proper storage.
   - Add **`plans`** subagent: run after plans/specs/tasks updates to verify accuracy and proper storage (status, locations, task-completion workflow).
   - Add `test-runner` and `security-auditor` subagents if you want proactive test runs or security reviews.

---

## 7. References

- [Cursor Rules](https://cursor.com/docs/context/rules)
- [Agent Skills](https://cursor.com/docs/context/skills)
- [Subagents](https://cursor.com/docs/context/subagents)
- [Commands](https://cursor.com/docs/context/commands)
- Project: `.cursorrules`, `.cursor/rules/`, `docs/development/guidelines/`, `docs/testing/SCRIPT_INDEX.md`
