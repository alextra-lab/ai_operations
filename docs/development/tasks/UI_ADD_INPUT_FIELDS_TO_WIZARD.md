# Feature Task: Add Input Fields Editor to Use Case Wizard

**Status:** 📋 PLANNED
**Date Created:** 2025-01-11
**Priority:** MEDIUM
**Type:** Feature Enhancement
**Related ADR:** ADR-044 (Bounded Refinement Spaces)
**Discovered During:** DATABASE_REFRESH_PLAN bug investigation

---

## Executive Summary

The Use Case Wizard UI is missing the ability to configure `input_fields` in the use case configuration. This prevents users from creating use cases with structured input forms, limiting all wizard-created use cases to conversational-only mode.

---

## Problem Statement

### Current State

**What's Missing:**
- No UI component for adding/editing input fields in the wizard
- No way to configure structured form fields (text, textarea, select, etc.)
- No way to define field labels, descriptions, placeholders
- No way to mark fields as required/optional
- No way to define select field options

**Current Workaround:**
- Users can only create conversational-mode use cases (no structured inputs)
- To add input fields, users must manually edit the database or config JSON

**Impact:**
- ADR-044 "Bounded Refinement Spaces" feature is incomplete
- Users cannot leverage structured input forms
- Security boundaries enabled by input fields are not accessible
- Use cases with specific, typed inputs cannot be created via UI

---

## Architecture Context

### Input Fields in UseCaseConfig

Per `src/orchestrator/app/schemas/use_case_config.py` (lines 99-140):

```python
class InputFieldConfig(BaseModel):
    """Configuration for a single dynamic input field."""

    name: str = Field(description="Field name (used as key in inputs dict)")
    type: InputFieldType = Field(description="Field type for UI rendering")
    label: str = Field(description="User-visible label for the field")
    description: str | None = Field(default=None, description="Help text shown to user")
    required: bool = Field(default=True, description="Whether field is required")
    placeholder: str | None = Field(default=None, description="Placeholder text")
    default_value: str | None = Field(default=None, description="Default value")
    options: list[InputFieldOption] | None = Field(
        default=None,
        description="Options for select fields (required if type=select)",
    )

class UseCaseConfig(BaseModel):
    """Complete use case configuration schema."""

    input_fields: list[InputFieldConfig] = Field(
        default_factory=list,
        description="Input fields for dynamic form generation. Empty array = conversational mode.",
    )
    # ... other fields ...
```

### Supported Field Types

```python
class InputFieldType(str, Enum):
    TEXT = "text"
    TEXTAREA = "textarea"
    SELECT = "select"
    NUMBER = "number"
    CHECKBOX = "checkbox"
    DATE = "date"
```

### Usage Modes (ADR-044)

1. **Conversational Mode:** `input_fields: []` (empty array)
   - Use case operates in pure conversational mode from start

2. **Structured Mode:** `input_fields: [...]` (populated array)
   - Use case shows structured form first
   - User fills in typed inputs
   - After execution, allows conversational refinement

---

## Requirements

### Functional Requirements

1. **Input Field Editor Component**
   - Add/remove input fields dynamically
   - Configure each field:
     - Name (internal key)
     - Type (dropdown: text, textarea, select, number, checkbox, date)
     - Label (user-visible)
     - Description (help text)
     - Required (checkbox)
     - Placeholder (optional)
     - Default value (optional)
   - For select fields:
     - Add/remove options
     - Configure option value and label

2. **Wizard Integration**
   - Add "Input Fields" step to Use Case Wizard
   - Position: After basic info, before prompts/config
   - Optional: Skip for conversational-only use cases
   - Validation: Ensure select fields have at least one option

3. **Preview Functionality**
   - Show preview of how input form will look
   - Live update as fields are added/edited
   - Validate field configuration before saving

4. **Edit Existing Use Cases**
   - Support editing input fields in existing use cases
   - Preserve existing fields when editing
   - Warning if removing fields that may be referenced

### Non-Functional Requirements

1. **Usability**
   - Drag-and-drop to reorder fields
   - Copy/duplicate field functionality
   - Clear, intuitive field editor UI
   - Inline validation and error messages

2. **Performance**
   - Handle up to 20 input fields without UI lag
   - Efficient re-rendering on field changes

3. **Accessibility**
   - WCAG 2.1 AA compliance
   - Keyboard navigation support
   - Screen reader compatible

---

## Proposed Solution

### UI Component Structure

```
Use Case Wizard
├── Step 1: Basic Info (existing)
├── Step 2: Intent & Category (existing)
├── Step 3: Input Fields (NEW)
│   ├── Input Fields List
│   │   ├── Field Card (repeatable)
│   │   │   ├── Field Name Input
│   │   │   ├── Field Type Dropdown
│   │   │   ├── Field Label Input
│   │   │   ├── Field Description Textarea
│   │   │   ├── Required Checkbox
│   │   │   ├── Placeholder Input
│   │   │   ├── Default Value Input
│   │   │   └── Options Editor (if type=select)
│   │   └── Add Field Button
│   └── Form Preview Panel
├── Step 4: Prompts (existing)
├── Step 5: RAG Config (existing)
└── Step 6: Review & Create (existing)
```

### Angular Components

**New Components:**

1. **`input-fields-editor.component.ts`**
   - Main editor component
   - Manages array of input field configurations
   - Add/remove/reorder fields

2. **`input-field-card.component.ts`**
   - Individual field editor
   - Form for configuring single field
   - Validation logic

3. **`input-field-options-editor.component.ts`**
   - Sub-component for select field options
   - Add/remove options
   - Option value/label pairs

4. **`input-form-preview.component.ts`**
   - Preview panel showing how form will render
   - Dynamic form generation based on field configs
   - Read-only demonstration

**Updated Components:**

1. **`use-case-wizard.component.ts`**
   - Add new step for input fields
   - Pass input_fields to config_json

2. **`use-case-edit.component.ts`**
   - Support editing input_fields
   - Load existing fields for editing

---

## Implementation Plan

### Phase 1: Core Editor Component (1 week)

**Tasks:**
1. Create `input-fields-editor.component.ts`
   - Array management (add/remove/reorder)
   - State management for field list

2. Create `input-field-card.component.ts`
   - Form for single field configuration
   - Basic fields (name, type, label, description)
   - Required/placeholder/default value

3. Add validation logic
   - Name uniqueness
   - Required fields filled
   - Select fields have options

### Phase 2: Select Field Support (3 days)

**Tasks:**
1. Create `input-field-options-editor.component.ts`
   - Add/remove options
   - Value/label pairs
   - Validation

2. Conditional rendering in field card
   - Show options editor only for type=select
   - Validate at least one option exists

### Phase 3: Preview Panel (3 days)

**Tasks:**
1. Create `input-form-preview.component.ts`
   - Dynamic form generation
   - Real-time updates
   - Mock data display

2. Add preview to editor layout
   - Side-by-side or tabbed view
   - Toggle preview visibility

### Phase 4: Wizard Integration (2 days)

**Tasks:**
1. Add step to `use-case-wizard.component.ts`
   - Insert after basic info step
   - Wire up to config_json

2. Update wizard navigation
   - Skip logic for optional fields
   - Preserve field data across steps

### Phase 5: Edit Support (2 days)

**Tasks:**
1. Update `use-case-edit.component.ts`
   - Load input_fields from existing use case
   - Populate editor with existing fields

2. Add edit warning
   - Warn if removing fields
   - Confirm changes

### Phase 6: Polish & Testing (3 days)

**Tasks:**
1. Add drag-and-drop reordering
2. Add copy/duplicate field
3. Improve UI/UX
4. Write unit tests
5. Write E2E tests
6. Documentation

**Total Estimated Time:** 3 weeks

---

## UI Mockup

### Input Fields Editor

```
┌─────────────────────────────────────────────────────────────────┐
│ Input Fields Configuration                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Define structured input fields for this use case. Leave empty  │
│ for conversational mode.                                       │
│                                                                 │
│ ┌───────────────────────────────────────────────────────────┐ │
│ │ Field 1: Query                                         ⋮ ✕ │ │
│ │                                                           │ │
│ │ Name: query                     Type: Textarea ▼          │ │
│ │ Label: Analysis Query                                     │ │
│ │ Description: Enter your security analysis query          │ │
│ │ ☑ Required                                                │ │
│ │ Placeholder: Example: Analyze this PowerShell command...  │ │
│ │ Default Value: _______________                            │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌───────────────────────────────────────────────────────────┐ │
│ │ Field 2: Severity                                      ⋮ ✕ │ │
│ │                                                           │ │
│ │ Name: severity                  Type: Select ▼            │ │
│ │ Label: Severity Level                                     │ │
│ │ Description: Select the severity level                    │ │
│ │ ☑ Required                                                │ │
│ │                                                           │ │
│ │ Options:                                                  │ │
│ │   • Low                    [low]                       ✕  │ │
│ │   • Medium                 [medium]                    ✕  │ │
│ │   • High                   [high]                      ✕  │ │
│ │   • Critical               [critical]                  ✕  │ │
│ │   + Add Option                                            │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│ + Add Input Field                                              │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ Preview                                                     ││
│ │                                                             ││
│ │ Analysis Query *                                            ││
│ │ ┌───────────────────────────────────────────────────────┐ ││
│ │ │ Enter your security analysis query                    │ ││
│ │ │ Example: Analyze this PowerShell command...           │ ││
│ │ └───────────────────────────────────────────────────────┘ ││
│ │                                                             ││
│ │ Severity Level *                                            ││
│ │ [ Low        ▼]                                             ││
│ │ Select the severity level                                   ││
│ └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## Testing Strategy

### Unit Tests

1. **Input Fields Editor Component**
   - Add field
   - Remove field
   - Reorder fields
   - Validate field uniqueness
   - Validate required fields

2. **Field Card Component**
   - Configure each field type
   - Validation logic
   - Options editor (for select)

3. **Preview Component**
   - Dynamic form generation
   - Field rendering for each type

### Integration Tests

1. **Wizard Flow**
   - Create use case with input fields
   - Save and verify config_json
   - Load and edit existing fields

2. **Backend Integration**
   - Validate config_json schema
   - Ensure input_fields persist correctly

### E2E Tests

1. **Create Use Case with Input Fields**
   - Navigate through wizard
   - Add multiple field types
   - Preview form
   - Save use case
   - Execute use case with structured inputs

2. **Edit Existing Use Case**
   - Load use case with input fields
   - Edit fields
   - Remove fields
   - Save changes

---

## Acceptance Criteria

- ✅ User can add input fields in Use Case Wizard
- ✅ User can configure all field properties (name, type, label, etc.)
- ✅ User can add/edit/remove select field options
- ✅ User can preview how input form will render
- ✅ User can reorder fields (drag-and-drop)
- ✅ User can copy/duplicate fields
- ✅ Validation ensures field names are unique
- ✅ Validation ensures select fields have options
- ✅ Use cases created with input fields save correctly
- ✅ Use cases with input fields can be edited
- ✅ Input form renders correctly in use case execution UI
- ✅ Unit tests pass (80%+ coverage)
- ✅ E2E tests pass
- ✅ Documentation updated

---

## Dependencies

### Technical Dependencies

- Angular Material (form components, drag-and-drop)
- Angular Reactive Forms (validation)
- Existing wizard infrastructure

### Blocked By

- None (can start immediately)

### Blocks

- Full ADR-044 implementation (Bounded Refinement Spaces)

---

## Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Complex UI for field editor | Medium | Medium | Incremental development, user testing |
| Performance with many fields | Low | Medium | Virtual scrolling, efficient rendering |
| Validation complexity | Medium | Medium | Comprehensive unit tests |
| Breaking existing use cases | Low | High | Thorough testing, backward compatibility |

---

## Rollout Plan

### Phase 1: Beta (Internal Testing)
- Deploy to test environment
- Internal team testing
- Gather feedback

### Phase 2: Production (Gradual Rollout)
- Deploy to production
- Monitor for issues
- Document known limitations

### Phase 3: Enhancement
- Address feedback
- Add advanced features (conditional fields, validation rules)

---

## Future Enhancements (Out of Scope)

1. **Conditional Field Visibility**
   - Show/hide fields based on other field values

2. **Advanced Validation Rules**
   - Regex patterns
   - Min/max length
   - Custom validation functions

3. **Field Groups**
   - Organize fields into collapsible sections

4. **Import/Export Templates**
   - Save field configurations as templates
   - Reuse across multiple use cases

---

## Related Documents

- **ADR-044:** Bounded Refinement Spaces (Use Cases as Iterative Refinement Workflows)
- **DB_REFRESH_03_FIX_SEED_USE_CASES.md:** Seed file bug fixes (discovered this issue)
- `src/orchestrator/app/schemas/use_case_config.py` - Schema definitions
- `src/frontend-angular/src/app/pages/use-cases/` - Existing wizard components

---

## Notes

### Why This Was Missed

The input_fields feature was likely added to the backend schema (UseCaseConfig) but the corresponding UI implementation was never completed. This is a common issue when backend and frontend development are not synchronized.

### User Impact

**High Priority Use Cases:**
- Security analysts creating IOC lookup forms (multiple typed inputs)
- Incident responders with structured incident forms
- Compliance teams with audit checklists

**Current Workaround:**
- Users must manually edit database records (not sustainable)
- Users can only create conversational-mode use cases

---

**Status:** 📋 PLANNED
**Estimated Effort:** 3 weeks
**Next Actions:**
1. Review and approve this task
2. Schedule for upcoming sprint
3. Assign to frontend developer
4. Create detailed sub-tasks in issue tracker
