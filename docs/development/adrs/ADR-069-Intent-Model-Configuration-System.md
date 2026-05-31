# ADR-069: Intent Model Configuration System

**Status:** Accepted
**Date:** 2026-02-08
**Deciders:** Architecture Team
**Tags:** configuration, model-selection, database, intents, deterministic, future-routing

---

## Context

**What is the issue we're addressing?**

The platform uses environment variables to configure which models are used for different intent types. This approach has critical limitations:

1. **Limited Coverage**: Only 4 of 11 intents have model configuration via env vars. The additional 7 intents have no configuration at all.

2. **Environment Blindness**: We do not know what models will be available in a given environment. Different deployments have different providers, models, and access restrictions. Hardcoding model names in env files or code is fundamentally wrong.

3. **Deployment Rigidity**: Changing model assignments requires editing env files and redeploying services.

4. **Enum-Database Mismatch**: The Python `RequestType` enum has 4 values, but the database `intent_types` table has 11 rows.

**What needs to be decided:**
How should the platform manage intent-to-model default mappings so that all intents are configurable, model selection is deterministic, and the system adapts to whatever models are available in each environment?

---

## Decision

**What did we decide?**

Replace environment variable-based model configuration with a simple, deterministic, database-driven default system:

1. **Admin sets defaults per intent** via the Development UI, selecting from models actually available in the environment (from the `models` registry).
2. **AIOp authors see the default** when they select an intent. They can optionally pin a specific model via `config.models.llm`.
3. **At runtime**: AIOp model pin wins; otherwise the intent default is used.
4. **If an intent has no default**: surface a clear "No default configured" indicator in the UI. Do not silently fall back or guess.

**Design principles:**

- **Deterministic**: No heuristics, no model-name pattern matching, no multi-tier priority chains. Intent → configured model. Done.
- **No hardcoded models**: Zero model names in code. All configuration comes from the database, populated by humans who know what's available.
- **Defaults as guidance**: Intent defaults are suggestions that pre-populate the model selection step. AIOp authors can accept or override.
- **Rich intent metadata for the future**: Intent descriptions and capability profiles are stored now for use by a future router model (see Future Vision below).

**Selection logic (simple):**

```text
if aiop.config.models.llm is set:
    use that model
else:
    use intent_model_defaults[intent_type]
    if not configured:
        error: "No default model configured for this intent"
```

That's it. No fallback chains, no execution-time overrides, no per-intent override maps on AIOps.

---

## Alternatives Considered

### Option 1: Keep Environment Variables, Add More

**Description:** Add `INTENT_MODEL_CLASSIFICATION`, `INTENT_MODEL_EXTRACTION`, etc.

**Why Rejected:** Doesn't solve environment blindness. Still requires deployment for changes. Becomes unwieldy with 11+ variables. No validation against available models.

### Option 2: Configuration File (YAML/JSON)

**Description:** Move configuration to a versioned YAML/JSON file.

**Why Rejected:** Still requires deployment cycle. No GUI. Can't vary by environment without complex templating.

### Option 3: Capabilities-Based Auto-Selection

**Description:** Define requirements per intent and auto-select best available model.

**Why Rejected:** Too much magic. "Best" is subjective. Unpredictable. Hard to debug. Admins need explicit control.

### Option 4: Multi-Tier Priority Hierarchy

**Description:** Execution overrides > AIOp overrides > admin defaults > fallback chains.

**Why Rejected:** Unnecessary complexity. An AIOp has one intent and either uses the default or pins a model. Multiple override layers add confusion without proportional value. Fallback chains (QUERY -> SUMMARIZATION) mask configuration problems instead of surfacing them.

---

## Consequences

### Positive Consequences

1. **Simplicity**: One place to configure, one lookup at runtime. Easy to understand, debug, and maintain.
2. **Environment Awareness**: Admins configure from models actually available in their environment.
3. **Scalability**: Supports all 11 current intents and future additions without code changes.
4. **Operational Flexibility**: Model assignments change without deployment.
5. **Audit Trail**: Configuration changes are tracked in the database.
6. **Future-Ready**: Intent metadata (descriptions, capability profiles) becomes the foundation for agentic routing (see Future Vision).

### Negative Consequences

1. **Initial Setup**: Admins must configure intent defaults during deployment.
2. **Database Dependency**: Model selection requires database access (mitigated by in-memory caching).

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Database unavailable during model selection | High | Cache intent defaults in memory at startup |
| Admin forgets to configure some intents | Medium | Clear "No default set" indicator in UI; validation warnings |
| Migration loses existing configuration | Medium | Seed script preserves env var values |

---

## Future Vision: Router Model and Agentic Delegation

The intent metadata we store today is designed to serve a future where model selection becomes intelligent:

### Progression

1. **Today (deterministic)**: User selects intent explicitly. System uses configured default model. Simple, predictable, debuggable.

2. **Near-term (assisted)**: A small, fast router model reads the user's query and the intent descriptions/capability profiles from `intent_types`. It suggests an intent. User confirms or overrides.

3. **Future (agentic)**: Router model reads user input, reads all intent profiles from the table, selects the best intent, picks the configured model for that intent, and delegates. No human selection step. The `intent_types` table becomes the router's "tool catalog."

### Why This Works

- The `intent_types` table already stores rich metadata per intent:
  - `description` - what the intent does (readable by both humans and models)
  - `recommended_capabilities` - what the model needs (reasoning, json_mode, large_context, vision)
  - `default_sampling_preset` - strict, balanced, creative
  - `default_output_format` - text, json, yaml, structured
  - `temperature_min / temperature_max` - acceptable range
  - `category` - domain grouping

- This metadata is the **contract between human administrators and a future routing agent**. Well-written intent descriptions today become agent instructions tomorrow.

- Adding a new intent = adding a row to the table, not changing code or routing logic.

- No redesign needed when we move from deterministic to agentic. The same data structure, the same configuration UI, the same model defaults. Only the selection mechanism changes.

### Extension: Per-Intent Temperature (2026-02)

`intent_model_defaults` includes an optional `temperature` column (now in `000_complete_init.sql` — AIO-65),
range 0.0–1.0. When set, it overrides the ModelType metadata default at runtime.
Admins configure it via the Intents Management UI alongside the model selection. Priority:
use case config > intent default (DB) > ParameterManager/ModelType metadata.

### Implication for Today

Write clear, detailed intent descriptions now. They are not just UI labels. They are future agent instructions.

---

## Implementation Notes

### Database Changes

- **New Table**: `intent_model_defaults` - maps intent_code to model_id from registry
- **Migration 037**: Create table, indexes, constraints, audit columns
- **Seed Script**: Migrate existing env var values to database

### Backend Changes

- `src/orchestrator/app/schemas/intent.py` - Expand `RequestType` enum to 11 values
- `src/orchestrator/app/schemas/llm.py` - Expand `ModelType` enum to 11 values
- `src/orchestrator/app/orchestrator/model_selection.py` - Simplified DB-driven lookup
- `src/orchestrator/app/orchestrator/llm_router.py` - Remove hardcoded model mappings, use simple lookup
- `src/orchestrator/app/routers/admin_intent_models.py` - Development API for configuration; **GET /available-models** uses `ModelRegistryService.list_models()` with a raw SQL fallback so the model dropdown is always populated even if the registry service path fails
- Remove `INTENT_MODEL_*` env vars from `config/env/env.template`

### Frontend Changes

- **New Component**: `src/frontend-angular/src/app/pages/dev/intent-model-config/`
- **Location**: AIOps Development section (sidebar: Intents Management)
- Shows all intents with current defaults, "No default set" indicators, model selection from registry
- **Per-intent temperature**: Optional temperature input per intent (range 0.0–1.0); min-width styling for temperature input and model column so labels/values are readable

### What Was Removed (Simplification)

- Execution-time model overrides on the execution API
- Per-intent override maps on AIOp config (`ModelOverrides` schema)
- Fallback chains between intent types
- Hardcoded model-name-to-ModelType pattern matching in LLMRouter
- Multi-tier priority resolution logic

---

## References

- [MODELS.md](../../orchestrator/app/llm/MODELS.md) - Model routing documentation
- [ADR-041](ADR-041-Use-Case-Template-System.md) - AIOp template system
- [ADR-067](ADR-067-Dynamic-Categories-Intent-Profiles.md) - Dynamic categories and intent profiles
- Migration 036: `ops/database/migrations/036_add_intent_capability_profiles.sql`
- Model Registry: `models` table in database schema
- Demo AIOps: `ops/database/seed/003_seed_use_cases.sql` - 8 demonstration AI Operations showcasing visualization templates

---

## Note on Terminology

This document uses "use case" for historical continuity with existing code and ADR references. The platform now refers to these as **AIOps (AI Operations)** in user-facing contexts to avoid confusion with business use cases. The database table name `use_cases` is retained for backward compatibility.

---

## Status Updates

### 2026-02-08 - Accepted

**Changed By:** Architecture Team
**Reason:** Addresses critical scalability and operational concerns with minimal complexity. Simplified from initial multi-tier design to deterministic defaults after design review.

### 2026-02-09 - Implementation notes

**Changed By:** Development (regression fixes)
**Reason:** Document evolutions from regression testing: (1) **/available-models** — use `ModelRegistryService.list_models()` with raw SQL fallback so Intents Management model dropdown is always populated. (2) **Intents Management UI** — per-intent temperature input and min-width styling for temperature/model column for readability.

---

**Template Version:** 1.0
**Based On:** [Michael Nygard's ADR pattern](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
