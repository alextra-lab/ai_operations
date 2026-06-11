---
name: aio-doc-governance
description: >
  Documentation governance skill for the ai_operations repo. Invoke this skill BEFORE creating
  or updating ANY file under docs/, or any README in src/*/. Covers where to place new docs
  (ADRs, plans, specs, tasks, guides, analysis, session logs), the ADR authoring process (next
  number, template, index update), the plan lifecycle (active/future/completed folders), task
  completion workflow, and the hard rules about what NOT to create. Trigger on phrases like:
  "create an ADR", "write a plan", "add documentation", "where should I put this doc",
  "write a spec", "create a task file", "add a guide", "log this session", "update the docs
  index", or any time a Write/Edit tool is about to be used on a file inside docs/ or a
  src/*/README.md. When in doubt, invoke this skill — it's faster than re-reading the source
  governance files.
---

# ai_operations Documentation Governance

Source of truth: `.cursorrules`, `.cursor/rules/documentation-organization.mdc`,
`docs/development/guidelines/DOCUMENTATION_GUIDELINES.md`,
`docs/development/guidelines/DOCUMENT_ORGANIZATION_GUIDE.md`,
`docs/development/adrs/template.md`

---

## Core principle

> `docs/development/` = **BUILD** the app.  All other `docs/` folders = **USE/OPERATE** the app.

- `docs/` is the single source of truth. **Update existing docs over creating new ones.**
- Nothing at `docs/` root except `README.md`.
- No verbose completion summaries — use a brief session log instead.
- Never duplicate information across files.

---

## Routing table

| What you are creating | Location | Naming convention |
|---|---|---|
| Architecture decision record | `docs/development/adrs/` | `ADR-NNN-kebab-case-title.md` |
| Implementation plan / roadmap | `docs/development/plans/` | `[NAME]_PLAN.md` |
| Feature spec / requirements | `docs/development/specs/` | `feature-name-spec.md` |
| Active task | `docs/development/tasks/` | `PX_FIX_XX_DESCRIPTION.md` |
| Completed task | `docs/development/completed/tasks/` | same file, add `Status: COMPLETED (YYYY-MM-DD)` |
| Technical investigation / gap analysis | `docs/development/analysis/` | `descriptive-name.md` |
| How-to guide (step-by-step, dev-facing) | `docs/development/guides/` | `topic-guide.md` |
| Coding standard / convention | `docs/development/guidelines/` | `PATTERN_NAME.md` |
| Work session log | `docs/development/sessions/` | `YYYY-MM-DD-brief-description.md` |
| Feature-level architecture detail | `docs/development/architecture/` | `FEATURE_ARCHITECTURE.md` |
| API contract (for integrators) | `docs/api/` | |
| System-wide architecture (cross-cutting) | `docs/architecture/` | |
| Test procedures / guides | `docs/testing/` | |
| Deployment / ops guide | `docs/deployment/` or `docs/operations/` | |
| Historical / superseded | `docs/archive/` | add archive date prefix |

**Decision shortcut:** Building the app? Use `docs/development/` and pick the sub-folder.
Using or operating the app? Use `docs/api/`, `docs/architecture/`, `docs/testing/`, `docs/operations/`.

---

## ADR process

1. **Find the next clean number:**
   ```bash
   ls docs/development/adrs/ADR-*.md | sort -V | tail -5
   ```
   Note: duplicate files exist for ADR-052 and ADR-053 (tracked by AIO-31). Skip past any
   duplicates. As of 2026-05-30 the last authored ADR is ADR-074, so the next is **ADR-075**.

2. **Use the template** at `docs/development/adrs/template.md` (Nygard format):
   Context / Decision / Alternatives Considered / Consequences / Implementation Notes /
   References / Status Updates

3. **Status lifecycle:** `Proposed` -> `Accepted` -> (if superseded) `Superseded`/`Deprecated`

4. **Update `docs/development/adrs/README.md`:**
   - Add to the relevant section (Security, Database, Architecture, Deployment & Operations, etc.)
   - Add to the "Index by Status" list
   - Add a "Recent Additions" entry (date, number, title, 3-5 bullet summary)

5. **Update `docs/README.md` nav** if the decision is significant.

---

## Plan lifecycle

```
plans/
  active/      <- one phase plan at a time (current work)
  future/      <- upcoming phases
  completed/   <- finished phases
  features/    <- feature specs (active/ and completed/)
  [root]       <- cross-cutting plans (e.g. BUILD_BOOTSTRAP_PLAN.md)
```

Phase transitions: `future -> active` when work starts, `active -> completed` when done.
Always update `MASTER_ROADMAP_V2.md` on transitions.

Commit message: `docs: Update PHASE_XX progress - [milestone]`

---

## Task completion workflow

1. Add `Status: COMPLETED (YYYY-MM-DD)` to task file header.
2. Move file: `docs/development/tasks/` -> `docs/development/completed/tasks/`
3. Add a brief entry to that day's session log.
4. Update related plans/guides if an interface or process changed.

---

## Session log format (max 50 lines)

```markdown
# Development Session - YYYY-MM-DD
**Focus:** [brief description]   **Status:** Complete / In Progress

## Work Completed
- [Task] (files: a.py, b.py)
- Tests: XX/XX passing

## Key Decisions
- [Chosen approach and why]

## Next Steps
- [What comes next]
```

---

## DO NOT create

- Verbose completion summaries after finishing work (use brief session log instead)
- Multiple meta-documents on the same topic (update the existing one)
- Anything at `docs/` root other than README.md
- Separate "migration log", "implementation summary", or "verification report"
- New folders inside `docs/development/` without a clear gap

---

## Quick pre-write checklist

1. Does a doc on this topic already exist? -> Update it.
2. Building the app or using it? -> Pick the right root.
3. Use the routing table above to confirm folder + naming.
4. For ADRs: verify next clean number before writing.
5. After writing: update `docs/README.md` nav (if significant) and the relevant index.
