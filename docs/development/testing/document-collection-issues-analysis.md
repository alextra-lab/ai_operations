# Document Collection Issues - Root Cause Analysis

**Date:** 2025-11-01
**Status:** ✅ Issues Identified - Backend Fixes Required
**Tested:** API endpoints directly + database verification

---

## Executive Summary

**User Report:** "Documents always show default collection even when different collection selected"

**Root Cause:** Backend schema mapping issues - collection data not returned in API responses

**Status:**
- ✅ Upload API works correctly (verified)
- ❌ Response schema missing collection fields
- ❌ Embedding model not inherited from collection

---

## Test Results

### ✅ **Test 1: Collection Selection During Upload**

**Objective:** Verify documents go to the specified collection

**Method:** Direct API testing with curl

**Results:**

| Test Case | Collection Specified | Collection in DB | Status |
|-----------|---------------------|------------------|--------|
| Upload to "security_docs" | `security_docs` | `security_docs` | ✅ PASS |
| Upload to "default" | `default` | `default` | ✅ PASS |

**SQL Verification:**
```sql
SELECT d.title, c.name as collection FROM documents d
JOIN collections c ON d.collection_id = c.id;

Result:
  Default Test            | default
  Default Collection Test | security_docs
  nist.cswp.29.pdf        | security_docs
  NIST Digital Guidelines | default
```

**✅ Conclusion:** Collection selection works perfectly at API level.

---

### ❌ **Issue 1: Collection ID Not Returned in API Response**

**Problem:** API response doesn't include collection information

**API Response:**
```json
GET /api/v1/documents/{id}
{
  "id": "d74db7be-672e-4834-a6f3-de94d045b347",
  "title": "Default Test",
  "collection_id": null,  ❌ Should be UUID of collection!
  "metadata": {}
}
```

**Database Reality:**
```sql
SELECT d.id, c.name, c.id as collection_id
FROM documents d JOIN collections c ON d.collection_id = c.id
WHERE d.id = 'd74db7be-672e-4834-a6f3-de94d045b347';

Result:
  id      | default | 9a6f58ea-88ff-4a98-906c-3165ed5ec70c
```

**Impact:**
- Frontend can't display which collection a document belongs to
- Users can't see collection assignments in Document Library
- No way to verify upload worked correctly

**Root Cause:** `DocumentResponse` schema in backend doesn't include `collection_id` field or the backend ORM mapping isn't loading it.

**Fix Location:** `src/corpus_svc/app/schemas/document.py`

---

### ❌ **Issue 2: Wrong Embedding Model Applied**

**Problem:** Documents don't use their collection's embedding model

**Evidence:**
```sql
SELECT
  d.title,
  c.name as collection,
  c.embedding_model as collection_model,
  d.embedding_model as document_model,
  c.embedding_dimensions as collection_dims,
  d.embedding_dimensions as document_dims
FROM documents d
JOIN collections c ON d.collection_id = c.id;

Result:
  Default Collection Test | security_docs | text-embedding-bge-m3 | all-minilm-l6-v2 | 1024 | 384  ❌
  nist.cswp.29.pdf        | security_docs | text-embedding-bge-m3 | all-minilm-l6-v2 | 1024 | 384  ❌
```

**Expected:** Documents in `security_docs` should use `text-embedding-bge-m3` (1024 dimensions)
**Actual:** Using `all-minilm-l6-v2` (384 dimensions) - wrong model!

**Impact:**
- Vector embeddings incompatible with collection's vector space
- Search quality degraded (wrong embedding dimensions)
- Semantic search won't work properly across collections

**Root Cause:** Upload endpoint doesn't retrieve collection's embedding model before creating embeddings

**Fix Location:** `src/corpus_svc/app/routers/documents.py` around line 310-370

**Required Fix:**
```python
# After getting collection (line 310):
collection = await collection_repo.get_by_name(collection_name)

# Use collection's embedding model (ADD THIS):
embedding_model = collection.embedding_model
embedding_provider = collection.embedding_provider
embedding_dimensions = collection.embedding_dimensions

# Pass to document creation and ingestion
```

---

## Frontend Changes Made

### ✅ **Document Upload Component**

**Changes:**
1. Added `collection_name` to FormData (was missing!)
2. Added chunking_config to FormData
3. Added debug logging for troubleshooting
4. Added compact chunking status indicator
5. Made upload button always visible

**File:** `src/frontend-angular/src/app/api/services/document.service.ts`

**Before:**
```typescript
formData.append('file', file);
// collection_name was NEVER appended!
```

**After:**
```typescript
formData.append('file', file);
if (uploadRequest.collection_name) {
    formData.append('collection_name', uploadRequest.collection_name);
}
```

### ✅ **Document Library Component**

**Changes:**
1. Added collection filter dropdown
2. Added `loadCollections()` method
3. Added `getCollectionName()` method
4. Added collection display in document cards
5. Added CollectionService injection

**Files:** `src/frontend-angular/src/app/pages/documents/document-library.component.ts`

**New Features:**
- Collection filter in search controls
- Collection name displayed in document metadata grid
- Collection indicator: 📁 collection_name

---

## Backend Changes Made

### ✅ **Chunking Proxy Router Created**

**New File:** `src/orchestrator/app/routers/chunking.py`

**Endpoints:**
- `POST /api/v1/chunking/preflight/analyze` - File upload for preflight
- `POST /api/v1/chunking/preflight` - JSON payload preflight
- `POST /api/v1/chunking/compare` - Strategy comparison
- `POST /api/v1/chunking/apply` - Apply chunking config
- `GET /api/v1/chunking/strategies` - List strategies
- `GET /api/v1/chunking/strategies/{strategy}/config` - Get defaults
- `POST/GET/DELETE /api/v1/chunking/presets` - Preset management

**Features:**
- PDF text extraction (using pdfplumber)
- TXT/MD support
- Proxies to retrieval service
- Auth forwarding

**Registered:** Added to `src/orchestrator/app/main.py`

---

## Backend Fixes Required

### **Priority 1: Add collection_id to DocumentResponse Schema**

**File:** `src/corpus_svc/app/schemas/document.py`

**Current Schema (Missing collection_id):**
```python
class Document(DocumentBase):
    id: str
    original_file_name: str
    # ... other fields
    # collection_id: MISSING!
```

**Required Fix:**
```python
class Document(DocumentBase):
    id: str
    collection_id: UUID | None = Field(None, description="Collection this document belongs to")
    original_file_name: str
    # ... other fields
```

Also need to ensure ORM mapping loads this field from the database.

---

### **Priority 2: Use Collection's Embedding Model**

**File:** `src/corpus_svc/app/routers/documents.py` (lines 310-380)

**Current Code:**
```python
collection = await collection_repo.get_by_name(collection_name)
# ... then creates document ...
# But doesn't use collection.embedding_model!
```

**Required Fix:**
```python
collection = await collection_repo.get_by_name(collection_name)
collection_id = collection.id

# GET EMBEDDING CONFIG FROM COLLECTION (ADD THIS):
embedding_model_to_use = embedding_model or collection.embedding_model
embedding_provider_to_use = embedding_provider or collection.embedding_provider
embedding_dims = collection.embedding_dimensions

# Then pass to document creation:
document = await document_repo.create_document(
    DocumentCreate(
        title=title or file_name_str,
        # ... other fields ...
        embedding_model=embedding_model_to_use,
        embedding_provider=embedding_provider_to_use,
        embedding_dimensions=embedding_dims,
    )
)
```

---

### **Priority 3: Store Collection Name in Metadata**

**File:** `src/corpus_svc/app/routers/documents.py`

**Add to metadata when creating document:**
```python
parsed_metadata = {
    **(parsed_metadata or {}),
    'collection_name': collection.name,  # ADD THIS
    'collection_id': str(collection.id)   # ADD THIS
}
```

This ensures collection info is accessible even if the foreign key isn't populated correctly.

---

## Recommended Action Plan

### **Phase 1: Backend Schema Fixes** (30 minutes)

1. **Add `collection_id` to Document schema**
   - File: `src/corpus_svc/app/schemas/document.py`
   - Add field to `Document` class
   - Ensure ORM loads it from DB

2. **Store collection info in metadata**
   - File: `src/corpus_svc/app/routers/documents.py`
   - Add to metadata dict before document creation

3. **Use collection's embedding model**
   - File: `src/corpus_svc/app/routers/documents.py`
   - Retrieve from collection object
   - Pass to embedding service

### **Phase 2: Rebuild & Test** (10 minutes)

```bash
# Rebuild backend container
docker-compose -f deploy/docker-compose.test.yml build --no-cache backend

# Restart services
docker-compose -f deploy/docker-compose.test.yml up -d

# Re-test API
curl -X POST "http://localhost:8006/api/v1/documents/" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test_doc_chunking.txt" \
  -F "collection_name=security_docs" \
  -F "title=Final Test" \
  -F "classification=internal" \
  -F "process_async=false"

# Verify response includes collection_id
# Verify embedding_model matches collection
```

### **Phase 3: Rebuild Frontend** (5 minutes)

```bash
cd src/frontend-angular
npm run build
```

### **Phase 4: UI Testing** (5 minutes)

1. Clear browser cache
2. Hard reload (Cmd+Shift+R)
3. Upload document to "security_docs"
4. Verify:
   - Document shows in security_docs collection
   - Embedding model shows "text-embedding-bge-m3"
   - Collection filter works
   - Collection name displays in card

---

## Current Test Data

**Collections in Database:**
```
  name          | is_default | document_count | embedding_model
 ---------------+------------+----------------+---------------------
  default       | true       | 2              | all-MiniLM-L6-v2
  security_docs | false      | 2              | text-embedding-bge-m3
```

**Test Documents Created:**
```
  ID                                    | Title                   | Collection
 ---------------------------------------+-------------------------+--------------
  d74db7be-672e-4834-a6f3-de94d045b347 | Default Test            | default
  3ccdbb47-a3dc-4db2-978e-ce6fb2ca2b5a | Default Collection Test | security_docs
```

**Test Files:**
- `/tmp/test_doc_chunking.txt` - Security Incident Response Guide (headings)
- `/tmp/test_doc_default.txt` - Lorem ipsum

---

## Summary

| Component | Status | Action Required |
|-----------|--------|-----------------|
| **Frontend Upload** | ✅ Fixed | None - collection_name now sent |
| **Frontend Library** | ✅ Enhanced | None - collection filter added |
| **Backend Upload API** | ⚠️ Partial | Add collection_id to response schema |
| **Backend Upload Logic** | ❌ Bug | Use collection's embedding model |
| **Backend Response Schema** | ❌ Missing | Add collection_id field |
| **Chunking Proxy** | ✅ Created | Rebuild container to activate |

---

## Next Steps

1. **User:** Decide if you want me to fix the backend schema issues now
2. **Or:** Test UI with current fixes and see if frontend logging shows correct collection being sent
3. **Then:** Fix backend to return collection data properly

**Recommendation:** Fix backend schema first, then rebuild everything with `--no-cache`, then test UI.

---

**Created By:** AI Assistant
**Test Date:** 2025-11-01
**Documentation:** `docs/development/testing/api-collection-upload-test-results.md`
