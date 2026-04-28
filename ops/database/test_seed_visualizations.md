# Seed Visualization AIOps Testing Guide

## Overview

This guide provides manual testing steps for the 8 demonstration AIOps that showcase all output visualization templates.

## Prerequisites

1. Database seeded with demonstration AIOps:

   ```bash
   PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
     -h $POSTGRES_HOST -p $POSTGRES_PORT \
     -U $POSTGRES_USER -d $POSTGRES_DB \
     -f ops/database/seed/003_seed_use_cases.sql
   ```

2. Frontend and backend services running
3. User logged in with appropriate permissions (admin/analyst role)

## Test Procedure

For each AIOp listed below:

1. Navigate to the AIOp execution page
2. Verify default input value is pre-populated
3. Click **Execute** button (without modifying input)
4. Wait for execution to complete
5. Verify structured output renders correctly with the specified visualization
6. Check all visualization components are displayed and functional

---

## 1. Threat Analysis & Triage (Demo)

**Visualization Template:** `score-table-timeline`

**Test Steps:**

- [ ] Navigate to "Threat Analysis & Triage (Demo)" AIOp
- [ ] Verify default threat data is pre-filled
- [ ] Click Execute
- [ ] Verify output contains:
  - [ ] **Gauge** showing confidence score (0-1) with color threshold indicators
  - [ ] **Data table** with threat indicators (type, value, context columns)
  - [ ] **Timeline** showing chronological events with severity markers

**Expected Visualization Components:**

- Score gauge (top-left, 1/3 width)
- Items table (full width, filterable/sortable)
- Event timeline (full width, chronological display)

---

## 2. IOC Extraction & Analysis (Demo)

**Visualization Template:** `filterable-table`

**Test Steps:**

- [ ] Navigate to "IOC Extraction & Analysis (Demo)" AIOp
- [ ] Verify default security log data is pre-filled
- [ ] Click Execute
- [ ] Verify output contains:
  - [ ] **Filterable table** with extracted IOCs
  - [ ] Columns: type, value, context, confidence
  - [ ] Filter controls functional
  - [ ] Sort functionality on each column
  - [ ] Export buttons (CSV, JSON, Excel)

**Expected Visualization Components:**

- Single filterable table (full width)
- Column headers with sort indicators
- Filter input fields
- Export toolbar

---

## 3. Incident Timeline Summary (Demo)

**Visualization Template:** `score-timeline`

**Test Steps:**

- [ ] Navigate to "Incident Timeline Summary (Demo)" AIOp
- [ ] Verify default incident data is pre-filled
- [ ] Click Execute
- [ ] Verify output contains:
  - [ ] **Severity gauge** (0-10 scale) with color thresholds
  - [ ] **Event timeline** showing incident progression
  - [ ] Status indicator (detected/investigating/contained/resolved)

**Expected Visualization Components:**

- Severity gauge (left, 1/3 width)
- Event timeline (right, 2/3 width)
- Metric details (affected count, data loss status)

---

## 4. Security Log Parser (Demo)

**Visualization Template:** `auto-table`

**Test Steps:**

- [ ] Navigate to "Security Log Parser (Demo)" AIOp
- [ ] Verify default raw log data is pre-filled
- [ ] Click Execute
- [ ] Verify output contains:
  - [ ] **Auto-generated table** with parsed log entries
  - [ ] Columns auto-detected from data structure
  - [ ] Consistent field names across rows
  - [ ] Filter and sort capabilities

**Expected Visualization Components:**

- Single table with auto-detected columns (full width)
- All log entries structured consistently
- Standard table controls (filter, sort)

---

## 5. Security Metrics Dashboard (Demo)

**Visualization Template:** `bar-chart`

**Test Steps:**

- [ ] Navigate to "Security Metrics Dashboard (Demo)" AIOp
- [ ] Verify default metrics summary is pre-filled
- [ ] Click Execute
- [ ] Verify output contains:
  - [ ] **Bar chart** with labeled metrics
  - [ ] Clear metric labels on X-axis
  - [ ] Numeric values on Y-axis
  - [ ] Bars properly scaled

**Expected Visualization Components:**

- Horizontal or vertical bar chart (full width)
- Grid lines for value reference
- Axis labels
- Optional legend

---

## 6. Policy Compliance Summary (Demo)

**Visualization Template:** `kv-summary`

**Test Steps:**

- [ ] Navigate to "Policy Compliance Summary (Demo)" AIOp
- [ ] Verify default policy data is pre-filled
- [ ] Click Execute
- [ ] Verify output contains:
  - [ ] **Key-value grid** with policy details
  - [ ] Clear labels for each field
  - [ ] Values properly formatted
  - [ ] 2-column grid layout

**Expected Visualization Components:**

- Key-value grid (full width)
- Two-column layout
- Clear typography hierarchy
- All summary fields displayed

---

## 7. Alert Correlation Analysis (Demo)

**Visualization Template:** `multi-table`

**Test Steps:**

- [ ] Navigate to "Alert Correlation Analysis (Demo)" AIOp
- [ ] Verify default alert feed data is pre-filled
- [ ] Click Execute
- [ ] Verify output contains:
  - [ ] **Tabbed interface** with multiple alert categories
  - [ ] Each tab shows a separate table
  - [ ] Tab labels match alert categories
  - [ ] Consistent columns within each table
  - [ ] Ability to switch between tabs

**Expected Visualization Components:**

- Tab navigation bar
- Multiple tables (one per category)
- Tab switching functionality
- Each table independently filterable/sortable

---

## 8. Configuration Comparison (Demo)

**Visualization Template:** `comparison-grid`

**Test Steps:**

- [ ] Navigate to "Configuration Comparison (Demo)" AIOp
- [ ] Verify default configuration change request is pre-filled
- [ ] Click Execute
- [ ] Verify output contains:
  - [ ] **Side-by-side panels** for comparison
  - [ ] Left panel: Current/before configuration
  - [ ] Right panel: Proposed/after configuration
  - [ ] Clear titles on each panel
  - [ ] Aligned settings for easy comparison

**Expected Visualization Components:**

- Two-column layout (50/50 split)
- Panel titles (left and right)
- Text content with preserved line breaks
- Visual separation between panels

---

## Verification Checklist

### Database Verification

```sql
-- Verify all 8 AIOps are created
SELECT COUNT(*) as aiop_count
FROM use_cases
WHERE metadata->>'seed_script' = '003_seed_use_cases'
  AND metadata->>'demo' = 'true';
-- Expected: 8

-- Verify each has output schema and template
SELECT
    use_case_id,
    name,
    config_json->>'output_contract'->>'template_id' as template,
    (config_json->'output_contract'->'output_schema' IS NOT NULL) as has_schema
FROM use_cases
WHERE metadata->>'seed_script' = '003_seed_use_cases'
ORDER BY use_case_id;
-- Expected: All rows have template and has_schema = true
```

### Functional Tests

- [ ] All 8 AIOps appear in the AIOps list
- [ ] All are marked as "(Demo)" in the name
- [ ] All have default input values populated
- [ ] All execute successfully without modification
- [ ] All return structured JSON output
- [ ] All render with the correct visualization template
- [ ] No RAG retrieval attempted (disabled)
- [ ] No tool execution attempted (empty allowlist)
- [ ] Execution completes within reasonable time (<30 seconds)

### Schema Validation Tests

For each AIOp, verify the output JSON:

- [ ] Matches the defined `output_schema` in config
- [ ] Contains all required fields
- [ ] Field types match schema definitions
- [ ] Enum values conform to allowed values
- [ ] No extra fields when `additionalProperties: false`

### UI/UX Tests

- [ ] Visualizations are responsive (resize browser)
- [ ] Export functionality works (where applicable)
- [ ] Filter/sort controls function properly (tables)
- [ ] Color coding is clear and consistent (gauges/charts)
- [ ] Tabs switch smoothly (multi-table)
- [ ] Text formatting preserved (comparison grid)

---

## Common Issues & Troubleshooting

### Issue: AIOp doesn't execute

**Possible Causes:**

- Model not configured in `intent_model_defaults` table
- Backend service not running
- Database connection issue

**Solution:**

```sql
-- Check model defaults
SELECT * FROM intent_model_defaults WHERE intent_type IN ('QUERY', 'EXTRACTION', 'SUMMARIZATION');

-- Ensure at least one model is configured per intent type
```

### Issue: Output doesn't match schema

**Possible Causes:**

- LLM not following prompt instructions
- Schema too strict
- Developer prompt unclear

**Solution:**

- Check execution logs for validation errors
- Review LLM output in raw format
- Adjust temperature (lower = more deterministic)

### Issue: Visualization doesn't render

**Possible Causes:**

- Template ID mismatch
- Schema incompatible with template
- Frontend component error

**Solution:**

- Verify `template_id` matches registered template
- Check browser console for errors
- Validate data paths in template definition

---

## Success Criteria

✅ **All tests pass when:**

1. All 8 AIOps execute without errors
2. All visualizations render correctly
3. All interactive controls function (filters, sort, tabs, export)
4. Output JSON validates against defined schemas
5. No console errors in browser
6. Execution times are reasonable (<30s per AIOp)

---

## Test Execution Log

Use this table to track your testing progress:

| AIOp Name | Executed | Renders | Components OK | Issues | Status |
|-----------|----------|---------|---------------|--------|--------|
| 1. Threat Triage | ☐ | ☐ | ☐ | | ⬜ |
| 2. IOC Extraction | ☐ | ☐ | ☐ | | ⬜ |
| 3. Incident Timeline | ☐ | ☐ | ☐ | | ⬜ |
| 4. Log Parser | ☐ | ☐ | ☐ | | ⬜ |
| 5. Metrics Dashboard | ☐ | ☐ | ☐ | | ⬜ |
| 6. Policy Summary | ☐ | ☐ | ☐ | | ⬜ |
| 7. Alert Correlation | ☐ | ☐ | ☐ | | ⬜ |
| 8. Config Comparison | ☐ | ☐ | ☐ | | ⬜ |

**Status Legend:** ⬜ Not Started | 🟡 In Progress | ✅ Passed | ❌ Failed

---

## Additional Notes

- These AIOps are for demonstration purposes only
- Default values are designed to trigger appropriate responses
- RAG is intentionally disabled to ensure consistent, immediate execution
- Production AIOps should have RAG enabled and more sophisticated prompts
- Consider creating custom AIOps based on these templates for real use cases
