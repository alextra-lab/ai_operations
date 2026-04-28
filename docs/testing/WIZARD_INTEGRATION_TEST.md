# Use Case Wizard Integration Test

**Test Type:** Manual Integration Testing
**Component:** Use Case Creation Wizard (5 Steps)
**Phase:** Phase 3 - Use Case Management
**Created:** October 19, 2025

---

## Test Overview

This document provides a comprehensive integration test checklist for the 5-step Use Case Creation Wizard.

---

## Prerequisites

### Environment Setup
- [ ] Frontend application running (`npm start`)
- [ ] Backend API running on http://localhost:8000
- [ ] Database with pattern library seeded
- [ ] Valid JWT authentication token

### Test Data
- [ ] At least 1 existing use case (for cloning)
- [ ] 29 prompt patterns loaded in database
- [ ] Test user with appropriate permissions

---

## Test Scenarios

### Scenario 1: Create Use Case from Blank

**Path:** Blank → No Prompts → Default Config

#### Step 1: Basic Information
- [ ] Navigate to `/dev/use-cases/new`
- [ ] Enter name: "Test Use Case 1"
- [ ] Enter description: "Integration test use case"
- [ ] Select category: "security"
- [ ] Select intent: "QUERY"
- [ ] Click "Next"
- [ ] Verify progress bar shows Step 2

**Expected:** Form validates, navigation succeeds

#### Step 2: Starting Point
- [ ] Click "Start from Blank" card
- [ ] Verify card shows selected state (blue border)
- [ ] Click "Next"
- [ ] Verify navigation to Step 3

**Expected:** Blank option selected, no additional fields required

#### Step 3: Edit Prompts
- [ ] Verify all prompt fields are empty
- [ ] Leave all fields empty (testing defaults)
- [ ] Click "Next"
- [ ] Verify navigation to Step 4

**Expected:** Empty prompts are allowed, navigation succeeds

#### Step 4: Configure
- [ ] Verify LLM model defaults to "Mistral Small 3.1 24B"
- [ ] Verify embedding model defaults to "BGE-M3"
- [ ] Verify temperature = 0.7
- [ ] Verify max_tokens = 2048
- [ ] Verify RAG enabled = true
- [ ] Verify top_k = 10
- [ ] Verify PII redaction = "anonymize"
- [ ] Click "Next"
- [ ] Verify navigation to Step 5

**Expected:** All default values populated, form valid

#### Step 5: Preview & Save
- [ ] Verify Basic Information card shows entered data
- [ ] Verify Models & Settings card shows defaults
- [ ] Verify RAG Configuration shows enabled
- [ ] Verify Policies card shows settings
- [ ] Verify validation shows warning for no prompts
- [ ] Verify "Create Use Case" button is enabled
- [ ] Click "Create Use Case"
- [ ] Verify redirect to editor page
- [ ] Verify success notification

**Expected:** Preview shows all data, creation succeeds

---

### Scenario 2: Create Use Case from Pattern

**Path:** Pattern → Chain-of-Thought → Custom Config

#### Step 1: Basic Information
- [ ] Enter name: "Test CoT Use Case"
- [ ] Enter description: "Testing pattern integration"
- [ ] Category: "analysis"
- [ ] Intent: "QUERY"
- [ ] Click "Next"

**Expected:** Form validates successfully

#### Step 2: Starting Point
- [ ] Click "Use a Pattern" card
- [ ] Verify pattern grid appears
- [ ] Enter search: "chain"
- [ ] Verify "Chain-of-Thought" pattern appears
- [ ] Click Chain-of-Thought pattern card
- [ ] Verify pattern card shows selected (green border)
- [ ] Verify pattern preview shows below
- [ ] Click "Next"
- [ ] Verify loading indicator appears
- [ ] Verify pattern is applied

**Expected:** Pattern selected, prompts loaded

#### Step 3: Edit Prompts
- [ ] Verify System Prompt contains pattern text
- [ ] Verify pattern badge shows "Chain-of-Thought"
- [ ] Edit system prompt (add custom text)
- [ ] Add one few-shot example
- [ ] Click "Show Preview"
- [ ] Verify preview displays all prompts
- [ ] Click "Next"

**Expected:** Pattern prompts loaded, editable, preview works

#### Step 4: Configure
- [ ] Change LLM model to "Qwen 3 Next 80B"
- [ ] Change temperature to 0.5
- [ ] Change max_tokens to 4096
- [ ] Change top_k to 5
- [ ] Change similarity_threshold to 0.7
- [ ] Enable hybrid BM25
- [ ] Change PII redaction to "redact"
- [ ] Click "Next"

**Expected:** All config changes accepted

#### Step 5: Preview & Save
- [ ] Verify pattern badge shows in Basic Info
- [ ] Verify Models shows "Qwen 3 Next 80B"
- [ ] Verify RAG shows top_k = 5, similarity = 0.7
- [ ] Verify BM25 enabled indicator
- [ ] Verify Policies shows PII redaction = "redact"
- [ ] Expand "Preview Prompts"
- [ ] Verify system prompt shows edited text
- [ ] Verify few-shot example displays
- [ ] Verify all validation checks pass
- [ ] Click "Create Use Case"

**Expected:** All custom config shown, creation succeeds

---

### Scenario 3: Create Use Case by Cloning

**Path:** Clone Existing → Modify Prompts → Custom Config

#### Step 1: Basic Information
- [ ] Enter name: "Cloned Test Use Case"
- [ ] Description: "Cloned from existing"
- [ ] Click "Next"

**Expected:** Basic info entered

#### Step 2: Starting Point
- [ ] Click "Clone Existing" card
- [ ] Verify use case dropdown appears
- [ ] Select an existing use case
- [ ] Verify selected use case preview shows
- [ ] Click "Next"

**Expected:** Clone selected, prompts loaded from source

#### Step 3: Edit Prompts
- [ ] Verify prompts populated from cloned use case
- [ ] Verify no pattern badge (unless source had one)
- [ ] Modify system prompt
- [ ] Add developer prompt
- [ ] Click "Next"

**Expected:** Cloned prompts editable

#### Step 4: Configure
- [ ] Change 2-3 config values
- [ ] Click "Next"

**Expected:** Config modified successfully

#### Step 5: Preview & Save
- [ ] Verify all changes shown in preview
- [ ] Create use case
- [ ] Verify different from source (new UUID)

**Expected:** New use case created with modified config

---

### Scenario 4: Navigation & Validation Tests

#### Back Navigation
- [ ] Complete Steps 1-3
- [ ] Click "Previous" from Step 3
- [ ] Verify Step 2 data retained
- [ ] Click "Previous" from Step 2
- [ ] Verify Step 1 data retained
- [ ] Navigate forward again
- [ ] Verify all data still present

**Expected:** Data persists through back/forward navigation

#### Validation Tests
- [ ] Step 1: Try to proceed with empty name
- [ ] Verify error message appears
- [ ] Verify "Next" button disabled
- [ ] Enter valid name
- [ ] Verify "Next" enabled

**Expected:** Validation prevents invalid progression

- [ ] Step 2: Try to proceed without selection
- [ ] Verify error notification
- [ ] Select starting point
- [ ] Verify progression allowed

**Expected:** Starting point selection required

#### Cancel Workflow
- [ ] Complete Steps 1-3
- [ ] Click "Cancel" button
- [ ] Verify confirmation dialog
- [ ] Click "OK"
- [ ] Verify redirect to use case list

**Expected:** Cancel aborts wizard, returns to list

---

### Scenario 5: Edge Cases

#### Minimum Configuration
- [ ] Create use case with only required fields:
  - Name only in Step 1
  - Blank in Step 2
  - No prompts in Step 3
  - Default config in Step 4
  - Create in Step 5
- [ ] Verify creation succeeds with defaults

**Expected:** Minimum viable configuration works

#### Maximum Configuration
- [ ] Fill all optional fields in Step 1
- [ ] Use pattern with all prompts in Step 2-3
- [ ] Customize all config options in Step 4
- [ ] Verify all data in Step 5
- [ ] Create use case

**Expected:** Maximum configuration works

#### Long Text Fields
- [ ] Enter 500+ character description
- [ ] Enter 2000+ character system prompt
- [ ] Verify fields accept long text
- [ ] Verify preview displays correctly

**Expected:** Long text handled properly

---

## Test Execution Log

### Test Run: [DATE]
**Tester:** [NAME]
**Environment:** [DEV/STAGING/PROD]
**Browser:** [Chrome/Firefox/Safari]

| Scenario | Status | Notes | Issues |
|----------|--------|-------|--------|
| 1. Blank | ⬜ | | |
| 2. Pattern | ⬜ | | |
| 3. Clone | ⬜ | | |
| 4. Navigation | ⬜ | | |
| 5. Edge Cases | ⬜ | | |

**Legend:** ✅ Pass | ❌ Fail | ⚠️ Warning | ⬜ Not Tested

---

## Known Issues

### Minor Issues
- [ ] None currently

### Backend Pending
- [ ] Multi-role prompts not yet used by orchestrator (P3-FIX-10)
  - Impact: Wizard creates prompts, backend uses fallback templates
  - Workaround: Use case saves correctly, will work when backend updated
  - Priority: High

---

## Success Criteria

### Functional Requirements
- [ ] All 5 steps navigate successfully
- [ ] Form validation works at each step
- [ ] All 3 starting points work (blank, pattern, clone)
- [ ] Configuration saved correctly to backend
- [ ] Use case created in DRAFT state
- [ ] Redirect to editor after creation

### Non-Functional Requirements
- [ ] Page load time < 2 seconds
- [ ] Step navigation < 500ms
- [ ] Pattern search results < 1 second
- [ ] Use case creation < 2 seconds
- [ ] No console errors
- [ ] No linter warnings

### User Experience
- [ ] Clear instructions at each step
- [ ] Validation messages are helpful
- [ ] Progress indicator accurate
- [ ] Preview shows all entered data
- [ ] Responsive on mobile (768px+)
- [ ] Keyboard navigation works

---

## Regression Testing

### After Backend Changes
- [ ] Verify wizard still creates use cases
- [ ] Verify Step 4 config applied to requests
- [ ] Verify multi-role prompts used (once implemented)

### After Pattern Library Updates
- [ ] Verify new patterns appear in wizard
- [ ] Verify pattern search works
- [ ] Verify pattern application succeeds

---

## Performance Benchmarks

### Target Metrics
- **Step 1 Load:** < 500ms
- **Pattern Library Load:** < 1 second (29 patterns)
- **Step Navigation:** < 300ms
- **Use Case Creation:** < 2 seconds
- **Total Wizard Time:** < 3 minutes (typical user)

### Actual Metrics
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Step 1 Load | < 500ms | TBD | ⬜ |
| Pattern Load | < 1s | TBD | ⬜ |
| Navigation | < 300ms | TBD | ⬜ |
| Creation | < 2s | TBD | ⬜ |

---

## Accessibility Checklist

- [ ] All form fields have labels
- [ ] Keyboard navigation works (Tab, Enter, Esc)
- [ ] Error messages announced by screen readers
- [ ] Color contrast meets WCAG AA standards
- [ ] Focus indicators visible
- [ ] ARIA labels on icon buttons

---

## Browser Compatibility

| Browser | Version | Status | Notes |
|---------|---------|--------|-------|
| Chrome | 119+ | ⬜ | |
| Firefox | 120+ | ⬜ | |
| Safari | 17+ | ⬜ | |
| Edge | 119+ | ⬜ | |

---

## Automated Testing

### Unit Tests (Angular)
```bash
# Not yet implemented
ng test --include='**/use-case-wizard.component.spec.ts'
```

### E2E Tests (Cypress/Playwright)
```bash
# Not yet implemented
npm run e2e:wizard
```

---

## Documentation

- **Component:** `src/frontend-angular/src/app/pages/use-cases/use-case-wizard.component.ts`
- **Session Log:** `docs/development/sessions/2025-10-19-p3-wizard-steps-4-5-complete.md`
- **Backend Task:** `docs/development/tasks/P3_FIX_10_BACKEND_MULTI_ROLE_PROMPTS.md`
- **Phase Plan:** `docs/development/plans/active/PHASE_03_USE_CASE_MGMT.md`

---

**Test Maintained By:** QA Team
**Last Updated:** October 19, 2025
**Next Review:** Weekly during Phase 3
