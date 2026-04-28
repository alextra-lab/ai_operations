---
id: ADR-019
title: Offline Tokenizer Strategy for Air-gapped Deployment
status: Accepted
date: 2025-01-27
deciders: AI Operations Platform Team
tags: [air-gapped, tokenizer, tiktoken, pricing, llm]
---

## Context

**Air-gapped deployment requirement**: Production environments cannot access HuggingFace or external tokenizer registries

**Current issue**: `tiktoken.encoding_for_model()` and `tiktoken.get_encoding()` require internet access on first use to download BPE vocabulary files

**Impact**: `ContextCompactionService` (line 30, 34) will fail in production without pre-bundled tokenizers

**LLMaaS pricing model**: Token-based pricing with input/output rates requiring precise token counting

**Dynamic pricing**: Pricing matrix must be configurable via UI without code changes

---

## Decision

Bundle tokenizer vocabulary files for all supported models in the codebase:

**Required tokenizers (per user specification):**
- Foundation-sec model
- Phi-4 mini
- Mistral Large (input: 1.10 TPM, output: 0.30 TPM, rate: 2000 TPM)
- Mistral Small (input: 1.60 TPM, output: 0.40 TPM, rate: 3000 TPM)
- GPT-oss
- Llama 3.3 (Codestral/Llama based on pricing table)

**Implementation approach:**
1. Store tokenizer BPE files in `data/tokenizers/` (gitignored but included in Docker image)
2. Update `ContextCompactionService.__init__()` to use local tokenizer files
3. Add fallback chain: local files → tiktoken defaults → character approximation
4. Document tokenizer installation in `ops/bootstrap/` for air-gapped deployments
5. **Database-backed pricing matrix** (not YAML file) for UI management
6. **Admin UI for pricing tier CRUD** operations

---

## Alternatives Considered

### Option 1: Character-based approximation only
**Description:** Use character count / 4 as token approximation
**Pros:**
- No external dependencies
- Works in any environment

**Cons:**
- 15-25% accuracy variance impacts rate limit calculations and cost estimates
- Insufficient precision for LLMaaS pricing model

**Why Rejected:** Insufficient precision for LLMaaS pricing model

### Option 2: HTTP proxy for tokenizer downloads
**Description:** Use corporate proxy to access HuggingFace during deployment
**Pros:**
- Standard tiktoken workflow
- No code changes required

**Cons:**
- Violates air-gapped security requirement
- Still requires external network access

**Why Rejected:** Non-negotiable security constraint

### Option 3: Pre-cache tiktoken files in Docker build
**Description:** Download tokenizers during Docker build on internet-connected machine
**Pros:**
- Minimal code changes
- Standard tiktoken usage pattern

**Cons:**
- Still requires internet during build, not fully offline
- Build environment may also be air-gapped

**Why Rejected:** Build environment may also be air-gapped

### Option 4: YAML-based pricing configuration
**Description:** Store pricing tiers in configuration files
**Pros:**
- Simple file-based management
- Version controlled pricing changes

**Cons:**
- Requires deployment to update pricing, no audit trail
- No dynamic updates without code changes

**Why Rejected:** User requires UI-based management

---

## Consequences

### Positive Consequences

**Benefits of this decision:**
- Air-gapped deployment compliant
- Accurate token counting for rate limit management
- Predictable cost estimation (±2% accuracy vs. ±20% with approximation)
- Supports all 15+ LLMaaS pricing tiers
- **Dynamic pricing updates without redeployment**
- **Full audit trail of pricing changes**
- **Role-based access control for pricing management**

### Negative Consequences

**Tradeoffs and costs:**
- ~50MB additional storage for tokenizer files (6 models × ~8MB each)
- Manual tokenizer updates when new models added
- Testing burden: verify tokenizers work offline
- Additional database schema for pricing tiers
- Admin UI development overhead

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Tokenizer files corrupted during transfer | Medium | Include checksums in bundle, verify on extraction |
| New models not supported | Low | Document process for adding tokenizers, provide clear error messages |
| Pricing tier conflicts | Medium | Unique constraints in database, validation in UI |
| Admin UI complexity | Low | Use Material Design patterns, comprehensive testing |

---

## Implementation Notes

**Files to modify:**
- `src/orchestrator/app/services/context_compaction_service.py` - Update `__init__()` with offline loading
- `data/tokenizers/README.md` - Document bundled tokenizers and update procedure
- `Dockerfile` (backend) - Copy tokenizer files into image
- `ops/bootstrap/prepare_tokenizers.sh` - Script to bundle tokenizers for air-gapped transfer
- **`src/orchestrator/app/db/models.py` - Add `PricingTier` and `ModelConfig` tables**
- **`src/orchestrator/app/routers/admin_pricing.py` - Admin API for pricing CRUD**
- **`src/frontend-angular/src/app/pages/admin/pricing-management/` - Admin UI components**

**Testing strategy:**
- Unit tests with mocked tokenizer files
- Integration test: disable network, verify token counting still works
- Performance test: compare online vs. offline tokenizer load times
- **E2E test: update pricing tier via UI, verify rate calculations update**

---

## References

- Current tiktoken usage: `src/orchestrator/app/services/context_compaction_service.py:12-34`
- Token tracking: `src/orchestrator/app/services/token_tracker.py`
- Existing metrics: `src/orchestrator/app/schemas/response.py:81-97` (ModelMetrics)
- Phase 4 plan: `docs/development/plans/UI_DEVELOPMENT_PLAN.md:3171-3475`
- Phase 5 plan: `docs/development/plans/UI_DEVELOPMENT_PLAN.md:3476-3650` (Admin features)
- LLMaaS pricing: User-provided pricing table (15 tiers)

---

## Status Updates

### 2025-01-27 - Accepted
**Changed By:** Development Team
**Reason:** Plan approved by user, implementation ready to begin

### 2025-12-11 - Frontend Font Bundling Correction
**Changed By:** Development Team
**Reason:** Fixed critical air-gapped deployment issue where Material Icons and Roboto fonts were loaded from Google Fonts CDN, breaking standalone mode.

**Correction:**
- Bundled Material Icons and Roboto fonts locally via npm packages (`material-icons`, `typeface-roboto`)
- Added `postinstall` script to automatically copy fonts from `node_modules/` to `public/fonts/` on clean installs
- Removed Google Fonts CDN links from `index.html`
- Updated CSP headers to remove `fonts.googleapis.com` and `fonts.gstatic.com` references
- Fonts now bundled in Layer 3 (Third-Party Library Styles) per ADR-012

**Impact:** Application now fully air-gapped compliant for standalone mode; all UI assets work without internet access.

---

**Template Version:** 1.0
**Based On:** [Michael Nygard's ADR pattern](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
