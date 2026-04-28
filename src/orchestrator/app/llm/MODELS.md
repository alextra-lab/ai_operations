# Model Types and Intent-Based Selection

This document describes how the platform maps **intent types** to **models** for LLM routing, using database-driven configuration (ADR-069).

## Intent Types (Platform-Defined, Dynamic)

**Intent types are not hardcoded.** They are defined in the platform and loaded dynamically:

- **Source of truth:** `GET /api/v1/config/intent-types` (from `intent_types` table)
- **Used by:** Use case wizard (Step 1: Identity), use case list, and any UI that shows intent options
- **Current system intents:** QUERY, RULE_GENERATION, SUMMARIZATION, ENRICHMENT, CLASSIFICATION, EXTRACTION, GENERATION, ANALYSIS, THREAT_TRIAGE, CONTRACT_REVIEW, COMPLIANCE_CHECK

All 11 intent types are supported in code (`RequestType` and `ModelType` enums).

## Deterministic Model Selection (ADR-069)

Model selection is **deterministic**. No heuristics, no fallback chains, no hardcoded model names.

### How It Works

1. **Admin sets defaults per intent** in the Development UI, selecting from models available in the environment (from the `models` registry table).
2. **User selects an intent** when authoring a use case. The configured default model is shown.
3. **Use case author can optionally pin a model** via `config.models.llm`.
4. **At runtime:**

```
if use_case.config.models.llm is set:
    use that model
else:
    use intent_model_defaults[intent_type]
    if not configured:
        error: "No default model configured for this intent"
```

That's it. No multi-tier priority, no execution-time overrides, no per-intent override maps.

### Configuration UI

- **UI Location:** `/dev/intent-models` (under AIOps Development section)
- **API:** `GET /api/v1/development/intent-models/summary` (list all intents with status)
- **API:** `PUT /api/v1/development/intent-models/{intent_code}` (update default)
- **Required Role:** Developer, use_case_publisher, or admin

Intents without a configured default show a clear "No default set" indicator.

## Intent Metadata and Future Routing

The `intent_types` table stores rich metadata per intent:

- `description` - what the intent does
- `recommended_capabilities` - what the model needs (reasoning, json_mode, large_context, vision)
- `default_sampling_preset` - strict, balanced, creative
- `default_output_format` - text, json, yaml, structured
- `temperature_min / temperature_max` - acceptable range
- `category` - domain grouping

Today this metadata is used for UI display and wizard auto-presets. In the future, a **router model** will read these descriptions to dynamically delegate requests to the appropriate intent and model. Write clear intent descriptions -- they are future agent instructions.

## Migration from Environment Variables

Prior to ADR-069, intent models were configured via `INTENT_MODEL_*` environment variables. These are now **deprecated**.

### Migration Steps

1. Run migration: `ops/database/migrations/037_create_intent_model_defaults.sql`
2. Seed defaults: `python ops/database/seed_intent_defaults_from_env.py`
3. Configure remaining intents via Development UI
4. Remove env vars from `.env` file

## References

- **ADR-069:** `docs/development/adrs/ADR-069-Intent-Model-Configuration-System.md`
- **Intent types API:** `GET /api/v1/config/intent-types`
- **Development API:** `src/orchestrator/app/routers/admin_intent_models.py`
- **Model selector:** `src/orchestrator/app/orchestrator/model_selection.py`
- **Database schema:** `ops/database/migrations/037_create_intent_model_defaults.sql`
