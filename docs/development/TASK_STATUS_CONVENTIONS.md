# Task Status Conventions

**Created:** October 18, 2025
**Purpose:** Standardize status labels across all task documents

---

## Standard Status Labels

Use these emoji-prefixed status labels in all task documents:

### Planning & Preparation

- **`📋 PENDING`** - Task defined but not yet started (ready to start)
- **`🔍 INVESTIGATION REQUIRED`** - Need research/analysis before implementation
- **`❌ BLOCKED`** - Cannot start due to dependencies or issues
- **`⏸️ ON HOLD`** - Intentionally paused (specify reason)

### Active Work

- **`🔄 IN PROGRESS`** - Currently being worked on
- **`🧪 TESTING`** - Implementation complete, undergoing testing
- **`👀 REVIEW`** - Ready for code review or approval

### Completion

- **`✅ COMPLETE`** - Task finished and verified
- **`🗄️ ARCHIVED`** - Historical task, moved to completed/

### Special

- **`🚨 URGENT`** - High priority, needs immediate attention
- **`🔄 TO BE REVIEWED`** - Needs status assessment (ambiguous)

---

## Task Document Header Format

Every task document should have this header structure:

```markdown
# [Task ID]: [Task Title]

**Status:** [Status Label from above]
**Priority:** [High/Medium/Low or 🔴 CRITICAL/🟡 HIGH/🟢 MEDIUM]
**Estimated Effort:** [Time estimate]
**Assigned:** [Person or TBD]
**Created:** YYYY-MM-DD
**Updated:** YYYY-MM-DD
**Dependencies:** [List dependencies or None]

## Objective
[Clear statement of what needs to be done]
```

---

## Current Task Status Summary (October 18, 2025)

### Active Tasks (docs/development/tasks/)

| Task File | Current Status | Assessment | Action Needed |
|-----------|---------------|------------|---------------|
| P2_FIX_10_RLS_ENFORCEMENT.md | "Status: Ready" | Not started | Change to `📋 PENDING` |
| P2_FIX_11_DATABASE_PERFORMANCE_MONITORING.md | `🔄 **PENDING**` | Not started | Change to `📋 PENDING` |
| P2_FIX_13_TOKEN_COST_CALCULATION.md | `🔍 INVESTIGATION REQUIRED` | ✅ Good label | No change needed |
| P3-FIX-10-CSP-MONITORING-FALSE-POSITIVE.md | [Need to check] | TBD | Review needed |
| P3-PERF-01-LAZY-LOAD-LIBRARIES.md | `📋 PENDING` | ✅ Good label | No change needed |
| P3-PERF-02-BUNDLE-SIZE-BUDGETS.md | [Need to check] | TBD | Review needed |
| P3-PERF-03-ONPUSH-CHANGE-DETECTION.md | [Need to check] | TBD | Review needed |
| P3-REFACTOR-01-TEMPLATE-TO-UC-MGMT.md | `🔄 In Progress` | Oct 13 | Update timestamp if still active |
| TASK_001_API_CONTRACT_ALIGNMENT.md | "To Be Reviewed" | Ambiguous | Change to `🔄 TO BE REVIEWED` or assess |

---

## Status Transition Flow

```
📋 PENDING
    ↓
🔍 INVESTIGATION REQUIRED (if needed)
    ↓
🔄 IN PROGRESS
    ↓
🧪 TESTING
    ↓
👀 REVIEW
    ↓
✅ COMPLETE
    ↓
🗄️ ARCHIVED (moved to docs/development/completed/tasks/)
```

**Blocked tasks:** Any status can transition to `❌ BLOCKED` if dependencies fail

**On hold:** Any status can transition to `⏸️ ON HOLD` if paused

---

## Migration Plan

### Phase 1: Update Active Tasks (This Session)

1. Review each task in docs/development/tasks/
2. Apply standard status label
3. Update "Updated" timestamp
4. Document any status changes in git commit

### Phase 2: Update Completed Tasks (Future)

1. Ensure all completed tasks have `✅ COMPLETE` status
2. Verify they're in docs/development/completed/tasks/

### Phase 3: Update Plans (Future)

1. Add phase/feature status tracking to major plans
2. Use consistent status labels in UI_DEVELOPMENT_PLAN.md
3. Apply to USE_CASE_MANAGEMENT_PLAN.md and TOOLS_IMPLEMENTATION_PLAN.md

---

## Examples

### Good Example

```markdown
# P3-PERF-01: Lazy Load Heavy Third-Party Libraries

**Status:** 📋 PENDING
**Priority:** 🔴 CRITICAL
**Estimated Effort:** 4-6 hours
**Created:** 2025-10-13
**Updated:** 2025-10-13
**Dependencies:** None
```

### Needs Improvement

```markdown
# P2-FIX-10: Investigate and Fix RLS Enforcement

**Time:** 6 hours | **Impact:** Critical security - user isolation | **Status:** Ready
```

**Issue:** Using "Ready" instead of standard label, non-standard header format

**Should be:**

```markdown
# P2-FIX-10: Investigate and Fix RLS Enforcement

**Status:** 📋 PENDING
**Priority:** 🔴 CRITICAL
**Estimated Effort:** 6 hours
**Impact:** Security - user isolation
**Created:** [date]
**Updated:** [date]
**Dependencies:** None
```

---

## Usage in Git Commits

When updating task status, use this commit message format:

```
docs(tasks): Update [Task ID] status to [Status Label]

- Previous status: [Old Status]
- New status: [New Status]
- Reason: [Brief explanation]
```

Example:

```
docs(tasks): Update P3-PERF-01 status to 🔄 IN PROGRESS

- Previous status: 📋 PENDING
- New status: 🔄 IN PROGRESS
- Reason: Started implementation of lazy loading
```

---

## Reference Documents

- **Task Template:** `docs/development/templates/task-template.md`
- **Development Guidelines:** `docs/development/guidelines/DOCUMENTATION_GUIDELINES.md`
- **Review Report:** `docs/DOCUMENTATION_REVIEW_2025-10-18.md`

---

**Last Updated:** October 18, 2025
**Next Review:** When new task conventions are needed
