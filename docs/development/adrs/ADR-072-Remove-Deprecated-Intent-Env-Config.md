# ADR-072: Remove Deprecated Intent Model and Temperature Environment Configuration

**Status:** Accepted
**Date:** 2026-02-18
**Deciders:** Architecture Team
**Tags:** configuration, cleanup, intent-models, temperature, ADR-069, dead-code

---

## Context

**What is the issue we're addressing?**

ADR-069 (Intent Model Configuration System, accepted 2026-02-08) moved intent-to-model mapping and per-intent temperature configuration from environment variables to the database (`intent_model_defaults` table). The runtime selection logic is now:

```text
use_case config.models.llm  →  intent_model_defaults (DB)  →  error
```

For temperature:

```text
use_case config.generation_params.temperature  →  intent_model_defaults.temperature (DB)  →  ParameterManager  →  0.7
```

However, the old environment-based configuration was never fully removed. Three separate layers remain active for temperature, and two for model selection:

### Ghost Fields in shared/config

`OrchestratorConfig` in `src/shared/config/schemas.py` still defines 8 intent fields:

- `intent_model_query`, `intent_model_rule_generation`, `intent_model_summarization`, `intent_model_enrichment`
- `intent_temp_query`, `intent_temp_rule_generation`, `intent_temp_summarization`, `intent_temp_enrichment`

The loader in `src/shared/config/loader.py` reads 8 corresponding env vars (`INTENT_MODEL_QUERY`, `INTENT_TEMP_QUERY`, etc.) into these fields.

**No code reads these fields.** A grep for `.intent_model_` and `.intent_temp_` on `OrchestratorConfig` returns zero hits. The fields are loaded and discarded.

### ParameterManager — Undocumented Parallel System

`src/orchestrator/app/orchestrator/parameter_manager.py` reads a separate set of env vars directly via `os.environ.get`:

- `MODEL_TEMPERATURE_QUERY`, `MODEL_TEMPERATURE_RULE_GENERATION`, `MODEL_TEMPERATURE_SUMMARIZATION`, `MODEL_TEMPERATURE_ENRICHMENT`
- `MODEL_MAX_TOKENS_QUERY`, `MODEL_MAX_TOKENS_RULE_GENERATION`, `MODEL_MAX_TOKENS_SUMMARIZATION`, `MODEL_MAX_TOKENS_ENRICHMENT`

These variables are **not in any `.env` file or template**. They fall back to `ModelType.metadata` defaults (hardcoded in the enum).

`ParameterManager` serves as a fallback in `llm_router.py` (line 136) when the DB has no temperature configured for an intent. This creates a 4-tier fallback chain for temperature (DB → ParameterManager env → ModelType metadata → 0.7), which contradicts ADR-069's explicit rejection of fallback chains.

Additionally, `ParameterManager` only covers the original 4 intents via `ModelType`. ADR-069 expanded to 11 intents. The 7 new intents have no `ParameterManager` mapping and silently fall back to 0.7.

### Stale Env Files and Templates

| File | Contains | Status |
|---|---|---|
| `config/env/.env.test` | `INTENT_MODEL_QUERY=openai/gpt-oss-120b`, etc. (4 model + 4 temp) | Dead — loaded into config but never read |
| `config/env/env.template` | `INTENT_MODEL_*` commented with deprecation note; `INTENT_TEMP_*` still active | Partially cleaned |
| `config/env/env.test.template` | `INTENT_MODEL_*` and `INTENT_TEMP_*` still active | Not cleaned |

### Three Naming Conventions for Temperature

| Convention | Variables | Where |
|---|---|---|
| `INTENT_TEMP_*` | `INTENT_TEMP_QUERY`, etc. | shared/config loader, env files |
| `MODEL_TEMPERATURE_*` | `MODEL_TEMPERATURE_QUERY`, etc. | ParameterManager (direct env read) |
| `INTENT_TEMPERATURE_*` | `INTENT_TEMPERATURE_QUERY`, etc. | README_INTENT_BASED_ROUTING.md only |

None of these are the actual source of truth. The DB `intent_model_defaults.temperature` column (in `000_complete_init.sql` — AIO-65) is the real configuration.

**What needs to be decided:** Complete the ADR-069 cleanup by removing all deprecated intent configuration from shared/config, env files, templates, and the ParameterManager fallback system.

---

## Decision

**What did we decide?**

### 1. Remove Intent Fields from OrchestratorConfig

Remove from `src/shared/config/schemas.py`:

- `intent_model_query`, `intent_model_rule_generation`, `intent_model_summarization`, `intent_model_enrichment`
- `intent_temp_query`, `intent_temp_rule_generation`, `intent_temp_summarization`, `intent_temp_enrichment`

Remove from `src/shared/config/loader.py`:

- The 8 corresponding `os.environ.get` calls in `load_orchestrator_config()`

### 2. Retire ParameterManager Temperature/Model Env Reads

`ParameterManager._load_parameter_mappings()` currently reads `MODEL_TEMPERATURE_*` and `MODEL_MAX_TOKENS_*` from environment. These env reads are removed.

`ParameterManager` is retained as a **code-level fallback only**, using `ModelType.metadata` defaults (no env). Its role is strictly: when the DB has no temperature or max_tokens configured for an intent, provide the `ModelType` enum's hardcoded default. No environment variable override layer.

Temperature priority becomes:

```text
use_case config.generation_params.temperature  →  intent_model_defaults.temperature (DB)  →  ModelType.metadata default
```

This is a 3-tier chain but each tier serves a distinct purpose (author override → admin default → code constant) with no env layer. The `ParameterManager` env override was undocumented and untested in practice (no env vars were ever set).

### 3. Clean Env Files and Templates

Remove from all env files and templates:

- `INTENT_MODEL_QUERY`, `INTENT_MODEL_RULE_GENERATION`, `INTENT_MODEL_SUMMARIZATION`, `INTENT_MODEL_ENRICHMENT`
- `INTENT_TEMP_QUERY`, `INTENT_TEMP_RULE_GENERATION`, `INTENT_TEMP_SUMMARIZATION`, `INTENT_TEMP_ENRICHMENT`

The `env.template` deprecation comment block for `INTENT_MODEL_*` is also removed (the migration seed script has already run; the comment served its purpose).

### 4. Update README

Update `src/orchestrator/app/orchestrator/README_INTENT_BASED_ROUTING.md` to reflect the DB-driven model (ADR-069) and remove references to `INTENT_TEMPERATURE_*` env vars.

### 5. Principle: DB-Driven Config Cleanup Rule

Per ADR-071 Section 5: when an ADR moves configuration from environment variables to the database, the corresponding env-based fields **must** be removed from schemas, loader, templates, and env files. This ADR is the first application of that rule.

---

## Alternatives Considered

### Option 1: Keep Fields as Deprecated (No-Op)

**Description:** Leave the ghost fields in `OrchestratorConfig` and `ParameterManager` env reads. They don't cause bugs.

**Pros:**

- Zero effort.

**Cons:**

- Three naming conventions for temperature remain, confusing developers.
- New developers may set `INTENT_TEMP_*` in their env file thinking it does something.
- ADR-069's stated goal ("Remove INTENT_MODEL_* env vars from config/env/env.template") is not completed.
- Vault integration (ADR-061) would need to handle dead env vars.
- Violates ADR-071's cleanup rule.

**Why Rejected:** Ghost configuration is a maintenance hazard and directly contradicts two accepted ADRs.

### Option 2: Move ParameterManager Defaults to shared/config

**Description:** Instead of removing ParameterManager env reads, absorb `MODEL_TEMPERATURE_*` and `MODEL_MAX_TOKENS_*` into `OrchestratorConfig`.

**Pros:**

- Env-based override capability preserved.
- Follows ADR-071's "everything through shared/config" rule.

**Cons:**

- Contradicts ADR-069: intent configuration is DB-driven, not env-driven.
- Creates a legitimate env override path that competes with the DB, re-introducing the multi-tier priority ADR-069 rejected.
- The env vars have never been set in any env file; there is no actual use case for them.

**Why Rejected:** ADR-069 explicitly chose DB over env for intent configuration. Adding these to shared/config would legitimize a path ADR-069 deprecated.

### Option 3: Remove ParameterManager Entirely

**Description:** Delete `parameter_manager.py` and have `llm_router.py` use only DB values (or error).

**Pros:**

- Simplest. True to ADR-069's "no fallback chains" philosophy.

**Cons:**

- If an admin hasn't configured temperature for an intent in the DB, the system would error instead of using a sensible default.
- `ParameterManager` also provides `max_tokens` defaults, which are not yet in the DB schema.
- Would require adding `max_tokens` column to `intent_model_defaults` before removal.

**Why Rejected for now:** Requires a DB migration to add `max_tokens` to `intent_model_defaults`. The right long-term path, but out of scope for this cleanup. `ParameterManager` is retained as a thin code-level fallback (no env reads) until that migration is done.

---

## Consequences

### Positive Consequences

1. **ADR-069 cleanup complete:** The stated removal of `INTENT_MODEL_*` env vars is finished.
2. **Single source for intent config:** Database only. No competing env layers.
3. **Naming confusion eliminated:** Three temperature variable naming conventions reduced to zero (DB column is the only source).
4. **Smaller OrchestratorConfig:** 8 fewer fields in the schema; 8 fewer env reads in the loader.
5. **Template accuracy:** `env.template` and `env.test.template` no longer contain dead variables.

### Negative Consequences

1. **ParameterManager still exists** as a code fallback. Full removal deferred until `max_tokens` is added to `intent_model_defaults`.
2. **Seed script assumption:** The migration seed script (`ops/database/seed_intent_defaults_from_env.py`) will no longer find `INTENT_MODEL_*` env vars. This is fine; it has already run and populated the DB.

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Deployment that relies on `INTENT_MODEL_*` env vars | Low | ADR-069 seed script already migrated values to DB. Env vars have been dead for 10+ days. |
| ParameterManager fallback masks missing DB config | Low | `ModelSelector` logs warnings for unconfigured intents at startup. Admin UI shows "No default set" indicators. |
| Tests depend on `INTENT_MODEL_*` / `INTENT_TEMP_*` in env | Medium | Update test fixtures. Remove env setup for these vars in conftest files. |

---

## Implementation Notes

### Files to Modify

| File | Change |
|------|--------|
| `src/shared/config/schemas.py` | Remove 8 `intent_model_*` / `intent_temp_*` fields from `OrchestratorConfig` |
| `src/shared/config/loader.py` | Remove 8 `os.environ.get` calls from `load_orchestrator_config()` |
| `src/orchestrator/app/orchestrator/parameter_manager.py` | Remove `os.environ.get` calls in `_load_parameter_mappings()`; use `ModelType.metadata` defaults directly |
| `config/env/env.template` | Remove `INTENT_MODEL_*` comment block and `INTENT_TEMP_*` active lines |
| `config/env/env.test.template` | Remove `INTENT_MODEL_*` and `INTENT_TEMP_*` lines |
| `config/env/.env.test` | Remove `INTENT_MODEL_*` and `INTENT_TEMP_*` lines |
| `src/orchestrator/app/orchestrator/README_INTENT_BASED_ROUTING.md` | Update to reflect DB-driven model selection (ADR-069) |
| `src/shared/tests/unit/config/test_loader.py` | Update `TestLoadOrchestratorConfig` to not expect intent fields |
| `src/orchestrator/tests/unit/orchestrator/test_parameter_manager.py` | Update to not set `MODEL_TEMPERATURE_*` env vars |

### Bump Schema Version

Increment `CONFIG_SCHEMA_VERSION` in `src/shared/config/version.py` since env vars are being removed.

### Future Work

- Add `max_tokens` column to `intent_model_defaults` table (new migration).
- Once `max_tokens` is in DB, `ParameterManager` can be fully retired.
- Consider adding a `default_max_tokens` column to `intent_types` capability profiles (ADR-067).

---

## References

- [ADR-069](ADR-069-Intent-Model-Configuration-System.md) - The decision that moved intent config to DB
- [ADR-071](ADR-071-Centralized-Configuration-Gateway.md) - Centralized config gateway rule (Section 5: DB supersedes env)
- [ADR-067](ADR-067-Dynamic-Categories-Intent-Profiles.md) - Intent capability profiles
- [USE_CASE_AUTHORING_COMPLETE_SPEC](../plans/features/active/USE_CASE_AUTHORING_COMPLETE_SPEC.md) - Feature spec referencing model config
- `src/orchestrator/app/orchestrator/model_selection.py` - DB-driven ModelSelector (ADR-069)
- `src/orchestrator/app/orchestrator/parameter_manager.py` - Legacy parameter manager
- `ops/database/init/000_complete_init.sql` - Intent defaults table + temperature column (consolidated from migrations 037/039 in AIO-65)

---

## Status Updates

### 2026-02-18 - Accepted

**Changed By:** Architecture Team
**Reason:** Completes the cleanup mandated by ADR-069 ("Remove INTENT_MODEL_* env vars from config/env/env.template"). Removes ghost fields from shared/config schemas and loader, eliminates the undocumented ParameterManager env override layer, and cleans env files and templates. First application of ADR-071 Section 5 (DB-driven config supersedes env).

---

**Template Version:** 1.0
**Based On:** [Michael Nygard's ADR pattern](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
