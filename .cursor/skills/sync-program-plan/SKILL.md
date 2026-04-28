---
name: sync-program-plan
description: Sync the MASTER_PROGRAM_PLAN.md status section with live Linear data. Use when asked to update plan status, check program progress, or reconcile the markdown plan with Linear.
---

# Sync Program Plan

Refresh the **Status** section of the master program plan by querying live
Linear data and updating the markdown file.

## When to Use

- User asks to sync, refresh, or update the program plan status
- Before or after a program review meeting
- After completing a batch of Linear issues

## Source of Truth Rules

| Concern | Source of Truth |
|---|---|
| Program vision, streams, milestones, ADR traceability, open questions | `docs/development/plans/MASTER_PROGRAM_PLAN.md` |
| Issue status, assignees, dates, blockers, acceptance criteria | Linear (filter: `label:AIO`) |

Never duplicate issue-level details into the markdown.
Never change stream/milestone structure based solely on Linear state.

## Instructions

### 1. Gather Linear State

For each of the 7 AIO projects, query issues and their statuses:

```
CallMcpTool server=plugin-linear-linear toolName=list_issues
  arguments: { "label": "AIO", "project": "<project-name>", "limit": 50 }
```

The 7 project names (use these exact strings):
- `AIO - RBAC V2 Completion`
- `AIO - Platform Stabilization and Demos`
- `AIO - Use Case Authoring Polish`
- `AIO - Quality Engineering`
- `AIO - User Documentation`
- `AIO - Database and Configuration`
- `AIO - Agentic AI and Future Features`

Also fetch each project's status:

```
CallMcpTool server=plugin-linear-linear toolName=get_project
  arguments: { "query": "<project-name>" }
```

### 2. Compute Progress

For each project, count:
- **Total issues** in the project
- **Done issues** (state type = "completed" or state name = "Done")
- **Project status** from `get_project` result (e.g., Backlog, Planned, In Progress, Completed)

Note any issues in "In Progress" or "In Review" states for the Notes column.

### 3. Update the Markdown

Open `docs/development/plans/MASTER_PROGRAM_PLAN.md` and update the
`## Status (last synced: ...)` section:

1. Replace the date with today's date in `YYYY-MM-DD` format.
2. For each row in the status table, update:
   - **Project Status** from the `get_project` response
   - **Done / Total** with the computed counts
   - **Notes** with brief context (active work, blockers, or key changes)

### 4. Flag Drift

After updating status, check for drift:
- If Linear has issues not traceable to a milestone in the markdown, warn the user.
- If a milestone in the markdown has no corresponding Linear issues, warn the user.
- If a project status suggests completion but the markdown still lists open questions, flag it.

Report drift findings as a short summary after the update.

## Example Output

After running, tell the user:

> Updated Status section in MASTER_PROGRAM_PLAN.md (synced 2026-03-15).
> - S1: 2/3 done (In Progress)
> - S4: 3/7 done, 2 in review
> - No drift detected.

## File Paths

- Plan: `docs/development/plans/MASTER_PROGRAM_PLAN.md`
- Linear filter: label `AIO`
- Team: `FrenchForest`
