# Task: Fix Seed Use Cases Configuration Bugs

**Status:** ✅ COMPLETED (2025-01-11)
**Date Created:** 2025-01-11
**Date Completed:** 2025-01-11
**Priority:** HIGH
**Part of:** DATABASE_REFRESH_PLAN (db-refresh-003)
**Related Files:**
- `ops/database/seed/003_seed_use_cases.sql`
- `ops/database/seed/009_seed_draft_use_cases.sql`

---

## Executive Summary

The seeded use cases in `003_seed_use_cases.sql` and `009_seed_draft_use_cases.sql` do not display correctly in the UI due to configuration schema mismatches. The `config_json` structure in the seed files does not match the expected Pydantic schema (`UseCaseConfig`), causing validation errors or missing fields.

---

## Problem Statement

### User-Reported Issue

Seeded use cases do not display completely/correctly in the UI. The RAG collection and parameters appear incomplete or missing.

### Root Cause Analysis

Comparison of a working use case (created via UI wizard) vs seeded use cases revealed multiple schema mismatches:

#### ✅ Working Use Case (Created via Wizard)

```json
{
  "config_json": {
    "models": { "llm": "openai/gpt-oss-120b" },
    "generation_params": {
      "sampling_preset": "balanced",
      "frequency_penalty": 0,
      "presence_penalty": 0
    },
    "rag": {
      "enabled": true,
      "top_k": 10,
      "similarity_threshold": 0.6,
      "vector_collections": ["documents"],
      "metadata_filters": {},
      "tags": [],
      "hybrid_bm25": true
    },
    "policy": {
      "streaming_enabled": true,
      "streaming_default": false,
      "history_persistence": true,
      "pii_redaction": "anonymize"
    },
    "output_contract": {
      "format": "text",
      "output_schema": null,              ← CORRECT: output_schema
      "validation_mode": "best_effort"
    },
    "tools_allowlist": [],
    "tool_restrictions": null,            ← PRESENT
    "visibility": { "roles": [], "tags": [] },
    "telemetry": {
      "required_metrics": ["retrieval", "performance", "model"]
    }
  },
  "prompts": {
    "system_prompt": "...",
    "developer_prompt": "...",
    "fewshots": [],
    "variables": []                       ← PRESENT
  }
}
```

#### ❌ Seeded Use Case (003_seed_use_cases.sql)

```json
{
  "config_json": {
    "output_contract": {
      "format": "text",
      "schema": null,                     ← BUG 1: Wrong field name
      "validation_mode": "best_effort"
    },
    "tools_allowlist": [],
    // Missing: tool_restrictions          ← BUG 2: Missing field
  },
  "metadata": {
    "prompts": {
      "system_prompt": "...",
      "developer_prompt": "...",
      "fewshots": []
      // Missing: variables                ← BUG 3: Missing field
    }
  }
}
```

---

## Bugs Identified

### Bug 1: Wrong Field Name in output_contract ⚠️ CRITICAL

**Location:** All use cases in `003_seed_use_cases.sql` and `009_seed_draft_use_cases.sql`

**Current (WRONG):**
```json
"output_contract": {
    "format": "text",
    "schema": null,
    "validation_mode": "best_effort"
}
```

**Should be:**
```json
"output_contract": {
    "format": "text",
    "output_schema": null,
    "validation_mode": "best_effort"
}
```

**Evidence:**
- `src/orchestrator/app/schemas/use_case_config.py` line 310-313:
```python
class OutputContractConfig(BaseModel):
    format: OutputFormat = Field(default=OutputFormat.TEXT)
    output_schema: dict[str, Any] | None = Field(default=None)  # ← Correct name
    validation_mode: ValidationMode = Field(default=ValidationMode.BEST_EFFORT)
```

**Impact:** Output contract configuration may not be recognized, causing output formatting issues.

---

### Bug 2: Missing tool_restrictions Field ⚠️ REQUIRED

**Location:** All use cases in `003_seed_use_cases.sql` and `009_seed_draft_use_cases.sql`

**Current (MISSING):**
```json
{
  "tools_allowlist": []
  // tool_restrictions is completely missing
}
```

**Should be:**
```json
{
  "tools_allowlist": [],
  "tool_restrictions": null
}
```

**Evidence:**
- `src/orchestrator/app/schemas/use_case_config.py` line 406-409:
```python
class UseCaseConfig(BaseModel):
    tools_allowlist: list[str] = Field(default_factory=list)
    tool_restrictions: UseCaseToolRestrictions | None = Field(
        default=None,
        description="Security-based tool restrictions. If None, only tools_allowlist is used.",
    )
```

**Impact:** Tool security configuration incomplete, may cause schema validation errors.

---

### Bug 3: Missing variables Field in Prompts 📝

**Location:** All use cases in `003_seed_use_cases.sql` and `009_seed_draft_use_cases.sql`

**Current (MISSING):**
```json
"prompts": {
    "system_prompt": "...",
    "developer_prompt": "...",
    "fewshots": []
    // variables is missing
}
```

**Should be:**
```json
"prompts": {
    "system_prompt": "...",
    "developer_prompt": "...",
    "fewshots": [],
    "variables": []
}
```

**Evidence:**
- `src/orchestrator/app/schemas/use_case_management.py` line 32-48:
```python
class UseCasePromptSet(BaseModel):
    system_prompt: str | None = Field(None)
    developer_prompt: str | None = Field(None)
    fewshots: list[FewshotPair] = Field(default_factory=list)
    variables: list[str] = Field(
        default_factory=list,
        description="Required variables for template substitution"
    )
```

**Impact:** Prompt template variable substitution may fail or cause errors.

---

### Bug 4: Missing team_id = NULL for Published Use Cases 🔒

**Location:** `003_seed_use_cases.sql` (published use cases)

**Current:** No explicit `team_id` handling

**Should add at end of script:**
```sql
-- Ensure published use cases are globally visible (team_id = NULL)
UPDATE use_cases
SET team_id = NULL
WHERE lifecycle_state = 'published'
  AND team_id IS NOT NULL
  AND metadata->>'seed_script' = '003_seed_use_cases';
```

**Evidence:**
- DATABASE_REFRESH_PLAN.md task db-refresh-003
- ADR-060: Published use cases must have `team_id = NULL` for global visibility

**Impact:** Published use cases may incorrectly be team-scoped, violating RBAC V2 visibility rules.

---

## Files Affected

### 1. `ops/database/seed/003_seed_use_cases.sql` (5 use cases)

All 5 published use cases need fixes:
- `threat-analysis-basic`
- `log-investigation`
- `ioc-lookup`
- `policy-review`
- `incident-summary`

**Changes needed per use case:**
1. Change `"schema": null` → `"output_schema": null` in output_contract
2. Add `"tool_restrictions": null` after tools_allowlist
3. Add `"variables": []` in prompts (metadata section)

**Add at end of file:**
4. SQL UPDATE statement to set `team_id = NULL` for all published use cases

### 2. `ops/database/seed/009_seed_draft_use_cases.sql` (5 use cases)

All 5 draft use cases need fixes:
- `team_uc_csirt_001`
- `team_uc_csirt_002`
- `team_uc_gov_001`
- `team_uc_dev_001`
- `team_uc_dev_002`

**Changes needed per use case:**
1. Same as above (schema field name, tool_restrictions, variables)
2. Verify `team_id` is correctly set to owning team

---

## Solution

### Step 1: Fix 003_seed_use_cases.sql

For each of the 5 use cases:

1. **Fix output_contract field name:**
```sql
-- BEFORE
"output_contract": {
    "format": "text",
    "schema": null,
    "validation_mode": "best_effort"
}

-- AFTER
"output_contract": {
    "format": "text",
    "output_schema": null,
    "validation_mode": "best_effort"
}
```

2. **Add tool_restrictions field:**
```sql
-- Add after tools_allowlist
"tools_allowlist": [],
"tool_restrictions": null,
```

3. **Add variables field to prompts:**
```sql
-- In metadata section
"prompts": {
    "system_prompt": "...",
    "developer_prompt": "...",
    "fewshots": [],
    "variables": []
}
```

4. **Add team_id cleanup at end of file:**
```sql
-- At end of 003_seed_use_cases.sql
COMMIT;

-- ============================================================================
-- RBAC V2: Ensure Published Use Cases are Globally Visible
-- ============================================================================
-- Published use cases must have team_id = NULL for global visibility (ADR-060)

UPDATE use_cases
SET team_id = NULL
WHERE lifecycle_state = 'published'
  AND team_id IS NOT NULL
  AND metadata->>'seed_script' = '003_seed_use_cases';

-- Verification
DO $$
DECLARE
    published_count INTEGER;
    team_scoped_published INTEGER;
BEGIN
    SELECT COUNT(*) INTO published_count
    FROM use_cases
    WHERE lifecycle_state = 'published'
      AND metadata->>'seed_script' = '003_seed_use_cases';

    SELECT COUNT(*) INTO team_scoped_published
    FROM use_cases
    WHERE lifecycle_state = 'published'
      AND team_id IS NOT NULL
      AND metadata->>'seed_script' = '003_seed_use_cases';

    RAISE NOTICE '✅ Published use cases seeded: %', published_count;
    RAISE NOTICE '✅ Team-scoped published (should be 0): %', team_scoped_published;

    IF team_scoped_published > 0 THEN
        RAISE WARNING '⚠️  Some published use cases have team_id set (should be NULL)';
    END IF;
END $$;
```

### Step 2: Fix 009_seed_draft_use_cases.sql

Apply the same 3 fixes (output_schema, tool_restrictions, variables) to all 5 draft use cases.

**Note:** Do NOT add the team_id = NULL update. Draft use cases MUST have team_id set.

### Step 3: Verification

After applying fixes:

1. **Schema validation:**
```bash
# Run seed scripts
bash ops/operations/reset_demo_database.sh

# Verify no SQL errors
```

2. **UI verification:**
```bash
# Login to UI
# Navigate to Use Cases page
# Verify all use cases display correctly
# Check that RAG configuration shows properly
```

3. **Database verification:**
```sql
-- Check published use cases have team_id = NULL
SELECT use_case_id, lifecycle_state, team_id
FROM use_cases
WHERE lifecycle_state = 'published';
-- All should have team_id = NULL

-- Check draft use cases have team_id set
SELECT use_case_id, lifecycle_state, team_id
FROM use_cases
WHERE lifecycle_state = 'draft';
-- All should have team_id = 'team:something'
```

---

## Related Issue: Missing input_fields UI Support

### Problem

The Use Case Wizard UI is completely missing support for configuring `input_fields` in the `config_json`.

**Evidence:**
- `UseCaseConfig` schema supports `input_fields: list[InputFieldConfig]` (line 382-385 in use_case_config.py)
- Working wizard-created use case has `"input_fields": []` in config_json
- No UI component exists for adding/editing input fields

**Impact:**
- Users cannot create use cases with structured input forms
- All wizard-created use cases default to conversational mode only
- ADR-044 "Bounded Refinement Spaces" feature incomplete

**Action Required:**
- Create separate Feature Task: `UI_ADD_INPUT_FIELDS_TO_WIZARD.md`
- Scope: Add input field editor to Use Case Wizard
- Estimate: Medium complexity (requires dynamic form builder)

---

## Testing Plan

### Unit Tests (Not Required)

Seed files are static data - no unit tests needed.

### Integration Tests (Manual)

1. **Test fresh database initialization:**
```bash
# Reset database
bash ops/operations/reset_demo_database.sh

# Verify no errors
bash ops/operations/verify_demo_setup.sh
```

2. **Test use case display in UI:**
- Login as admin
- Navigate to Use Cases page
- Verify all 10 use cases display
- Open each use case detail page
- Verify RAG configuration shows correctly
- Verify output contract displays
- Verify tools configuration displays

3. **Test use case execution:**
- Select published use case
- Execute with test query
- Verify response generated correctly
- Check logs for schema validation errors

### Acceptance Criteria

- ✅ All 5 published use cases load without errors
- ✅ All 5 draft use cases load without errors
- ✅ RAG configuration displays correctly in UI
- ✅ Output contract configuration displays correctly
- ✅ Tool configuration displays correctly
- ✅ Published use cases have `team_id = NULL`
- ✅ Draft use cases have `team_id = 'team:xxx'`
- ✅ Use case execution works correctly
- ✅ No schema validation errors in logs

---

## Rollback Plan

If issues occur after applying fixes:

1. **Immediate rollback:**
```bash
# Restore database from backup or re-run old seed files
```

2. **Git revert:**
```bash
git revert <commit-hash>
```

3. **Recreate database:**
```bash
bash ops/operations/reset_demo_database.sh
```

---

## Timeline

- **Investigation:** ✅ Complete (2025-01-11)
- **Fix Implementation:** 2 hours
- **Testing:** 1 hour
- **Documentation:** 30 minutes
- **Total:** 3.5 hours

---

## Related Documents

- **DATABASE_REFRESH_PLAN.md** - Parent plan (task db-refresh-003)
- **ADR-060** - RBAC V2 architecture (team_id requirements)
- **ADR-044** - Bounded Refinement Spaces (input_fields concept)
- `src/orchestrator/app/schemas/use_case_config.py` - Schema definitions
- `src/orchestrator/app/schemas/use_case_management.py` - Prompt schema

---

## Notes

### Why Schema Mismatch Occurred

The seed files were likely created before:
1. `output_schema` field was renamed from `schema`
2. `tool_restrictions` field was added (ADR-057)
3. `variables` field was added to prompts

The UI wizard uses the current Pydantic schemas, so wizard-created use cases are always correct.

### Prevention

- Add JSON schema validation to seed files
- Add integration test that validates all seeded use cases against Pydantic schemas
- Document schema changes in ADRs with migration notes

---

**Status:** 📋 READY TO START
**Next Actions:**
1. Apply fixes to 003_seed_use_cases.sql
2. Apply fixes to 009_seed_draft_use_cases.sql
3. Test with reset_demo_database.sh
4. Verify in UI
5. Create separate feature task for input_fields UI support
