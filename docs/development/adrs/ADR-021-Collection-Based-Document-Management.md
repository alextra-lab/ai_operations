# ADR-021: Collection-Based Document Management

**Status:** ✅ Accepted
**Date:** October 17, 2025
**Decision Makers:** Architecture Team
**Related:** UI_DEVELOPMENT_PLAN.md (P2-F3), USE_CASE_MANAGEMENT_PLAN.md, ADR-018 Use Case Owned Architecture

---

## Context

The AI Operations Platform system currently stores all documents in a single logical repository without collection organization. This creates several challenges:

### **Problems with Current State**

1. **No Logical Organization**
   - All documents mixed together regardless of purpose or domain
   - No way to separate threat intelligence from playbooks from internal docs
   - Difficult for users to understand what documents are available

2. **Embedding Model Inflexibility**
   - Cannot experiment with different embedding models without re-embedding entire corpus
   - No way to maintain multiple embedding strategies for different use cases
   - Upgrading embedding models requires re-processing all documents

3. **Use Case Configuration Complexity**
   - Use Cases reference `vector_collections: ["documents"]` but this is hardcoded
   - No way to scope RAG queries to relevant document subsets
   - Performance impact from searching all documents for specialized queries

4. **Access Control Limitations**
   - Cannot restrict document uploads to specific domains
   - No way to delegate corpus management for specific topics
   - All-or-nothing permissions model

5. **Vector Database Consistency Risk**
   - Documents with different embedding models stored in same Qdrant collection
   - Query embeddings must match document embeddings for semantic search to work
   - No enforcement of embedding model consistency

### **Key Architectural Constraint: Embedding Model Consistency**

**Critical Discovery:** Embedding models create incompatible vector spaces. Documents embedded with Model A cannot be semantically searched with queries embedded using Model B, even if dimensions match.

**Requirements:**

- Query embedding model MUST match document embedding model
- Cosine similarity only works within the same vector space
- Collections must be homogeneous regarding embedding models

### **Multi-Collection RAG Support Already Exists**

From `src/orchestrator/app/schemas/use_case_config.py`:

```python
class RAGConfig(BaseModel):
    vector_collections: list[str] = Field(
        default_factory=lambda: ["documents"],
        description="List of vector collections to search",
        min_items=1,
    )
```

**Use Cases can already reference multiple collections** - we just need to implement the collection management infrastructure.

---

## Decision

We implement a **Collection-Based Document Management System** where:

1. **Collections are bound to embedding models (1:1, immutable)**
2. **Documents belong to exactly one collection**
3. **Use Cases can query multiple collections with same embedding model**
4. **Corpus management roles have full control over all collections**

### **Core Architecture**

#### **1. Collection → Embedding Model Binding**

**Decision:** Each collection is permanently bound to one embedding model at creation time.

**Properties:**

- Embedding model is set during collection creation
- Embedding model is **immutable** (cannot be changed after creation)
- All documents in a collection use the same embedding model
- Changing embedding model requires creating a new collection and re-embedding

**Rationale:**

- ✅ Enforces vector space consistency (correctness)
- ✅ Prevents accidental model mismatches (safety)
- ✅ Simplifies query logic (no model filtering needed)
- ✅ Makes embedding model explicit and visible

**Collection Schema:**

```python
class Collection(Base):
    id = Column(UUID, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)

    # Embedding model binding (immutable)
    embedding_model = Column(String, nullable=False)       # "text-embedding-3-small"
    embedding_provider = Column(String, nullable=False)    # "openai" or "local"
    embedding_dimensions = Column(Integer, nullable=False) # 384

    # Qdrant mapping
    qdrant_collection_name = Column(String, unique=True, nullable=False)

    # Flags
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_system_managed = Column(Boolean, default=False)

    # Metadata
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    document_count = Column(Integer, default=0)
```

#### **2. Multi-Collection RAG Queries**

**Decision:** Use Cases can reference multiple collections, but all must use the same embedding model.

**Validation Rules:**

1. All referenced collections must exist and be active
2. All referenced collections must use the same embedding model
3. Use Case's `models.embedding` must match collection(s) embedding model
4. Use Case creator must have permission to access all referenced collections

**Example Use Case Config:**

```json
{
  "rag": {
    "enabled": true,
    "vector_collections": ["threat_intel", "mitre_attack", "cisa_advisories"],
    "top_k": 10,
    "similarity_threshold": 0.7
  },
  "models": {
    "embedding": "text-embedding-3-small"  // Must match all 3 collections
  }
}
```

**Query Flow:**

1. Use Case specifies collections to search
2. Orchestrator validates all collections use same embedding model
3. Query embedded using collection's embedding model
4. Qdrant searches across all specified collections
5. Results merged and ranked by similarity score

#### **3. Role-Based Permissions (Simplified)**

**Decision:** Corpus management roles have full control; others have read-only access.

| Role | Create Collection | Upload Documents | Delete Documents | Manage Collections | Use in UC |
|------|------------------|------------------|-----------------|-------------------|-----------|
| **`admin`** | ✅ | ✅ | ✅ | ✅ ALL | ✅ |
| **`corpus_admin`** | ✅ | ✅ | ✅ | ✅ ALL | ✅ |
| **`use_case_publisher`** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **`analyst`** | ❌ | ❌ | ❌ | ❌ | ✅ Published UCs |
| **`user`** | ❌ | ❌ | ❌ | ❌ | ❌ |

**Rationale:**

- ✅ Simple and clear permission model
- ✅ Aligns with existing RBAC patterns
- ✅ No per-collection ownership complexity
- ✅ `corpus_admin` empowered to manage entire corpus
- ✅ Analysts can use collections via published Use Cases

#### **4. Default Collection Strategy**

**Decision:** System-managed "default" collection auto-created on first startup.

**Properties:**

- **Name:** `"default"`
- **Embedding Model:** From environment variable or system config
- **Flags:** `is_default=True`, `is_system_managed=True`
- **Protection:** Cannot be deleted, can be disabled
- **Fallback:** Used when no collection selected during upload

**System Behavior:**

- Migration 016 creates default collection
- Default collection uses `DEFAULT_EMBEDDING_MODEL` from env
- If env not set, uses first available embedding model
- Only one collection can have `is_default=True`

**Migration SQL:**

```sql
-- Create default collection with system default embedding model
INSERT INTO collections (
    id, name, description,
    embedding_model, embedding_provider, embedding_dimensions,
    qdrant_collection_name,
    is_default, is_system_managed, is_active,
    created_by, created_at
) VALUES (
    gen_random_uuid(),
    'default',
    'System default collection for general-purpose documents',
    '${DEFAULT_EMBEDDING_MODEL}',  -- From environment
    '${DEFAULT_EMBEDDING_PROVIDER}',
    ${DEFAULT_EMBEDDING_DIMENSIONS},
    'fc_default_${MODEL_HASH}',
    true,  -- is_default
    true,  -- is_system_managed
    true,  -- is_active
    'system',
    NOW()
);
```

#### **5. Document-Collection Relationship**

**Decision:** Documents belong to exactly one collection (1:many).

**Document Schema Changes:**

```python
class Document(Base):
    # ... existing fields ...

    # NEW: Collection reference (required)
    collection_id = Column(UUID, ForeignKey("collections.id"), nullable=False)

    # EXISTING: Embedding metadata (must match collection)
    embedding_model = Column(String)
    embedding_provider = Column(String)
    embedding_dimensions = Column(Integer)
```

**Foreign Key Constraint:**

- `ON DELETE RESTRICT` - Cannot delete collection with documents
- Must move/delete documents first before deleting collection

**Upload Workflow:**

1. User selects collection (required field)
2. System validates user permissions (`admin` or `corpus_admin`)
3. System validates collection exists and is active
4. Document embedded using collection's embedding model
5. Document saved with `collection_id` reference
6. Collection's `document_count` incremented

#### **6. Moving Documents Between Collections**

**Decision:** Documents can be moved, but different embedding models require re-embedding.

**API Endpoint:**

```python
PUT /api/v1/documents/{document_id}/collection
{
    "target_collection_id": "uuid",
    "force_reembed": false  # Required if models differ
}
```

**Logic:**

1. Validate user has permission (`admin` or `corpus_admin`)
2. Check source and target collection embedding models
3. If models match:
   - Update `document.collection_id`
   - Update Qdrant point metadata
   - Update document counts
4. If models differ and `force_reembed=False`:
   - Return error: "Embedding models differ, set force_reembed=true"
5. If models differ and `force_reembed=True`:
   - Queue document for re-embedding with new model
   - Update `document.collection_id` after re-embedding completes
   - Update Qdrant collection references

#### **7. Qdrant Collection Naming Convention**

**Decision:** Namespaced collection names with embedding model hash.

**Format:** `fc_<collection_name>_<model_hash>`

**Example:**

- Collection: `"threat_intel"`
- Embedding Model: `"text-embedding-3-small"`
- Qdrant Name: `"fc_threat_intel_abc123def"`

**Benefits:**

- ✅ Namespace prevents conflicts with other apps
- ✅ Model hash prevents accidental model mismatches
- ✅ Collection name visible in Qdrant UI
- ✅ Safe to have multiple collections with different models

**Model Hash Calculation:**

```python
import hashlib

def generate_model_hash(embedding_model: str, dimensions: int) -> str:
    """Generate a short hash for embedding model + dimensions."""
    combined = f"{embedding_model}:{dimensions}"
    return hashlib.sha256(combined.encode()).hexdigest()[:8]
```

---

## Consequences

### **Positive**

✅ **Vector Space Consistency**

- Embedding model mismatches impossible by design
- Semantic search correctness guaranteed
- Query results always meaningful

✅ **Corpus Organization**

- Logical separation of document domains
- Clear purpose for each collection
- Easier to understand and manage corpus

✅ **Use Case Flexibility**

- Can scope queries to relevant collections
- Multi-collection queries supported
- Performance improvement from targeted searches

✅ **Embedding Model Evolution**

- Can test new embedding models in parallel
- Gradual migration strategy possible
- No need to re-embed entire corpus

✅ **Access Control Foundation**

- Clear permissions model
- Audit trail for document management
- Ready for future per-collection access control

✅ **Simple Permission Model**

- No per-collection ownership complexity
- Clear corpus management roles
- Easy to understand and implement

### **Negative**

⚠️ **Migration Complexity**

- Existing documents must be assigned to collections
- Default collection migration required
- Qdrant collection names must be updated

⚠️ **Immutable Embedding Models**

- Cannot change collection's embedding model
- Must create new collection and re-embed to change
- Additional storage during migration period

⚠️ **Foreign Key Constraints**

- Cannot delete collection with documents
- Must clean up documents first
- Additional validation logic required

⚠️ **Moving Documents Requires Re-embedding**

- If target collection uses different model
- Background job processing required
- Temporary unavailability during re-embedding

### **Neutral**

- Adds new `collections` table to database schema
- Requires UI updates for collection management
- Use Case configuration becomes slightly more complex
- Admin/corpus_admin roles required for document upload

---

## Implementation Plan

### **Phase 1: Database & Backend (Week 1)**

#### **Database Migration 016**

```sql
-- Create collections table
CREATE TABLE collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    embedding_model VARCHAR(255) NOT NULL,
    embedding_provider VARCHAR(100) NOT NULL,
    embedding_dimensions INTEGER NOT NULL,
    qdrant_collection_name VARCHAR(255) UNIQUE NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_system_managed BOOLEAN DEFAULT FALSE,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    document_count INTEGER DEFAULT 0,
    CONSTRAINT unique_default CHECK (
        NOT is_default OR (
            SELECT COUNT(*) FROM collections WHERE is_default = TRUE
        ) <= 1
    )
);

-- Add collection_id to documents table
ALTER TABLE documents
ADD COLUMN collection_id UUID REFERENCES collections(id) ON DELETE RESTRICT;

-- Create default collection
INSERT INTO collections (
    name, description,
    embedding_model, embedding_provider, embedding_dimensions,
    qdrant_collection_name,
    is_default, is_system_managed, is_active,
    created_by
) VALUES (
    'default',
    'System default collection for general-purpose documents',
    COALESCE(NULLIF(current_setting('app.default_embedding_model', true), ''), 'text-embedding-3-small'),
    COALESCE(NULLIF(current_setting('app.default_embedding_provider', true), ''), 'openai'),
    COALESCE(NULLIF(current_setting('app.default_embedding_dimensions', true), '')::INTEGER, 384),
    'fc_default_' || LEFT(MD5('text-embedding-3-small:384'), 8),
    true, true, true,
    'system'
);

-- Migrate existing documents to default collection
UPDATE documents
SET collection_id = (SELECT id FROM collections WHERE is_default = TRUE)
WHERE collection_id IS NULL;

-- Make collection_id NOT NULL after migration
ALTER TABLE documents ALTER COLUMN collection_id SET NOT NULL;

-- Create indexes
CREATE INDEX idx_collections_active ON collections(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_collections_embedding_model ON collections(embedding_model);
CREATE INDEX idx_documents_collection_id ON documents(collection_id);
```

#### **Backend APIs**

**Collection Management (`/api/v1/admin/collections`)**

```python
# src/orchestrator/app/routers/collections.py

@router.get("/", response_model=CollectionListResponse)
async def list_collections(
    active_only: bool = True,
    embedding_model: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: TokenPayload = Depends(corpus_admin_required)
):
    """List all collections with filters."""
    pass

@router.post("/", response_model=CollectionResponse)
async def create_collection(
    collection: CollectionCreate,
    current_user: TokenPayload = Depends(corpus_admin_required)
):
    """Create a new collection."""
    pass

@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(
    collection_id: UUID,
    current_user: TokenPayload = Depends(corpus_admin_required)
):
    """Get collection details."""
    pass

@router.put("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: UUID,
    collection: CollectionUpdate,
    current_user: TokenPayload = Depends(corpus_admin_required)
):
    """Update collection (description, is_active only)."""
    pass

@router.delete("/{collection_id}")
async def delete_collection(
    collection_id: UUID,
    current_user: TokenPayload = Depends(corpus_admin_required)
):
    """Delete collection (must have no documents)."""
    pass
```

**Public Collection APIs (`/api/v1/collections`)**

```python
@router.get("/available", response_model=CollectionListResponse)
async def list_available_collections(
    current_user: TokenPayload = Depends(auth_required)
):
    """List active collections for use in Use Case configuration."""
    pass
```

**Document Upload Enhancement**

```python
@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile,
    collection_id: UUID,  # NEW: Required parameter
    title: Optional[str] = None,
    current_user: TokenPayload = Depends(corpus_admin_required)
):
    """Upload document to specific collection."""
    # 1. Validate collection exists and is active
    # 2. Get collection's embedding model
    # 3. Process and embed document with collection's model
    # 4. Store with collection_id reference
    pass
```

### **Phase 2: Frontend UI (Week 2)**

#### **Collection Management Page**

- `src/frontend-angular/src/app/pages/collections/collection-list.component.ts`
- `src/frontend-angular/src/app/pages/collections/collection-editor.component.ts`
- `src/frontend-angular/src/app/pages/collections/collection-create.component.ts`

#### **Document Upload Enhancement**

- Add collection selector dropdown to upload form
- Show collection's embedding model in UI
- Validate collection selection before upload

#### **Use Case Configuration Enhancement**

- Multi-select for `vector_collections`
- Validate all selected collections use same embedding model
- Show embedding model compatibility warnings

### **Phase 3: Migration & Testing (Week 3)**

#### **Data Migration**

- Run migration 016 in staging environment
- Verify all existing documents migrated to default collection
- Test Qdrant collection creation

#### **Integration Testing**

- Test multi-collection RAG queries
- Test embedding model validation
- Test document upload with collection selection
- Test collection deletion protection

#### **Documentation**

- Update user guides
- Update API documentation
- Create collection management tutorial

---

## Alternatives Considered

### **Alternative 1: Document-Level Embedding Model (Rejected)**

**Approach:** Store embedding model per document, no collection enforcement.

**Rejected Because:**

- ❌ Complex query logic (must filter by model before searching)
- ❌ Qdrant doesn't efficiently filter by embedding model
- ❌ Risk of accidental model mismatches
- ❌ Would require multiple Qdrant collections anyway

### **Alternative 2: System-Wide Single Embedding Model (Rejected)**

**Approach:** Entire system uses one embedding model.

**Rejected Because:**

- ❌ No flexibility for different use cases
- ❌ Cannot leverage model improvements without full re-embedding
- ❌ Not future-proof for enterprise needs

### **Alternative 3: Per-Collection Ownership (Rejected)**

**Approach:** Each collection has owner who controls access.

**Rejected Because:**

- ❌ Adds unnecessary complexity for MVP
- ❌ corpus_admin role purpose is corpus-wide management
- ❌ Can be added in Phase 2 if needed

### **Alternative 4: Mutable Embedding Models (Rejected)**

**Approach:** Allow changing collection's embedding model.

**Rejected Because:**

- ❌ Requires re-embedding all documents in collection
- ❌ Temporary inconsistency during migration
- ❌ Better to create new collection and migrate documents

---

## Future Enhancements (Phase 2+)

### **1. Collection-Level Access Control**

```python
class Collection(Base):
    # Add fields:
    allowed_roles = Column(ARRAY(String), default=["admin", "corpus_admin"])
    allowed_users = Column(ARRAY(UUID), default=[])
    visibility = Column(String, default="private")  # private, organization, public
```

### **2. Collection Templates**

- Pre-configured collections for common use cases
- "Threat Intelligence" template with recommended settings
- "SOC Playbooks" template with specific metadata filters

### **3. Collection Analytics Dashboard**

- Documents per collection
- Usage statistics (which UCs use which collections)
- Embedding cost tracking per collection
- Collection health metrics

### **4. Bulk Document Operations**

- Move multiple documents at once
- Bulk re-embedding jobs
- Progress tracking UI

### **5. Collection Versioning**

- Snapshot collections at specific points in time
- Reproducible query results
- Compliance audit trail

### **6. Collection Lifecycle States**

```python
class CollectionStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"
```

---

## Related Work

- **UI_DEVELOPMENT_PLAN.md**: P2-F3 Document Management System enhancement
- **USE_CASE_MANAGEMENT_PLAN.md**: Collection references in RAG config
- **ADR-018**: Use Case Owned Architecture (UC config pattern)
- **ADR-020**: Use Case Publisher Role (RBAC patterns)

---

## References

- Backend: `src/orchestrator/app/schemas/use_case_config.py` (RAGConfig)
- Backend: `src/corpus_svc/app/db/models.py` (Document model)
- Backend: `src/embedding/app/config/models.yaml` (Embedding models)
- Frontend: `src/frontend-angular/src/app/pages/documents/` (Document management)

---

## Implementation Notes (October 2025)

### **Single Embedding Model Strategy (Phase 3-5)**

**Decision Date:** October 19, 2025
**Status:** ⚠️ **SUPERSEDED** by Addendum 3 (October 27, 2025)

**Decision:** System-wide single embedding model for Phase 1-5, with multi-model support deferred to Phase 5+ (admin-managed migration).

**Rationale:**

- ✅ Simpler implementation and maintenance
- ✅ Guaranteed vector space consistency across all collections
- ✅ Direct score comparability in all RAG searches
- ✅ Easier testing and validation
- ✅ Sufficient for MVP and initial production use

**Configuration:**

```bash
# System-wide embedding model (environment variables)
DEFAULT_EMBEDDING_MODEL=text-embedding-3-small
DEFAULT_EMBEDDING_PROVIDER=openai
DEFAULT_EMBEDDING_DIMENSIONS=1536
```

**Implementation:**

- All collections created with system default embedding model
- Collection create UI shows system model as read-only information
- Use Case configuration does NOT include `models.embedding` field
- Embedding model determined by system configuration, not per-collection or per-use-case

**Benefits:**

1. **Consistency:** All documents in all collections use same embedding model
2. **Multi-Collection Search:** Can search across multiple collections without score normalization
3. **Simplicity:** No complex cross-model score merging required
4. **Performance:** Single embedding call per query

**Changing the Embedding Model:**

- Requires admin intervention (Phase 5 feature: P5-F8)
- Triggers re-embedding of ALL documents in system
- Managed migration process with progress tracking
- Production-safe with off-hours scheduling

**Future Multi-Model Support (Phase 5+):**

- Admin can change system embedding model
- Migration service re-embeds all documents
- Optional: Per-collection model selection with compatibility validation
- Score normalization for cross-model searches (if implemented)

**Related Tasks:**

- **P3-TASK-01:** Remove `models.embedding` from Use Case Config
- **P3-TASK-02:** Simplify Collection Create Dialog (show system model)
- **P3-TASK-03:** Add Collection Selector to Document Upload
- **P5-F8:** Embedding Model Configuration & Migration (admin feature)

---

## Addendum 2: Exemplars as Specialized Documents (October 22, 2025)

**Context:** P4-F10 originally planned separate `fewshot_exemplars` table, but this creates unnecessary complexity and duplication.

**Decision:** **Exemplars are documents with `document_type="exemplar"`**

**Architecture:**

```
PostgreSQL documents table:
- document_type: "exemplar" | "pdf" | "txt" | ...
- metadata: {
    "exemplar_type": "sigma-rule" | "yara-rule" | "playbook-snippet",
    "quality_score": 0.0-1.0,
    "approval_status": "draft" | "approved",
    "domain": "soc" | "threat-intel" | "incident-response"
  }

Qdrant (same as all documents):
- Vectors stored with document_id as point_id
- Payload includes document_type for filtering
```

**Benefits:**

- ✅ Reuse all existing document/collection infrastructure
- ✅ No new tables or services needed
- ✅ Exemplars benefit from collection organization
- ✅ Access control via existing collection permissions
- ✅ Can mix exemplars with documents in same collection or separate

**Use Case Integration:**

```python
# Use case can reference exemplar collections
{
  "rag": {
    "vector_collections": ["soc-playbooks"],  # Regular documents
    "exemplar_collections": ["sigma-rules", "yara-rules"]  # Exemplars only
  }
}
```

**Upload Workflow:**

1. Document upload UI adds "Upload as Exemplar" toggle
2. When enabled, shows exemplar-specific fields (exemplar_type, quality_score)
3. Sets `document_type="exemplar"` on creation
4. Stores in chosen collection (can be exemplar-dedicated or mixed)

**Selection Workflow:**

1. Use case specifies exemplar_collections
2. Retrieval service queries those collections with filter: `document_type="exemplar"`
3. Can use semantic search (similar), quality ranking (pinned), or MMR (diverse)
4. Returns top-K exemplars for inclusion in prompt

**Implementation:**

- ✅ No new database tables needed
- ✅ Extend document upload UI with exemplar mode
- ✅ Add exemplar collection selector to use case wizard
- ✅ Filter by document_type in retrieval queries

---

## Addendum 3: Per-Collection Embedding Model Selection (October 27, 2025)

**Context:** The "Single Embedding Model Strategy" (Addendum 1) simplified initial implementation but prevented experimentation with different embedding models and limited collection flexibility.

**Problem:** Cross-model similarity score fusion is architecturally complex:

- Different embedding models create incompatible vector spaces
- Similarity scores have different distributions and norms across models
- Merging/ranking results from different embedding spaces requires score calibration or cross-encoder re-ranking
- This complexity is significant and not needed for current use cases

**Decision:** Enable per-collection embedding model selection NOW, with Use Case-level enforcement of single-model multi-collection searches.

### **Architecture**

#### **1. Built-in Embedding Model**

- **all-MiniLM-L6-v2** is bundled as a local, always-available embedding model
- Must be seeded in Model Registry: `model_type='embedding'`, `provider='local'`, `embedding_dimensions=384`, `is_available=true`
- Appears in all embedding model dropdowns alongside available remote models

#### **2. Collection Creation**

- User selects embedding model from dropdown:
  - Built-in `all-MiniLM-L6-v2` (always enabled)
  - Remote embedding models where `model_type='embedding'` AND `is_available=true`
- Collection stores: `embedding_model`, `embedding_provider`, `embedding_dimensions` (immutable)
- System Config's `default_embedding_model` becomes the pre-selected default in create dialog (not enforced globally)

#### **3. Document Ingestion**

- Backend MUST use the collection's stored `embedding_model` for document embeddings
- No global override; collection's model is authoritative

#### **4. Multi-Collection Search Enforcement**

**Use Case Configuration (Frontend):**

- When selecting `rag_vector_collections` in Use Case Wizard:
  - After first collection is selected, filter remaining options to collections with same `embedding_model`
  - Display inline validation error if user attempts to mix models: "All selected collections must share the same embedding model"
  - Save validation rejects mixed-model configurations

**Query Execution (Backend):**

- When query requests multiple collections:
  - Validate ALL collections share the same `embedding_model`
  - If not, return `HTTP 400` with clear message: "Collections use different embedding models: {model_list}. Select collections with the same embedding model."
  - If valid, use the shared `embedding_model` for query embedding and search

#### **5. System Configuration Role**

- `Default_embedding_model` in System Configuration:
  - Used as the pre-selected default for Collection Create dialog
  - Health check warns if default is unavailable (prevents confusion)
  - NOT enforced globally; each collection manages its own model

### **Implementation**

**Backend:**

```python
# Validation in multi-collection query handler
def _assert_same_embedding_model(collections: list[Collection]) -> str:
    model_ids = {c.embedding_model for c in collections}
    if len(model_ids) != 1:
        raise HTTPException(
            status_code=400,
            detail=f"Collections use different embedding models: {', '.join(sorted(model_ids))}. "
                   "Select collections with the same embedding model."
        )
    return next(iter(model_ids))

# Use collection's model for search
def search_multi_collection(req: MultiCollectionSearchRequest):
    collections = get_collections(req.collection_names)
    shared_model = _assert_same_embedding_model(collections)
    embedder = get_embedder_for_model(shared_model)
    return vector_store.search(collections, req.query, embedder, top_k=req.top_k)
```

**Frontend:**

- `CollectionCreateDialog`: Replace static display with `mat-select` dropdown loading from `ModelRegistryService.getEmbeddingModels()` + built-in MiniLM
- `UseCaseWizard`: Add same-model collection filtering and validation

**Database:**

- Seed script ensures `all-MiniLM-L6-v2` exists in `models` table with `is_available=true`

### **Deferred: Multi-Model Search**

**Status:** ❌ Explicitly deferred - complexity not justified for current requirements

**Future Considerations (if needed):**

- Per-collection score calibration/normalization
- Cross-encoder re-ranking after initial retrieval
- Model distillation to common embedding space
- Hybrid search with BM25 as model-agnostic baseline

### **Benefits**

✅ Collections can use different embedding models for different domains
✅ Built-in local model always available (no API costs/dependency)
✅ Use Cases enforce single-model constraint (simple, correct)
✅ Backend always uses collection's model (no confusion)
✅ Clear validation messages guide users
✅ Defers complex cross-model fusion until actually needed

### **Related Changes**

- ADR-021 Addendum 1 "Single Embedding Model Strategy" marked as SUPERSEDED
- System Configuration `default_embedding_model` role clarified
- Collection Create UI updated to show embedding model dropdown
- Use Case Wizard updated to enforce same-model collection selection
- Backend query validation added for multi-collection searches

---

**Status:** ✅ Accepted - October 17, 2025
**Updated:** October 19, 2025 (Single-Model Strategy Addendum)
**Updated:** October 22, 2025 (Exemplars-as-Documents Pattern)
**Updated:** October 27, 2025 (Per-Collection Embedding Model Selection)
**Next Steps:** Implement per-collection model selection, Update Use Case Wizard validation
