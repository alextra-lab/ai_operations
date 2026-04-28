Update plans for: [TASK_ID]
Date: [YYYY-MM-DD]

## 1. MASTER_ROADMAP (Single Source of Truth)

docs/development/plans/MASTER_ROADMAP_V2.md

- Update phase completion %
- Update last milestone date
- Mark task status (✅/🔄/⏳/❌/📋)

## 2. ACTIVE PHASE FILE

docs/development/plans/active/PHASE_XX_*.md

- Update task status
- Update progress %
- Update remaining work

## 3. RELATED DOCUMENTS (Auto-detect from cross-references)

- Tasks: development/tasks/*.md → development/completed/tasks/*.md
- Specs: development/specs/*.md (update status if referenced)
- Features: development/plans/features/active/*.md → features/completed/*.md
- ADRs: development/adrs/*.md (reference only, no changes)

## 4. TASK LIFECYCLE (If task file exists)

- Move: development/tasks/[TASK_ID].md → development/completed/tasks/[TASK_ID].md
- Update header: "Status: ✅ COMPLETED (YYYY-MM-DD)"
- Add completion summary if missing

## 5. SESSION LOG

- Create: development/sessions/YYYY-MM-DD-[description].md
- Keep under 200 lines
- Link to completed task

## 6. VERIFICATION

- Confirm all cross-references valid (grep task ID across docs/)
- Verify phase completion % matches completed tasks
- Check no orphaned tasks in development/tasks/
- Validate status consistency across all related docs
- List all files modified for review

Wait for APPLY command.
