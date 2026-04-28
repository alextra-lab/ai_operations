# ADR-064: User Interaction Combined Panel for Input Fields and User Prompt Template

**Status:** Accepted
**Date:** 2026-02-04
**Deciders:** AI Operations Platform Team
**Tags:** use-case, wizard, ux, input-fields, user-prompt-template, validation

---

## Context

**What is the issue we're addressing?**

The Use Case Authoring Wizard has a workflow dependency problem between Input Fields and User Prompt Templates:

### Current Wizard Flow (Problematic)

| Step | Panel | Purpose |
|------|-------|---------|
| Step 3 | Edit Prompts | User Prompt Template with `{{variable}}` placeholders |
| Step 4 | Configure | User Input Fields that define available variables |

**The Problem:** The User Prompt Template Editor (Step 3) receives `inputFields` as input to display available variable chips, but `inputFields` are configured in Step 4 which comes *after* Step 3.

```html
<!-- Step 3: Template editor needs fields that aren't defined yet -->
<app-user-prompt-template-editor
  [inputFields]="inputFields"  <!-- Empty or stale in create mode! -->
  [value]="userPromptTemplate"
  (valueChange)="userPromptTemplate = $event">
</app-user-prompt-template-editor>
```

**Consequences of current design:**

1. **No guidance** - When writing templates in Step 3, users see empty/stale variable chips
2. **Back-and-forth navigation** - Users must jump between steps to synchronize
3. **No validation** - Template can reference `{{severity}}` but no `severity` field exists
4. **Easy misconfiguration** - Broken templates that fail at runtime
5. **Poor discoverability** - Connection between fields and template is not obvious

**What needs to be decided?** How to restructure the wizard UI so Input Fields and User Prompt Template are properly synchronized with validation.

---

## Decision

**What did we decide?**

Create a **unified "User Interaction" expansion panel** in Step 3 that combines Input Fields and User Prompt Template with:

1. **Tabbed interface** - Tab 1: Input Fields, Tab 2: User Prompt Template
2. **Real-time synchronization validation** - Shows which fields are used, unused, or missing
3. **Auto-generate template** - Creates starter template from defined fields (new templates only)
4. **Helper actions** - Quick buttons to fix mismatches

### Architecture Overview

```
Step 3: Edit Prompts
├── System Prompt (existing)
├── Developer Prompt (existing)
├── Few-Shot Examples (existing)
└── UserInteractionConfigComponent (NEW)
    ├── MatTabGroup
    │   ├── Tab 1: InputFieldBuilderComponent (existing, moved)
    │   └── Tab 2: UserPromptTemplateEditorComponent (existing, moved)
    ├── FieldTemplateSyncStatusComponent (NEW)
    └── Auto-generate template button
```

### UI Wireframe

```
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
│ [TAB CONTENT: Input Field Builder or User Prompt Template Editor]       │
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

### Validation Rules

| Status | Icon | Condition | Severity | Blocks Save? |
|--------|------|-----------|----------|--------------|
| **Synced** | ✅ | Field exists AND used in template | None | No |
| **Field Only** | ⚠️ | Field exists but NOT in template | Warning | No |
| **Template Only** | ❌ | In template but NO field defined | Error | **Yes** |

**Rationale:**
- **Template Only = Error**: Variable cannot be populated at runtime; always a mistake
- **Field Only = Warning**: Field might be used for metadata, logging, or future use; acceptable

### Auto-Generate Template

When input fields are defined but template is empty, offer to generate a starter:

```
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

**Example output:**
```
Incident ID: {{incident_id}}
Severity: {{severity}}
Time Range: {{time_range}}

Please analyze the above information and provide your response.
```

---

## Alternatives Considered

### Option A: Reorder Panels (Move Input Fields Before Template)

**Description:** Keep separate panels but move Input Fields to Step 3 before User Prompt Template.

**Pros:**
- Minimal code changes
- Natural flow: define → use

**Cons:**
- Still no validation of synchronization
- No visual connection between related concepts
- Step 4 becomes smaller/imbalanced

**Why Rejected:** Doesn't solve the validation problem or improve discoverability.

### Option C: Keep Current Order + Add Validation Layer

**Description:** Keep Step 3/Step 4 separation but add cross-step validation and "Jump to" buttons.

**Pros:**
- No UI restructuring
- Flexible workflow

**Cons:**
- Doesn't fix fundamental ordering issue
- Users still need to jump between steps
- More complex cross-step state management

**Why Rejected:** Poor UX; treats symptoms rather than root cause.

---

## Consequences

### Positive Consequences

- **Ergonomic workflow** - Define fields, then immediately use them in template
- **Real-time validation** - Mismatches visible as you work
- **Discoverability** - Clear visual connection between fields and template
- **Reduced errors** - Template-only variables caught before save
- **Guided authoring** - Auto-generate provides starting point

### Negative Consequences

- **New component development** - ~18 hours of implementation
- **Step 4 smaller** - Input Fields removed from Configure step
- **Learning curve** - Users familiar with old layout need to adapt

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Users miss the combined panel | Low | Panel is prominent; sync status draws attention |
| Auto-generate creates poor templates | Low | Only generates skeleton; user must customize |
| Complex component state | Medium | Clear Input/Output contract; unit tests |

---

## Implementation Notes

### New Components

| Component | Path | Purpose |
|-----------|------|---------|
| `UserInteractionConfigComponent` | `components/user-interaction-config/` | Wrapper with tabs, orchestrates children |
| `FieldTemplateSyncStatusComponent` | `components/field-template-sync-status/` | Displays validation status with actions |

### Modified Components

| Component | Change |
|-----------|--------|
| `use-case-wizard.component.html` | Replace separate panels with `<app-user-interaction-config>` |
| `use-case-wizard.component.ts` | Add validation change handler |

### Removed from Step 4

The "User Input Fields" expansion panel will be removed from Step 4 (Configure) since it moves to Step 3.

### Component Interfaces

```typescript
// UserInteractionConfigComponent inputs/outputs
@Input() inputFields: InputField[] = [];
@Output() inputFieldsChange = new EventEmitter<InputField[]>();

@Input() userPromptTemplate: UserPromptTemplateConfig | null = null;
@Output() userPromptTemplateChange = new EventEmitter<UserPromptTemplateConfig | null>();

@Output() validationChange = new EventEmitter<SyncValidationResult>();

// Validation types
interface FieldSyncStatus {
  fieldName: string;
  status: 'synced' | 'field_only' | 'template_only';
  message: string;
}

interface SyncValidationResult {
  isValid: boolean;  // false if any template_only errors
  statuses: FieldSyncStatus[];
  errors: FieldSyncStatus[];   // template_only items
  warnings: FieldSyncStatus[]; // field_only items
}
```

### Save-Time Validation

The wizard's save/create function must check `SyncValidationResult.isValid` and block submission if `false`, displaying the specific errors.

---

## References

- **Supersedes:** Implicit design in Phase 1 & 2 implementation
- **Related ADRs:** ADR-062 (User Prompt Templates), ADR-063 (Structured Output Pipeline)
- **Implementation Spec:** `docs/development/plans/features/active/USE_CASE_AUTHORING_COMPLETE_SPEC.md`

---

## Amendment: Step Reference Update (2026-02-05)

### Context

ADR-065 (Wizard Step Restructuring) reorganizes the wizard steps. The User Interaction Combined Panel remains in the same logical position but the step naming and grouping changes:

- **Before (ADR-064):** Panel is in Step 3 "Edit Prompts" alongside system prompt, developer prompt, and fewshots
- **After (ADR-065):** Panel is in Step 3 "User Experience" alongside Output Configuration (output format, schema, visualization template)

### What Changes

1. **Step name:** Step 3 is now "User Experience" (was "Edit Prompts")
2. **Sibling panels:** The User Interaction panel is now adjacent to Output Configuration (was adjacent to prompt editing panels)
3. **Prompts move out:** System prompt, developer prompt, and fewshots move to Step 4 "AI Engine"

### What Does NOT Change

- The `UserInteractionConfigComponent` itself is unchanged
- The `FieldTemplateSyncStatusComponent` is unchanged
- All validation logic (synced/field_only/template_only) is unchanged
- The tabbed interface (Input Fields + User Prompt Template) is unchanged
- Save-time validation blocking on template_only errors is unchanged

### Architecture After Amendment

```
Step 3: User Experience
├── UserInteractionConfigComponent (THIS ADR - unchanged)
│   ├── MatTabGroup
│   │   ├── Tab 1: InputFieldBuilderComponent
│   │   └── Tab 2: UserPromptTemplateEditorComponent
│   ├── FieldTemplateSyncStatusComponent
│   └── Auto-generate template button
├── Contextual description banner (NEW per ADR-065)
└── Output Configuration panel (NEW per ADR-065)
    ├── Output Format selector
    ├── Schema Editor (conditional)
    ├── Visualization Template selector (conditional)
    └── Preview (conditional)
```

---

## Status Updates

### 2026-02-04 - Accepted

**Changed By:** AI Operations Platform Team
**Reason:** Addresses critical UX issue identified during Phase 2 review. Input Fields and User Prompt Template are tightly coupled concepts that should be configured together with real-time validation.

### 2026-02-05 - Amended (Step Reference)

**Changed By:** AI Operations Platform Team
**Reason:** ADR-065 restructures wizard steps. The User Interaction Combined Panel remains in Step 3 but the step is now "User Experience" (not "Edit Prompts") and prompt panels move to Step 4. This amendment updates the architectural context; the component itself is unchanged.

---

**Template Version:** 1.0
**Based On:** Michael Nygard's ADR pattern
