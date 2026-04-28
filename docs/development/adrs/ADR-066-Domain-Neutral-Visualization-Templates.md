# ADR-066: Domain-Neutral Visualization Template Architecture

**Status:** Accepted
**Date:** 2026-02-05
**Deciders:** AI Operations Platform Team
**Tags:** visualization, templates, domain-neutral, extensibility, output-formatting

---

## Context

**What is the issue we're addressing?**

The platform's five built-in visualization templates are overwhelmingly Security AIOps artifacts:

| Template ID | Domain | Generic? |
|---|---|---|
| `threat-triage-dashboard` | Security | No |
| `ioc-extraction-table` | Security | No |
| `incident-summary` | Security (incident response) | Borderline |
| `simple-table` | Any | Yes (minimal) |
| `metrics-dashboard` | Any | Yes (minimal) |

The platform is not purely a Security AIOps tool — it serves Legal, HR, Finance, Compliance, IT Operations, and other domains. An author opening the "Visualization Template" selector sees security jargon that signals "this tool is not for me" and offers templates that don't match their data shapes.

Additionally, templates are hardcoded in `TemplateRegistryService` (frontend-only, in-memory). There is no backend persistence, no per-deployment customization, no user-created templates, and no extension point. Templates cannot survive a frontend rebuild with different code and cannot be shared across deployments.

**What needs to be decided?** How to make the template system domain-neutral and extensible.

---

## Decision

**What did we decide?**

Three changes:

1. **Rename** existing templates from domain-specific to structural/layout-descriptive names
2. **Add** new domain-neutral structural templates
3. **Design extensibility** via backend-persisted custom templates

### 1. Rename Existing Templates

| Current ID | New ID | New Name | Description |
|---|---|---|---|
| `threat-triage-dashboard` | `score-table-timeline` | Score + Table + Timeline | Gauge score, data table, and chronological timeline |
| `ioc-extraction-table` | `filterable-table` | Filterable Data Table | Single sortable/filterable table with export |
| `incident-summary` | `score-timeline` | Score + Timeline | Gauge metric with event timeline |
| `simple-table` | `auto-table` | Auto-Column Table | Generic table with auto-detected columns |
| `metrics-dashboard` | `bar-chart` | Bar Chart | Bar chart for labeled numeric data |

Template IDs describe **structure**, not business domain. The layout, sections, and component types remain identical — only the ID, name, and description change. Schema presets (which are separate from templates) carry the domain-specific examples.

### 2. New Structural Templates

| ID | Name | Layout | Component Types | Use Cases |
|---|---|---|---|---|
| `kv-summary` | Key-Value Summary | Grid of labeled values | Text blocks in grid | Any single-object result (compliance check, config audit, entity lookup) |
| `multi-table` | Multi-Table View | Tabbed tables | Multiple tables in tabs | Results with collections (findings + recommendations, before + after) |
| `comparison-grid` | Comparison Grid | Side-by-side columns | Paired text/table columns | Before/after, option comparison, policy diff |

### 3. Domain Starter Packs (Schema Presets)

Domain expertise is expressed through **schema presets** (existing mechanism in `SchemaEditorComponent`), NOT through template names. Each preset is a JSON Schema + a recommended template ID.

**Security:** Threat Triage, IOC List, Incident Summary, Alert Correlation
**Legal:** Contract Review, Compliance Check, Risk Matrix
**HR:** Candidate Summary, Policy Compliance, Engagement Metrics
**IT Operations:** Health Check, Change Impact, Capacity Report
**General:** Summary Report, Decision Matrix, Categorized List

Selecting a preset populates the schema editor and suggests a compatible visualization template.

### 4. Extensibility: Custom Templates via Backend

Add a lightweight CRUD API for custom templates:

- `GET /api/v1/admin/output-templates` — list (built-in + custom)
- `POST /api/v1/admin/output-templates` — create custom
- `PUT /api/v1/admin/output-templates/{id}` — update custom
- `DELETE /api/v1/admin/output-templates/{id}` — delete custom (built-in templates cannot be deleted)

Built-in templates remain hardcoded in `TemplateRegistryService` as the baseline. On initialization, the service loads custom templates from the backend and merges them. Custom templates are stored in a new `output_templates` table.

### API Consumer Note

For API consumers, `template_id` is a UI presentation hint. The API always returns raw `structured_data` regardless of template. The output schema is the contract. Documentation must make this explicit.

---

## Alternatives Considered

### Option A: Keep Security Templates, Add Generic Ones

**Description:** Keep `threat-triage-dashboard` etc. and add new generic templates alongside.

**Pros:** No breaking change for existing use cases referencing old IDs.
**Cons:** Security bias persists in the selector; mixed naming conventions confuse authors.
**Why Rejected:** The naming problem is the core issue; adding templates without renaming doesn't fix it.

### Option B: Remove All Built-in Templates, Custom Only

**Description:** Ship no built-in templates; everything is user-created.

**Pros:** Maximum flexibility; no opinionated defaults.
**Cons:** Empty template selector on fresh install is hostile to new users; removes the "it just works" experience.
**Why Rejected:** Example templates are crucial for end-user adoption.

---

## Consequences

### Positive Consequences

- Template selector is domain-neutral — authors in any domain see relevant structural options
- Domain expertise is expressed through schema presets, which are more granular and combinable
- Custom templates enable per-deployment specialization without code changes
- Template names describe what authors get (layout), not what domain they must be in

### Negative Consequences

- Existing use cases referencing old template IDs (e.g., `threat-triage-dashboard`) need migration
- Schema presets need authoring for each target domain
- Custom template CRUD adds a new backend surface area

### Migration

Existing `config_json.output_contract.template_id` values must be updated:

```sql
UPDATE use_cases SET config_json = jsonb_set(
  config_json, '{output_contract,template_id}',
  CASE config_json->'output_contract'->>'template_id'
    WHEN 'threat-triage-dashboard' THEN '"score-table-timeline"'
    WHEN 'ioc-extraction-table' THEN '"filterable-table"'
    WHEN 'incident-summary' THEN '"score-timeline"'
    WHEN 'simple-table' THEN '"auto-table"'
    WHEN 'metrics-dashboard' THEN '"bar-chart"'
    ELSE config_json->'output_contract'->'template_id'
  END
) WHERE config_json->'output_contract'->>'template_id' IS NOT NULL;
```

---

## References

- ADR-068: Portable Visualization Specification (Vega-Lite) — templates feed the spec generator
- P3-F5 Spec: `docs/development/plans/features/completed/P3-F5_OUTPUT_FORMATTING_ENGINE_SPEC.md`
- `src/frontend-angular/src/app/services/template-registry.service.ts` — current implementation

---

## Status Updates

### 2026-02-05 - Accepted

**Changed By:** AI Operations Platform Team
**Reason:** Phase 4bis review identified that security-specific template names prevent adoption in non-security domains. The platform must be domain-neutral by default.

---

**Template Version:** 1.0
**Based On:** Michael Nygard's ADR pattern
