# ADR-067: Dynamic Categories, Intent Capability Profiles, and Auto-Presets

**Status:** Accepted
**Date:** 2026-02-05
**Deciders:** AI Operations Platform Team
**Tags:** categories, intent-types, capability-profiles, auto-presets, domain-neutral

---

## Context

**What is the issue we're addressing?**

The platform's category and intent type systems are hardcoded and heavily security-biased:

```typescript
// Frontend: 6 of 7 categories are security-related
export const UseCaseCategories = [
  'security', 'compliance', 'threat-intel',
  'incident-response', 'siem-analysis',
  'risk-assessment', 'test',
];

// Frontend: all 4 intent types originate from security use cases
export enum IntentType {
  QUERY = 'QUERY',
  RULE_GENERATION = 'RULE_GENERATION',
  SUMMARIZATION = 'SUMMARIZATION',
  ENRICHMENT = 'ENRICHMENT',
}
```

The backend has a dynamic intent system (ADR-016, database-driven), but the seed data categorizes all four system intents under `SECURITY`. The wizard defaults to `'security'` category.

Additionally, intent types are simple labels with no behavioral impact. Different types of AI operations have fundamentally different engine requirements — extraction tasks need strict sampling and JSON output; analysis tasks benefit from reasoning models and structured output; generation tasks need creative sampling and text output. The wizard provides no guidance based on intent selection.

**What needs to be decided?** How to make categories and intent types dynamic, domain-neutral, and behaviorally meaningful.

---

## Decision

**What did we decide?**

Three changes:

1. **Dynamic loading** — categories and intent types loaded from backend API, not hardcoded
2. **Broader defaults** — ship a domain-neutral seed set covering security, legal, HR, finance, IT ops, and general
3. **Capability profiles with auto-presets** — each intent type carries engine defaults (sampling preset + output format) that auto-apply in the wizard

### Intent Type Schema

```python
class IntentTypeConfig(BaseModel):
    """Intent type with capability profile and engine defaults."""

    intent_type: str
    category: str
    description: str
    recommended_capabilities: list[str]  # Informational tags
    default_sampling_preset: str         # "strict" | "balanced" | "creative"
    default_output_format: str           # "text" | "json" | "structured"
```

`recommended_capabilities` are informational metadata for future model filtering (e.g., `["reasoning"]`, `["json_mode"]`, `["vision", "large_context"]`). They have no behavioral effect in this iteration but establish the data foundation.

### Default Categories

`security`, `compliance`, `legal`, `hr`, `finance`, `it-operations`, `data-analysis`, `content`, `general`, `custom`

### Default Intent Types

| Intent Type | Category | Sampling | Output | Capabilities | Description |
|---|---|---|---|---|---|
| QUERY | general | balanced | text | general | General question answering |
| SUMMARIZATION | general | balanced | text | large_context | Content summarization |
| ENRICHMENT | general | balanced | structured | json_mode | Data enrichment and augmentation |
| CLASSIFICATION | general | strict | json | json_mode | Categorization and labeling |
| EXTRACTION | general | strict | json | json_mode | Structured data extraction |
| GENERATION | general | creative | text | general | Content or artifact generation |
| ANALYSIS | general | balanced | structured | reasoning | Deep analysis and assessment |
| RULE_GENERATION | security | strict | json | reasoning, json_mode | Detection rule creation |
| THREAT_TRIAGE | security | strict | structured | reasoning | Threat assessment and prioritization |
| CONTRACT_REVIEW | legal | balanced | structured | vision, large_context | Contract analysis |
| COMPLIANCE_CHECK | compliance | strict | json | json_mode | Compliance verification |

### Auto-Preset Behavior

When the author selects an intent type in Step 1 (Identity):

1. **Sampling preset** auto-sets in the config form (Step 4: AI Engine per ADR-065)
2. **Output format** auto-sets in the config form (Step 3: User Experience per ADR-065) — this causes the schema editor and visualization template selector to appear automatically when format is `json` or `structured`
3. Both values are **overridable** — the author can change them in later steps
4. A subtle info line below the intent selector shows: "Defaults applied: strict sampling, JSON output. You can change these in later steps."
5. **Smart override detection**: if the author changes intent type, defaults re-apply only if the current form values still match the previous intent's defaults. If the author has manually customized, the new intent's defaults are shown as suggestions but not auto-applied.

### API Endpoints

- `GET /api/v1/config/categories` — returns `string[]` of category IDs
- `GET /api/v1/config/intent-types` — returns `IntentTypeConfig[]` with full capability profiles

Both endpoints read from the database. Categories are derived from the distinct `category` values in the intent types table plus any additional entries in a `categories` config table.

---

## Alternatives Considered

### Option A: Broader Hardcoded Constants (No Backend)

**Description:** Expand the hardcoded arrays in the frontend with more categories and intent types.

**Pros:** Zero backend work; immediate.
**Cons:** Still not customizable per deployment; adding new types requires a code release; no capability profiles.
**Why Rejected:** Doesn't solve the extensibility problem; misses the auto-preset opportunity.

### Option B: Full Capability Profiles with Model Filtering

**Description:** Intent types filter the model dropdown based on `recommended_capabilities` matching model capability tags.

**Pros:** Maximum wizard intelligence; authors see only compatible models.
**Cons:** Requires capability tags on every model in the registry (data problem); model registry may not have rich enough metadata yet.
**Why Rejected for this iteration:** Deferred to a future iteration when the model registry has capability metadata. The `recommended_capabilities` field is included now as informational data to enable this later.

---

## Consequences

### Positive Consequences

- Authors see relevant categories for their domain, not just security options
- Intent type selection immediately configures the engine for optimal performance
- Output format auto-set activates the right UI panels in Step 3 (schema editor appears for json/structured)
- Deployments can add custom categories and intent types without code changes
- Foundation laid for future model filtering via capability tags

### Negative Consequences

- New backend endpoints to maintain
- Existing frontend code that references `IntentType` enum must be refactored to use dynamic values
- Wizard default changes from `'security'` to `'general'` — existing workflows may need adjustment

### Migration

- Existing use cases with old intent types (`QUERY`, `RULE_GENERATION`, `SUMMARIZATION`, `ENRICHMENT`) remain valid — these are preserved in the new seed data
- Frontend `IntentType` enum and `UseCaseCategories` constant are removed in favor of runtime loading
- Wizard default category changes from `'security'` to `'general'`

---

## Implementation Notes

### Backend

- New or extended config router with two GET endpoints
- Seed SQL update with expanded intent types including `default_sampling_preset`, `default_output_format`, `recommended_capabilities`
- Intent types table may need new columns or a JSONB metadata field

### Frontend

- Remove hardcoded `UseCaseCategories` and `IntentType` enum from `use-case-management.models.ts`
- Add `IntentTypeConfig` interface
- Load categories and intent types on wizard init via service call
- On intent type change: apply `default_sampling_preset` to `configForm` and `default_output_format` to `configForm`
- Smart override detection: track whether current form values were set by a previous intent auto-preset

---

## References

- ADR-016: Dynamic Intent System (proposed, establishes DB-driven intents)
- ADR-065: Wizard Step Restructuring (auto-presets connect Step 1 to Steps 3 and 4)
- ADR-023: Sampling Presets (strict, balanced, creative presets)
- `src/orchestrator/app/schemas/intent.py` — existing backend intent schema
- `ops/database/seed/002_seed_intents.sql` — existing seed data

---

## Status Updates

### 2026-02-05 - Accepted

**Changed By:** AI Operations Platform Team
**Reason:** Phase 4bis review identified that hardcoded security-biased categories and behaviorally inert intent types limit platform adoption across domains. Auto-presets improve the authoring experience by connecting intent selection to engine configuration.

---

**Template Version:** 1.0
**Based On:** Michael Nygard's ADR pattern
