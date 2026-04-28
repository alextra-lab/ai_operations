# ADR-065: Wizard Step Restructuring — UX Contract vs Engine Configuration

**Status:** Accepted
**Date:** 2026-02-05
**Deciders:** AI Operations Platform Team
**Tags:** wizard, ux, steps, use-case-authoring, ergonomics
**Supersedes:** Implicit step layout from P3-F2 implementation (October 2025)

---

## Context

**What is the issue we're addressing?**

The Use Case Authoring Wizard has five steps. After completing Phases 1-4 of the authoring spec, a design review (Phase 4bis) identified that the step groupings mix two distinct concerns:

1. **User-facing contract** — what the end user sees (input fields, user prompt template, output format, schema, visualization)
2. **Engine configuration** — how the AI produces its response (prompts, model, RAG, tools, sampling, policies)

### Current Step Layout (Problematic)

| Step | Name | Contents | Audience Mix |
|------|------|----------|--------------|
| 1 | Basic Info | Name, description, category, intent | Metadata |
| 2 | Starting Point | Blank, pattern, clone (create only) | Author tooling |
| 3 | Edit Prompts | System prompt, developer prompt, fewshots, **User Interaction** (input fields + user prompt template) | Engine + **User-facing** |
| 4 | Configure | Model, RAG, tools, sampling, **Output Contract** (format, schema, template, preview), policies | Engine + **User-facing** |
| 5 | Preview & Save | Summary, validation, lifecycle state | Author tooling |

**Problems:**

1. **Input contract** (fields + user prompt template) and **output contract** (schema, visualization) are split across Steps 3 and 4 — the author cannot design the complete user experience in one place
2. **Engine settings** are also split across Steps 3 (prompts) and 4 (model, RAG, tools) — no clean boundary
3. The author's mental model has no clear separation of "what the user sees" vs "how the AI works"
4. Output Contract is buried among model selection, RAG, tools, and policies — easy to miss
5. For API consumers (the majority of platform users), the output schema is the primary contract, but it is presented as a sub-section of "Configure" alongside engine knobs

### Additional Context: API-First Platform

This platform is primarily consumed through API calls from external systems (scripts, SOAR platforms, automation). Browser UI users are roughly half the audience. The wizard must reflect that the **output schema is the primary contract** (shared by API + UI consumers) and **visualization templates are UI-only presentation**.

**What needs to be decided?** How to reorder wizard steps so that user-facing configuration is grouped together and engine configuration is grouped separately.

---

## Decision

**What did we decide?**

Reorganize the 5 wizard steps into audience-separated concerns. Step 3 becomes "User Experience" (the complete user-facing contract). Step 4 becomes "AI Engine" (all behind-the-scenes configuration).

### New Step Layout

| Step | Name | Contents | Mental Model |
|------|------|----------|--------------|
| 1 | **Identity** | Name, description, category, intent type | "What is this operation?" |
| 2 | **Starting Point** | Blank, pattern, clone (create only) | "Where do I start?" |
| 3 | **User Experience** | Input fields, user prompt template, output format, schema, visualization template, preview | "What does the end user see?" |
| 4 | **AI Engine** | System prompt, developer prompt, fewshots, model, sampling, RAG, tools, policies | "How does the AI work?" |
| 5 | **Review & Publish** | Summary, validation, lifecycle state, JSON preview | "Is this ready?" |

### Step 3 Density Management

Step 3 contains two independently collapsible expansion panels:

**Panel A: User Interaction** (existing `UserInteractionConfigComponent`, per ADR-064)
- Tab 1: Input Fields
- Tab 2: User Prompt Template
- Sync status bar
- Expanded by default

**Panel B: Output Configuration** (new grouping within existing wizard template)
- Output Format selector (text / json / yaml / structured)
- Conditional (when json or structured):
  - Schema Editor with presets and "Import from Example"
  - Visualization Template selector (optional, UI-only)
  - Schema-template compatibility status
  - Visualization preview
- Collapsed by default

Between the two panels, a contextual description:
> "This step defines what end users see: the input form they fill in and how results are displayed. For API consumers, the Output Schema is the contract; visualization templates apply only to the browser UI."

### Step 4 Contents

All engine/behind-the-scenes configuration moves here:

- **Prompt Engineering** (system prompt, developer prompt, fewshots) — with message assembly preview
- **Model Selection & Sampling** (LLM model, sampling preset, generation parameters)
- **RAG Settings** (collections, top-k, similarity threshold, hybrid BM25)
- **Tools Configuration** (tools allowlist, security restrictions per ADR-057)
- **Policies & Security** (streaming, history persistence, PII redaction)

### Intent Type Auto-Preset Connection

When an intent type is selected in Step 1 (per ADR-067), its `default_output_format` auto-sets in Step 3 and its `default_sampling_preset` auto-sets in Step 4. For example, selecting EXTRACTION in Step 1 sets output format to "json" in Step 3, which causes the schema editor to appear automatically.

---

## Alternatives Considered

### Option A: Keep Current Layout, Add Visual Grouping

**Description:** Add sub-headers ("User-Facing" / "Engine") within existing Steps 3 and 4 without moving panels.

**Pros:** Minimal code change.
**Cons:** Doesn't solve the fundamental split; output contract still separated from input contract.
**Why Rejected:** Cosmetic fix that doesn't address the mental model problem.

### Option B: Six Steps (Split Step 3 into Input + Output)

**Description:** Step 3 = Input Contract, Step 4 = Output Contract, Step 5 = Engine, Step 6 = Review.

**Pros:** Maximum separation of concerns.
**Cons:** Too many steps; 6 steps (5 in edit mode) creates wizard fatigue; Input and Output contracts are closely related and benefit from adjacency.
**Why Rejected:** Over-segmentation; authors need to see input and output together to design a coherent user experience.

---

## Consequences

### Positive Consequences

- Author designs the complete user experience (input + output) in one step
- Engine configuration is cleanly separated — author can skip Step 4 for simple use cases
- Output schema gets appropriate prominence (not buried under model settings)
- API-first framing is explicit in the step description
- Intent type auto-presets flow naturally across steps

### Negative Consequences

- Step 3 is dense — two expansion panels, each with sub-tabs or conditional sections
- Moving prompts from Step 3 to Step 4 is a significant layout change for existing users
- The prompt preview (message assembly) moves from Step 3 to Step 4

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Step 3 feels overwhelming | Medium | Panel B collapsed by default; simple use cases only see Panel A |
| Existing users disoriented | Low | Step names are descriptive; progress bar labels updated |
| Cross-step validation complexity | Low | Validation logic already exists; just moves between steps |

---

## Implementation Notes

### Files Changed

| File | Change |
|------|--------|
| `use-case-wizard.component.html` | Reorder step content: move output contract to Step 3, move prompts to Step 4 |
| `use-case-wizard.component.ts` | Update step labels in progress bar, adjust validation per step, update step navigation logic |
| `use-case-wizard.component.scss` | Add contextual banner styles for audience descriptions |

### Migration

- No backend changes required
- No data migration required
- Pure frontend layout restructuring

---

## References

- ADR-064: User Interaction Combined Panel (amended to reference new step)
- ADR-067: Dynamic Categories and Intent Capability Profiles (auto-preset connection)
- Phase 4bis discussion in `USE_CASE_AUTHORING_COMPLETE_SPEC.md`

---

## Status Updates

### 2026-02-06 - Implemented

**Changed By:** AI Operations Platform Team
**Reason:** Wizard steps restructured in `use-case-wizard.component.{ts,html,scss}`. Step 3 is now "User Experience" (input fields + output configuration) and Step 4 is now "AI Engine" (prompts + model + RAG + tools + policies). Contextual audience banner added between panels in Step 3. Step labels updated throughout (Identity, Starting Point, User Experience, AI Engine, Review & Publish). Test describe blocks updated to match new names.

### 2026-02-05 - Accepted

**Changed By:** AI Operations Platform Team
**Reason:** Phase 4bis design review identified that user-facing configuration and engine configuration should be cleanly separated into distinct wizard steps.

---

**Template Version:** 1.0
**Based On:** Michael Nygard's ADR pattern
