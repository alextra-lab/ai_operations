# Embedding Model Architecture - Developer Guide

**Version:** 1.0
**Date:** October 27, 2025
**Status:** ✅ Production Ready
**ADR:** [ADR-021 Addendum 3](../adrs/ADR-021-Collection-Based-Document-Management.md)

---

## Quick Summary

**Architecture:** Per-collection embedding model selection with same-model enforcement for multi-collection searches.

**Key Points:**

- ✅ Collections choose embedding model at creation (immutable thereafter)
- ✅ Built-in `all-MiniLM-L6-v2` always available (local, 384D, $0)
- ✅ Use Cases search multiple collections ONLY if same embedding model
- ✅ System Configuration default is convenience pre-select (not enforcement)
- ✅ Backend validates model availability via Model Registry
- ✅ Frontend provides rich UI with health indicators and filtering

---

## Architecture Evolution

### Phase 1: Single Global Model (Oct 19, 2025)

- System-wide embedding model configuration
- All collections forced to use same model
- Documented in ADR-021 original version

### Phase 2: Per-Collection Selection (Oct 27, 2025) ← **CURRENT**

- Collections choose their own embedding model
- Same-model constraint for multi-collection searches
- Built-in model always available
- Documented in ADR-021 Addendum 3

### Phase 3: Multi-Model Fusion (Future - Phase 5+)

- Score normalization research
- Cross-model similarity benchmarking
- Optional advanced feature
- Requires extensive validation

---

## Components & Data Flow

### 1. Model Registry (Source of Truth)

**Table:** `models`
**Relevant Columns:**

- `model_id` - Unique identifier (e.g., "all-MiniLM-L6-v2")
- `model_type` - Must be 'embedding'
- `provider` - Provider name (local, openai, etc.)
- `embedding_dimensions` - Vector dimensions (384, 1536, etc.)
- `is_available` - Availability status (true/false)
- `health_status` - Health indicator (healthy, degraded, unhealthy)

**Built-in Model:**

```sql
INSERT INTO models (
    model_id, name, provider, model_type,
    embedding_dimensions, is_available, health_status
) VALUES (
    'all-MiniLM-L6-v2', 'all-MiniLM-L6-v2', 'local', 'embedding',
    384, TRUE, 'healthy'
);
```

**Query Available Models:**

```sql
SELECT model_id, name, provider, embedding_dimensions
FROM models
WHERE model_type = 'embedding' AND is_available = true
ORDER BY embedding_dimensions, model_id;
```

### 2. System Configuration (Convenience Default)

**Table:** `system_config`
**Section:** `corpus`
**Field:** `config->>'default_embedding_model'`

**Purpose:**

- Pre-selects model in Collection Create Dialog
- Provides consistent default for new collections
- **NOT a global enforcement** - each collection chooses independently

**Health Check:**

```sql
SELECT
    sc.config->>'default_embedding_model' as configured_model,
    m.is_available,
    m.health_status
FROM system_config sc
LEFT JOIN models m ON m.model_id = sc.config->>'default_embedding_model'
WHERE sc.section = 'corpus';
```

**Update Default:**

```sql
UPDATE system_config
SET config = jsonb_set(config, '{default_embedding_model}', '"all-MiniLM-L6-v2"')
WHERE section = 'corpus';
```

### 3. Collections (Model Binding)

**Table:** `collections`
**Relevant Columns:**

- `embedding_model` - Model ID (immutable after creation)
- `embedding_provider` - Provider name
- `embedding_dimensions` - Vector dimensions

**Creation Flow:**

1. User selects model from dropdown (frontend)
2. POST `/admin/collections` with model ID, provider, dimensions
3. Backend validates:
   - Model exists in `models` table
   - `model_type = 'embedding'`
   - `is_available = true`
4. Backend normalizes provider/dimensions from registry (ignores client values)
5. Collection created with authoritative model metadata

**Validation Query:**

```sql
SELECT provider, embedding_dimensions
FROM models
WHERE model_id = :model_id
  AND model_type = 'embedding'
  AND is_available = true;
```

### 4. Use Cases (Same-Model Enforcement)

**Configuration:** `config_json.rag.vector_collections`
**Constraint:** All selected collections must share same embedding model

**Frontend Enforcement (Use Case Wizard):**

```typescript
// Load collections with models
collectionService.listAvailableCollections()
  .subscribe(resp => {
    this.allCollectionsWithModels = resp.collections;
    // After first selection, filter to same-model only
    this.enforceSameModelSelection(selected);
  });
```

**Backend Enforcement (Query Service):**

```python
def _assert_same_embedding_model(
    self, collections: List[Collection]
) -> str:
    """Validates all collections use same embedding model."""
    model_ids = {c.embedding_model for c in collections}
    if len(model_ids) != 1:
        raise HTTPException(
            status_code=400,
            detail=f"Collections use different embedding models: {info}"
        )
    return next(iter(model_ids))
```

---

## Implementation Checklist

### Creating a Collection

**Frontend (Collection Create Dialog):**

1. ✅ Load available models from Model Registry
2. ✅ Pre-select system default from System Configuration
3. ✅ Display model dropdown with:
   - Model name
   - Provider badge
   - Dimensions badge
   - "BUILT-IN" badge for `all-MiniLM-L6-v2`
   - Warning icon if unavailable (disabled)
4. ✅ Show selected model details card
5. ✅ Display immutability warning
6. ✅ Submit model_id, provider, dimensions to backend

**Backend (Collection Router):**

1. ✅ Validate model exists in registry
2. ✅ Check `is_available=true` and `model_type='embedding'`
3. ✅ Normalize provider/dimensions from registry
4. ✅ Create collection with authoritative metadata
5. ✅ Return 400 error if model unavailable

### Configuring Use Case RAG

**Frontend (Use Case Wizard Step 4):**

1. ✅ Load all collections with their embedding models
2. ✅ Display all collections initially
3. ✅ On first selection, filter to same-model collections
4. ✅ Auto-correct if mixed selection detected
5. ✅ Show inline error: "All collections must share same model"
6. ✅ Block save if validation fails

**Backend (Query Service):**

1. ✅ If collection_names provided, load collection metadata
2. ✅ Validate all collections exist and are active
3. ✅ Assert same embedding model across all
4. ✅ Use resolved model for query embedding
5. ✅ Return 400 error with collection details if mixed

### System Configuration Health

**Frontend (System Config Page):**

1. ✅ Call `/health/config` on load and after save
2. ✅ Display red banner if `healthy: false`
3. ✅ Show issues with severity, message, recommendation, impact
4. ✅ Hide banner when `healthy: true`

**Backend (Health Router):**

1. ✅ Query `system_config` for default embedding model
2. ✅ Query `models` to check if model exists and is available
3. ✅ Return structured health report with issues array
4. ✅ Include severity (critical/warning), component, recommendation, impact

---

## Code Examples

### Frontend: Load Models for Dropdown

```typescript
export class CollectionCreateDialogComponent implements OnInit {
  embeddingModels: Model[] = [];
  selectedModel: Model | null = null;

  ngOnInit(): void {
    this.loadEmbeddingModels();
  }

  private loadEmbeddingModels(): void {
    this.modelRegistryService.getEmbeddingModels().subscribe({
      next: (models: Model[]) => {
        this.embeddingModels = models;
        // Pre-select system default
        this.systemConfigService.getConfig().subscribe({
          next: (config) => {
            const defaultModel = config.corpus?.default_embedding_model;
            if (defaultModel) {
              this.createForm.patchValue({ embedding_model: defaultModel });
            }
          }
        });
      }
    });
  }
}
```

### Backend: Validate Model on Creation

```python
from sqlalchemy import text as sa_text

@admin_router.post("/", response_model=CollectionResponse)
async def create_collection(
    collection: CollectionCreate,
    session: AsyncSession = Depends(get_async_session)
):
    # Validate embedding model
    registry_check = await session.execute(
        sa_text(
            "SELECT provider, embedding_dimensions FROM models "
            "WHERE model_id = :model_id AND model_type = 'embedding' "
            "AND is_available = true"
        ),
        {"model_id": collection.embedding_model},
    )
    row = registry_check.fetchone()

    if not row:
        raise ValueError(
            f"Embedding model '{collection.embedding_model}' is not available. "
            "Choose an available embedding model."
        )

    # Normalize from registry
    provider = str(row[0])
    dimensions = int(row[1])

    # Create with authoritative values
    normalized = CollectionCreate(
        name=collection.name,
        description=collection.description,
        embedding_model=collection.embedding_model,
        embedding_provider=provider,
        embedding_dimensions=dimensions,
    )

    new_collection = await repo.create_collection(normalized, created_by=user_id)
    return CollectionResponse.model_validate(new_collection)
```

### Backend: Enforce Same-Model for Multi-Collection Search

```python
class QueryService:
    def _assert_same_embedding_model(
        self, collections: List[Collection]
    ) -> str:
        """Asserts all collections use same embedding model."""
        model_ids = {c.embedding_model for c in collections}

        if len(model_ids) != 1:
            collection_info = [
                f"{c.name} ({c.embedding_model})"
                for c in collections
            ]
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Collections use different embedding models: "
                    f"{', '.join(collection_info)}. "
                    "All collections in a Use Case must use the same "
                    "embedding model."
                )
            )

        return next(iter(model_ids))

    async def perform_semantic_search(
        self,
        collection_names: list[str] | None = None,
        embedding_model: str | None = None,
        ...
    ):
        # If multiple collections, validate same-model
        if collection_names:
            collections = await self.repo.get_collections_by_names(
                collection_names
            )
            # Enforce constraint
            shared_model = self._assert_same_embedding_model(collections)
            embedding_model = shared_model  # Use for query embedding

        # Generate embeddings with resolved model
        embedding = await self.embedding_client.get_embedding(
            query_text, model=embedding_model
        )
        ...
```

### Frontend: Same-Model Filtering in Wizard

```typescript
export class UseCaseWizardComponent {
  availableCollections: string[] = [];
  allCollectionsWithModels: Array<{
    name: string;
    embedding_model: string;
  }> = [];

  private loadAvailableModels(): void {
    this.collectionService.listAvailableCollections().subscribe({
      next: (resp) => {
        this.allCollectionsWithModels = resp.collections || [];
        this.availableCollections = this.allCollectionsWithModels.map(
          c => c.name
        );

        // Subscribe to selection changes
        this.configForm.get('rag_vector_collections')?.valueChanges
          .subscribe((selected: string[]) => {
            this.enforceSameModelSelection(selected);
          });
      }
    });
  }

  private enforceSameModelSelection(selected: string[]): void {
    if (!selected || selected.length === 0) {
      // Reset to all
      this.availableCollections = this.allCollectionsWithModels.map(
        c => c.name
      );
      return;
    }

    // Get model of first selection
    const first = this.allCollectionsWithModels.find(
      c => c.name === selected[0]
    );
    if (!first) return;

    // Filter to same model
    const sameModelCollections = this.allCollectionsWithModels
      .filter(c => c.embedding_model === first.embedding_model)
      .map(c => c.name);

    this.availableCollections = sameModelCollections;

    // Auto-correct invalid selections
    const mismatched = selected.filter(
      name => !sameModelCollections.includes(name)
    );
    if (mismatched.length > 0) {
      const filtered = selected.filter(
        name => sameModelCollections.includes(name)
      );
      this.configForm.patchValue(
        { rag_vector_collections: filtered },
        { emitEvent: false }
      );
      this.showError(
        'All selected collections must share the same embedding model'
      );
    }
  }
}
```

---

## Database Schema Reference

### Models Table

```sql
CREATE TABLE models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(500) NOT NULL,
    provider VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) NOT NULL CHECK (model_type IN ('llm', 'embedding')),
    context_window INTEGER,
    embedding_dimensions INTEGER,  -- Required for embedding models
    description TEXT,
    capabilities TEXT[],
    is_available BOOLEAN DEFAULT TRUE,
    health_status VARCHAR(50) DEFAULT 'healthy',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_models_type_available
ON models(model_type, is_available);
```

### Collections Table

```sql
CREATE TABLE collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    embedding_model VARCHAR(255) NOT NULL,  -- Immutable
    embedding_provider VARCHAR(100) NOT NULL,  -- Immutable
    embedding_dimensions INTEGER NOT NULL,  -- Immutable
    qdrant_collection_name VARCHAR(255) UNIQUE NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_system_managed BOOLEAN DEFAULT FALSE,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    document_count INTEGER DEFAULT 0 CHECK (document_count >= 0)
);

-- No foreign key to models table (allows model deletion without cascading)
CREATE INDEX idx_collections_embedding_model ON collections(embedding_model);
```

### System Config Table

```sql
CREATE TABLE system_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section TEXT NOT NULL UNIQUE,
    config JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL
);

-- Corpus section example
{
  "chunk_size": 512,
  "chunk_overlap": 50,
  "default_embedding_model": "all-MiniLM-L6-v2",
  "max_document_size_mb": 50,
  "allowed_file_types": ["pdf", "txt", "docx", "md"]
}
```

---

## API Endpoints Reference

### Model Registry

**GET** `/api/v1/models?model_type=embedding&is_available=true`

Returns available embedding models.

```json
{
  "models": [
    {
      "id": "uuid",
      "model_id": "all-MiniLM-L6-v2",
      "name": "all-MiniLM-L6-v2",
      "provider": "local",
      "model_type": "embedding",
      "embedding_dimensions": 384,
      "is_available": true,
      "health_status": "healthy"
    }
  ]
}
```

### Collection Creation

**POST** `/api/v1/admin/collections/`

Validates and creates collection with normalized model metadata.

```json
// Request
{
  "name": "threat_intel",
  "description": "Threat intelligence reports",
  "embedding_model": "all-MiniLM-L6-v2",
  "embedding_provider": "local",  // Ignored - normalized from registry
  "embedding_dimensions": 384      // Ignored - normalized from registry
}

// Response (201 Created)
{
  "id": "uuid",
  "name": "threat_intel",
  "embedding_model": "all-MiniLM-L6-v2",
  "embedding_provider": "local",      // From registry
  "embedding_dimensions": 384,        // From registry
  "qdrant_collection_name": "collection_threat_intel",
  ...
}

// Error (400 Bad Request)
{
  "detail": "Embedding model 'text-embedding-3-small' is not available. Choose an available embedding model."
}
```

### Multi-Collection Query

**POST** `/api/v1/semantic-search`

Validates same-model constraint and uses collection's model for embedding.

```json
// Request
{
  "query_text": "What are the latest ransomware trends?",
  "collection_names": ["threat_intel", "malware_reports"],
  "top_k": 10
}

// Success (200 OK) - Same model
{
  "query_id": "uuid",
  "results": [...],
  "total_results": 10
}

// Error (400 Bad Request) - Mixed models
{
  "detail": "Collections use different embedding models: threat_intel (all-MiniLM-L6-v2), executive_briefs (text-embedding-3-small). All collections in a Use Case must use the same embedding model."
}
```

### Configuration Health

**GET** `/health/config`

Validates default embedding model availability.

```json
// Healthy
{
  "healthy": true,
  "issues": [],
  "checked_at": "2025-10-27T18:50:00Z",
  "status": "healthy"
}

// Unhealthy
{
  "healthy": false,
  "issues": [
    {
      "severity": "critical",
      "component": "corpus_config",
      "message": "Default embedding model 'text-embedding-3-small' is not available",
      "recommendation": "Update default_embedding_model to an available model",
      "impact": "Cannot create new collections"
    }
  ],
  "checked_at": "2025-10-27T18:50:00Z",
  "status": "unhealthy"
}
```

---

## Testing Strategies

### Unit Tests

**Test Model Validation:**

```python
def test_create_collection_with_unavailable_model():
    """Should return 400 if model unavailable."""
    response = client.post(
        "/api/v1/admin/collections/",
        json={
            "name": "test_collection",
            "embedding_model": "unavailable-model",
            "embedding_provider": "openai",
            "embedding_dimensions": 1536
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400
    assert "is not available" in response.json()["detail"]
```

**Test Same-Model Enforcement:**

```python
def test_multi_collection_search_mixed_models():
    """Should return 400 if collections use different models."""
    response = client.post(
        "/api/v1/semantic-search",
        json={
            "query_text": "test query",
            "collection_names": ["collection_a", "collection_b"]
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "different embedding models" in response.json()["detail"]
```

### Integration Tests

**Test End-to-End Flow:**

1. Create collection with built-in model
2. Upload document to collection
3. Create Use Case with collection
4. Execute query
5. Verify results use correct embedding model

**Test Health Monitoring:**

1. Set unavailable model as default
2. Call `/health/config`
3. Verify `healthy: false` and issues array populated
4. Update to available model
5. Call `/health/config` again
6. Verify `healthy: true`

### Manual Testing

**Scenario 1: Collection Creation**

1. Navigate to Collections → Create
2. Select different models, verify dropdown behavior
3. Create with built-in model
4. Verify model metadata in collection details

**Scenario 2: Use Case Configuration**

1. Create collections with different models
2. Open Use Case Wizard → Step 4 (RAG Settings)
3. Select first collection (model A)
4. Verify dropdown filters to model A only
5. Try to select model B collection → should be disabled/hidden
6. Clear selections → verify all collections shown again

**Scenario 3: System Configuration**

1. Set unavailable model as default
2. Verify red health banner appears
3. Change to available model
4. Click "Save All"
5. Verify health banner disappears
6. Create new collection → verify model pre-selected

---

## Troubleshooting

### Problem: Model Dropdown Empty

**Causes:**

- Model Registry service not responding
- No embedding models seeded
- Network connectivity issue

**Diagnostics:**

```bash
# Check models table
psql-17 -h localhost -p 5433 -U testuser -d aio-test \
  -c "SELECT model_id, is_available FROM models WHERE model_type='embedding';"

# Check API endpoint
curl http://localhost:8006/api/v1/models?model_type=embedding
```

**Solution:**

- Seed embedding models: `ops/database/seed/006_seed_embedding_models.sql`
- Verify Model Registry API responding
- Check backend logs for errors

### Problem: Configuration Save 500 Error

**Known Fixes (Oct 27, 2025):**

**Fix 1: RLS Middleware**

```python
# Before (BROKEN)
roles = token_payload.get("roles", [])

# After (FIXED)
role = token_payload.get("role") or token_payload.get("roles")
if isinstance(role, str):
    roles = [role]
```

**Fix 2: SQL Syntax**

```python
# Before (BROKEN)
SET config = :config::jsonb

# After (FIXED)
SET config = CAST(:config AS jsonb)
```

**Verification:**

- Restart container: `docker restart orchestrator-api-test`
- Check logs: `docker logs orchestrator-api-test --tail 50`
- Test save: Should return 200 OK

### Problem: Health Banner Persists

**Causes:**

- Save failed (check console)
- Model still unavailable
- Browser cache stale

**Solution:**

- Hard refresh: Cmd+Shift+R / Ctrl+Shift+F5
- Check backend logs for save errors
- Verify model in registry
- Clear browser localStorage

---

## Best Practices

### 1. Always Use Built-in Model for Default

**Recommended:**

```json
{
  "default_embedding_model": "all-MiniLM-L6-v2"
}
```

**Why:**

- Guaranteed 100% availability
- No API costs
- Air-gapped friendly
- Fast local processing

### 2. Organize Collections by Model

**Good Organization:**

```
Built-in Model (all-MiniLM-L6-v2):
  ├── threat_intelligence
  ├── malware_reports
  ├── incident_postmortems
  └── security_advisories

Remote Model (text-embedding-3-large):
  ├── strategic_analysis
  └── executive_briefings
```

**Benefits:**

- Use Cases can search across related collections
- Clear cost/availability boundaries
- Easier to manage API quotas

### 3. Validate Models Before Deployment

**Pre-Deployment Checklist:**

```bash
# 1. Seed all required models
psql -f ops/database/seed/006_seed_embedding_models.sql

# 2. Verify availability
curl http://localhost:8006/api/v1/models?model_type=embedding | jq '.models[] | {model_id, is_available}'

# 3. Check health
curl http://localhost:8006/health/config | jq '.healthy'

# 4. Update system default
# Via UI: Admin → System Configuration → Corpus Settings
```

### 4. Document Model Requirements

For each collection, document:

- Chosen embedding model and why
- Expected query types
- Cost implications (if remote model)
- Availability requirements

---

## Future Enhancements (Phase 5)

### P5-F8: Embedding Model Migration Tool

**Features:**

- Admin interface for changing collection embedding model
- Multi-step approval workflow with impact analysis
- Background document re-embedding service
- Progress tracking with ETA
- Cost estimation for remote models
- Comprehensive audit trail

**Use Cases:**

- Upgrade to higher-quality model
- Migrate from remote to built-in (cost reduction)
- Consolidate collections to single model
- Recover from deprecated model

---

## Related Documentation

- **ADR-021 Addendum 3:** Per-Collection Embedding Model Selection
- **Session Log:** [2025-10-27-per-collection-embedding-model-architecture.md](../sessions/2025-10-27-per-collection-embedding-model-architecture.md)
- **Database Schema:** [SCHEMA.md](../../architecture/database/SCHEMA.md)
- **API Docs:** [Collection Management](../../api/collection-management.md), [System Configuration](../../api/admin/system-configuration.md)
- **User Guides:** [Collection Management](../../user-guides/collection-management-guide.md), [System Configuration](../../user-guides/system-configuration-guide.md)

---

**Document Owner:** Project team
**Last Updated:** October 27, 2025
**Status:** Production Ready - All Components Implemented and Tested
