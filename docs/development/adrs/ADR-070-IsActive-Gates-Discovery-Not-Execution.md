# ADR-070: is_active Gates Discovery, Not Execution

**Status:** Accepted
**Date:** 2026-02-08
**Deciders:** Development team
**Tags:** use-case, lifecycle, execution, config-loading

---

## Context

**What is the issue we're addressing?**

The `use_cases.is_active` column was being used for two distinct purposes:

1. **Discovery** — should this use case appear in user-facing menus and
   intent-based lookups?
2. **Executability** — can this use case's config and prompts be loaded for
   execution?

Use cases are created with `is_active = False` (draft state). On publish,
`is_active` is set to `True`. This means drafts and unpublished use cases
could not be executed because `UseCaseConfigLoader.load_config(uuid)` and
`Orchestrator.load_use_case_prompts(uuid)` both filtered by `is_active`,
returning `None` for inactive use cases.

The execute endpoint (`POST /use-cases/{id}/execute`) loads the use case
row **without** an `is_active` filter and performs its own lifecycle and RBAC
checks. This mismatch caused the config/prompts to be `None` even though the
use case was accessible and had valid configuration — resulting in the model
pin being silently dropped and the intent default being used instead.

---

## Decision

**`is_active` gates discovery, not execution. Authorization gates execution.**

When loading by **explicit UUID** (the caller knows exactly which use case they
want), do **not** filter by `is_active`. The caller is responsible for access
control via RBAC, lifecycle state checks, and draft ownership verification.

When loading by **intent type** or **preloading** (discovery / browsing),
continue to filter by `is_active` so only published use cases are surfaced.

| Method                                          | Filter by `is_active`? | Why                                       |
|-------------------------------------------------|------------------------|--------------------------------------------|
| `UseCaseConfigLoader.load_config(uuid)`         | No                     | Explicit request; caller handles access     |
| `Orchestrator.load_use_case_prompts(uuid)`      | No                     | Explicit request; caller handles access     |
| `TemplateEngine.load_use_case_prompts(id)`      | No                     | Explicit request; caller handles access     |
| `UseCaseConfigLoader.load_config_by_intent()`   | Yes                    | Discovery; only active use cases            |
| `TemplateEngine.load_use_case_prompts(intent=)` | Yes                    | Discovery; only active use cases            |
| `UseCaseConfigLoader.preload_configs()`          | Yes                    | Cache warming with production configs       |
| List/menu endpoints                              | Yes                    | User-facing menus                           |

---

## Alternatives Considered

### Option 1: Add fallback in execute endpoint

**Description:** If config loader returns `None`, parse `use_case.config_json`
directly from the already-loaded row.

**Pros:**

- Minimal change (one extra block in execute endpoint)

**Cons:**

- Duplicates parsing logic
- Doesn't fix prompt loading (same `is_active` filter)
- Band-aid; every new caller would need the same fallback

**Why Rejected:** Treats symptom, not cause.

### Option 2: Split `is_active` into two columns

**Description:** Add a separate `is_executable` column.

**Pros:**

- Explicit, independent control

**Cons:**

- Schema migration required
- Two booleans to maintain and keep consistent
- `lifecycle_state` already captures the semantic intent

**Why Rejected:** Over-engineering; `lifecycle_state` + RBAC already control
execution access.

### Option 3: Use `lifecycle_state` instead of `is_active` in config loader

**Description:** Load config for `draft`, `review`, and `published` states;
exclude only `archived`.

**Pros:**

- Fine-grained control

**Cons:**

- Tightly couples config loading to lifecycle vocabulary
- `lifecycle_state` values may evolve independently

**Why Rejected:** Simpler to remove the filter entirely for UUID-based loads
and let the caller handle authorization.

---

## Consequences

### Positive Consequences

- Drafts and unpublished use cases can be executed (tested) before publishing
- Model pins, prompts, and all config are correctly loaded regardless of
  `is_active` state
- Single responsibility: `is_active` = visibility; RBAC + lifecycle = access
- No schema changes or migrations needed

### Negative Consequences

- Config can be loaded for any use case by UUID, including archived ones —
  but the execute endpoint already validates lifecycle state and access, so
  this is not a security concern

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Archived use cases being executed | Low | Execute endpoint checks lifecycle state and RBAC before running |
| Stale config cached for inactive use cases | Low | Cache is invalidated on use case update (existing behavior) |

---

## Implementation Notes

**Files affected:**

- `src/orchestrator/app/services/use_case_config_loader.py` — removed
  `UseCase.is_active` filter from `load_config(uuid)`
- `src/orchestrator/app/orchestrator/controller.py` — removed
  `DBUseCase.is_active` filter from `load_use_case_prompts(uuid)`
- `src/orchestrator/app/orchestrator/template_engine.py` — removed
  `is_active` filter for explicit `use_case_id` path; kept for intent-type
  discovery path

**No migration required.** No schema changes. No API contract changes.

**Testing strategy:**

- Execute a draft (inactive) use case and verify the model pin is applied
- Verify intent-based discovery still only returns active use cases

---

## References

- ADR-069: Intent Model Configuration System (model selection context)
- ADR-044: Use Cases As Bounded Refinement Spaces
- ADR-041: Role-Based Use Case Permissions

---

## Status Updates

### 2026-02-08 - Accepted

**Changed By:** Development team
**Reason:** Bug discovered during testing — draft use case with model pin
`qwen/qwen3-4b-2507` was executing with intent default `openai/gpt-oss-120b`
because config loader returned `None` for `is_active = False`.
