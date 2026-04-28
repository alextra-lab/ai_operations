# ADR-071: Centralized Configuration Gateway (shared/config)

**Status:** Accepted
**Date:** 2026-02-18
**Deciders:** Architecture Team
**Tags:** configuration, shared-config, environment-variables, centralization, governance

---

## Context

**What is the issue we're addressing?**

The AI Operations Platform loads runtime configuration from environment variables sourced from `config/env/.env` (production) and `config/env/.env.test` (test). A centralized configuration library (`src/shared/config/`) was introduced in P4-CONFIG-01 (November 2025) to provide typed schemas, validation, and a single loader for all services. That migration was declared complete, but:

1. **No ADR was created.** The decision to centralize config was recorded only in a session log and task document, not as an architecture decision record. There is no authoritative reference for the rule or its exceptions.

2. **Drift has occurred.** At least 15 call sites across 8 files read `os.environ.get` / `os.getenv` directly, bypassing the shared loader. Some were missed during the original migration; others were added afterward (e.g. P5-A7 pool config, embedding security key).

3. **Naming mismatches.** The shared loader reads generic env var names (e.g. `DOCUMENTS_PATH`, `MODEL_CACHE_DIR`) while `config/env/.env.test` and `docker-compose.test.yml` use service-prefixed names (e.g. `CORPUS_DOCUMENTS_PATH`, `EMBEDDING_MODEL_CACHE_DIR`). This causes the loader to fall back to hardcoded defaults rather than picking up the configured values.

4. **Undocumented variables.** Several env vars read outside the loader (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `LOG_VERBOSE`, `EMBEDDING_SERVICE_CLIENT_API_KEY`, `MODEL_TEMPERATURE_*`, `MODEL_MAX_TOKENS_*`) are not in any template or `.env` file.

5. **Vault readiness.** ADR-061 designates the shared module as the single backend gateway to a future Vault integration. Every direct `os.environ.get` outside the loader is a site that would need separate Vault wiring, defeating the purpose.

**What needs to be decided:** Codify the rule that `shared.config.loader` is the mandatory single gateway for all runtime configuration, define the allowed exceptions, and establish the naming and template governance to prevent future drift.

---

## Decision

**What did we decide?**

### 1. Single Gateway Rule

All backend runtime configuration **must** be read through `src/shared/config/loader.py` functions (`load_*_config()`). No service or shared module may call `os.environ.get`, `os.getenv`, or `os.environ[...]` for application configuration outside the loader, except for the documented bootstrap exceptions below.

### 2. Bootstrap Exceptions (Exhaustive)

The following are the **only** permitted direct env reads outside `shared/config/loader.py`:

| Variable | Location | Reason |
|---|---|---|
| `TESTING`, `DEVELOPMENT` | `loader.py` internals, `database.py` | Process-detection flags the loader itself depends on for DB name selection. |
| `PYTEST_CURRENT_TEST` | Test instrumentation in orchestrator | Injected by pytest; never in `.env` files. Read-only guard, not configuration. |
| `SECRET_PROVIDER` | `shared/config/secrets.py` | Selects the secret backend before config loads (bootstrap). |
| `CONFIG_PATH` | `embedding/app/main.py` | YAML config file path for embedding provider setup; loader-adjacent. |

Any new exception requires an update to this ADR with justification.

### 3. Env Variable Naming Convention

Loader env var names **must** match the names used in `config/env/.env`, `config/env/.env.test`, `config/env/env.template`, `config/env/env.test.template`, and `deploy/docker-compose*.yml` exactly. No silent translation layers.

Where services use prefixed names in compose (e.g. `CORPUS_DOCUMENTS_PATH`), the loader **must** read those prefixed names. Generic unprefixed names (e.g. bare `DOCUMENTS_PATH`) are acceptable only when compose or the env file sets them directly.

### 4. Template Governance

- Every env var that the loader reads **must** be present in both `env.template` and `env.test.template` with an appropriate default or placeholder.
- `CONFIG_SCHEMA_VERSION` is bumped when variables are added, removed, or renamed.
- The validation script (`ops/validate_configuration.py`) checks alignment between the version in templates, env files, and the Python constant.

### 5. DB-Driven Config Supersedes Env

When an ADR moves configuration from environment variables to the database (e.g. ADR-069 for intent model defaults), the corresponding fields **must** be removed from:

- `shared/config/schemas.py` (Pydantic schema)
- `shared/config/loader.py` (env reads)
- `config/env/env.template` and `config/env/env.test.template`
- `config/env/.env` and `config/env/.env.test`

Leaving deprecated fields as ghost code is explicitly prohibited.

### 6. Relationship to ADR-061 (Vault)

The loader is the single backend gateway for secrets via `resolve_secret()` / `SecretProvider`. When Vault is enabled (`SECRET_PROVIDER=vault`), secrets resolve transparently through the loader. Every direct env read for a secret outside the loader breaks this contract.

---

## Alternatives Considered

### Option 1: Status Quo (No Formal Rule)

**Description:** Continue with the informal convention from P4-CONFIG-01. Trust developers to use the loader.

**Pros:**

- No work required now.

**Cons:**

- Drift has already proven this doesn't work (15+ violations since the migration was "complete").
- Vault integration (ADR-061) becomes expensive: each direct read is a separate integration point.
- No enforcement mechanism or audit baseline.

**Why Rejected:** The drift is real and measurable. An informal convention is not sufficient.

### Option 2: Per-Service Config Loaders

**Description:** Each service has its own config loading, reading its own env vars.

**Pros:**

- Services are fully independent.
- No shared library dependency.

**Cons:**

- Duplicated validation, schema, and secret resolution logic.
- Vault integration must be implemented N times.
- No cross-service consistency check.
- Contradicts the existing shared module architecture (auth, db, logging all use shared).

**Why Rejected:** The platform already uses shared modules for auth, DB, logging, and telemetry. Config is a natural fit for the same pattern.

### Option 3: Dotenv File Parsing in the Loader

**Description:** Have the loader read `.env` files directly instead of relying on process environment.

**Pros:**

- Guaranteed that the file is the source, not stale env.

**Cons:**

- Conflicts with Docker/compose env injection which sets process env, not files.
- Breaks standard 12-factor app conventions.
- Would need to handle variable expansion (`${VAR}`), which the shell and compose already do.

**Why Rejected:** Process environment is the correct abstraction for containerized services. The `.env` files are the *source* that populates process env; the loader reads process env.

---

## Consequences

### Positive Consequences

1. **Single source of truth:** One place to find every config variable, its type, and its default.
2. **Vault-ready:** ADR-061 implementation touches only the loader and secret provider; no per-service changes.
3. **Auditable:** `ops/validate_configuration.py` can verify that templates, env files, and the loader are in sync.
4. **Type-safe:** Pydantic schemas catch misconfiguration at startup, not at request time.
5. **Discoverable:** New developers look at `shared/config/schemas.py` to understand what the platform expects.

### Negative Consequences

1. **Refactoring cost:** Existing direct env reads must be migrated (estimated ~13 hours across all sites).
2. **Shared dependency:** All services depend on `shared.config`. If the loader has a bug, all services are affected.
3. **Schema maintenance:** Every new env var requires updating the Pydantic schema, the loader, and both templates.

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Loader bug breaks all services | Medium | 99% test coverage on loader (existing); integration tests per service. |
| Naming alignment breaks existing deployments | Medium | Change loader to read new names, keep old names as fallback during transition, then remove. |
| Developers bypass rule for speed | Low | CI lint or grep check for `os.environ.get` outside allowed files. |

---

## Implementation Notes

### Files to Modify (Drift Cleanup)

**Add fields to existing schemas:**

| Schema | New fields | Env vars |
|---|---|---|
| `DatabaseConfig` | `pool_size`, `max_overflow`, `pool_recycle`, `pool_pre_ping` | `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_RECYCLE`, `DB_POOL_PRE_PING` |
| `LoggingConfig` | `verbose` | `LOG_VERBOSE` |
| `EmbeddingConfig` | `client_api_key` | `EMBEDDING_SERVICE_CLIENT_API_KEY` |
| `OrchestratorConfig` | `transcript_storage_enabled` | `ENABLE_TRANSCRIPT_STORAGE` |

**Replace direct env reads with loader calls:**

| File | Current direct read | Replace with |
|---|---|---|
| `shared/auth/base.py` | `os.environ.get("JWT_SECRET")` | Accept `JWTConfig` or use `load_jwt_config()` |
| `shared/auth/database.py` | `os.getenv("DATABASE_URL")`, `POSTGRES_*` | Use `load_database_config()` |
| `shared/db/connection.py` | `DB_POOL_*` via local helpers | Use `DatabaseConfig` pool fields |
| `shared/logging_utils/fastapi.py` | `LOG_VERBOSE` | Use `LoggingConfig.verbose` |
| `shared/logging_utils/base.py` | `LOG_VERBOSE` | Use `LoggingConfig.verbose` |
| `corpus_svc/app/routers/collections.py` | `QDRANT_URL`, `QDRANT_PORT` | Use `load_qdrant_config()` |
| `llm_guard_svc/app/guard.py` | `LLM_GUARD_MODELS_PATH` | Use `load_llm_guard_config()` |
| `embedding/app/security.py` | `EMBEDDING_SERVICE_CLIENT_API_KEY` | Use `EmbeddingConfig` |
| `embedding/app/config/models.py` | `OPENAI_BASE_URL`, `MODEL_DIR` | Use `EmbeddingConfig` |
| `orchestrator/app/orchestrator/llm_client.py` | `OPENAI_API_KEY` fallback | Callers pass from config |
| `orchestrator/app/db/database.py` | `ENABLE_TRANSCRIPT_STORAGE` | Use `OrchestratorConfig` |

**Naming alignment (loader reads prefixed names):**

| Current loader name | Change to match env/compose |
|---|---|
| `DOCUMENTS_PATH` | `CORPUS_DOCUMENTS_PATH` |
| `TEMP_PATH` | `CORPUS_TEMP_PATH` |
| `CHUNK_SIZE` | `CORPUS_CHUNK_SIZE` |
| `CHUNK_OVERLAP` | `CORPUS_CHUNK_OVERLAP` |
| `MAX_CHUNKS_PER_DOCUMENT` | `CORPUS_MAX_CHUNKS_PER_DOCUMENT` |
| `MODEL_CACHE_DIR` | `EMBEDDING_MODEL_CACHE_DIR` |
| `ENABLE_MODEL_CACHING` | `EMBEDDING_ENABLE_MODEL_CACHING` |

**Template updates:** Regenerate `env.template` and `env.test.template` from `.env.test` as the reference. Add any missing variables. Bump `CONFIG_SCHEMA_VERSION`.

### Testing Strategy

- Existing `shared/tests/unit/config/test_loader.py` (31 tests) covers loader functions.
- Add tests for new schema fields (pool config, verbose logging, etc.).
- Add a CI check (grep-based or AST-based) that flags `os.environ.get` / `os.getenv` outside `shared/config/` and the documented exception files.

---

## References

- [P4-CONFIG-01 Session](../sessions/2025-11-25-p4-config-01-complete.md) - Original migration
- [P5-A7 Session](../sessions/2025-11-26-P5-A7-pool-config.md) - Pool config (introduced drift)
- [ADR-061](ADR-061-HashiCorp-Vault-Secrets-Integration.md) - Vault integration (depends on this gateway)
- [ADR-032](ADR-032-Capabilities-Edition-Flags.md) - Feature flags (env-driven, should go through loader)
- [ADR-069](ADR-069-Intent-Model-Configuration-System.md) - DB-driven intent config (see ADR-072 for cleanup)
- `src/shared/config/` - Loader, schemas, secrets, version
- `config/env/` - Environment templates and files
- `ops/validate_configuration.py` - Validation script

---

## Status Updates

### 2026-02-18 - Accepted

**Changed By:** Architecture Team
**Reason:** Formalizes the centralized configuration rule that was implemented in P4-CONFIG-01 but never recorded as an ADR. Documents the bootstrap exceptions, naming conventions, and template governance needed to prevent the drift observed between November 2025 and February 2026. Establishes the foundation for ADR-061 (Vault) integration.

---

**Template Version:** 1.0
**Based On:** [Michael Nygard's ADR pattern](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
