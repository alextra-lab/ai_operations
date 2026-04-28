# Use Case Authoring — Implementation Tracker & Traceability

**Spec:** `docs/development/plans/features/active/USE_CASE_AUTHORING_COMPLETE_SPEC.md`
**Date Created:** February 7, 2026
**Overall Status:** ✅ Implementation Complete (Phases 1–4bis) — Phase 5 (Documentation & Polish) pending

---

## Commit History (chronological)

| # | Commit | Date | Phase | Description |
|---|--------|------|-------|-------------|
| 1 | `1a50c8c` | 2026-02-04 | Phase 1 | Input Fields Configuration + plan update |
| 2 | `637b2f9` | 2026-02-04 | Phase 2 | User Prompt Template + spec task table standard |
| 3 | `d277963` | 2026-02-04 | Phase 2.5 | ADR-064 User Interaction Combined Panel (doc only) |
| 4 | `30da18d` | 2026-02-04 | Phase 2.5 | User Interaction Combined Panel (implementation) |
| 5 | `b14aa35` | 2026-02-05 | Phase 3 | Structured Output Pipeline |
| 6 | `fd7e8ad` | 2026-02-05 | Phase 3 | Updated missing items in spec |
| 7 | `064a81c` | 2026-02-05 | Phase 4 | Output Visualization Configuration + Phase 4bis Revisit section added |
| 8 | `910008b` | 2026-02-06 | Phase 4bis | ADRs 065–068 + dynamic categories + structural templates |
| 9 | `01c070c` | 2026-02-06 | Phase 4bis | Ruff/isort auto-formatting (config_public) |
| 10 | `c50791e` | 2026-02-06 | Phase 4bis | ADR-065 Wizard Step Restructuring (implementation) |
| 11 | `0157f12` | 2026-02-06 | Phase 4bis | Whitespace fix |
| 12 | `71b0b99` | 2026-02-06 | Phase 4bis | Schema compatibility, refine-from-output, custom template CRUD, domain presets, Vega-Lite viz spec |

---

## ADR Traceability

| ADR | Title | Phase | Commit(s) | Status |
|-----|-------|-------|-----------|--------|
| ADR-062 | User Prompt Templates Parameter Injection | Phase 2 | `637b2f9` | ✅ Implemented |
| ADR-063 | Structured Output End-to-End Pipeline | Phase 3 | `b14aa35` | ✅ Implemented |
| ADR-063 Amend. 1 | Schema-Template Compatibility Validation | Phase 4bis | `71b0b99` | ✅ Implemented |
| ADR-063 Amend. 2 | Schema Feedback Loop (Refine from Output) | Phase 4bis | `71b0b99` | ✅ Implemented |
| ADR-064 | User Interaction Combined Panel | Phase 2.5 | `d277963`, `30da18d` | ✅ Implemented |
| ADR-064 Amend. | Step references updated for restructuring | Phase 4bis | `c50791e` | ✅ Implemented |
| ADR-065 | Wizard Step Restructuring | Phase 4bis.2 | `c50791e` | ✅ Implemented |
| ADR-066 | Domain-Neutral Visualization Templates | Phase 4bis.1 | `910008b`, `71b0b99` | ✅ Implemented |
| ADR-067 | Dynamic Categories, Intent Profiles, Auto-Presets | Phase 4bis.3 | `910008b` | ✅ Implemented |
| ADR-068 | Portable Visualization Specification (Vega-Lite) | Phase 4bis.5 | `71b0b99` | ✅ Implemented |

---

## Database Migrations

| Migration | Purpose | Phase | Commit |
|-----------|---------|-------|--------|
| `036_add_intent_capability_profiles.sql` | Add capability profile columns to `intent_types`, domain-neutral seed data | Phase 4bis.3 | `910008b` |
| `037_rename_template_ids.sql` | Rename template IDs from domain-specific to structural names in existing use cases | Phase 4bis.1 | `910008b` |
| `038_output_templates.sql` | New `output_templates` table for custom template CRUD | Phase 4bis.1 | `71b0b99` |

---

## Phase Completion Summary

### Phase 1: Input Fields Configuration ✅ (2026-02-04)

**Commit:** `1a50c8c`

| Deliverable | Status |
|-------------|--------|
| `InputFieldBuilderComponent` | ✅ |
| `InputFieldEditorComponent` | ✅ |
| InputFieldPreviewComponent (live form layout) | ⏸ Deferred |
| Wizard integration (Step 4 → later moved to Step 3) | ✅ |
| config_json.input_fields persistence | ✅ |
| Unit tests | ✅ |
| E2E tests | ⏸ Deferred |

### Phase 2: User Prompt Template ✅ (2026-02-04)

**Commit:** `637b2f9`

| Deliverable | Status |
|-------------|--------|
| `UserPromptTemplateConfig` (backend schema) | ✅ |
| `template_renderer.py` (render, extract, validate) | ✅ |
| Execution path (template vs legacy concatenation) | ✅ |
| `UserPromptTemplateEditorComponent` (variable chips, preview) | ✅ |
| Wizard Step 3 integration | ✅ |
| Template editor with syntax highlighting | ⏸ Deferred |
| Unit tests (backend + frontend) | ✅ |
| Integration tests | ⏸ Deferred |

### Phase 2.5: User Interaction Combined Panel ✅ (2026-02-04)

**Commits:** `d277963`, `30da18d`

| Deliverable | Status |
|-------------|--------|
| ADR-064 document | ✅ |
| `UserInteractionConfigComponent` (tabbed panel) | ✅ |
| `FieldTemplateSyncStatusComponent` | ✅ |
| Real-time sync status (synced/warning/error) | ✅ |
| Auto-generate template (empty only) | ✅ |
| "Create Field" / "Insert into Template" actions | ✅ |
| Save blocked on template_only errors | ✅ |
| Input Fields moved from Step 4 to Step 3 | ✅ |
| Unit tests | ✅ |

### Phase 3: Structured Output Pipeline ✅ (2026-02-05)

**Commits:** `b14aa35`, `fd7e8ad`

| Deliverable | Status |
|-------------|--------|
| ADR-063 document | ✅ |
| `structured_data` field on `FormattedResponse` | ✅ |
| `ResponseFormatter` extracts JSON/YAML | ✅ |
| Schema validation (strict + best-effort modes) | ✅ |
| Frontend receives and renders `structured_data` | ✅ |
| `StructuredOutputRenderer` visualizers | ✅ |
| `response_format` parameter on LLM client (json_mode) | ⏸ Deferred |

### Phase 4: Output Visualization Configuration ✅ (2026-02-05)

**Commit:** `064a81c`

| Deliverable | Status |
|-------------|--------|
| `OutputTemplateSelectorComponent` | ✅ |
| Template selector in Output Contract section | ✅ |
| template_id saved to config_json | ✅ |
| `SchemaEditorComponent` (syntax/structure validation, format, import) | ✅ |
| Visualization preview with sample data | ✅ |
| End-to-end rendering (template_id in config → execution) | ✅ |

### Phase 4bis: Revisit ✅ (2026-02-06)

**Commits:** `910008b`, `01c070c`, `c50791e`, `0157f12`, `71b0b99`

| Item | Deliverable | ADR | Status |
|------|-------------|-----|--------|
| 4bis.1 | Structural template rename (5 renamed + 3 new) | ADR-066 | ✅ |
| 4bis.1 | Custom template CRUD backend + API | ADR-066 | ✅ |
| 4bis.1 | Domain-grouped schema presets (11 presets, 4 domains) | ADR-066 | ✅ |
| 4bis.2 | Wizard step restructuring (Step 3 = UX, Step 4 = AI Engine) | ADR-065 | ✅ |
| 4bis.3 | Dynamic categories & intent types from backend | ADR-067 | ✅ |
| 4bis.3 | Intent capability profiles + auto-presets | ADR-067 | ✅ |
| 4bis.3 | `PlatformConfigService` with caching/fallback | ADR-067 | ✅ |
| 4bis.4 | Schema-template compatibility validation | ADR-063 Am.1 | ✅ |
| 4bis.4 | "Refine Schema from Output" dialog | ADR-063 Am.2 | ✅ |
| 4bis.4 | `SchemaInferenceService` (infer, merge, diff) | ADR-063 Am.2 | ✅ |
| 4bis.5 | Vega-Lite `visualization_spec` on API response | ADR-068 | ✅ |
| 4bis.5 | `VisualizationSpecGenerator` service | ADR-068 | ✅ |

### Phase 5: Documentation, Polish & Completing Deferred Work

**Single source of truth:** All Phase 5 tasks and deferred-item decisions are defined in the spec only.

- **Task list and execution order:** [USE_CASE_AUTHORING_COMPLETE_SPEC.md — Phase 5](USE_CASE_AUTHORING_COMPLETE_SPEC.md#phase-5-documentation-polish--completing-deferred-work)
- **Deferred items (D1–D7):** [Spec Phase 5.1](USE_CASE_AUTHORING_COMPLETE_SPEC.md#phase-51--deferred-items-resolution). D2 (E2E) and D7 (mypy/CI) implemented.
- **Regression (D6 / 5.6.1):** Loosely completed 2026-02-09 — demo AIOps (8 visualization types), user prompt templates with `{{variable}}`, multi-table tabbed rendering, prompts API deduplication verified manually.

---

## Session Logs

| Date | Session | Summary |
|------|---------|---------|
| 2026-02-04 | (commits `1a50c8c` through `30da18d`) | Phases 1, 2, 2.5 implemented in single session |
| 2026-02-05 | (commits `b14aa35` through `064a81c`) | Phases 3 and 4 implemented |
| 2026-02-06 | `docs/development/sessions/2026-02-06-phase-4bis-completion.md` | Full Phase 4bis: ADRs, dynamic categories, structural templates, wizard restructuring, schema compatibility, refine-from-output, custom templates, domain presets, Vega-Lite |
| 2026-02-07 | (this document) | Traceability audit and spec updates |

---

## Key Files Created or Modified

### Backend (New)

- `src/orchestrator/app/routers/config_public.py` — Public config endpoints (categories, intent types)
- `src/orchestrator/app/routers/output_templates.py` — Custom template CRUD
- `src/orchestrator/app/schemas/output_template.py` — Template Pydantic schemas
- `src/orchestrator/app/schemas/visualization_spec.py` — Vega-Lite Pydantic models
- `src/orchestrator/app/services/visualization_spec_generator.py` — Component-to-Vega-Lite translation
- `src/orchestrator/app/orchestrator/template_renderer.py` — Variable substitution engine
- `ops/database/migrations/036_add_intent_capability_profiles.sql`
- `ops/database/migrations/037_rename_template_ids.sql`
- `ops/database/migrations/038_output_templates.sql`

### Frontend (New)

- `src/frontend-angular/.../api/models/platform-config.models.ts`
- `src/frontend-angular/.../api/services/platform-config.service.ts`
- `src/frontend-angular/.../api/services/output-template.service.ts`
- `src/frontend-angular/.../services/schema-template-compatibility.service.ts`
- `src/frontend-angular/.../services/schema-inference.service.ts`
- `src/frontend-angular/.../components/schema-refine-dialog/schema-refine-dialog.component.ts`
- `src/frontend-angular/.../constants/domain-schema-presets.ts`
- `src/frontend-angular/.../models/visualization-spec.model.ts`

### Key Modified Files

- `src/frontend-angular/.../pages/use-cases/use-case-wizard.component.{ts,html,scss}`
- `src/frontend-angular/.../pages/use-cases/use-case-list.component.{ts,html}`
- `src/frontend-angular/.../pages/use-cases/use-case-execution.component.{ts,html,scss}`
- `src/frontend-angular/.../services/template-registry.service.ts`
- `src/frontend-angular/.../components/schema-editor/schema-editor.component.{ts,html,scss}`
- `src/orchestrator/app/main.py`
- `src/orchestrator/app/orchestrator/response_formatter.py`
- `src/orchestrator/app/schemas/response.py`
- `src/orchestrator/app/schemas/use_case_config.py`
- `src/orchestrator/app/db/models.py`
- `ops/database/seed/002_seed_intents.sql`
