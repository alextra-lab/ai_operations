# P3-REFACTOR-01: Disambiguate Provider Class Names

**Status:** 📋 PENDING
**Priority:** Low
**Created:** November 7, 2025
**Category:** Code Quality / Refactoring
**Estimated Effort:** 2-3 hours

## Context

After consolidating inference provider models into `src/shared/providers/`, we now have multiple classes named `ProviderConfig` serving different purposes:

1. **Inference Providers** (`src/shared/providers/models.py`)
   - Purpose: LLM/embedding provider configuration (OpenAI, Mistral, local models)
   - Used by: Inference Gateway, Backend Orchestrator, Embedding Service
   - Fields: `name`, `provider_type`, `base_url`, `api_key`, `models`, etc.

2. **Stateful Architecture Providers** (`src/orchestrator/app/schemas/provider_interfaces.py`)
   - Purpose: History/evidence/crypto provider configuration
   - Used by: Backend stateful features (Core vs Plus edition)
   - Fields: `provider_type` (none/governed), `enabled`, `config`, `timeout_seconds`, etc.

3. **Capabilities Providers** (`src/orchestrator/app/schemas/capabilities.py`)
   - Purpose: System capability provider configuration
   - Used by: Capabilities API responses
   - Fields: `history`, `evidence`, `crypto` (each a ProviderType)

This naming collision can cause confusion when:

- Importing from multiple modules
- Reading code without full context
- Onboarding new developers
- Using IDE autocomplete/navigation

## Objective

Rename provider classes to be self-descriptive and avoid naming collisions.

## Proposed Changes

### 1. Inference Provider Models (No Change)

Keep `ProviderConfig` in `src/shared/providers/models.py` as the "canonical" provider config since it's the most commonly used.

### 2. Stateful Architecture Providers

**File:** `src/orchestrator/app/schemas/provider_interfaces.py`

```python
# Before
class ProviderConfig(BaseModel):
    """Configuration for a provider."""
    provider_type: ProviderType = Field(...)
    enabled: bool = Field(True, ...)
    # ...

# After
class StatefulProviderConfig(BaseModel):
    """Configuration for stateful architecture providers (history/evidence/crypto)."""
    provider_type: ProviderType = Field(...)
    enabled: bool = Field(True, ...)
    # ...
```

### 3. Capabilities Providers

**File:** `src/orchestrator/app/schemas/capabilities.py`

```python
# Before
class ProviderConfig(BaseModel):
    """Configuration for a provider."""
    history: ProviderType = Field(...)
    evidence: ProviderType = Field(...)
    crypto: ProviderType = Field(...)

# After
class CapabilitiesProviderConfig(BaseModel):
    """Provider configuration for system capabilities."""
    history: ProviderType = Field(...)
    evidence: ProviderType = Field(...)
    crypto: ProviderType = Field(...)
```

## Implementation Steps

1. **Rename Classes**
   - [ ] Rename `ProviderConfig` → `StatefulProviderConfig` in `provider_interfaces.py`
   - [ ] Rename `ProviderConfig` → `CapabilitiesProviderConfig` in `capabilities.py`

2. **Update Imports**
   - [ ] Find all imports of these classes (use `grep -r "from.*provider_interfaces import.*ProviderConfig"`)
   - [ ] Update import statements across the codebase
   - [ ] Update any type hints referencing these classes

3. **Update References**
   - [ ] Update `CapabilitiesResponse.providers` field type hint
   - [ ] Update any API endpoint response models
   - [ ] Update any database models or schemas

4. **Update Documentation**
   - [ ] Update docstrings to clarify purpose
   - [ ] Update API documentation if these are exposed in OpenAPI schemas
   - [ ] Update architecture diagrams if they reference these classes

5. **Testing**
   - [ ] Run backend unit tests
   - [ ] Run integration tests
   - [ ] Verify API responses still match expected schemas
   - [ ] Check for any mypy/linter errors

6. **Verification**
   - [ ] Search for remaining `ProviderConfig` references: `grep -r "ProviderConfig" src/orchestrator/app/schemas/`
   - [ ] Ensure only inference provider references remain
   - [ ] Verify IDE autocomplete shows distinct options

## Files to Modify

- `src/orchestrator/app/schemas/provider_interfaces.py`
- `src/orchestrator/app/schemas/capabilities.py`
- Any files importing from these modules (TBD - run grep to find)

## Testing Checklist

- [ ] Backend unit tests pass
- [ ] Integration tests pass
- [ ] No mypy errors
- [ ] No linter warnings
- [ ] API documentation renders correctly
- [ ] IDE autocomplete shows distinct class names

## Success Criteria

- No naming collisions between provider config classes
- All imports use descriptive, unambiguous names
- IDE autocomplete clearly distinguishes between provider types
- Code is more readable and maintainable

## Dependencies

None - this is a pure refactoring task.

## Related

- **Completed:** Consolidation of inference provider models (November 7, 2025)
- **ADR-032:** Capabilities System (stateful vs stateless architecture)
- **ADR-033:** Stateless Core v1 (provider interfaces)

## Notes

- This is a low-priority code quality improvement
- Can be done incrementally without blocking other work
- Consider doing this before any major refactoring of the capabilities system
- The inference provider `ProviderConfig` should remain unchanged as it's the most widely used
