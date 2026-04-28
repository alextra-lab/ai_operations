# Next Developer Quickstart - Embedding Model Architecture

**Last Updated:** October 30, 2025
**Current State:** P4-TOOLS-01 Shared Components - COMPLETE ✅
**Next Task:** P4-TOOLS-02 Semantic Search Enhancement (integrate shared components)

---

## What Just Happened (Oct 30, 2025)

We delivered foundational shared components for Query Developer Tools:

### New Shared Components

- `QueryResultsPanelComponent` — conversation-style results with streaming,
  sources, and metrics (standalone, OnPush)
- `ParameterConfigPanelComponent` — reactive forms; ADR-023 presets;
  RAG and advanced vector DB settings; emits `configChanged`
- `AutoScrollService` — stream-aware auto-scroll with user override detection
- `EnterToExecuteDirective` — Enter executes; Shift+Enter newline; persisted

These will be integrated in P4-TOOLS-02/03/04.

### Architecture Evolution

**From (Oct 19):** System-wide single embedding model
**To (Oct 27):** Per-collection model selection with same-model enforcement

### What's Different Now

1. **Collections Choose Their Own Model**
   - At creation time, user selects from available embedding models
   - Built-in `all-MiniLM-L6-v2` always available (local, 384D, $0)
   - Remote models (OpenAI, etc.) available when configured
   - Choice is immutable after creation

2. **System Configuration Default Changed**
   - **Was:** Global enforcement of embedding model
   - **Now:** Convenience pre-select in Collection Create Dialog
   - Health indicator if default model unavailable
   - Each collection still chooses independently

3. **Multi-Collection Search Constraint Added**
   - Use Cases can search multiple collections ONLY if same embedding model
   - Frontend filters collection list after first selection
   - Backend validates and returns 400 error if mixed
   - Rationale: Similarity scores differ between models (no normalization)

4. **Critical Bug Fixes**
   - RLS middleware: Fixed `role` extraction from JWT (was `roles` plural)
   - SQL syntax: Fixed CAST parameter style (was `:param::type`, now `CAST(:param AS type)`)
   - Result: System Configuration saves working correctly

---

## Current System State

### Embedding Models Available

**Built-in (Always Available):**
- `all-MiniLM-L6-v2` - 384D, local, $0, always available

**Remote (When Configured):**
- `text-embedding-3-small` - 1536D, OpenAI, requires API key
- `text-embedding-3-large` - 3072D, OpenAI, requires API key
- Others as seeded in `ops/database/seed/006_seed_embedding_models.sql`

### Database Seeded

**Test Database:**
- Host: localhost:5433
- Database: aio-test
- User: testuser
- Password: test_password_123

**Seeded Tables:**
- ✅ `users` (001_seed_users.sql)
- ✅ `intents` (002_seed_intents.sql)
- ✅ `use_cases` (003_seed_use_cases.sql)
- ✅ `pricing_tiers` (004_seed_pricing.sql)
- ✅ `models` (005_seed_models.sql - LLM models)
- ✅ `models` (006_seed_embedding_models.sql - Embedding models including all-MiniLM-L6-v2)
- ✅ `prompt_patterns` (007_seed_prompt_patterns.sql)

**Verify:**
```bash
PGPASSWORD=test_password_123 psql-17 -h localhost -p 5433 -U testuser -d aio-test \
  -c "SELECT model_id, provider, embedding_dimensions, is_available FROM models WHERE model_type='embedding';"
```

### System Configuration Updated

**Current Corpus Config:**
```json
{
  "chunk_size": 512,
  "chunk_overlap": 50,
  "default_embedding_model": "all-MiniLM-L6-v2",
  "max_document_size_mb": 50,
  "allowed_file_types": ["pdf", "txt", "docx", "md"]
}
```

**Health Status:** ✅ Healthy (default model available)

### Services Running

**Docker Compose Test Environment:**
```bash
docker ps | grep -E "orchestrator|corpus|embedding"
```

**Expected:**
- ✅ orchestrator-api-test (port 8006)
- ✅ corpus-service-test (port 8004)
- ✅ embedding-service-test (port 8005)

---

## Files Modified (17 Total)

### Backend (7 files)

1. **`src/orchestrator/app/middleware/rls.py`** ⭐ Critical fix
   - Fixed JWT role extraction: `role` not `roles`
   - RLS session variables now set correctly
   - Configuration saves working

2. **`src/orchestrator/app/routers/admin_config.py`** ⭐ Critical fix
   - Fixed SQL syntax: `CAST(:param AS type)` not `:param::type`
   - Configuration updates execute successfully

3. **`src/orchestrator/app/routers/health.py`**
   - Added `/health/config` endpoint
   - Validates default embedding model availability
   - Returns structured health report

4. **`src/corpus_svc/app/services/query_service.py`**
   - Added `_assert_same_embedding_model()` helper
   - Validates all collections share same model
   - Uses resolved model for query embeddings

5. **`src/corpus_svc/app/routers/query.py`**
   - Catches HTTPException from QueryService
   - Re-raises for FastAPI error handling

6. **`src/corpus_svc/app/routers/collections.py`**
   - Validates model availability on creation
   - Normalizes provider/dimensions from registry
   - Returns 400 if model unavailable

7. **`src/corpus_svc/app/schemas/query.py`**
   - Updated for collection_names parameter

### Frontend (9 files)

8-10. **System Configuration Component** (TS, HTML, SCSS)
   - Health banner for configuration issues
   - Model dropdown with available models
   - Validation for current selection

11-13. **Config Editor Component** (TS, HTML, SCSS)
   - Dynamic model dropdown in corpus settings
   - Model details display (provider, dimensions)
   - Warning icons for unavailable models

14-16. **Collection Create Dialog** (TS, HTML, SCSS)
   - Model selector dropdown
   - "BUILT-IN" badge for all-MiniLM-L6-v2
   - Model details card
   - Pre-selects system default
   - Immutability warning

17. **Use Case Wizard Component** (TS)
   - Loads collections with embedding models
   - Same-model filtering after first selection
   - Auto-correction for invalid selections
   - Validation blocks mixed models

### Database (1 file)

18. **`ops/database/seed/006_seed_embedding_models.sql`**
   - Added `all-MiniLM-L6-v2` model
   - Updated seed notices

### Documentation (10 files)

19. **ADR-021 Addendum 3** - Architecture decision
20. **SCHEMA.md** - Database documentation
21. **RAG_Architecture.md** - Architecture overview
22. **collection-management.md** - API documentation
23. **system-configuration.md** (NEW) - API documentation
24. **collection-management-guide.md** (NEW) - User guide
25. **system-configuration-guide.md** (NEW) - User guide
26. **embedding-model-architecture-guide.md** (NEW) - Developer guide
27. **2025-10-27-per-collection-embedding-model-architecture.md** - Session log
28. **MASTER_ROADMAP.md** - Progress tracking

---

## How To Use This Architecture

### As a User

**Creating a Collection:**
1. Navigate to Collections → Create
2. Select embedding model from dropdown
3. See "BUILT-IN" badge for `all-MiniLM-L6-v2`
4. Read immutability warning
5. Create collection

**Configuring Use Case RAG:**
1. Use Case Wizard → Step 4 (Configure)
2. Enable RAG
3. Select first collection
4. Dropdown filters to same-model collections only
5. Select additional collections (same model)
6. Save Use Case

**Monitoring Configuration Health:**
1. Admin → System Configuration
2. Check for red health banner
3. If shown, update default embedding model
4. Click "Save All"
5. Verify banner disappears

### As a Developer

**Adding a New Embedding Model:**

1. **Register in Model Registry:**
```sql
INSERT INTO models (
    model_id, name, provider, model_type,
    embedding_dimensions, is_available, health_status,
    description
) VALUES (
    'new-model-id', 'New Model Name', 'provider', 'embedding',
    768, TRUE, 'healthy',
    'Model description'
);
```

2. **Configure Backend Service:**
- Update embedding service to support new model
- Add to model loading logic
- Test embedding generation

3. **Verify Registration:**
```bash
curl http://localhost:8006/api/v1/models?model_type=embedding | jq '.models[] | select(.model_id=="new-model-id")'
```

4. **Test in UI:**
- Collection Create Dialog should show new model
- System Configuration dropdown should include it
- Select and create test collection

**Adding Same-Model Validation:**

Already implemented! But if you need to add additional validation:

```python
# Backend: Add to QueryService
def _validate_collection_compatibility(self, collections):
    """Additional compatibility checks beyond same-model."""
    # Example: Check vector dimensions match
    dimensions = {c.embedding_dimensions for c in collections}
    if len(dimensions) > 1:
        raise HTTPException(400, "Dimension mismatch")
```

```typescript
// Frontend: Add to Use Case Wizard
private validateCollectionCompatibility(selected: string[]): void {
  // Additional validation beyond same-model
  // Example: Check collection activity status
  const inactive = selected.filter(name => {
    const coll = this.allCollectionsWithModels.find(c => c.name === name);
    return coll && !coll.is_active;
  });
  if (inactive.length > 0) {
    this.showError('Selected collections must be active');
  }
}
```

---

## Testing Checklist

### Manual Testing (Already Complete)

- ✅ System Configuration health banner displays
- ✅ Model dropdown populated from registry
- ✅ Configuration saves after bug fixes
- ✅ Health banner disappears with available model
- ✅ Collection creation validates model
- ✅ Collection creation shows model dropdown
- ✅ Use Case wizard filters collections
- ✅ Use Case wizard blocks mixed models
- ✅ Backend enforces same-model constraint

### Automated Testing (Recommended for Next PR)

**Backend Tests:**
```python
# Test collection creation validation
def test_create_collection_validates_model_availability()
def test_create_collection_normalizes_from_registry()
def test_create_collection_rejects_unavailable_model()

# Test multi-collection search validation
def test_semantic_search_enforces_same_model()
def test_semantic_search_allows_same_model()
def test_semantic_search_returns_detailed_error()

# Test health endpoint
def test_config_health_detects_unavailable_model()
def test_config_health_returns_healthy_when_available()
```

**Frontend Tests:**
```typescript
// Test Collection Create Dialog
describe('CollectionCreateDialogComponent', () => {
  it('should load embedding models from registry');
  it('should pre-select system default model');
  it('should display BUILT-IN badge for all-MiniLM-L6-v2');
  it('should show model details card');
});

// Test Use Case Wizard
describe('UseCaseWizardComponent - RAG Configuration', () => {
  it('should load collections with embedding models');
  it('should filter to same-model after first selection');
  it('should auto-correct mixed model selections');
  it('should validate same-model on save');
});

// Test System Configuration
describe('SystemConfigComponent', () => {
  it('should display health banner when model unavailable');
  it('should hide health banner when model available');
  it('should check health after config save');
});
```

---

## Known Issues & Limitations

### Current (v1.0)

1. **Multi-Model Search Not Supported**
   - Use Cases cannot search collections with different embedding models
   - Similarity score normalization deferred to Phase 5+
   - Frontend filters to same-model automatically
   - Backend enforces constraint with 400 error

2. **Immutable Collection Model**
   - Cannot change collection's embedding model after creation
   - Must create new collection and re-upload documents
   - Migration tool planned for Phase 5 (P5-F8)

3. **No Automated Model Health Monitoring**
   - Manual check required via `/health/config`
   - No proactive alerts if model becomes unavailable
   - Future: Automated monitoring service (Phase 6)

### Future Enhancements (Phase 5+)

1. **P5-F8: Collection Migration Tool**
   - Automated re-embedding service
   - Progress tracking with ETA
   - Cost estimation for remote models
   - Safe rollback on failure

2. **Multi-Model Search (Research Phase)**
   - Score normalization investigation
   - Cross-model similarity benchmarking
   - Optional advanced feature for power users

3. **Model Health Monitoring**
   - Automated health checks
   - Proactive alerts when models degrade
   - Automatic fallback to built-in model

---

## Next Steps for Development

### Immediate (Phase 4)

**Option A: P4-TOOLS - Query Developer Tools Suite (24-30 days)**
- Shared components (QueryResultsPanel, ParameterConfigPanel)
- Enhanced Semantic Search and RAG Q&A pages
- Unified `/dev/query-tools` interface
- Parameter injection workflow
- Use Case Execution refactor
- Metrics dashboard
- **Recommended:** Use Claude 4.5 for architecture decisions

**Option B: P2-FIX-13 - Simplified Pricing Model (1-2 days)**
- Replace 15-tier model with 3-category model
- ADR-042 implementation
- Simpler user experience
- **Recommended:** Use Auto for straightforward refactor

### Medium-Term (Phase 5)

**P5-F8: Embedding Model Migration Tool (4-5 days)**
- Per-collection migration interface
- Background re-embedding service
- Progress tracking
- Cost estimation
- Requires: Current architecture complete ✅

### Long-Term (Phase 6+)

**Multi-Model Search Research**
- Score normalization methods
- Cross-model benchmarking
- User studies for result quality

---

## Architecture Quick Reference

### Key Concepts

1. **Collection** - Isolated namespace for documents with one embedding model
2. **Embedding Model** - AI model converting text to vectors (e.g., all-MiniLM-L6-v2)
3. **Built-in Model** - Local model (all-MiniLM-L6-v2), always available, $0
4. **Remote Model** - Cloud model (OpenAI, etc.), requires API key
5. **Immutable Binding** - Collection's model cannot change after creation
6. **Same-Model Constraint** - Multi-collection searches require same model

### Data Flow

```
System Configuration (default_embedding_model)
    ↓ (convenience pre-select)
Collection Create Dialog (user chooses model)
    ↓ (validates availability)
Collection Created (model immutable)
    ↓ (documents embedded with collection's model)
Use Case Configuration (selects collections)
    ↓ (filters to same-model)
Query Execution (uses collection's model)
    ↓ (results merged, same score scale)
Results Returned
```

### Validation Points

1. **Collection Creation:** Model exists in registry + is_available=true
2. **Use Case Configuration:** All selected collections share same model (frontend filter)
3. **Query Execution:** Backend validates same-model, returns 400 if mixed
4. **System Configuration:** Health check validates default model available

---

## Important Files

### Backend Critical Files

| File | Purpose | Key Changes |
|------|---------|-------------|
| `src/orchestrator/app/middleware/rls.py` | RLS session variables | Fixed role extraction |
| `src/orchestrator/app/routers/admin_config.py` | System config API | Fixed SQL CAST syntax |
| `src/orchestrator/app/routers/health.py` | Health endpoints | Added /health/config |
| `src/corpus_svc/app/services/query_service.py` | Query orchestration | Added same-model validation |
| `src/corpus_svc/app/routers/collections.py` | Collection CRUD | Added model availability check |

### Frontend Critical Files

| File | Purpose | Key Changes |
|------|---------|-------------|
| `src/frontend-angular/src/app/pages/admin/system-config/system-config.component.ts` | System config page | Added health banner |
| `src/frontend-angular/src/app/pages/admin/system-config/components/config-editor/config-editor.component.*` | Config form | Added model dropdown |
| `src/frontend-angular/src/app/pages/collections/collection-create-dialog.component.*` | Collection creation | Added model selector |
| `src/frontend-angular/src/app/pages/use-cases/use-case-wizard.component.ts` | Use case wizard | Added same-model filtering |

### Documentation

| File | Purpose |
|------|---------|
| `docs/development/adrs/ADR-021-Collection-Based-Document-Management.md` | Architecture decision (Addendum 3) |
| `docs/development/guides/embedding-model-architecture-guide.md` | Developer guide |
| `docs/user-guides/collection-management-guide.md` | User guide for collections |
| `docs/user-guides/system-configuration-guide.md` | User guide for system config |
| `docs/api/collection-management.md` | API reference |
| `docs/api/admin/system-configuration.md` | API reference (NEW) |
| `docs/architecture/database/SCHEMA.md` | Database schema |
| `docs/architecture/RAG_Architecture.md` | RAG architecture |

---

## Quick Commands

### Check Database State

```bash
# Check embedding models
PGPASSWORD=test_password_123 psql-17 -h localhost -p 5433 -U testuser -d aio-test \
  -c "SELECT model_id, is_available FROM models WHERE model_type='embedding';"

# Check system config
PGPASSWORD=test_password_123 psql-17 -h localhost -p 5433 -U testuser -d aio-test \
  -c "SELECT config->>'default_embedding_model' FROM system_config WHERE section='corpus';"

# Check collections
PGPASSWORD=test_password_123 psql-17 -h localhost -p 5433 -U testuser -d aio-test \
  -c "SELECT name, embedding_model, embedding_dimensions FROM collections;"
```

### Test API Endpoints

```bash
# Get admin token
TOKEN=$(curl -s -X POST "http://localhost:4201/auth/token" \
  -d "username=admin&password=admin" | jq -r '.access_token')

# Check available embedding models
curl -X GET "http://localhost:4201/api/v1/models?model_type=embedding" \
  -H "Authorization: Bearer $TOKEN" | jq '.models[] | {model_id, is_available}'

# Check configuration health
curl -X GET "http://localhost:4201/health/config" \
  -H "Authorization: Bearer $TOKEN" | jq

# Get system configuration
curl -X GET "http://localhost:4201/api/v1/admin/config/corpus" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Restart Services

```bash
# After code changes
docker restart orchestrator-api-test
docker restart corpus-service-test

# Verify health
docker ps | grep -E "orchestrator|corpus"
curl http://localhost:4201/health
```

---

## Common Gotchas

### 1. RLS Session Variables

**Problem:** Configuration saves fail with 500 error
**Cause:** JWT token doesn't have correct role
**Fix:** Middleware extracts `role` (singular) from TokenPayload
**Verify:** Check logs for "Set RLS session variables" debug message

### 2. SQL Parameter Syntax

**Problem:** `syntax error at or near ":"`
**Cause:** Using `:param::type` with SQLAlchemy named parameters
**Fix:** Use `CAST(:param AS type)` syntax instead
**Verify:** Query executes without syntax errors

### 3. Container Not Updated

**Problem:** Code changes not reflected in application
**Cause:** Container not rebuilt or restarted
**Fix:** `docker restart orchestrator-api-test`
**Verify:** Check container logs for startup messages

### 4. Model Dropdown Empty

**Problem:** Collection Create Dialog shows no models
**Cause:** Models not seeded or API error
**Fix:** Run `006_seed_embedding_models.sql`, check API response
**Verify:** GET `/api/v1/models?model_type=embedding` returns models

### 5. Health Banner Won't Disappear

**Problem:** Banner persists after selecting available model
**Cause:** Save failed, cache stale, or model still unavailable
**Fix:** Hard refresh, check console, verify model in registry
**Verify:** GET `/health/config` returns `healthy: true`

---

## Decision Context for Next Developer

### Why Per-Collection Models?

**Problem Solved:**
- Flexibility: Different collections can use different quality/cost models
- Availability: Built-in model guarantees uptime (air-gapped friendly)
- Cost Control: Mix free (built-in) and paid (remote) models
- Migration Path: Clear upgrade strategy per collection

**Tradeoffs Accepted:**
- Multi-model search deferred (complexity)
- Same-model constraint for Use Cases (consistency)
- Migration requires tool (Phase 5)

### Why Same-Model Constraint?

**Technical Reason:**
- Similarity scores differ between embedding models
- All-MiniLM-L6-v2 score 0.85 ≠ text-embedding-3-small score 0.85
- No reliable normalization method
- Merging would produce inconsistent rankings

**Alternative Considered:**
- Score normalization research
- Statistical calibration
- **Rejected:** Too complex for v1, uncertain accuracy

**Future Path:**
- Research score normalization (Phase 5+)
- Benchmark cross-model similarity
- User studies for result quality
- Optional advanced feature

### Why Built-in Model?

**Business Requirements:**
- Air-gapped deployment support (critical)
- Zero API costs (budget friendly)
- Guaranteed availability (no external dependencies)
- Fast local processing (low latency)

**Technical Benefits:**
- 384D sufficient for semantic search
- sentence-transformers proven technology
- No API quota limits
- Privacy: embeddings stay local

---

## References

### ADRs
- **ADR-021 Addendum 3:** Per-Collection Embedding Model Selection
- **ADR-037:** UUID Primary Keys
- **ADR-038:** JSONB Configuration Storage
- **ADR-039:** Row-Level Security

### Session Logs
- **2025-10-27-per-collection-embedding-model-architecture.md** - Implementation details
- **2025-10-26-model-registry-bug-fix.md** - embedding_dimensions column added
- **2025-10-19-embedding-model-strategy.md** - Original single-model decision

### User Guides
- **collection-management-guide.md** - How to create and manage collections
- **system-configuration-guide.md** - How to configure system settings

### API Docs
- **collection-management.md** - Collection CRUD API
- **system-configuration.md** - System configuration API (NEW)

### Developer Guides
- **embedding-model-architecture-guide.md** - Architecture and code examples (NEW)

---

**Ready for Next Task!** 🚀

All documentation updated, architecture implemented, bugs fixed, and system operational.

**Recommended Next:** P4-TOOLS Query Developer Tools Suite (high impact, 24-30 days)
**Alternative Next:** P2-FIX-13 Simplified Pricing Model (quick win, 1-2 days)

---

**Document Owner:** Project team
**Last Updated:** October 27, 2025
**Status:** Current - Ready for Next Developer
