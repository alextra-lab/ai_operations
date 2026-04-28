# RAG Collection Configuration Issue - ✅ RESOLVED

**Fix Applied:** December 9, 2025
**File Modified:** `src/corpus_svc/app/services/query_service.py`

## Problem Identified

**Use Case:** Incident Summary v3 (`413acdd5-43bc-4b63-a8f4-f77e0b7f0c16`)

**Root Cause:** The system is using database collection `name` to query Qdrant, but should use `qdrant_collection_name`.

### Collection Mapping

| Database Name | Qdrant Collection Name | Status |
|--------------|------------------------|--------|
| `security_docs` | `fc_security_docs_d40a039f` | Active, 7 documents |
| `default` | `documents_test` | Active, 7 documents |

### Code Issue

**File:** `src/corpus_svc/app/services/query_service.py`

**Line 161-165:** The code iterates over collection names and passes them directly to Qdrant:

```python
for collection_name in collection_names:  # collection_name = "security_docs"
    coll_results = await self.vector_repository.search_similar_in_collection(
        collection_name=collection_name,  # ❌ Should be "fc_security_docs_d40a039f"
        ...
    )
```

**Should be:**

```python
# Resolve collection names to Qdrant collection names
for collection_name in collection_names:
    collection = await self.collection_repository.get_by_name(collection_name)
    if not collection:
        continue
    qdrant_collection_name = collection.qdrant_collection_name
    coll_results = await self.vector_repository.search_similar_in_collection(
        collection_name=qdrant_collection_name,  # ✅ Use Qdrant name
        ...
    )
```

## Verification

✅ **Vectordb queries ARE happening** - confirmed by logs
❌ **Wrong collection names used** - using database names instead of Qdrant names
✅ **Collections exist** - both `security_docs` and `default` have 7 documents each
✅ **Collections are active** - both are marked as active in database

## Solution

The `_resolve_embedding_model_for_collections()` method already looks up collections. We need to:

1. Store the collection objects (not just names) when resolving
2. Use `collection.qdrant_collection_name` when querying Qdrant
3. Update the code to resolve names → Qdrant names before querying

## Current Status

- ✅ Issue identified
- ✅ Root cause documented
- ✅ Code fix applied to `query_service.py`
- ✅ Name resolution implemented (lines 160-186)

## Fix Details

**Changed:** `perform_semantic_search()` method in `query_service.py`

**Before:**

```python
for collection_name in collection_names:
    coll_results = await self.vector_repository.search_similar_in_collection(
        collection_name=collection_name,  # ❌ Using database name
        ...
    )
```

**After:**

```python
for collection_name in collection_names:
    # Resolve database collection name to Qdrant collection name
    collection = await self.collection_repository.get_by_name(collection_name)
    if not collection:
        logger.warning(f"Collection '{collection_name}' not found, skipping")
        continue

    qdrant_collection_name = str(getattr(collection, "qdrant_collection_name", ""))
    if not qdrant_collection_name:
        logger.warning(f"Collection '{collection_name}' has no Qdrant name, skipping")
        continue

    logger.debug(f"Querying Qdrant: {collection_name} -> {qdrant_collection_name}")

    coll_results = await self.vector_repository.search_similar_in_collection(
        collection_name=qdrant_collection_name,  # ✅ Using Qdrant name
        ...
    )
```

**Verification:** Run `./tests/integration/verify_rag_vectordb_simple.sh` to confirm sources are now found.

---

## Additional Issues Resolved (December 9, 2025)

### Issue #2: Embedding Model Resolution
**Root Cause:** Collection's `embedding_model` and `embedding_provider` were not being passed to the embedding service, causing dimension mismatches.

**Fixed Files:**
- `src/corpus_svc/app/services/query_service.py` - Added provider resolution logic
- `src/corpus_svc/app/clients/embedding_client.py` - Added provider parameter support
- `src/embedding/app/routers/embedding.py` - Fixed provider routing
- `src/embedding/app/schemas/embedding.py` - Allow `model` to be `str | ModelType | None`

**Result:** Embeddings now use the correct model specified by the collection.

---

### Issue #3: Context Source Transformation Bug
**Root Cause:** In `src/orchestrator/app/orchestrator/steps/format_response.py`, the code was extracting only the `metadata` dictionary from each `RetrievalSource` object, but `ResponseFormatter._convert_context_sources()` expected full source dictionaries with fields like `document_id`, `title`, `content`, etc.

**Fixed File:** `src/orchestrator/app/orchestrator/steps/format_response.py` (lines 74-87)

**Before:**
```python
context_sources = [
    s.metadata if isinstance(getattr(s, "metadata", {}), dict) else {}
    for s in ctx.sources
]
```

**After:**
```python
context_sources = []
for s in ctx.sources:
    source_dict = {
        "document_id": s.document_id,
        "title": s.title,
        "chunk_id": getattr(s, "chunk_id", None),
        "score": s.score,
        "relevance_score": s.score,
        "url": getattr(s, "url", None),
        "content": s.metadata.get("content", "") if s.metadata else "",
        "snippet": s.metadata.get("content", "") if s.metadata else "",
        "metadata": s.metadata if s.metadata else {},
    }
    context_sources.append(source_dict)
```

**Result:** Sources now properly flow through the entire pipeline and appear in the final response.

---

### Issue #4: Similarity Threshold Support
**Added:** `min_relevancy_score` parameter support in orchestrator's retrieval client.

**Fixed Files:**
- `src/orchestrator/app/orchestrator/clients/retrieval_client.py` - Added parameter
- `src/orchestrator/app/orchestrator/steps/retrieve_context.py` - Pass threshold from use case config

**Result:** Use case `similarity_threshold` config is now properly applied (e.g., 0.6 threshold filters 20 results down to 2).

---

## Final Status: ✅ FULLY RESOLVED

All RAG retrieval issues have been resolved. The system now:
- ✅ Correctly resolves database collection names to Qdrant collection names
- ✅ Uses the correct embedding model and provider for each collection
- ✅ Properly transforms retrieval sources for the final response
- ✅ Applies similarity thresholds from use case configuration
- ✅ Returns sources in the API response with proper metadata
