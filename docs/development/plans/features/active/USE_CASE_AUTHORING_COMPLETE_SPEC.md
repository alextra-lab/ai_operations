# Use Case Authoring Complete Experience Specification

**Status:** Phases 1–4bis ✅ Complete — Phase 5 (Documentation, Polish & Deferred Completion) in progress
**Priority:** Critical
**Estimated Time:** Phase 5 ~22–28 hours (single block; no sprints)
**Phase:** Phase 5 — Documentation, tests, CI, and QA (executable from this spec)
**Date Created:** February 4, 2026
**Last Updated:** February 9, 2026 (breadcrumb fix, AIOps Library rename, Refine Schema flow fixes)
**Author:** AI Operations Platform Team

**Implementation Progress:** Phase 1 ✅ (2026-02-04). Phase 2 ✅ (2026-02-04). Phase 2.5 ✅ (2026-02-04). Phase 3 ✅ (2026-02-04). Phase 4 ✅ (2026-02-05). Phase 4bis ✅ (2026-02-06). **Phase 5** — follow [Phase 5: Documentation, Polish & Completing Deferred Work](#phase-5-documentation-polish--completing-deferred-work) task list in this spec to close the feature.

**Dependencies:**

- P3-F2 (Use Case Management - complete)
- P3-F5 (Output Formatting Engine - complete)
- ADR-018 (Use Case Owned Architecture)
- ADR-044 (Use Cases as Bounded Refinement Spaces)
- ADR-062 (User Prompt Templates Parameter Injection)
- ADR-063 (Structured Output End-to-End Pipeline) + Amendments 1 & 2
- ADR-064 (User Interaction Combined Panel) + Amendment
- ADR-065 (Wizard Step Restructuring)
- ADR-066 (Domain-Neutral Visualization Templates)
- ADR-067 (Dynamic Categories, Intent Capability Profiles, Auto-Presets)
- ADR-068 (Portable Visualization Specification — Vega-Lite)
- ADR-069 (Intent Model Configuration System)

---

## Executive Summary

This specification defines the complete implementation needed to enable AI Ops developers to create fully-configured, interactive use cases through the wizard UI.

**Completed:** Input Fields Configuration (Phase 1) — initially Step 4; moved to Step 3 per Phase 2.5. User Prompt Template (Phase 2) — Step 3. Phase 2.5 combined both into the "User Interaction" panel (Step 3) with {{variable}} placeholders, variable chips, preview, sync validation, and backend template_renderer + execution path.

**Remaining:**

1. ~~**Output Visualization Selection**~~ - Phase 4 ✅ Complete (2026-02-05)

**Business Value:** Without these capabilities, AI Ops developers cannot build custom, parameterized interactions. Phase 1 removes the "single generic query field" limitation for authoring; Phases 2–4 complete the end-to-end experience.

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Gap Analysis](#gap-analysis)
3. [Feature 1: Input Fields Configuration](#feature-1-input-fields-configuration)
4. [Feature 2: User Prompt Template](#feature-2-user-prompt-template)
5. [Feature 2.5: User Interaction Combined Panel](#feature-25-user-interaction-combined-panel)
6. [Feature 3: Structured Output Pipeline](#feature-3-structured-output-pipeline)
7. [Feature 4: Output Visualization Configuration](#feature-4-output-visualization-configuration)
8. [Implementation Phases](#implementation-phases) — **[Phase 5 (current work)](#phase-5-documentation-polish--completing-deferred-work)** is the executable task list
9. [Technical Specifications](#technical-specifications)
10. [Testing Strategy](#testing-strategy)
11. [Success Criteria](#success-criteria)

---

## Current State Analysis

### Wizard Steps (Current → Target)

| Step | Name | Current Status | Target (Post Phase 2.5) |
| ------ | ------ | ---------------- | ------------------------- |
| 1 | Basic Info | ✅ Complete | Name, description, category, intent |
| 2 | Starting Point | ✅ Complete | Blank/pattern/clone (create mode) |
| 3 | Edit Prompts | ✅ Complete | System, developer, fewshots, **User Interaction Panel** (combined Input Fields + User Prompt Template) |
| 4 | Configure | ✅ Complete | Models, RAG, Tools, Output Contract, Policies (Input Fields **moved to Step 3**) |
| 5 | Preview & Save | ✅ Complete | Summary and validation |

**Phase 2.5 Change:** Input Fields panel moves from Step 4 to Step 3, combined with User Prompt Template in a unified "User Interaction" panel. See ADR-064.

### Current Hardcoded Behavior

```typescript
// src/frontend-angular/src/app/pages/use-cases/use-case-wizard.component.ts
// Lines 905-915 (create) and 1001-1015 (update)

// Every use case gets this default field - no customization possible
input_fields: [
  {
    name: 'query',
    type: 'textarea',
    label: 'Query',
    description: 'Enter your query',
    required: true,
    placeholder: 'Enter your query here...'
  }
]
```

### What Exists But Isn't Connected

| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| InputField interface | `use-case.models.ts` | Data model for fields | ✅ Exists |
| DynamicFieldComponent | `features/dynamic-forms/` | Renders form fields | ✅ Exists (execution) |
| DynamicFormComponent | `features/dynamic-forms/` | Generates forms | ✅ Exists (execution) |
| DynamicFormService | `features/dynamic-forms/` | Form generation service | ✅ Exists |
| OutputContractConfig | `use_case_config.py` | Schema validation config | ✅ Exists (backend) |
| OutputFormattingService | `services/` | Template rendering | ✅ Exists |
| StructuredOutputRenderer | `components/` | Visualizers | ✅ Exists |
| TemplateRegistryService | `services/` | Built-in templates | ✅ Exists |

**Key Insight:** The components exist for both input field rendering and output visualization - they're just not wired into the wizard or execution pipeline.

---

## Gap Analysis

### Gap 1: Input Fields Configuration (Critical)

**Problem:** No UI to configure `input_fields` in the wizard.

**Impact:**

- Every use case has identical generic "Query" field
- Cannot create structured inputs (incident IDs, severity dropdowns, date ranges)
- Cannot validate user input (types, patterns, required fields)
- Cannot build parameterized interactions

**Solution:** Add Input Fields Builder section. Originally Step 4; per Phase 2.5, Input Fields are now in Step 3 (User Interaction panel).

### Gap 2: User Prompt Template (High)

**Problem:** Parameters are concatenated as `"key: value"` strings, not merged into templates.

**Current Code:**

```python
# src/orchestrator/app/routers/use_cases.py:438-445
query_parts = []
for field_name, field_value in execution.inputs.items():
    query_parts.append(f"{field_name}: {field_value}")
query_text = "\n".join(query_parts)  # Becomes the entire "query"
```

**Impact:**

- No control over how parameters appear in prompts
- Cannot add contextual framing around parameters
- Prompts are not optimized for specific use cases

**Solution:** Add user prompt template with `{{variable}}` placeholder support.

### Gap 3: Structured Output Not Returned (High)

**Problem:** Backend validates structured output but doesn't return it.

**Current Flow:**

```text
Use Case Config (output_schema defined)
  → LLM Response (text)
  → ResponseFormatter.validate_output() ← validates but discards
  → FormattedResponse ← no structured_data field
  → Frontend ← receives only text
```

**Impact:**

- Visualizers cannot render structured data
- Output Contract is essentially unused
- P3-F5 components are orphaned

**Solution:** Complete the pipeline to extract and return `structured_data`.

### Gap 4: Output Visualization Not Configurable (Medium)

**Problem:** Output Contract section lacks template selection and configuration.

**Current UI:**

- Output Format dropdown
- Validation Mode dropdown
- Raw JSON Schema textarea

**Missing:**

- Template selection dropdown
- Visual schema builder
- Preview with sample data

---

## Feature 1: Input Fields Configuration

### 1.1 User Experience

**Location:** Step 3 (Edit Prompts) — "User Input Fields" tab within the User Interaction panel. (Originally Step 4; moved per Phase 2.5.)

#### Wireframe: Input Fields Builder

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ 🔧 User Input Fields                                                    │
│                                                                          │
│ Define the input fields that users will fill in when executing this     │
│ use case. Fields are displayed in order.                                │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ 📝 incident_id                                              [↑][↓][✕]│ │
│ ├─────────────────────────────────────────────────────────────────────┤ │
│ │ Type: [Text ▼]      Label: [Incident ID        ]  [✓] Required     │ │
│ │ Description: [Enter the incident ID to analyze                    ]│ │
│ │ Placeholder: [e.g., INC-12345                                     ]│ │
│ │ Default Value: [                                                  ]│ │
│ │                                                                     │ │
│ │ ▸ Advanced Validation                                              │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ 📝 severity                                                 [↑][↓][✕]│ │
│ ├─────────────────────────────────────────────────────────────────────┤ │
│ │ Type: [Select ▼]    Label: [Severity Filter   ]  [✓] Required     │ │
│ │ Description: [Filter by severity level                            ]│ │
│ │                                                                     │ │
│ │ Options (for select fields):                                        │ │
│ │ ┌────────────────────────────────────────────────────────────────┐ │ │
│ │ │ [critical] → [Critical    ]                              [✕]  │ │ │
│ │ │ [high    ] → [High        ]                              [✕]  │ │ │
│ │ │ [medium  ] → [Medium      ]                              [✕]  │ │ │
│ │ │ [low     ] → [Low         ]                              [✕]  │ │ │
│ │ │ [+ Add Option]                                                 │ │ │
│ │ └────────────────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ 📝 time_range                                               [↑][↓][✕]│ │
│ ├─────────────────────────────────────────────────────────────────────┤ │
│ │ Type: [Text ▼]      Label: [Time Range        ]  [ ] Required     │ │
│ │ Description: [Optional: Specify time range for analysis           ]│ │
│ │ Placeholder: [e.g., last 24 hours, 2025-01-01 to 2025-01-15       ]│ │
│ │ Default Value: [last 7 days                                       ]│ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│ [+ Add Input Field]                                                      │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│ 👁️ Form Preview                                          [Show Preview] │
│                                                                          │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │                    Incident Analysis                                 │ │
│ │                                                                      │ │
│ │ Incident ID *                                                        │ │
│ │ ┌──────────────────────────────────────────────────────────────────┐│ │
│ │ │ e.g., INC-12345                                                  ││ │
│ │ └──────────────────────────────────────────────────────────────────┘│ │
│ │                                                                      │ │
│ │ Severity Filter *                                                    │ │
│ │ ┌──────────────────────────────────────────────────────────────────┐│ │
│ │ │ Select severity... ▼                                             ││ │
│ │ └──────────────────────────────────────────────────────────────────┘│ │
│ │                                                                      │ │
│ │ Time Range                                                           │ │
│ │ ┌──────────────────────────────────────────────────────────────────┐│ │
│ │ │ last 7 days                                                      ││ │
│ │ └──────────────────────────────────────────────────────────────────┘│ │
│ └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Specification

#### New Component: InputFieldBuilderComponent

```typescript
// src/frontend-angular/src/app/components/input-field-builder/

@Component({
  selector: 'app-input-field-builder',
  templateUrl: './input-field-builder.component.html',
  styleUrls: ['./input-field-builder.component.scss']
})
export class InputFieldBuilderComponent {
  @Input() fields: InputField[] = [];
  @Output() fieldsChange = new EventEmitter<InputField[]>();

  // Supported field types
  fieldTypes = [
    { value: 'text', label: 'Text', icon: 'text_fields' },
    { value: 'textarea', label: 'Text Area', icon: 'notes' },
    { value: 'select', label: 'Dropdown', icon: 'arrow_drop_down_circle' },
    { value: 'number', label: 'Number', icon: 'pin' },
    { value: 'checkbox', label: 'Checkbox', icon: 'check_box' },
    { value: 'date', label: 'Date', icon: 'calendar_today' }
  ];

  addField(): void { /* ... */ }
  removeField(index: number): void { /* ... */ }
  moveField(from: number, to: number): void { /* ... */ }
  onFieldChange(index: number, field: InputField): void { /* ... */ }
}
```

#### New Component: InputFieldEditorComponent

```typescript
// Single field editor with all properties

@Component({
  selector: 'app-input-field-editor',
  templateUrl: './input-field-editor.component.html'
})
export class InputFieldEditorComponent {
  @Input() field!: InputField;
  @Output() fieldChange = new EventEmitter<InputField>();
  @Output() remove = new EventEmitter<void>();
  @Output() moveUp = new EventEmitter<void>();
  @Output() moveDown = new EventEmitter<void>();

  showAdvancedValidation = false;
}
```

### 1.3 Data Model

```typescript
// Already exists in use-case.models.ts - ensure completeness

export interface InputField {
  name: string;                    // Field identifier (used in template)
  type: InputFieldType;            // text | textarea | select | number | checkbox | date
  label: string;                   // Display label
  description?: string;            // Help text
  required: boolean;               // Required validation
  placeholder?: string;            // Placeholder text
  default_value?: string | number | boolean;  // Default value
  options?: SelectOption[];        // For select fields
  validation?: FieldValidation;    // Advanced validation rules
}

export interface SelectOption {
  value: string;
  label: string;
}

export interface FieldValidation {
  min_length?: number;
  max_length?: number;
  min_value?: number;
  max_value?: number;
  pattern?: string;                // Regex pattern
  pattern_message?: string;        // Error message for pattern
}

export type InputFieldType = 'text' | 'textarea' | 'select' | 'number' | 'checkbox' | 'date';
```

### 1.4 Wizard Integration

```typescript
// use-case-wizard.component.ts modifications

// Add to configForm
inputFieldsForm = this.fb.array([]);

// New method
private initializeInputFields(fields: InputField[]): void {
  this.inputFieldsForm.clear();
  fields.forEach(field => {
    this.inputFieldsForm.push(this.createFieldFormGroup(field));
  });
}

// Create form group for a field
private createFieldFormGroup(field: InputField): FormGroup {
  return this.fb.group({
    name: [field.name, [Validators.required, Validators.pattern(/^[a-z_][a-z0-9_]*$/)]],
    type: [field.type, Validators.required],
    label: [field.label, Validators.required],
    description: [field.description || ''],
    required: [field.required],
    placeholder: [field.placeholder || ''],
    default_value: [field.default_value || ''],
    options: [field.options || []],
    validation: this.fb.group({
      min_length: [field.validation?.min_length],
      max_length: [field.validation?.max_length],
      min_value: [field.validation?.min_value],
      max_value: [field.validation?.max_value],
      pattern: [field.validation?.pattern],
      pattern_message: [field.validation?.pattern_message]
    })
  });
}

// Update buildConfigJson() to include inputFieldsForm values
```

---

## Feature 2: User Prompt Template

### 2.1 User Experience

**Location:** Step 3 (Edit Prompts) - New "User Prompt Template" expansion panel

#### Wireframe: User Prompt Template Editor

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ 📝 User Prompt Template                                                 │
│                                                                          │
│ Define how user inputs are presented to the LLM. Use {{variable_name}}  │
│ to insert input field values.                                           │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ Available Variables (from Input Fields):                                 │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ [{{incident_id}}] [{{severity}}] [{{time_range}}]                  │  │
│ │  Click to insert                                                    │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ Analyze the following security incident:                           │  │
│ │                                                                     │  │
│ │ **Incident ID:** {{incident_id}}                                   │  │
│ │ **Severity Filter:** {{severity}}                                  │  │
│ │ **Time Range:** {{time_range}}                                     │  │
│ │                                                                     │  │
│ │ Please provide:                                                     │  │
│ │ 1. Executive summary of the incident                               │  │
│ │ 2. Timeline of key events                                          │  │
│ │ 3. List of indicators of compromise (IOCs)                         │  │
│ │ 4. Recommended response actions                                     │  │
│ │                                                                     │  │
│ │ Format the response as structured JSON.                            │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│ Variable Status:                                                         │
│ ✅ incident_id - Defined in Input Fields                                │
│ ✅ severity - Defined in Input Fields                                   │
│ ✅ time_range - Defined in Input Fields                                 │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│ 👁️ Template Preview (with sample data)                  [Show Preview] │
│                                                                          │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ Analyze the following security incident:                           │  │
│ │                                                                     │  │
│ │ **Incident ID:** INC-12345                                         │  │
│ │ **Severity Filter:** high                                          │  │
│ │ **Time Range:** last 7 days                                        │  │
│ │                                                                     │  │
│ │ Please provide:                                                     │  │
│ │ 1. Executive summary of the incident                               │  │
│ │ 2. Timeline of key events                                          │  │
│ │ ...                                                                 │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│ ℹ️ If no template is defined, inputs will be sent as "field: value"    │
│    format (legacy behavior).                                             │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Schema Changes

#### Backend: Add to UseCaseConfig

```python
# src/orchestrator/app/schemas/use_case_config.py

class UserPromptTemplateConfig(BaseModel):
    """Configuration for user-facing prompt template with variable injection."""

    template: str = Field(
        description="User prompt template with {{variable}} placeholders"
    )
    variables: list[str] = Field(
        default_factory=list,
        description="Declared variables (auto-extracted if empty)"
    )
    fallback_mode: Literal["concatenate", "error"] = Field(
        default="concatenate",
        description="Behavior when input field missing: concatenate (legacy) or error"
    )

class UseCaseConfig(BaseModel):
    # ... existing fields ...

    # NEW: User prompt template
    user_prompt_template: UserPromptTemplateConfig | None = Field(
        default=None,
        description="Optional user prompt template. If None, uses legacy concatenation."
    )
```

#### Frontend: Add to TypeScript Models

```typescript
// src/frontend-angular/src/app/api/models/use-case.models.ts

export interface UserPromptTemplateConfig {
  template: string;
  variables: string[];
  fallback_mode: 'concatenate' | 'error';
}

// Add to UseCaseConfig interface
export interface UseCaseConfig {
  // ... existing fields ...
  user_prompt_template?: UserPromptTemplateConfig;
}
```

### 2.3 Template Rendering Logic

```python
# src/orchestrator/app/orchestrator/template_renderer.py (new file)

import re
from typing import Any

VARIABLE_PATTERN = re.compile(r'\{\{(\w+)\}\}')

def render_user_prompt_template(
    template: str,
    inputs: dict[str, Any],
    fallback_mode: str = "concatenate"
) -> str:
    """
    Render user prompt template with input values.

    Args:
        template: Template string with {{variable}} placeholders
        inputs: Dictionary of input field values
        fallback_mode: How to handle missing variables

    Returns:
        Rendered template string

    Raises:
        ValueError: If fallback_mode is "error" and variable is missing
    """
    def replace_variable(match: re.Match) -> str:
        var_name = match.group(1)
        if var_name in inputs:
            return str(inputs[var_name])
        elif fallback_mode == "error":
            raise ValueError(f"Missing required variable: {var_name}")
        else:
            # concatenate mode: leave placeholder
            return f"[{var_name}: not provided]"

    return VARIABLE_PATTERN.sub(replace_variable, template)


def extract_template_variables(template: str) -> list[str]:
    """Extract all variable names from a template."""
    return list(set(VARIABLE_PATTERN.findall(template)))


def validate_template_variables(
    template: str,
    input_fields: list[dict]
) -> tuple[list[str], list[str]]:
    """
    Validate that template variables match input fields.

    Returns:
        Tuple of (matched_vars, unmatched_vars)
    """
    template_vars = set(extract_template_variables(template))
    field_names = {f['name'] for f in input_fields}

    matched = template_vars & field_names
    unmatched = template_vars - field_names

    return list(matched), list(unmatched)
```

### 2.4 Execution Path Integration

```python
# src/orchestrator/app/routers/use_cases.py - modify execute_use_case

# BEFORE (current):
query_parts = []
for field_name, field_value in execution.inputs.items():
    query_parts.append(f"{field_name}: {field_value}")
query_text = "\n".join(query_parts)

# AFTER (with template support):
from ..orchestrator.template_renderer import render_user_prompt_template

if use_case_config.user_prompt_template:
    # Use template-based rendering
    query_text = render_user_prompt_template(
        template=use_case_config.user_prompt_template.template,
        inputs=execution.inputs,
        fallback_mode=use_case_config.user_prompt_template.fallback_mode
    )
else:
    # Legacy concatenation (backward compatible)
    query_parts = []
    for field_name, field_value in execution.inputs.items():
        query_parts.append(f"{field_name}: {field_value}")
    query_text = "\n".join(query_parts)
```

---

## Feature 2.5: User Interaction Combined Panel

> **ADR:** ADR-064-User-Interaction-Combined-Panel.md
> **Priority:** HIGH (UX Critical)
> **Status:** ✅ Complete (2026-02-04)

### 2.5.1 Problem Statement

The current wizard has a **workflow dependency inversion** problem:

| Step | Panel | What It Configures |
|------|-------|-------------------|
| Step 3 | Edit Prompts | User Prompt Template with `{{variable}}` placeholders |
| Step 4 | Configure | User Input Fields that define available variables |

**The Problem:** When editing the User Prompt Template in Step 3, the editor needs to know which input fields exist to show available variable chips. But input fields are defined in Step 4, which comes *after* Step 3.

```html
<!-- Current: Template editor receives fields that aren't defined yet -->
<app-user-prompt-template-editor
  [inputFields]="inputFields"  <!-- Empty or stale in create mode! -->
  [value]="userPromptTemplate"
  (valueChange)="userPromptTemplate = $event">
</app-user-prompt-template-editor>
```

**Consequences:**

1. No guidance on available variables when writing templates
2. Users must jump back-and-forth between steps
3. No validation that template variables match actual input fields
4. Easy to create broken configurations (e.g., template uses `{{severity}}` but no `severity` field exists)
5. Poor discoverability of the connection between fields and template

### 2.5.2 Solution: Combined "User Interaction" Panel

Create a unified expansion panel in Step 3 that combines Input Fields and User Prompt Template with:

1. **Tabbed interface** - Tab 1: Input Fields, Tab 2: User Prompt Template
2. **Real-time synchronization validation** - Shows sync status for all fields/variables
3. **Auto-generate template** - Creates starter template from defined fields (new templates only)
4. **Helper actions** - Quick buttons to fix mismatches

### 2.5.3 UI Wireframe

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ 👤 User Interaction                                              [▼/▲] │
│                                                                          │
│ Configure user inputs and how they appear in the prompt                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ ┌──────────────────┐ ┌────────────────────────┐                         │
│ │ 1. Input Fields  │ │ 2. User Prompt Template │                        │
│ └──────────────────┘ └────────────────────────┘                         │
│ ━━━━━━━━━━━━━━━━━━━                                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ [TAB CONTENT]                                                            │
│                                                                          │
│ Tab 1: InputFieldBuilderComponent (existing)                            │
│   - Add/edit/reorder input fields                                        │
│   - Field types: text, textarea, select, number, checkbox, date         │
│   - Validation rules: required, min/max, pattern                        │
│                                                                          │
│ Tab 2: UserPromptTemplateEditorComponent (existing)                     │
│   - Variable chips (from input fields)                                   │
│   - Template textarea with {{variable}} placeholders                    │
│   - Preview with sample data                                             │
│   - Fallback mode selector                                               │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│ 📊 Field & Template Sync Status                                          │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ ✅ incident_id    │ Synced - defined and used in template          │  │
│ │ ✅ severity       │ Synced - defined and used in template          │  │
│ │ ⚠️ time_range     │ Warning - defined but NOT used in template     │  │
│ │ ❌ analyst_notes  │ Error - used in template but NO field defined  │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│ [+ Create "analyst_notes" field]  [Insert "time_range" into template]  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.5.4 Auto-Generate Template

When input fields are defined but the template is empty, show a generation button:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ 💡 No template defined yet.                                             │
│                                                                          │
│ [✨ Generate Template from Fields]                                       │
│                                                                          │
│ Creates a starter template with all your input fields.                  │
└────────────────────────────────────────────────────────────────────────┘
```

**Generation Rules:**

- Only available when `template` is empty/null/whitespace
- **Never overwrites** existing template content
- Uses field labels for human-readable output
- Adds generic closing instruction

**Example Generated Template:**

```text
Incident ID: {{incident_id}}
Severity: {{severity}}
Time Range: {{time_range}}

Please analyze the above information and provide your response.
```

**Implementation:**

```typescript
generateTemplate(): void {
  if (!this.canGenerateTemplate) return;

  const lines = this.inputFields.map(f =>
    `${f.label || this.formatLabel(f.name)}: {{${f.name}}}`
  );
  lines.push('');
  lines.push('Please analyze the above information and provide your response.');

  this.userPromptTemplateChange.emit({
    template: lines.join('\n'),
    variables: this.inputFields.map(f => f.name),
    fallback_mode: 'concatenate'
  });
}

get canGenerateTemplate(): boolean {
  return this.inputFields.length > 0 &&
         (!this.userPromptTemplate || !this.userPromptTemplate.template?.trim());
}
```

### 2.5.5 Validation Rules

| Status | Icon | Condition | Severity | Blocks Save? | Action |
|--------|------|-----------|----------|--------------|--------|
| **Synced** | ✅ | Field exists AND used in template | None | No | — |
| **Field Only** | ⚠️ | Field exists but NOT in template | Warning | No | "Insert into template" |
| **Template Only** | ❌ | In template but NO field defined | **Error** | **Yes** | "Create field" |

**Rationale:**

- **Template Only = Error**: Variable cannot be populated at runtime; always a configuration mistake
- **Field Only = Warning**: Field might be used for metadata, logging, or future use; acceptable but worth noting

### 2.5.6 Component Architecture

```text
Step 3: Edit Prompts
├── System Prompt (existing)
├── Developer Prompt (existing)
├── Few-Shot Examples (existing)
└── UserInteractionConfigComponent (NEW)
    ├── MatTabGroup
    │   ├── Tab 1: InputFieldBuilderComponent (existing, moved from Step 4)
    │   └── Tab 2: UserPromptTemplateEditorComponent (existing, moved within Step 3)
    ├── FieldTemplateSyncStatusComponent (NEW)
    └── Auto-generate template button (conditional)
```

### 2.5.7 New Component: UserInteractionConfigComponent

**File:** `src/frontend-angular/src/app/components/user-interaction-config/user-interaction-config.component.ts`

```typescript
/**
 * Combined panel for Input Fields and User Prompt Template configuration.
 * Provides tabbed interface with real-time synchronization validation.
 *
 * @see ADR-064-User-Interaction-Combined-Panel.md
 */
import { CommonModule } from '@angular/common';
import {
  Component,
  EventEmitter,
  Input,
  Output,
  computed,
  signal,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  InputField,
  UserPromptTemplateConfig,
} from '../../api/models/use-case.models';
import { InputFieldBuilderComponent } from '../input-field-builder/input-field-builder.component';
import { UserPromptTemplateEditorComponent } from '../user-prompt-template-editor/user-prompt-template-editor.component';
import { FieldTemplateSyncStatusComponent } from '../field-template-sync-status/field-template-sync-status.component';

/** Sync status for a single field/variable */
export interface FieldSyncStatus {
  fieldName: string;
  status: 'synced' | 'field_only' | 'template_only';
  message: string;
}

/** Overall validation result */
export interface SyncValidationResult {
  isValid: boolean;
  statuses: FieldSyncStatus[];
  errors: FieldSyncStatus[];
  warnings: FieldSyncStatus[];
}

const VARIABLE_PATTERN = /\{\{(\w+)\}\}/g;

function extractTemplateVariables(template: string): string[] {
  const set = new Set<string>();
  let m: RegExpExecArray | null;
  VARIABLE_PATTERN.lastIndex = 0;
  while ((m = VARIABLE_PATTERN.exec(template)) !== null) {
    set.add(m[1]);
  }
  return Array.from(set);
}

@Component({
  selector: 'app-user-interaction-config',
  templateUrl: './user-interaction-config.component.html',
  styleUrls: ['./user-interaction-config.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatExpansionModule,
    MatIconModule,
    MatTabsModule,
    MatTooltipModule,
    InputFieldBuilderComponent,
    UserPromptTemplateEditorComponent,
    FieldTemplateSyncStatusComponent,
  ],
})
export class UserInteractionConfigComponent {
  @Input() inputFields: InputField[] = [];
  @Output() inputFieldsChange = new EventEmitter<InputField[]>();

  @Input() userPromptTemplate: UserPromptTemplateConfig | null = null;
  @Output() userPromptTemplateChange = new EventEmitter<UserPromptTemplateConfig | null>();

  @Output() validationChange = new EventEmitter<SyncValidationResult>();

  selectedTabIndex = signal(0);

  /** Compute sync status whenever inputs change */
  get syncStatus(): FieldSyncStatus[] {
    return this.computeSyncStatus();
  }

  get validationResult(): SyncValidationResult {
    const statuses = this.syncStatus;
    const errors = statuses.filter(s => s.status === 'template_only');
    const warnings = statuses.filter(s => s.status === 'field_only');
    return {
      isValid: errors.length === 0,
      statuses,
      errors,
      warnings,
    };
  }

  get hasErrors(): boolean {
    return this.validationResult.errors.length > 0;
  }

  get hasWarnings(): boolean {
    return this.validationResult.warnings.length > 0;
  }

  get canGenerateTemplate(): boolean {
    return (
      this.inputFields.length > 0 &&
      (!this.userPromptTemplate ||
        !this.userPromptTemplate.template?.trim())
    );
  }

  private computeSyncStatus(): FieldSyncStatus[] {
    const fieldNames = new Set(this.inputFields.map(f => f.name));
    const templateVars = new Set(
      this.userPromptTemplate?.template
        ? extractTemplateVariables(this.userPromptTemplate.template)
        : []
    );

    const results: FieldSyncStatus[] = [];

    // Check fields
    for (const fieldName of fieldNames) {
      if (templateVars.has(fieldName)) {
        results.push({
          fieldName,
          status: 'synced',
          message: 'Defined and used in template',
        });
      } else {
        results.push({
          fieldName,
          status: 'field_only',
          message: 'Defined but NOT used in template',
        });
      }
    }

    // Check template vars without fields
    for (const varName of templateVars) {
      if (!fieldNames.has(varName)) {
        results.push({
          fieldName: varName,
          status: 'template_only',
          message: 'Used in template but NO field defined',
        });
      }
    }

    return results;
  }

  onInputFieldsChange(fields: InputField[]): void {
    this.inputFieldsChange.emit(fields);
    this.emitValidation();
  }

  onUserPromptTemplateChange(
    template: UserPromptTemplateConfig | null
  ): void {
    this.userPromptTemplateChange.emit(template);
    this.emitValidation();
  }

  private emitValidation(): void {
    // Use setTimeout to ensure inputs are updated
    setTimeout(() => {
      this.validationChange.emit(this.validationResult);
    }, 0);
  }

  generateTemplate(): void {
    if (!this.canGenerateTemplate) return;

    const lines = this.inputFields.map(
      f => `${f.label || this.formatLabel(f.name)}: {{${f.name}}}`
    );
    lines.push('');
    lines.push(
      'Please analyze the above information and provide your response.'
    );

    this.userPromptTemplateChange.emit({
      template: lines.join('\n'),
      variables: this.inputFields.map(f => f.name),
      fallback_mode: 'concatenate',
    });

    // Switch to template tab to show result
    this.selectedTabIndex.set(1);
  }

  createFieldFromVariable(varName: string): void {
    const newField: InputField = {
      name: varName,
      type: 'text',
      label: this.formatLabel(varName),
      description: '',
      required: true,
      placeholder: `Enter ${this.formatLabel(varName).toLowerCase()}`,
    };
    this.inputFieldsChange.emit([...this.inputFields, newField]);
    // Switch to fields tab
    this.selectedTabIndex.set(0);
  }

  insertFieldIntoTemplate(fieldName: string): void {
    const placeholder = `{{${fieldName}}}`;
    const current = this.userPromptTemplate?.template || '';
    const updated = current + (current ? '\n' : '') + placeholder;

    this.userPromptTemplateChange.emit({
      template: updated,
      variables: extractTemplateVariables(updated),
      fallback_mode: this.userPromptTemplate?.fallback_mode || 'concatenate',
    });
    // Switch to template tab
    this.selectedTabIndex.set(1);
  }

  private formatLabel(name: string): string {
    return name
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
  }
}
```

### 2.5.8 New Component: FieldTemplateSyncStatusComponent

**File:** `src/frontend-angular/src/app/components/field-template-sync-status/field-template-sync-status.component.ts`

```typescript
/**
 * Displays synchronization status between input fields and template variables.
 * Shows synced, warnings (field_only), and errors (template_only).
 */
import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

import { FieldSyncStatus } from '../user-interaction-config/user-interaction-config.component';

@Component({
  selector: 'app-field-template-sync-status',
  templateUrl: './field-template-sync-status.component.html',
  styleUrls: ['./field-template-sync-status.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
  ],
})
export class FieldTemplateSyncStatusComponent {
  @Input() statuses: FieldSyncStatus[] = [];

  @Output() createField = new EventEmitter<string>();
  @Output() insertIntoTemplate = new EventEmitter<string>();

  get syncedItems(): FieldSyncStatus[] {
    return this.statuses.filter(s => s.status === 'synced');
  }

  get warningItems(): FieldSyncStatus[] {
    return this.statuses.filter(s => s.status === 'field_only');
  }

  get errorItems(): FieldSyncStatus[] {
    return this.statuses.filter(s => s.status === 'template_only');
  }

  get hasAnyItems(): boolean {
    return this.statuses.length > 0;
  }

  getIcon(status: FieldSyncStatus['status']): string {
    switch (status) {
      case 'synced':
        return 'check_circle';
      case 'field_only':
        return 'warning';
      case 'template_only':
        return 'error';
    }
  }

  getIconClass(status: FieldSyncStatus['status']): string {
    switch (status) {
      case 'synced':
        return 'text-green-600';
      case 'field_only':
        return 'text-amber-600';
      case 'template_only':
        return 'text-red-600';
    }
  }

  onCreateField(varName: string): void {
    this.createField.emit(varName);
  }

  onInsertIntoTemplate(fieldName: string): void {
    this.insertIntoTemplate.emit(fieldName);
  }
}
```

### 2.5.9 Template: FieldTemplateSyncStatusComponent

**File:** `src/frontend-angular/src/app/components/field-template-sync-status/field-template-sync-status.component.html`

```html
<div class="sync-status-container" *ngIf="hasAnyItems">
  <div class="sync-status-header">
    <mat-icon>sync</mat-icon>
    <span>Field & Template Sync Status</span>
    <span class="status-summary">
      <span *ngIf="errorItems.length > 0" class="error-count">
        {{ errorItems.length }} error{{ errorItems.length > 1 ? 's' : '' }}
      </span>
      <span *ngIf="warningItems.length > 0" class="warning-count">
        {{ warningItems.length }} warning{{ warningItems.length > 1 ? 's' : '' }}
      </span>
    </span>
  </div>

  <div class="sync-status-list">
    <!-- Errors first (template_only) -->
    <div
      *ngFor="let item of errorItems"
      class="sync-status-item error"
    >
      <mat-icon [class]="getIconClass(item.status)">
        {{ getIcon(item.status) }}
      </mat-icon>
      <span class="field-name">{{ item.fieldName }}</span>
      <span class="status-message">{{ item.message }}</span>
      <button
        mat-stroked-button
        color="primary"
        (click)="onCreateField(item.fieldName)"
        matTooltip="Create input field for this variable"
      >
        <mat-icon>add</mat-icon>
        Create Field
      </button>
    </div>

    <!-- Warnings (field_only) -->
    <div
      *ngFor="let item of warningItems"
      class="sync-status-item warning"
    >
      <mat-icon [class]="getIconClass(item.status)">
        {{ getIcon(item.status) }}
      </mat-icon>
      <span class="field-name">{{ item.fieldName }}</span>
      <span class="status-message">{{ item.message }}</span>
      <button
        mat-stroked-button
        (click)="onInsertIntoTemplate(item.fieldName)"
        matTooltip="Insert this field into the template"
      >
        <mat-icon>add</mat-icon>
        Insert
      </button>
    </div>

    <!-- Synced items (collapsed by default if many) -->
    <div
      *ngFor="let item of syncedItems"
      class="sync-status-item synced"
    >
      <mat-icon [class]="getIconClass(item.status)">
        {{ getIcon(item.status) }}
      </mat-icon>
      <span class="field-name">{{ item.fieldName }}</span>
      <span class="status-message">{{ item.message }}</span>
    </div>
  </div>
</div>

<div class="sync-status-empty" *ngIf="!hasAnyItems">
  <mat-icon>info</mat-icon>
  <span>Define input fields and a template to see sync status.</span>
</div>
```

### 2.5.10 Template: UserInteractionConfigComponent

**File:** `src/frontend-angular/src/app/components/user-interaction-config/user-interaction-config.component.html`

```html
<mat-expansion-panel [expanded]="true">
  <mat-expansion-panel-header>
    <mat-panel-title>
      <mat-icon>person</mat-icon>
      User Interaction
      <span class="validation-badge" *ngIf="hasErrors">
        <mat-icon class="text-red-600">error</mat-icon>
      </span>
      <span class="validation-badge" *ngIf="!hasErrors && hasWarnings">
        <mat-icon class="text-amber-600">warning</mat-icon>
      </span>
    </mat-panel-title>
    <mat-panel-description>
      Configure user inputs and how they appear in the prompt
    </mat-panel-description>
  </mat-expansion-panel-header>

  <!-- Tab Group -->
  <mat-tab-group
    [(selectedIndex)]="selectedTabIndex"
    class="user-interaction-tabs"
  >
    <!-- Tab 1: Input Fields -->
    <mat-tab>
      <ng-template mat-tab-label>
        <mat-icon>edit_note</mat-icon>
        <span>1. Input Fields</span>
        <span class="field-count" *ngIf="inputFields.length > 0">
          ({{ inputFields.length }})
        </span>
      </ng-template>

      <div class="tab-content">
        <p class="tab-description">
          Define the input fields that users fill in when executing this use case.
        </p>

        <app-input-field-builder
          [fields]="inputFields"
          (fieldsChange)="onInputFieldsChange($event)"
        ></app-input-field-builder>
      </div>
    </mat-tab>

    <!-- Tab 2: User Prompt Template -->
    <mat-tab>
      <ng-template mat-tab-label>
        <mat-icon>description</mat-icon>
        <span>2. User Prompt Template</span>
      </ng-template>

      <div class="tab-content">
        <p class="tab-description">
          Define how user inputs are merged into the prompt using
          <code>{{ '{{variable}}' }}</code> placeholders.
        </p>

        <!-- Auto-generate button (only when template is empty) -->
        <div
          class="auto-generate-section"
          *ngIf="canGenerateTemplate"
        >
          <div class="auto-generate-hint">
            <mat-icon>lightbulb</mat-icon>
            <span>No template defined yet.</span>
          </div>
          <button
            mat-raised-button
            color="primary"
            (click)="generateTemplate()"
            [disabled]="inputFields.length === 0"
            matTooltip="Generate a starter template using all defined input fields"
          >
            <mat-icon>auto_awesome</mat-icon>
            Generate Template from Fields
          </button>
          <p
            class="auto-generate-note"
            *ngIf="inputFields.length === 0"
          >
            Define input fields first (Tab 1) to enable auto-generation.
          </p>
        </div>

        <app-user-prompt-template-editor
          [inputFields]="inputFields"
          [value]="userPromptTemplate"
          (valueChange)="onUserPromptTemplateChange($event)"
        ></app-user-prompt-template-editor>
      </div>
    </mat-tab>
  </mat-tab-group>

  <!-- Sync Status (always visible below tabs) -->
  <div class="sync-status-section">
    <app-field-template-sync-status
      [statuses]="syncStatus"
      (createField)="createFieldFromVariable($event)"
      (insertIntoTemplate)="insertFieldIntoTemplate($event)"
    ></app-field-template-sync-status>
  </div>
</mat-expansion-panel>
```

### 2.5.11 Wizard Integration

**Modify:** `src/frontend-angular/src/app/pages/use-cases/use-case-wizard.component.ts`

```typescript
// Add import
import { UserInteractionConfigComponent } from '../../components/user-interaction-config/user-interaction-config.component';
import { SyncValidationResult } from '../../components/user-interaction-config/user-interaction-config.component';

// Add to imports array
imports: [
  // ... existing imports ...
  UserInteractionConfigComponent,
],

// Add property
userInteractionValidation: SyncValidationResult | null = null;

// Add handler
onUserInteractionValidationChange(result: SyncValidationResult): void {
  this.userInteractionValidation = result;
}

// Modify canProceedToNextStep() or step validation
canSaveUseCase(): boolean {
  // ... existing validation ...

  // Block save if user interaction has errors
  if (this.userInteractionValidation && !this.userInteractionValidation.isValid) {
    this.snackBar.open(
      'Please fix template errors before saving. Some template variables have no matching input field.',
      'Dismiss',
      { duration: 5000 }
    );
    return false;
  }

  return true;
}
```

**Modify:** `src/frontend-angular/src/app/pages/use-cases/use-case-wizard.component.html`

```html
<!-- Step 3: Edit Prompts -->
<div class="step-container" *ngIf="currentStep === 3">
  <h2>Step 3: Edit Prompts</h2>
  <p class="step-description">
    Configure the multi-role prompts for your use case
  </p>

  <form [formGroup]="promptsForm">
    <!-- System Prompt (existing) -->
    <mat-expansion-panel [expanded]="true">
      <!-- ... existing system prompt content ... -->
    </mat-expansion-panel>

    <!-- Developer Prompt (existing) -->
    <mat-expansion-panel>
      <!-- ... existing developer prompt content ... -->
    </mat-expansion-panel>

    <!-- Few-Shot Examples (existing) -->
    <mat-expansion-panel>
      <!-- ... existing fewshots content ... -->
    </mat-expansion-panel>

    <!-- REPLACE the separate user-prompt-template-editor with combined panel -->
    <app-user-interaction-config
      [inputFields]="inputFields"
      (inputFieldsChange)="inputFields = $event"
      [userPromptTemplate]="userPromptTemplate"
      (userPromptTemplateChange)="userPromptTemplate = $event"
      (validationChange)="onUserInteractionValidationChange($event)"
    ></app-user-interaction-config>

    <!-- Prompt Preview Toggle (existing) -->
    <!-- ... -->
  </form>
</div>

<!-- Step 4: Configure -->
<div class="step-container" *ngIf="currentStep === 4">
  <!-- REMOVE the User Input Fields panel - it's now in Step 3 -->
  <!-- Keep: Model Selection, RAG, Tools, Output Contract, Policies -->
</div>
```

### 2.5.12 Styles

**File:** `src/frontend-angular/src/app/components/user-interaction-config/user-interaction-config.component.scss`

```scss
.user-interaction-tabs {
  margin-bottom: 1rem;

  .mat-mdc-tab-body-wrapper {
    padding-top: 1rem;
  }
}

.tab-content {
  padding: 0.5rem 0;
}

.tab-description {
  color: var(--mdc-theme-text-secondary-on-background, rgba(0, 0, 0, 0.6));
  font-size: 0.875rem;
  margin-bottom: 1rem;

  code {
    background: #f5f5f5;
    padding: 0.125rem 0.375rem;
    border-radius: 4px;
    font-family: monospace;
  }
}

.field-count {
  margin-left: 0.25rem;
  color: var(--mdc-theme-text-secondary-on-background);
}

.validation-badge {
  margin-left: 0.5rem;

  mat-icon {
    font-size: 1.25rem;
    width: 1.25rem;
    height: 1.25rem;
  }
}

.auto-generate-section {
  background: #e3f2fd;
  border: 1px solid #90caf9;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.auto-generate-hint {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #1565c0;

  mat-icon {
    color: #ffc107;
  }
}

.auto-generate-note {
  font-size: 0.75rem;
  color: #666;
  margin: 0;
}

.sync-status-section {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e0e0e0;
}
```

**File:** `src/frontend-angular/src/app/components/field-template-sync-status/field-template-sync-status.component.scss`

```scss
.sync-status-container {
  background: #fafafa;
  border-radius: 8px;
  padding: 1rem;
}

.sync-status-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  font-weight: 500;

  mat-icon {
    color: #666;
  }

  .status-summary {
    margin-left: auto;
    font-size: 0.75rem;
    display: flex;
    gap: 0.75rem;
  }

  .error-count {
    color: #d32f2f;
  }

  .warning-count {
    color: #f57c00;
  }
}

.sync-status-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.sync-status-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  font-size: 0.875rem;

  &.error {
    background: #ffebee;
  }

  &.warning {
    background: #fff8e1;
  }

  &.synced {
    background: #e8f5e9;
  }

  .field-name {
    font-weight: 500;
    font-family: monospace;
    min-width: 120px;
  }

  .status-message {
    color: #666;
    flex: 1;
  }

  button {
    margin-left: auto;
  }
}

.sync-status-empty {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #666;
  font-size: 0.875rem;
  padding: 0.75rem;
  background: #f5f5f5;
  border-radius: 4px;
}
```

---

## Feature 3: Structured Output Pipeline

### 3.1 Problem Statement

The backend validates structured output but discards the parsed data:

```python
# Current: ResponseFormatter validates but doesn't return structured_data
# FormattedResponse has no structured_data field
# Frontend never receives parsed JSON
```

### 3.2 Backend Changes

#### 3.2.1 Add structured_data to FormattedResponse

```python
# src/orchestrator/app/schemas/response.py

class FormattedResponse(BaseModel):
    """Model for structured response output."""

    response: str = Field(..., description="The formatted response text")
    sources: list[SourceMetadata] = Field(default_factory=list)
    confidence: float = Field(...)
    metrics: ConsolidatedMetrics = Field(...)
    suggested_actions: dict = Field(default_factory=dict)
    request_id: str = Field(...)
    cache_stats: dict | None = Field(None)

    # NEW FIELD
    structured_data: dict[str, Any] | None = Field(
        default=None,
        description="Parsed structured output when output_contract.format is json/yaml/structured"
    )
```

#### 3.2.2 Extract Structured Data in ResponseFormatter

```python
# src/orchestrator/app/orchestrator/response_formatter.py

async def process(
    self,
    response_text: str,
    output_contract: OutputContractConfig | None,
    # ... other params
) -> FormattedResponse:
    """Process LLM response and extract structured data if applicable."""

    structured_data = None

    if output_contract and output_contract.format in [
        OutputFormat.JSON,
        OutputFormat.YAML,
        OutputFormat.STRUCTURED
    ]:
        try:
            # Parse the response
            if output_contract.format == OutputFormat.YAML:
                import yaml
                structured_data = yaml.safe_load(response_text)
            else:
                import json
                structured_data = json.loads(response_text)

            # Validate against schema if provided
            if output_contract.output_schema:
                from jsonschema import validate, ValidationError
                try:
                    validate(instance=structured_data, schema=output_contract.output_schema)
                except ValidationError as e:
                    if output_contract.validation_mode == ValidationMode.STRICT:
                        raise HTTPException(
                            status_code=422,
                            detail=f"Output validation failed: {e.message}"
                        )
                    else:
                        logger.warning(f"Output validation warning: {e.message}")

        except (json.JSONDecodeError, yaml.YAMLError) as e:
            if output_contract.validation_mode == ValidationMode.STRICT:
                raise HTTPException(
                    status_code=422,
                    detail=f"Failed to parse structured output: {str(e)}"
                )
            else:
                logger.warning(f"Failed to parse structured output: {str(e)}")
                structured_data = None

    return FormattedResponse(
        response=response_text,
        sources=sources,
        confidence=confidence,
        metrics=metrics,
        suggested_actions=suggested_actions,
        request_id=request_id,
        structured_data=structured_data  # NEW
    )
```

#### 3.2.3 Pass response_format to LLM (Optional Enhancement)

```python
# src/orchestrator/app/orchestrator/llm_client.py

async def make_completion_request(
    self,
    messages: list[dict],
    model: str,
    output_contract: OutputContractConfig | None = None,
    **kwargs
) -> dict:
    """Make LLM completion request with optional structured output."""

    request_params = {
        "messages": messages,
        "model": model,
        **kwargs
    }

    # Add response_format for JSON/structured outputs
    if output_contract and output_contract.format in [OutputFormat.JSON, OutputFormat.STRUCTURED]:
        if output_contract.output_schema:
            # Use JSON Schema mode (OpenAI)
            request_params["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_response",
                    "schema": output_contract.output_schema,
                    "strict": output_contract.validation_mode == ValidationMode.STRICT
                }
            }
        else:
            # Basic JSON mode
            request_params["response_format"] = {"type": "json_object"}

    return await self._make_request(request_params)
```

### 3.3 Frontend Changes

#### 3.3.1 Update ExecutionResponse Type

```typescript
// src/frontend-angular/src/app/api/models/use-case.models.ts

export interface ExecutionResponse {
  response: string;
  sources: SourceMetadata[];
  metrics: ConsolidatedMetrics;
  suggested_actions?: SuggestedAction[];
  request_id: string;
  execution_time_ms: number;
  timestamp: string;

  // NEW FIELD
  structured_data?: Record<string, unknown>;
}
```

#### 3.3.2 Wire Structured Output Rendering

```typescript
// src/frontend-angular/src/app/pages/use-case-execution/use-case-execution.component.ts

private async processExecutionResult(result: ExecutionResponse): Promise<void> {
  this.executionResult = result;
  this.isExecuting = false;

  // NEW: Process structured output
  if (result.structured_data && this.useCaseConfig?.output_contract?.template_id) {
    await this.renderStructuredOutput(result);
  }
}

private async renderStructuredOutput(result: ExecutionResponse): Promise<void> {
  const templateId = this.useCaseConfig?.output_contract?.template_id;

  if (!templateId || !result.structured_data) {
    return;
  }

  // Get template from registry
  const template = this.templateRegistry.getTemplate(templateId);

  if (template) {
    try {
      this.formattedOutput = await this.outputFormattingService.formatResponse(
        {
          answer: result.response,
          structured_data: result.structured_data
        },
        template
      );
      this.hasStructuredOutput = true;
      this.cdr.detectChanges();
    } catch (error) {
      console.error('Failed to format structured output:', error);
      this.hasStructuredOutput = false;
    }
  }
}
```

---

## Feature 4: Output Visualization Configuration

### 4.1 User Experience

**Location:** Step 4 (Configure) - Enhance "Output Contract" expansion panel

#### Wireframe: Enhanced Output Contract Section

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ 📊 Output Contract                                                      │
│                                                                          │
│ Configure how the LLM response is formatted and visualized.             │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ Output Format *                                                          │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ Structured (JSON with visualization) ▼                              │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│ Validation Mode                                                          │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ Best Effort ▼                                                       │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│ 📋 Visualization Template                              (for structured) │
│                                                                          │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ ● threat-triage-dashboard                                          │  │
│ │   Gauge + IOC Table + Timeline                                     │  │
│ │   Best for: Comprehensive threat assessments                        │  │
│ ├────────────────────────────────────────────────────────────────────┤  │
│ │ ○ ioc-extraction-table                                             │  │
│ │   Filterable IOC table with export                                 │  │
│ │   Best for: Simple IOC lists                                        │  │
│ ├────────────────────────────────────────────────────────────────────┤  │
│ │ ○ incident-summary-cards                                           │  │
│ │   Multiple gauges + chart                                          │  │
│ │   Best for: Incident overview with metrics                          │  │
│ ├────────────────────────────────────────────────────────────────────┤  │
│ │ ○ metrics-dashboard                                                │  │
│ │   Multiple gauges + line chart                                     │  │
│ │   Best for: System health and performance                           │  │
│ ├────────────────────────────────────────────────────────────────────┤  │
│ │ ○ simple-table                                                     │  │
│ │   Generic table with auto-columns                                  │  │
│ │   Best for: Any tabular data                                        │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│ 📝 Output Schema                                                        │
│                                                                          │
│ [Visual Builder] [JSON Editor]                                          │
│                                                                          │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ {                                                                   │  │
│ │   "type": "object",                                                 │  │
│ │   "required": ["confidence", "iocs", "timeline"],                   │  │
│ │   "properties": {                                                   │  │
│ │     "confidence": {                                                 │  │
│ │       "type": "number",                                             │  │
│ │       "minimum": 0,                                                 │  │
│ │       "maximum": 1                                                  │  │
│ │     },                                                              │  │
│ │     "iocs": {                                                       │  │
│ │       "type": "array",                                              │  │
│ │       "items": { ... }                                              │  │
│ │     },                                                              │  │
│ │     "timeline": { ... }                                             │  │
│ │   }                                                                 │  │
│ │ }                                                                   │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│ Schema matches template: ✅ threat-triage-dashboard                     │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│ 👁️ Visualization Preview                               [Show Preview]  │
│                                                                          │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ ┌────────────┐                                                     │  │
│ │ │   87%      │ Threat Confidence                                   │  │
│ │ │   HIGH     │                                                      │  │
│ │ └────────────┘                                                     │  │
│ │                                                                     │  │
│ │ ┌────────────────────────────────────────────────────────────────┐│  │
│ │ │ Indicators of Compromise                                       ││  │
│ │ │ Type   │ Value        │ Context        │ Severity              ││  │
│ │ │ ───────────────────────────────────────────────────────────────││  │
│ │ │ IP     │ 192.0.2.1    │ C2 Server      │ Critical              ││  │
│ │ │ Domain │ evil.com     │ Malware dist.  │ High                  ││  │
│ │ └────────────────────────────────────────────────────────────────┘│  │
│ │                                                                     │  │
│ │ [Sample data - actual output will vary based on LLM response]      │  │
│ └────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Template Selector Component

```typescript
// src/frontend-angular/src/app/components/output-template-selector/

@Component({
  selector: 'app-output-template-selector',
  templateUrl: './output-template-selector.component.html'
})
export class OutputTemplateSelectorComponent {
  @Input() selectedTemplateId: string | null = null;
  @Output() templateChange = new EventEmitter<string>();

  templates: OutputFormatTemplate[];

  constructor(private templateRegistry: TemplateRegistryService) {
    this.templates = this.templateRegistry.getAllTemplates();
  }

  selectTemplate(templateId: string): void {
    this.selectedTemplateId = templateId;
    this.templateChange.emit(templateId);
  }
}
```

### 4.3 Schema Editor with Validation

The current textarea is primitive. We'll enhance it with multi-level validation:

#### Schema Validation Levels

| Level | What It Validates | How |
|-------|-------------------|-----|
| **Syntax** | Valid JSON | `JSON.parse()` with error position |
| **Structure** | Valid JSON Schema | Ajv `compile()` - already in project |
| **Compatibility** | Matches template expectations | Compare required fields |

#### Enhanced Schema Editor Component

```typescript
// src/frontend-angular/src/app/components/schema-editor/

@Component({
  selector: 'app-schema-editor',
  templateUrl: './schema-editor.component.html'
})
export class SchemaEditorComponent {
  @Input() schema: string = '';
  @Output() schemaChange = new EventEmitter<string>();
  @Output() validationChange = new EventEmitter<SchemaValidationResult>();

  validationResult: SchemaValidationResult = { valid: true, errors: [] };
  private ajv = new Ajv({ strict: false, allErrors: true });

  onSchemaChange(value: string): void {
    this.schema = value;
    this.validateSchema(value);
    this.schemaChange.emit(value);
  }

  private validateSchema(schemaText: string): void {
    // Level 1: JSON Syntax
    let parsed: any;
    try {
      parsed = JSON.parse(schemaText);
    } catch (e) {
      this.validationResult = {
        valid: false,
        errors: [{ level: 'syntax', message: `Invalid JSON: ${e.message}` }]
      };
      this.validationChange.emit(this.validationResult);
      return;
    }

    // Level 2: JSON Schema Structure
    try {
      this.ajv.compile(parsed);
      this.validationResult = { valid: true, errors: [] };
    } catch (e) {
      this.validationResult = {
        valid: false,
        errors: [{ level: 'schema', message: `Invalid JSON Schema: ${e.message}` }]
      };
    }

    this.validationChange.emit(this.validationResult);
  }

  formatSchema(): void {
    try {
      const parsed = JSON.parse(this.schema);
      this.schema = JSON.stringify(parsed, null, 2);
      this.schemaChange.emit(this.schema);
    } catch (e) {
      // Can't format invalid JSON
    }
  }
}

interface SchemaValidationResult {
  valid: boolean;
  errors: Array<{ level: 'syntax' | 'schema' | 'compatibility'; message: string }>;
}
```

#### Import from Example JSON (High Value Feature)

Allow users to paste example LLM output and generate schema automatically:

```typescript
// Schema generation from example
import { toJsonSchema } from 'to-json-schema';  // or custom implementation

generateSchemaFromExample(exampleJson: string): string {
  try {
    const example = JSON.parse(exampleJson);
    const schema = toJsonSchema(example, {
      required: true,
      objects: { additionalProperties: false },
      arrays: { mode: 'first' }
    });
    return JSON.stringify(schema, null, 2);
  } catch (e) {
    throw new Error(`Cannot generate schema: ${e.message}`);
  }
}
```

#### Wireframe: Enhanced Schema Editor

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ 📝 Output Schema                                                        │
│                                                                          │
│ [Manual Schema] [Import from Example] [Use Template Schema]              │
│                                                                          │
│ ─── Import from Example ────────────────────────────────────────────────│
│                                                                          │
│ Paste example LLM output:                                                │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ {                                                                   │  │
│ │   "confidence": 0.87,                                               │  │
│ │   "iocs": [{ "type": "IP", "value": "192.0.2.1" }]                  │  │
│ │ }                                                                   │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│                                              [Generate Schema]           │
│                                                                          │
│ ─── Schema ─────────────────────────────────────────────────────────────│
│                                                                          │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ {                                                                   │  │
│ │   "type": "object",                                                 │  │
│ │   "required": ["confidence", "iocs"],                               │  │
│ │   "properties": {                                                   │  │
│ │     "confidence": { "type": "number" },                             │  │
│ │     "iocs": {                                                       │  │
│ │       "type": "array",                                              │  │
│ │       "items": { ... }                                              │  │
│ │     }                                                               │  │
│ │   }                                                                 │  │
│ │ }                                                                   │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│ ✅ Valid JSON Schema                              [Format] [Clear]       │
│                                                                          │
│ ─── Template Schemas ───────────────────────────────────────────────────│
│                                                                          │
│ Quick start with a pre-built schema:                                     │
│ [Threat Triage] [IOC List] [Incident Summary] [Metrics] [Simple Table]  │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Template-Based Schema Presets

```typescript
// Pre-built schemas matching visualization templates
const SCHEMA_PRESETS = {
  'threat-triage': {
    type: 'object',
    required: ['confidence', 'iocs', 'timeline'],
    properties: {
      confidence: { type: 'number', minimum: 0, maximum: 1 },
      iocs: {
        type: 'array',
        items: {
          type: 'object',
          required: ['type', 'value', 'severity'],
          properties: {
            type: { type: 'string', enum: ['IP', 'Domain', 'Hash', 'Email', 'URL'] },
            value: { type: 'string' },
            context: { type: 'string' },
            severity: { type: 'string', enum: ['low', 'medium', 'high', 'critical'] }
          }
        }
      },
      timeline: {
        type: 'array',
        items: {
          type: 'object',
          required: ['timestamp', 'description', 'severity'],
          properties: {
            timestamp: { type: 'string', format: 'date-time' },
            description: { type: 'string' },
            severity: { type: 'string', enum: ['low', 'medium', 'high', 'critical'] },
            details: { type: 'string' }
          }
        }
      }
    }
  },
  'ioc-list': { /* ... */ },
  'incident-summary': { /* ... */ },
  'metrics-dashboard': { /* ... */ },
  'simple-table': { /* ... */ }
};
```

---

## Implementation Phases

### Phase 1: Input Fields Configuration (Week 1) ✅ COMPLETE (2026-02-04)

**Priority: CRITICAL**

| Task | Est. Hours | Status |
|------|-----------|--------|
| Create InputFieldBuilderComponent | 8 | ✅ Done |
| Create InputFieldEditorComponent | 4 | ✅ Done |
| Create InputFieldPreviewComponent | 4 | Deferred (inline empty-state in builder) |
| Integrate into wizard Step 4 | 4 | ✅ Done |
| Update wizard form handling | 4 | ✅ Done |
| Write unit tests | 4 | ✅ Done |
| Write e2e tests | 4 | Deferred |

**Total: ~32 hours (4 days)** — Delivered: InputFieldBuilder, InputFieldEditor, "User Input Fields" panel (originally Step 4; moved to Step 3 per Phase 2.5), create/update/clone/populate handling, config_json.input_fields, unit tests. Form preview and e2e tests deferred.

### Phase 2: User Prompt Template (Week 2) ✅ COMPLETE (2026-02-04)

**Priority: HIGH**

| Task | Est. Hours | Status |
|------|-----------|--------|
| Add UserPromptTemplateConfig to backend schema | 2 | ✅ Done |
| Create template_renderer.py | 4 | ✅ Done |
| Update execution path to use template | 4 | ✅ Done |
| Create UserPromptTemplateEditor component | 8 | ✅ Done |
| Add variable chips/insertion UI | 4 | ✅ Done (in editor) |
| Create template preview | 4 | ✅ Done (in editor) |
| Integrate into wizard Step 3 | 4 | ✅ Done |
| Write unit tests | 4 | ✅ Done |
| Write integration tests | 4 | Deferred |

**Total: ~38 hours (5 days)** — Delivered: UserPromptTemplateConfig (backend + frontend), template_renderer.py (render, extract_template_variables, validate_template_variables), execution path in use_cases.py (template vs legacy concatenation), UserPromptTemplateEditor (variable chips, textarea, fallback mode, preview), wizard Step 3 integration and config_json load/save (create/update/edit/clone). Unit tests: test_template_renderer.py, test_use_case_config.py (UserPromptTemplateConfig), user-prompt-template-editor.component.spec.ts. Integration tests deferred.

### Phase 2.5: User Interaction Combined Panel ✅ Complete (2026-02-04)

**Priority: HIGH (UX Critical)**
**ADR:** ADR-064-User-Interaction-Combined-Panel.md

| Task | Est. Hours | Status |
|------|-----------|--------|
| Create `FieldTemplateSyncStatusComponent` | 3 | ✅ Complete |
| Create `UserInteractionConfigComponent` (wrapper with tabs) | 4 | ✅ Complete |
| Add auto-generate template logic | 2 | ✅ Complete |
| Add helper actions (create field, insert into template) | 2 | ✅ Complete |
| Integrate into wizard Step 3, remove from Step 4 | 2 | ✅ Complete |
| Add save-time validation (block on template_only errors) | 2 | ✅ Complete |
| Unit tests | 3 | ✅ Complete |

**Total: ~18 hours (2.5 days)** — Delivered 2026-02-04.

**Deliverables:**

- `UserInteractionConfigComponent` - Tabbed container with Input Fields and User Prompt Template
- `FieldTemplateSyncStatusComponent` - Validation display with action buttons
- Auto-generate template from fields (empty templates only)
- Real-time sync validation between fields and template variables
- Save-time validation blocking on template_only errors
- Input Fields panel removed from Step 4

**Success Criteria:**

- [x] Tabbed interface shows Input Fields (Tab 1) and User Prompt Template (Tab 2)
- [x] Sync status displays: synced (✅), field_only (⚠️), template_only (❌)
- [x] "Create Field" action works for template_only errors
- [x] "Insert into Template" action works for field_only warnings
- [x] Auto-generate creates template only when template is empty
- [x] Save blocked when template_only errors exist
- [x] All unit tests pass

### Phase 3: Structured Output Pipeline (Week 2-3)

**Priority: HIGH** ✅ Complete (2026-02-04)

| Task | Est. Hours | Status |
|------|-----------|--------|
| Add structured_data to FormattedResponse | 2 | ✅ Done |
| Update ResponseFormatter to extract data | 4 | ✅ Done |
| Add response_format to LLM client (optional) | 4 | ✅ Done |
| Update ExecutionResponse type (frontend) | 1 | ✅ Done |
| Wire renderStructuredOutput in execution component | 4 | ✅ Done |
| End-to-end testing | 4 | Unit tests done |

**Total: ~19 hours (2.5 days)**

#### Testing Phase 3 in the live application

1. **Backend pipeline (structured_data in API)**
   - Create or edit a use case in the wizard. In **Step 4 → Configure → Output Contract**, set **Output Format** to **JSON** (or **Structured**).
   - In **Step 3 → Edit Prompts**, add a **system** or **developer** instruction so the LLM returns only valid JSON, e.g.
     `Respond with valid JSON only. No markdown, no explanation. Example: {"summary": "...", "items": []}.`
   - Save the use case, open the **Use Case Execution** page, fill inputs and run.
   - Open **DevTools → Network**, find the `execute` request (e.g. `POST .../execute`), open the response body and confirm it contains **`structured_data`** with the parsed object (and `response` still has the raw text).

2. **Full flow with visualization (optional)**
   - The wizard does not yet expose **template_id** (Phase 4). To see the structured output rendered with a built-in template:
     - **Option A:** Patch the use case config so `output_contract.template_id` is set. Example via SQL (adjust `id` and use your DB client):

       ```sql
       UPDATE use_cases
       SET config_json = jsonb_set(
         config_json,
         '{output_contract,template_id}',
         '"simple-table"'
       )
       WHERE id = '<your-use-case-uuid>';
       ```

       Built-in template IDs: `simple-table`, `threat-triage-dashboard`, `ioc-extraction-table`, `incident-summary`, `metrics-dashboard`.
     - **Option B:** When saving via the API (e.g. from another tool), include `output_contract.template_id` in `config_json`.
   - Reload the use case execution page, run again. You should see the **Structured Output** section with the template-driven visualization when the backend returns `structured_data` and the template matches the data shape.

3. **Quick sanity check**
   - Use a use case that already has **Output Format = JSON** and prompts that force JSON. Run it once and in the execute response payload confirm `structured_data` is present and the UI still shows the normal response text; then add `template_id` as above and confirm the visualization appears.

### Phase 4: Output Visualization Configuration (Week 3) ✅ Complete (2026-02-05)

**Priority: MEDIUM**

| Task | Est. Hours | Status |
|------|-----------|--------|
| Create OutputTemplateSelectorComponent | 4 | ✅ Done |
| Create SchemaEditorComponent with validation | 6 | ✅ Done |
| Add schema validation (syntax + structure) | 4 | ✅ Done |
| Add "Import from Example JSON" feature | 4 | ✅ Done |
| Add template-based schema presets | 3 | ✅ Done |
| Enhance Output Contract UI section | 4 | ✅ Done |
| Add template_id to wizard form handling | 2 | ✅ Done |
| Create visualization preview | 6 | ✅ Done |
| Write tests | 4 | ✅ Done |

**Total: ~37 hours (5 days)**

### Phase 4bis: Revisit (before Phase 5) — ✅ COMPLETE (2026-02-06)

**Priority: HIGH — Address before Phase 5 (Documentation & Polish)**
**Status:** ✅ Complete — All items addressed across commits `910008b`, `c50791e`, `71b0b99`
These items had an impact on the product and documentation; they were resolved before polish.

#### 4bis.1 Visualization templates ✅

The built-in visualization templates (e.g. threat-triage-dashboard, ioc-extraction-table, simple-table) were derived from existing seeded test AIOps use cases. **The product owner challenged whether these templates are sufficiently generic and useful** for production.

**Resolution (ADR-066, commit `910008b`):** All 5 existing templates renamed from domain-specific to structural/layout-descriptive IDs (`score-table-timeline`, `filterable-table`, `score-timeline`, `auto-table`, `bar-chart`). 3 new structural templates added (`kv-summary`, `multi-table`, `comparison-grid`). Database migration `037_rename_template_ids.sql` updates existing use cases. Custom template CRUD backend added (migration `038_output_templates.sql`, commit `71b0b99`). Domain-grouped schema presets created across Security, Legal, IT Ops, and General domains.

#### 4bis.2 Wizard UX ergonomics (Input → Output vs Configure) ✅

The wizard should reflect a clear separation:

- **Input then Output** — Configuration of the **user-facing contract** should flow in that order and be adjacent.
- **Configure = “behind the scenes”** — Engine/backend settings only.

**Resolution (ADR-065, commit `c50791e`):** Wizard restructured to 5 steps: (1) Basic Info, (2) Starting Point, (3) User Experience (Input Fields + User Prompt Template + Output Contract), (4) AI Engine (Model + RAG + Tools + Policies), (5) Preview & Save. Output Contract moved from old Step 4 to new Step 3, adjacent to input configuration.

#### 4bis.3 Domain-Neutral Categories & Intent Types ✅

**Resolution (ADR-067, commit `910008b`):** Dynamic loading of categories and intent types from backend API (`/api/v1/config/categories`, `/api/v1/config/intent-types`). Intent capability profiles with auto-presets for sampling_preset and output_format. Frontend `PlatformConfigService` with caching and fallback. Migration `036_add_intent_capability_profiles.sql` adds profile columns and domain-neutral seed data.

#### 4bis.4 Schema-Template Compatibility + Refine from Output ✅

**Resolution (ADR-063 Amendments 1 & 2, commit `71b0b99`):** `SchemaTemplateCompatibilityService` validates schema against template JSONPath data_paths. `SchemaRefineDialogComponent` provides side-by-side comparison with Replace/Merge/Cancel. "Generate Schema from This Output" button on execution page navigates to wizard with inferred schema.

#### 4bis.5 Portable Visualization Specification (Vega-Lite) ✅

**Resolution (ADR-068, commit `71b0b99`):** `VisualizationSpecGenerator` service translates component definitions to Vega-Lite specs. `FormattedResponse` extended with optional `visualization_spec` field. Frontend TypeScript interfaces added.

### Phase 5: Documentation, Polish & Completing Deferred Work

**Objective:** Close the Use Case Authoring feature by (1) resolving all deferred items with explicit decisions, (2) updating documentation to match implemented behavior, (3) completing deferred testing where done (D4, D2), and (4) running final QA. D2 (E2E) implemented (Cypress E2E in place). D7 (mypy/CI) was completed Feb 2025 (mypy errors fixed, pre-commit re-enabled). See Phase 5.1.

**Execution order:** Follow the task list below in sequence. Triage and decision gate first, then docs, then tests (D4), then QA.

---

#### Phase 5.1 — Deferred items resolution

Items deferred during Phases 1–4bis are resolved as follows. Implement "Do now" items in Phase 5; "Backlog" and "Deferred (advanced LLM)" items are documented and revisited later.

| ID | Item | Decision | Rationale | Action in Phase 5 |
|----|------|----------|------------|------------------|
| D1 | InputFieldPreviewComponent (live form layout) | **Backlog** (Low) | Inline empty-state in builder is sufficient; full preview is polish. | None. Revisit: when prioritizing UX polish. |
| D2 | E2E tests Phase 1 (wizard + custom input fields) | **Do now** ✅ | E2E required for Phase 5 completion. | Implemented: Cypress E2E `src/frontend-angular/cypress/e2e/use-case-wizard-authoring.cy.ts` (create → Step 3 custom input → save → execute). |
| D3 | Template editor syntax highlighting | **Backlog** (Low) | Variable chips + validation are sufficient. | None. Revisit: when improving template editor UX. |
| D4 | Integration tests Phase 2 (template rendering pipeline) | **Do now** | Validates template_renderer + execution path without UI. | Add integration test(s): template render through execution pipeline (orchestrator + use case config). |
| D5 | `response_format` on LLM client (json_object) | **Done (2026-02)** | Implemented: `AssemblePrompt` reads `output_contract.format`; when JSON/Structured, sets `response_format` (`json_object` or `json_schema`) on `LLMRequest`, threaded through `LLMRouter` → `LLMClient`. | Complete. Files: `schemas/llm.py`, `steps/assemble_prompt.py`, `llm_router.py`, `llm_client.py`, `streaming_response.py`. |
| D6 | No regression in existing functionality | **Phase 5 required** (High) | Not deferrable. | Manual regression checklist in Final QA (Phase 5.6). |
| D7 | All tests pass (mypy blocking CI) | **Done (2025-02)** | Mypy P1/P2/P3 errors fixed; mypy re-enabled in pre-commit (`.pre-commit-config.yaml`). CI/pre-commit now run mypy on `src`, `tests`, `ops`. | Complete. |

**Deliverable:** Tracker points to this spec only (no duplicated task list). D4, D2, and D7 implemented.

---

#### Phase 5.2 — Decision gate: output-templates API scope

Before writing API docs, decide and record in tracker or session log:

- **Is the output-templates CRUD API (`/api/v1/output-templates` or equivalent) public or internal?**
  - **If public:** Add first-class doc `docs/api/output-templates.md` with endpoints and schema.
  - **If internal:** Add a short note in use-case-management (or template-management) pointing to ADR-066/068; label "internal".

This determines depth of docs for public config (`/api/v1/config/categories`, `/api/v1/config/intent-types`) and output-templates.

---

#### Phase 5.3 — API documentation updates

| # | Task | Est. | Status |
|---|------|------|--------|
| 5.3.1 | **template-management.md** — Add disambiguation at top: this API is legacy prompt-template CRUD; use case authoring uses `config_json` on Use Case Management. Link to use-case-management for `input_fields`, `user_prompt_template`, `output_contract` (including `template_id`). | 1 h | ✅ |
| 5.3.2 | **use-case-management.md** — Document `config_json` authoring sections: `user_prompt_template` (optional), `output_contract` (`template_id`, `output_schema`, `validation_mode`). Examples use structural template IDs and current schema. | 2 h | ✅ |
| 5.3.3 | **Public config** — Document `GET /api/v1/config/categories` and `GET /api/v1/config/intent-types` (in new `docs/api/config-public.md` or section in use-case-management). | 1 h | ✅ |
| 5.3.4 | **Output templates** — Per Phase 5.2 decision: either `docs/api/output-templates.md` (public) or short internal note in use-case-management. | 0.5–1.5 h | ✅ |

**Deliverable:** API docs accurate for config_json shape, public config, and output-templates (if public).

---

#### Phase 5.4 — User guide update

| # | Task | Est. | Status |
|---|------|------|--------|
| 5.4.1 | **STRUCTURED_OUTPUT_GUIDE.md** — Use structural template IDs (e.g. `score-table-timeline`, `filterable-table`, `auto-table`, `bar-chart`, `kv-summary`, `multi-table`, `comparison-grid`); remove or update deprecated names. | 1 h | ✅ |
| 5.4.2 | Document Output Contract in wizard Step 3: template selector, schema editor, validation mode, schema presets by domain, compatibility check, "Refine Schema from Output". | 1.5 h | ✅ |
| 5.4.3 | Document custom output templates (ADR-066, migration 038), how TemplateRegistryService merges built-in + backend custom; link to API if documented. | 0.5 h | ✅ |
| 5.4.4 | Optional: short Vega-Lite (ADR-068) section for `visualization_spec` consumers. Fix any old wizard step numbers (Output Contract is Step 3 per ADR-065). | 0.5 h | ✅ |

**Deliverable:** User guide matches current wizard flow and backend behavior.

---

#### Phase 5.5 — Testing and CI (D4, D2, D7 done)

| # | Task | Est. | Status |
|---|------|------|--------|
| 5.5.1 | **D4 — Integration tests** — Add test(s) for template rendering through execution pipeline (config load + template render). | 4 h | ✅ Done (`src/orchestrator/tests/integration/test_user_prompt_template_pipeline.py`) |
| 5.5.2 | **D2 — E2E tests** — Add E2E: wizard flow to create use case with custom input fields; save; execute. | 4 h | ✅ Done (`src/frontend-angular/cypress/e2e/use-case-wizard-authoring.cy.ts`) |
| 5.5.3 | **D7 — All tests pass** — Resolve mypy and CI blockers so full suite passes. | 4–8 h | ✅ Done (Feb 2025: mypy errors fixed, pre-commit mypy hook re-enabled). |
| 5.5.4 | **Angular control flow** — Replace `*ngIf` with `@if` in authoring-related and shared templates (login, breadcrumb, quick-actions-bar, use-case-execution, use-case-role-management, developer-teams, model-pricing-dialog, dynamic-form-test); fix NG8107/NG8113 build warnings. | — | ✅ Done (2026-02-08). |
| 5.5.5 | **Regression fixes** — Breadcrumb: "My AI Operations" now navigates to `/dev/use-cases` (not `/use-cases`); NavigationService builds full path from root. Rename "Use Case Library" to "AIOps Library" (routes, menu, page title). Refine Schema from Output: role-restrict Merge/Replace (canModifySchema); backend _deep_merge_config replaces output_schema entirely; frontend cache invalidation on execution load. | — | ✅ Done (2026-02-09). |

**Deliverable:** D4, D2, and D7 in place; templates use new control flow where applicable.

---

#### Phase 5.6 — Final QA and polish

| # | Task | Est. | Status |
|---|------|------|--------|
| 5.6.1 | **Regression (D6)** — Manual pass: create use case (blank/pattern/clone), Step 3 (Input Fields + User Prompt Template + Output Contract), Step 4 (AI Engine), save; execute; verify structured output and visualization. | 2 h | ✅ Loosely completed (2026-02-09): demo AIOps exercised; prompt templates, multi-table tabbed viz, prompts deduplication verified. |

**5.6.1 Guidance — Regression-test AIOps for structured output and visualization**

- **Purpose:** One or more test AIOps that validate structured outputs and template-driven visualizations end-to-end (Execution UI).
- **Suggested “Regression Test” AIOps setup:**
  1. **Create/use a use case** (blank or clone). Step 1: name e.g. “Regression Test”, category and intent as needed.
  2. **Step 3 — User Experience**
     - **Input fields:** At least one (e.g. `query` or a simple field) so execution has inputs.
     - **User prompt template:** Optional; can use a single variable (e.g. `{{query}}`) or leave for legacy concatenation.
     - **Output contract:** Set **Output format** to **JSON** (or **Structured**). Choose a **template** (e.g. `filterable-table`, `auto-table`, `kv-summary`) and, if needed, add a minimal **output schema** that matches the template’s `data_paths` (or use a schema preset).
  3. **Step 4 — AI Engine**
     - **Model:** Pick a model that returns valid JSON (e.g. `openai/gpt-oss-120b` or `openai/gpt-oss-20b`).
     - **Prompts:** In system or developer prompt, instruct the LLM to return **only valid JSON** (no markdown, no prose), with a short example shape if helpful (e.g. `{"summary": "...", "items": []}`).
  4. **Save** the use case (required for config, including model, to persist).
  5. **Execute** from the Execution UI with test inputs; confirm:
     - **Structured output** section shows and the response body contains `structured_data`.
     - If a `template_id` is set, the visualization for that template appears and matches the data shape.
  6. **Model change test:** In the wizard, change the model (e.g. from `openai/gpt-oss-120b` to `openai/gpt-oss-20b`), **Save**, then run Execute again — the run must use the **newly saved model** (see backend fix: config cache invalidated on use case update).
- **Note:** After changing the model in Step 4, **Save** before executing; otherwise the previous model may be used until the config cache is refreshed.
| 5.6.2 | **Platform config** — Verify `/api/v1/config/categories` and `/api/v1/config/intent-types` return data; confirm caching/fallback if backend unavailable. | 0.5 h | ⬜ |
| 5.6.3 | **Edge cases** — Empty input fields, template-only vs field-only sync errors, schema/template mismatch, invalid JSON schema, refine-from-output flow. | 1.5 h | ⬜ |
| 5.6.4 | **Docs consistency** — Spec success criteria, tracker, API docs, and user guide aligned; mark Phase 5 complete in spec and tracker. | 0.5 h | ⬜ |
| 5.6.5 | **Session log** — Add `docs/development/sessions/YYYY-MM-DD-phase5-use-case-authoring-complete.md` with brief summary. | 0.5 h | ⬜ |

**Deliverable:** Regression and edge-case sign-off; docs consistent; Phase 5 marked complete; session log created.

---

#### Phase 5 task summary (execution checklist)

Execute in this order:

1. **5.1** — Apply deferred-item decisions; update tracker with Decision/Rationale.
2. **5.2** — Record output-templates API scope (public vs internal).
3. **5.3** — API docs (template-management, use-case-management, config-public, output-templates per 5.2).
4. **5.4** — STRUCTURED_OUTPUT_GUIDE.md updates.
5. **5.5** — D4 integration tests (done); D2 E2E (done); D7 mypy/CI (done).
6. **5.6** — Final QA, docs consistency, session log, mark Phase 5 complete.

**Phase 5 total estimate:** ~22–28 hours (docs ~5–6 h, user guide ~3.5 h, tests/CI ~12–16 h, QA ~5 h).

---

## Technical Specifications

### File Changes Summary

#### Backend Files

| File | Change Type | Description |
|------|-------------|-------------|
| `src/orchestrator/app/schemas/use_case_config.py` | Modify ✅ | Add UserPromptTemplateConfig (Phase 2) |
| `src/orchestrator/app/schemas/response.py` | Modify ✅ | Add structured_data field (Phase 3) |
| `src/orchestrator/app/routers/use_cases.py` | Modify ✅ | Use template rendering (Phase 2) |
| `src/orchestrator/app/orchestrator/template_renderer.py` | **New** ✅ | Template rendering logic (Phase 2) |
| `src/orchestrator/app/orchestrator/response_formatter.py` | Modify ✅ | Extract structured_data (Phase 3) |
| `src/orchestrator/app/orchestrator/llm_client.py` | Modify ✅ | Add response_format (D5, Phase 5) |
| `src/orchestrator/app/routers/use_case_management.py` | Modify ✅ | _deep_merge_config: replace output_schema entirely, not recursive merge (Phase 5.5.5) |

#### Frontend Files

| File | Change Type | Description |
|------|-------------|-------------|
| `src/frontend-angular/src/app/api/models/use-case.models.ts` | Modify ✅ | Add UserPromptTemplateConfig (Phase 2) |
| `src/frontend-angular/src/app/pages/use-cases/use-case-wizard.component.ts` | Modify ✅ | Input fields + userPromptTemplate (Phase 1 & 2), User Interaction validation (Phase 2.5) |
| `src/frontend-angular/src/app/pages/use-cases/use-case-wizard.component.html` | Modify ✅ | User Input Fields + User Prompt Template (Phase 1 & 2), Replace with UserInteractionConfig (Phase 2.5) |
| `src/frontend-angular/src/app/pages/use-case-execution/use-case-execution.component.ts` | Modify ✅ | Wire structured output (Phase 3); canModifySchema, cache invalidation (Phase 5.5.5) |
| `src/frontend-angular/src/app/components/input-field-builder/` | **New** ✅ | Input fields builder (Phase 1) |
| `src/frontend-angular/src/app/components/input-field-editor/` | **New** ✅ | Single field editor (Phase 1) |
| `src/frontend-angular/src/app/components/user-prompt-template-editor/` | **New** ✅ | Template editor (Phase 2) |
| `src/frontend-angular/src/app/components/user-interaction-config/` | **New** ✅ | Combined panel wrapper with tabs (Phase 2.5) |
| `src/frontend-angular/src/app/components/field-template-sync-status/` | **New** ✅ | Sync validation display with actions (Phase 2.5) |
| `src/frontend-angular/src/app/components/output-template-selector/` | **New** ✅ | Template selector (Phase 4) |
| `src/frontend-angular/src/app/components/schema-editor/` | **New** ✅ | Schema editor with validation (Phase 4) |
| `src/frontend-angular/src/app/components/schema-refine-dialog/` | Modify ✅ | canModifySchema to restrict Merge/Replace (Phase 5.5.5) |
| `src/frontend-angular/src/app/core/services/navigation.service.ts` | Modify ✅ | getBreadcrumbs: build full path from root for correct breadcrumb links (Phase 5.5.5) |
| `src/frontend-angular/src/app/app.routes.ts` | Modify ✅ | "Use Case Library" → "AIOps Library" (Phase 5.5.5) |
| `src/frontend-angular/src/app/pages/use-case-menu/use-case-menu.component.html` | Modify ✅ | "Use Case Library" → "AIOps Library" (Phase 5.5.5) |
| `src/frontend-angular/src/app/pages/use-cases/use-case-list.component.ts` | Modify ✅ | Default pageTitle "AIOps Library" (Phase 5.5.5) |
| `src/frontend-angular/src/app/pages/use-cases/use-case-wizard.component.ts` | Modify ✅ | applyRefinedSchemaFromQueryParams, scrollToCurrentStep (Phase 5.5.5) |

### API Changes

No API endpoint changes required - all changes are to request/response schemas.

### Database Changes

No database schema changes required - all configuration stored in existing `config_json` JSONB field.

### Migration Path

**Backward Compatibility:**

- All changes are additive (new optional fields)
- Existing use cases continue to work unchanged
- Legacy concatenation behavior preserved when `user_prompt_template` is null
- `structured_data` is optional in response

---

## Testing Strategy

### Unit Tests

| Component | Test Coverage | Status |
|-----------|---------------|--------|
| InputFieldBuilderComponent | Add/remove/reorder fields | ✅ Phase 1 |
| InputFieldEditorComponent | All field types, validation | ✅ Phase 1 |
| UserPromptTemplateEditor | Variable extraction, preview | ✅ Phase 2 |
| template_renderer.py | Variable substitution, edge cases | ✅ Phase 2 |
| UseCaseConfig (UserPromptTemplateConfig) | Schema validation | ✅ Phase 2 |
| UserInteractionConfigComponent | Tab switching, sync status, auto-generate | ✅ Phase 2.5 |
| FieldTemplateSyncStatusComponent | Status display, action emissions | ✅ Phase 2.5 |
| ResponseFormatter | Structured data extraction | ✅ Phase 3 |
| OutputTemplateSelectorComponent | Template list, selection, clear | ✅ Phase 4 |
| SchemaEditorComponent | Validation, format, import, presets | ✅ Phase 4 |

Phase 1: `input-field-builder.component.spec.ts`, `input-field-editor` tests. Phase 2: `test_template_renderer.py`, `test_use_case_config.py` (UserPromptTemplateConfig), `user-prompt-template-editor.component.spec.ts`. Phase 2.5: ✅ `user-interaction-config.component.spec.ts`, `field-template-sync-status.component.spec.ts`.

### Integration Tests

| Scenario | Description |
|----------|-------------|
| Create use case with input fields | Full wizard flow |
| Execute with template rendering | Template → LLM → response |
| Structured output end-to-end | Config → LLM → parse → render |
| Backward compatibility | Old use cases still work |

### E2E Tests

| Test | Steps |
|------|-------|
| Create parameterized use case | Wizard → fields → template → save |
| Execute and verify rendering | Execute → check structured output |
| Edit existing use case | Load → modify fields → save |

---

## Success Criteria

### Feature 1: Input Fields ✅ (Phase 1 complete)

- [x] AI Ops developer can add/remove/reorder input fields
- [x] All field types supported (text, textarea, select, number, checkbox, date)
- [x] Select fields can have configurable options
- [x] Validation rules can be defined (min/max length, min/max value, pattern, pattern_message)
- [ ] Preview shows actual form layout (deferred)
- [x] Saved use case includes input_fields in config_json

### Feature 2: User Prompt Template ✅ (Phase 2 complete)

- [ ] Template editor with syntax highlighting (deferred)
- [x] Variable chips show available fields
- [x] Click-to-insert variables
- [x] Preview with sample data
- [x] Validation of variable names (variable status in editor)
- [x] Execution uses rendered template

### Feature 2.5: User Interaction Combined Panel ✅ Complete (2026-02-04)

- [x] Tabbed interface with Input Fields (Tab 1) and User Prompt Template (Tab 2)
- [x] Real-time sync status showing synced/warning/error states
- [x] Auto-generate template button (only when template is empty)
- [x] Auto-generate never overwrites existing template
- [x] "Create Field" action for template_only errors
- [x] "Insert into Template" action for field_only warnings
- [x] Save blocked when template_only errors exist
- [x] Input Fields panel removed from Step 4
- [x] Validation badge shown in panel header when errors/warnings exist

### Feature 3: Structured Output ✅ (Phase 3 complete)

- [x] FormattedResponse includes structured_data
- [x] JSON/YAML output parsed correctly
- [x] Schema validation works (both modes)
- [x] Frontend receives structured_data
- [x] Visualizers render correctly

### Feature 4: Output Visualization ✅ (Phase 4 complete)

- [x] Template selector shows available templates
- [x] Selected template_id saved to config
- [x] Preview shows sample visualization
- [x] End-to-end rendering works (template_id in config, execution uses it)

### Feature 4b: Schema Editor with Validation ✅ (Phase 4 + 4bis complete)

- [x] JSON syntax validation with error messages
- [x] JSON Schema structure validation (using Ajv)
- [x] Real-time validation feedback
- [x] Format/prettify button works
- [x] "Import from Example JSON" generates valid schema
- [x] Template-based schema presets available
- [x] Schema-template compatibility check (ADR-063 amendment, Phase 4bis)
- [x] Domain-grouped schema presets (Security, Legal, IT Ops, General)
- [x] "Refine Schema from Output" dialog (ADR-063 amendment 2)
- [x] Custom template CRUD backend (ADR-066, migration 038)
- [x] Vega-Lite portable visualization spec (ADR-068)

### Overall (closed by Phase 5)

- [ ] No regression in existing functionality (Phase 5.6.1–5.6.3)
- [ ] All tests pass — unit, integration, e2e (D2 E2E ✅); mypy/CI green ✅ (Phase 5.5 — D7 done)
- [ ] Documentation updated — API docs, STRUCTURED_OUTPUT_GUIDE, config/public (Phase 5.3–5.4)
- [x] ADRs created (ADR-062 through ADR-068)

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Template syntax conflicts with JSON | Medium | Use `{{var}}` with smart parsing |
| LLM doesn't return valid JSON | Medium | Best-effort mode, graceful fallback |
| Performance with large schemas | Low | Lazy validation, caching |
| Breaking existing use cases | High | All changes additive, thorough testing |

---

## UI Design Guidelines

All new components MUST follow established styling and layout patterns:

### ADR-012: Hybrid CSS Strategy (Accepted)

**Reference:** `docs/development/adrs/ADR-012-Hybrid-CSS-Strategy.md`

The hybrid styling stack is the default:

1. **Angular Material** for accessible UI primitives and CSS-variable tokens
2. **Tailwind CSS v4** for layout/spacing/responsive utilities
3. **Component-scoped SCSS** for complex states and edge cases

**Layering Order:**

1. Material theme (tokens/variables)
2. Tailwind (`@tailwind base; components; utilities`)
3. App overrides

### Layered Page Layout Pattern

**Reference:** `docs/development/guidelines/LAYERED_PAGE_LAYOUT_PATTERN.md`

All wizard steps and new components must follow the 4-layer pattern:

```text
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1: Page Container                                         │
│   - display: flex; flex-direction: column                       │
│   - height: calc(100vh - 200px)                                 │
│   - overflow: hidden                                            │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2: Page Header Section (NEVER SCROLLS)                    │
│   - background: white                                           │
│   - border-bottom: 1px solid #e0e0e0                            │
│   - box-shadow: 0 2px 4px rgba(0,0,0,0.1)                       │
│   - .page-title: icon + h1 + subtitle                           │
│   - .page-controls: .controls-container (rounded, #f5f5f5)      │
├─────────────────────────────────────────────────────────────────┤
│ Layer 3: Content Area (SCROLLS)                                 │
│   - flex: 1; overflow-y: auto                                   │
│   - background: #fafafa                                         │
│   - padding: 24px                                               │
├─────────────────────────────────────────────────────────────────┤
│ Layer 4: Page Footer (NEVER SCROLLS) - Optional                 │
│   - Pagination, action buttons                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Color Scheme (ADR-012 Compliant)

| Element | Color |
|---------|-------|
| Page header background | `white` |
| Controls container background | `#f5f5f5` |
| Content area background | `#fafafa` |
| Border separator | `#e0e0e0` |
| Controls container border-radius | `8px` |
| Controls container shadow | `0 2px 8px rgba(0,0,0,0.1)` |

### Component Design Requirements

All new components (InputFieldBuilder, SchemaEditor, etc.) must:

1. **Use Material components** for form controls (mat-form-field, mat-select, mat-input)
2. **Use Tailwind utilities** for layout and spacing (`flex`, `gap-4`, `p-6`, `mb-4`)
3. **Use CSS variables** for theming (not hardcoded colors where possible)
4. **Follow WCAG 2.1 AA** accessibility requirements
5. **Support mobile responsive** breakpoints (`@media max-width: 768px`)
6. **Use mat-expansion-panel** for collapsible sections (consistent with existing wizard)

---

## References

- **Discovery Document:** `docs/development/analysis/AI_OPS_USE_CASE_AND_STRUCTURED_OUTPUT_DISCOVERY.md`
- **Related ADRs:** ADR-018, ADR-044
- **New ADRs (this work):**
  - ADR-062 (User Prompt Templates Parameter Injection) — Phase 2
  - ADR-063 (Structured Output End-to-End Pipeline) + Amendments 1 & 2 — Phase 3/4bis
  - ADR-064 (User Interaction Combined Panel) + Amendment — Phase 2.5
  - ADR-065 (Wizard Step Restructuring) — Phase 4bis.2
  - ADR-066 (Domain-Neutral Visualization Templates) — Phase 4bis.1
  - ADR-067 (Dynamic Categories, Intent Capability Profiles, Auto-Presets) — Phase 4bis.3
  - ADR-068 (Portable Visualization Specification — Vega-Lite) — Phase 4bis.5
- **Styling ADRs:** ADR-012 (Hybrid CSS - Accepted), ADR-013 (Material-Only - Rejected), ADR-014 (Tailwind-Only - Rejected)
- **Layout Pattern:** `docs/development/guidelines/LAYERED_PAGE_LAYOUT_PATTERN.md`
- **P3-F5 Spec:** `docs/development/plans/features/completed/P3-F5_OUTPUT_FORMATTING_ENGINE_SPEC.md`
- **Structured Output Guide:** `docs/user-guides/STRUCTURED_OUTPUT_GUIDE.md`
- **Session Log:** `docs/development/sessions/2026-02-06-phase-4bis-completion.md`

---

**Document Version:** 1.4
**Last Updated:** February 9, 2026
**Status:** Phases 1–4bis ✅ Complete. Phase 5 (Documentation, Polish & Completing Deferred Work) in progress; E2E (D2), build warnings, Angular @if control flow, and regression fixes (breadcrumb, AIOps Library rename, Refine Schema flow) done; execute remaining Phase 5.6 tasks from this spec.
