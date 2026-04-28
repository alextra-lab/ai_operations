# ADR-042: Simplified Category-Based Pricing Model

**Status:** Superseded by ADR-046 (2025-10-29)
**Date:** 2025-10-25
**Deciders:** Architecture Team, AI Assistant
**Tags:** pricing, cost-model, simplification, token-economics

---

## Context

**What is the issue we're addressing?**

The current LLMaaS pricing model uses a complex 15-tier structure:

- **5 Plan Sizes:** XS, S, M, L, XL (volume-based multipliers)
- **3 Model Classes:** Large, Small, Codestral/Llama
- **15 Total Tiers:** Every combination of plan size × model class
- **Complexity:** Different prices for same model depending on plan size

**Forces at play:**

1. **Operational complexity:** 15 tiers are difficult to maintain and explain
2. **Business model evolution:** Actual LLMaaS provider pricing is simpler
3. **User confusion:** Plan size multipliers are unintuitive
4. **Maintenance burden:** Every pricing change requires updating 15 tiers
5. **Rate limit coupling:** Plan sizes conflate pricing with rate limits

**What needs to be decided:**
Replace the 15-tier system with a simpler model that:

- Reduces administrative overhead
- Aligns with actual provider pricing
- Separates pricing from rate limit concerns
- Is easier to understand and maintain

---

## Decision

Note: This ADR is superseded by ADR-046 which adopts per-model, effective-dated
pricing with an admin UI and immutable cost capture for analytics. The
category-based model below may still be used as seed/default guidance.

**Replace 15-tier pricing with 3-category model based on model capabilities.**

### New Pricing Structure (EUR per million tokens)

**Category A: Premium Models** (2.98€ input, 12.01€ output)

- Mistral Large
- Mistral Medium
- Magistral Medium

**Category B: Standard Models** (2.09€ input, 8.41€ output)

- Mistral Small
- Codestral
- Devstral
- Magistral Small

**Category C: Open Source Models** (1.49€ input, 6.01€ output)

- Meta Llama (all variants)
- GPT OSS 120b
- GPT OSS 20b

**Auxiliary Services:**

- **Embedding:** 0.00008€ per million tokens
- **Reranking:** 0.00008€ per million tokens

### Key Implementation Details

1. **Category Assignment:** Each model is assigned to one category based on capabilities
2. **Fixed Pricing:** Prices are fixed per category (no plan size multipliers)
3. **Currency:** EUR (euros) instead of USD
4. **Rate Limits:** Decoupled from pricing, managed separately
5. **Database Schema:** Simplified to 3 pricing records (one per category)

---

## Alternatives Considered

### Option 1: Keep Current 15-Tier System

**Description:** Maintain existing plan size × model class structure

**Pros:**

- No migration required
- Granular pricing control
- Rate limits integrated

**Cons:**

- High operational complexity (15 tiers to maintain)
- Difficult to explain to users
- Doesn't match actual provider pricing
- Conflates pricing with rate limits

**Why Rejected:** Operational complexity outweighs granularity benefits

---

### Option 2: Hybrid Model (Categories + Small/Medium/Large Multipliers)

**Description:** Keep 3 categories but add 3 tier sizes (S/M/L) for volume discounts

**Pros:**

- Some volume discount capability
- Simpler than current 15 tiers (9 total)
- More pricing flexibility

**Cons:**

- Still more complex than needed
- Volume discounts may not align with business model
- Adds maintenance burden

**Why Rejected:** Unnecessary complexity; straight category pricing is sufficient

---

### Option 3: Per-Model Pricing (No Categories)

**Description:** Each model has individual pricing (10+ separate prices)

**Pros:**

- Maximum flexibility
- Can match provider pricing exactly
- Easy to add new models

**Cons:**

- Many pricing records to maintain
- Difficult to predict costs across models
- No logical grouping

**Why Rejected:** Too granular; categories provide better user understanding

---

## Consequences

### Positive Consequences

**Operational Benefits:**

- ✅ **Reduced complexity:** 15 tiers → 3 categories (80% reduction)
- ✅ **Easier maintenance:** Single price update per category
- ✅ **Better clarity:** Users understand category-based pricing
- ✅ **Faster onboarding:** Simpler pricing is easier to explain
- ✅ **Aligned with reality:** Matches actual LLMaaS provider pricing

**Technical Benefits:**

- ✅ **Simplified code:** Less pricing lookup logic
- ✅ **Easier testing:** 3 test cases instead of 15
- ✅ **Better performance:** Fewer database queries for pricing
- ✅ **Clearer analytics:** Category-based cost reporting

**Business Benefits:**

- ✅ **Transparent pricing:** Easy to understand and predict
- ✅ **Competitive positioning:** Clear model capabilities vs. cost
- ✅ **Flexible rate limits:** Decoupled from pricing tiers
- ✅ **Currency alignment:** EUR matches European deployment

---

### Negative Consequences

**Tradeoffs:**

- ❌ **Less granular control:** Cannot have volume-based pricing tiers
- ❌ **Migration required:** Must update existing pricing data
- ❌ **Some users may pay more:** Users on small plans lose volume discount
- ❌ **Rate limit decoupling:** Need separate rate limit management

**Mitigation:**

- Volume discounts can be handled via separate rate limit tiers if needed
- Migration is straightforward (3 categories vs. 15 tiers)
- Existing users can be grandfathered or migrated with notice
- Rate limits become a separate, more flexible system

---

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| User pricing confusion during migration | Medium | Clear communication, migration guide, grace period |
| Existing cost calculations break | High | Comprehensive testing, backward compatibility layer |
| Rate limit management gaps | Medium | Implement separate rate limit system (already planned: P4-F7) |
| Revenue impact (if some users pay less) | Low | Model only; actual pricing set by business team |
| Currency conversion issues (EUR vs USD) | Low | Clear documentation, consistent currency throughout |

---

## Implementation Notes

### Migration Steps Required

**1. Database Changes:**

- Replace 15 pricing tier records with 3 category records
- Update `pricing_tiers` table: remove plan_size, add category field
- Update model_configs to reference category instead of plan_size+model_class
- Migrate existing token_usage records (if cost calculation changes)

**2. Code Changes:**

```
Files to Update:
- src/orchestrator/app/db/models.py (PricingTier model)
- src/orchestrator/app/utils/cost_estimator.py (MODEL_PRICING dict)
- ops/database/seed/004_seed_pricing.sql (seed data)
- ops/database/seed/005_seed_models.sql (pricing associations)
- src/orchestrator/app/schemas/pricing.py (API schemas)
- docs/api/pricing-management.md (API documentation)
```

**3. Model → Category Mapping:**

```python
CATEGORY_A = ["mistral-large", "mistral-medium", "magistral-medium"]
CATEGORY_B = ["mistral-small", "codestral", "devstral", "magistral-small"]
CATEGORY_C = ["llama-3.1-405b", "llama-3.1-70b", "llama-3.1-8b", "gpt-oss-120b", "gpt-oss-20b"]
```

**4. New Pricing Constants (EUR per million tokens):**

```python
PRICING_CATEGORIES = {
    "A": {"input": 2.98, "output": 12.01},
    "B": {"input": 2.09, "output": 8.41},
    "C": {"input": 1.49, "output": 6.01},
    "embedding": {"cost": 0.00008},
    "reranking": {"cost": 0.00008}
}
```

**5. Testing Strategy:**

- Unit tests for category assignment
- Integration tests for cost calculation
- API tests for all pricing endpoints
- Frontend tests for cost display
- Migration script validation

---

## Files Affected

### Backend (8 files)

1. `src/orchestrator/app/db/models.py` - PricingTier model schema update
2. `src/orchestrator/app/utils/cost_estimator.py` - Replace MODEL_PRICING dict
3. `src/orchestrator/app/schemas/pricing.py` - Update API schemas
4. `src/orchestrator/app/routers/admin_pricing.py` - Update CRUD logic (minimal)
5. `src/orchestrator/app/routers/token_analytics.py` - Cost aggregation (verify)
6. `src/orchestrator/app/services/token_tracker.py` - Cost recording (verify)
7. `ops/database/seed/004_seed_pricing.sql` - New 3-category seed data
8. `ops/database/seed/005_seed_models.sql` - Update model → category associations

### Database Migration (1 file)

- `ops/migrations/sql/043_simplified_category_pricing.sql` - Migration script

### Documentation (3 files)

- `docs/api/pricing-management.md` - Update API examples
- `docs/architecture/database/SCHEMA.md` - Update pricing_tiers table
- This ADR

### Testing (2 files)

- `src/orchestrator/tests/unit/test_cost_estimator.py` - Update pricing tests
- `src/orchestrator/tests/integration/test_pricing_api.py` - Update integration tests

---

## Dependencies

**Prerequisites:**

- P4-F7 backend complete (token rate limit management)
- Token tracking system operational
- Pricing API endpoints implemented

**Blockers:**

- None - can be implemented independently

**Related Work:**

- P2-FIX-13: Token Cost Calculation (will implement this ADR)
- P4-F7: Token Rate Limit Management UI (separates rate limits)

---

## References

- **Previous Pricing ADR:** None (original design not documented as ADR)
- **Implementation Task:** [P2-FIX-13: Token Cost Calculation](../tasks/P2_FIX_13_TOKEN_COST_CALCULATION.md)
- **Pricing API Docs:** [docs/api/pricing-management.md](../../api/pricing-management.md)
- **Database Schema:** [docs/architecture/database/SCHEMA.md](../../architecture/database/SCHEMA.md)
- **Session Log:** [2025-10-13-pricing-management-implementation.md](../sessions/2025-10-13-pricing-management-implementation.md)

---

## Migration Path

### Phase 1: Update Code & Schema (Backend Only)

1. Create migration 043_simplified_category_pricing.sql
2. Update PricingTier model (add category field, remove plan_size logic)
3. Update cost_estimator.py with new PRICING_CATEGORIES
4. Update seed data (004_seed_pricing.sql)
5. Update model seed data (005_seed_models.sql)

### Phase 2: Data Migration

1. Run migration to update pricing_tiers table
2. Update existing model_configs with category assignments
3. Optionally backfill historical token_usage costs (if needed)

### Phase 3: Testing & Verification

1. Unit tests for category assignment
2. Integration tests for cost calculation
3. Verify API endpoints return correct costs
4. Test frontend cost display

### Phase 4: Documentation

1. Update API documentation
2. Update database schema docs
3. Create user-facing pricing guide (future)

---

## Status Updates

### 2025-10-25 - Accepted

**Changed By:** Development Team
**Reason:** Simplifies operational overhead, aligns with actual LLMaaS pricing model, reduces maintenance burden

---

## Comparison: Before vs After

### Before (15 Tiers)

| Plan | Model Class | Input | Output |
|------|-------------|-------|--------|
| XS | Large | 1.10 | 0.30 |
| XS | Small | 1.60 | 0.40 |
| XS | Codestral/Llama | 3.70 | 0.90 |
| S | Large | 2.20 | 0.60 |
| S | Small | 3.20 | 0.80 |
| S | Codestral/Llama | 7.40 | 1.80 |
| ... | ... | ... | ... |
| **15 total tiers** | | | |

**Complexity:** High
**Currency:** KEUR (thousands of euros)
**Maintenance:** Update 15 records for pricing changes

---

### After (3 Categories)

| Category | Models | Input | Output |
|----------|--------|-------|--------|
| **A** | Mistral Large, Medium, Magistral Medium | 2.98 | 12.01 |
| **B** | Mistral Small, Codestral, Devstral, Magistral Small | 2.09 | 8.41 |
| **C** | Llama, GPT OSS 120b, GPT OSS 20b | 1.49 | 6.01 |
| **Embedding** | All embedding models | 0.00008 | - |
| **Reranking** | All reranking models | 0.00008 | - |

**Complexity:** Low
**Currency:** EUR (euros per million tokens)
**Maintenance:** Update 3 categories for pricing changes

**Improvement:** 80% fewer tiers, 100% clearer pricing

---

**ADR Version:** 1.0
**Created:** October 25, 2025
**Based On:** [Michael Nygard's ADR pattern](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
