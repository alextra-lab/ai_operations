# P4-MULTI-COLLECTION: Multi-Collection RAG Search

**Priority:** High
**Estimated Time:** 2-3 days
**Status:** ✅ **COMPLETE** (October 27, 2025)
**Phase:** Phase 4 - Security & Enterprise Features
**Date Created:** October 19, 2025
**Date Activated:** October 25, 2025
**Date Completed:** October 27, 2025
**Prerequisites:** Phase 3 completion ✅, per-collection embedding model architecture ✅, P4-F10 Corpus Management ✅

---

## ✅ COMPLETION SUMMARY

**Completion Date:** October 27, 2025
**Integrated With:** Per-Collection Embedding Model Architecture (ADR-021 Addendum 3)
**Implementation:** Complete with same-model enforcement

**Delivered:**
- ✅ Multi-collection semantic search capability
- ✅ Same-model constraint enforcement (frontend + backend)
- ✅ Collection metadata loading and validation
- ✅ Error handling for mixed-model selections
- ✅ Use Case Wizard automatic filtering
- ✅ Backend 400 error with detailed collection info

**Architecture Decision:**
- Original plan assumed system-wide single model
- Implemented with per-collection model flexibility
- Added same-model enforcement for multi-collection searches
- Multi-model fusion explicitly deferred (score normalization complex)

**Session Log:** [2025-10-27-per-collection-embedding-model-architecture.md](../sessions/2025-10-27-per-collection-embedding-model-architecture.md)
**ADR:** [ADR-021 Addendum 3](../../adrs/ADR-021-Collection-Based-Document-Management.md)

---

## Objective

Implement multi-collection search capability for RAG queries, allowing Use Cases to retrieve relevant documents from multiple collections in a single query.

---

## Background

**Current State (Phase 3):**

- Use Cases can reference multiple collections in RAG config
- Backend doesn't implement multi-collection search yet
- Single collection search works correctly

**Desired State (Phase 4):**

- Use Cases can search across multiple collections simultaneously
- Results merged and ranked by relevance score
- Efficient single-query embedding + multi-collection retrieval

**Constraint:**

- Phase 3-5: All collections use same embedding model (single system-wide model)
- Therefore: No cross-model score normalization needed
- Direct score comparison valid across all collections

---

## Architecture

### **Search Flow**

```
User Query
    ↓
Use Case: RAG Config
  - vector_collections: ["threat_intel", "mitre_attack", "cisa_advisories"]
  - top_k: 10
    ↓
Orchestrator → Retrieval Service
    ↓
Retrieval Service:
  1. Validate collections exist and active
  2. Verify all use same embedding model (system default)
  3. Embed query once with system embedding model
  4. Search each collection in Qdrant
  5. Merge results and sort by score
  6. Return top_k across all collections
    ↓
Results to Orchestrator → Use Case → User
```

---

## Implementation

### **1. Retrieval Service Update**

**File:** `src/corpus_svc/app/services/query_service.py`

**Current signature:**

```python
async def perform_semantic_search(
    query_text: str,
    top_k: int = 10,
    filters: Optional[List[SearchFilter]] = None,
    user_id: Optional[str] = None,
    min_relevancy_score: float = 0.0,
    auth_token: Optional[str] = None,
    run_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    embedding_model: Optional[str] = None,  # ← REMOVE (use system default)
) -> List[QueryResultItem]:
```

**New signature:**

```python
async def perform_semantic_search(
    query_text: str,
    collection_names: List[str] = None,  # ← NEW: List of collections to search
    top_k: int = 10,
    filters: Optional[List[SearchFilter]] = None,
    user_id: Optional[str] = None,
    min_relevancy_score: float = 0.0,
    auth_token: Optional[str] = None,
    run_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> List[QueryResultItem]:
    """
    Perform semantic search across one or more collections.

    Args:
        query_text: The search query
        collection_names: List of collection names to search (defaults to ["default"])
        top_k: Total number of results to return across all collections
        ...

    Returns:
        List of query results, merged and sorted by relevance score
    """

    # Default to "default" collection if not specified
    if not collection_names:
        collection_names = ["default"]

    # 1. Get collection metadata from database
    collections = await self.collection_repository.get_by_names(collection_names)

    if not collections:
        logger.warning(f"No collections found for names: {collection_names}")
        return []

    if len(collections) != len(collection_names):
        found_names = {c.name for c in collections}
        missing = set(collection_names) - found_names
        logger.warning(f"Collections not found or inactive: {missing}")

    # 2. Validate all collections use same embedding model
    #    (Phase 3-5: All should use system default, so this is a sanity check)
    embedding_models = {c.embedding_model for c in collections}
    if len(embedding_models) > 1:
        raise ValueError(
            f"Cannot search collections with different embedding models: {embedding_models}. "
            f"All collections must use the same embedding model."
        )

    # 3. Use system embedding model
    embedding_model = collections[0].embedding_model

    # 4. Get query embedding (once for all collections)
    try:
        embedding_objects = await self.embedding_client.embed_texts(
            texts=[query_text],
            model=embedding_model,
            auth_token=auth_token
        )
        if not embedding_objects or not embedding_objects[0].embedding:
            logger.error(f"Failed to get embedding for query: {query_text}")
            return []

        query_vector = embedding_objects[0].embedding
    except Exception as e:
        logger.error(f"Embedding error for query '{query_text}': {e}", exc_info=True)
        return []

    # 5. Search each collection
    all_results = []

    for collection in collections:
        try:
            # Get Qdrant collection name
            qdrant_collection = collection.qdrant_collection_name

            # Search this collection
            qdrant_results = await self.vector_repository.search_similar_in_collection(
                collection_name=qdrant_collection,
                query_vector=query_vector,
                filter_params=qdrant_filters_payload if filters else None,
                limit=top_k * 2,  # Get more results per collection for better ranking
            )

            # Tag results with source collection
            for result in qdrant_results:
                result.metadata['source_collection'] = collection.name

            all_results.extend(qdrant_results)

        except Exception as e:
            logger.error(f"Error searching collection '{collection.name}': {e}", exc_info=True)
            # Continue with other collections

    # 6. Filter by minimum relevancy score
    if all_results:
        all_results = [r for r in all_results if r.score >= min_relevancy_score]

    # 7. Sort all results by score and return top_k
    #    (Valid because all collections use same embedding model)
    all_results.sort(key=lambda x: x.score, reverse=True)
    top_results = all_results[:top_k]

    # 8. Hydrate results with document metadata and track usage
    #    (existing logic)
    # ... (unchanged from current implementation)

    return hydrated_results
```

---

### **2. Vector Repository Update**

**File:** `src/corpus_svc/app/repositories/vector_repository.py`

**Add new method:**

```python
async def search_similar_in_collection(
    self,
    collection_name: str,
    query_vector: list[float],
    filter_params: dict[str, Any] | None = None,
    limit: int | None = None,
    offset: int = 0,
    score_threshold: float | None = None,
) -> list[QdrantSearchResult]:
    """
    Search a specific Qdrant collection.

    Args:
        collection_name: Exact Qdrant collection name (not config collection_name)
        query_vector: Query embedding vector
        filter_params: Optional filter parameters
        limit: Maximum results to return
        offset: Offset for pagination
        score_threshold: Minimum similarity score

    Returns:
        List of search results from this collection
    """
    client = await self._get_client()
    try:
        # Convert filter params to Qdrant filter
        qdrant_filter = self._build_filter(filter_params) if filter_params else None

        # Use provided limit or default
        actual_limit = limit if limit is not None else self.config.default_limit

        # Execute search on specific collection
        search_kwargs: dict[str, Any] = {
            "collection_name": collection_name,  # Use provided collection name
            "query_vector": query_vector,
            "query_filter": qdrant_filter,
            "limit": actual_limit,
            "offset": offset,
            "with_payload": True,
            "score_threshold": score_threshold,
        }

        # Add search params if configured
        if self.config.ef_search is not None:
            search_kwargs["search_params"] = qdrant_models.SearchParams(
                hnsw_ef=self.config.ef_search
            )

        # Execute search
        search_result = await client.search(**search_kwargs)

        # Convert to QdrantSearchResult objects
        results = []
        for hit in search_result:
            document_id = hit.payload.get("document_id") if hit.payload else None
            chunk_id = hit.payload.get("chunk_id") if hit.payload else None

            result = QdrantSearchResult(
                id=str(hit.id),
                score=hit.score,
                payload=hit.payload or {},
                document_id=document_id,
                chunk_id=chunk_id,
            )
            results.append(result)

        logger.info(f"Found {len(results)} results in collection '{collection_name}'")
        return results

    except Exception as e:
        logger.error(f"Failed to search collection '{collection_name}': {e!s}", exc_info=True)
        raise
```

---

### **3. Collection Repository (New)**

**File:** `src/corpus_svc/app/repositories/collection_repository.py` (new file)

```python
"""
Repository for collection metadata access.
"""

from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging
from ..db.models import Collection

logger = configure_logging(service_name="collection_repository")


class CollectionRepository:
    """Repository for collection metadata operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_names(self, names: List[str]) -> List[Collection]:
        """
        Fetch collections by names.

        Args:
            names: List of collection names

        Returns:
            List of active Collection objects
        """
        query = select(Collection).where(
            Collection.name.in_(names),
            Collection.is_active == True
        )

        result = await self.session.execute(query)
        collections = result.scalars().all()

        logger.info(f"Found {len(collections)} collections for names: {names}")
        return list(collections)

    async def get_default(self) -> Collection | None:
        """Get the default collection."""
        query = select(Collection).where(
            Collection.is_default == True,
            Collection.is_active == True
        )

        result = await self.session.execute(query)
        collection = result.scalars().first()

        return collection
```

**Add dependency injection:**

**File:** `src/corpus_svc/app/main.py`

```python
from .repositories.collection_repository import CollectionRepository

async def get_collection_repository(
    session: AsyncSession = Depends(get_db_session)
) -> CollectionRepository:
    """Dependency injection for collection repository."""
    return CollectionRepository(session)
```

---

### **4. Orchestrator Update**

**File:** `src/orchestrator/app/orchestrator/controller.py`

**Update retrieve_context() method:**

```python
async def retrieve_context(
    self,
    query: str,
    intent_type: RequestType,
    request_id: str | None = None,
    token: str | None = None,
    use_case_config: UseCaseConfig | None = None,
) -> dict[str, Any]:
    """Retrieve relevant context for the query using the retrieval service."""

    logger.info(f"Retrieving context for query (intent: {intent_type})")

    # Extract search query
    search_query = self._extract_search_query(query)

    # Check if RAG enabled
    if use_case_config and not use_case_config.rag.enabled:
        logger.info("RAG disabled in use case config, skipping context retrieval")
        return {
            "sources": [],
            "metadata": {"retrieval_time": 0.0, "total_sources": 0, "rag_enabled": False},
        }

    retrieval_start_time = time.time()

    try:
        retrieval_svc_url = self.config.get(
            "retrieval_svc_url",
            os.environ.get("CORPUS_SVC_URL", "http://corpus-service:8001/api/v1"),
        )

        # Get config from use case or defaults
        if use_case_config:
            top_k = use_case_config.rag.top_k
            similarity_threshold = use_case_config.rag.similarity_threshold
            collection_names = use_case_config.rag.vector_collections  # ← NEW: List of collections
        else:
            top_k = self._get_top_k_for_intent(intent_type)
            similarity_threshold = self.config.get("min_relevancy_score", 0.3)
            collection_names = ["default"]  # ← NEW: Default collection

        # Prepare request
        retrieval_request = {
            "query_text": search_query,
            "collection_names": collection_names,  # ← NEW: Send list of collections
            "top_k": top_k,
            "min_relevancy_score": similarity_threshold,
            "run_id": request_id,
        }

        # NOTE: Embedding model NOT sent - retrieval service uses system default

        # Add metadata filters if specified
        if use_case_config and use_case_config.rag.metadata_filters:
            filters = []
            for field, value in use_case_config.rag.metadata_filters.items():
                filters.append({"field": field, "value": value})
            retrieval_request["filters"] = filters

        # Make request
        url = f"{retrieval_svc_url}/query/semantic-search"
        headers = {"Content-Type": "application/json"}
        if request_id:
            headers["X-Request-ID"] = request_id
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=retrieval_request, headers=headers)
            response.raise_for_status()
            search_results = response.json()

        # Transform results
        # ... (existing logic)

    except Exception as e:
        logger.error(f"Error retrieving context: {e}", exc_info=True)
        # Return empty context on error
        return {
            "sources": [],
            "metadata": {"retrieval_time": 0.0, "total_sources": 0, "error": str(e)},
        }
```

---

### **5. API Schema Update**

**File:** `src/corpus_svc/app/schemas/query.py`

**Update QueryRequest:**

```python
class QueryRequest(BaseModel):
    """Request schema for semantic search."""

    query_text: str = Field(..., description="The search query text")
    collection_names: List[str] = Field(
        default_factory=lambda: ["default"],
        description="List of collection names to search"
    )
    top_k: int = Field(default=10, description="Number of results to return", gt=0, le=100)
    filters: Optional[List[SearchFilter]] = Field(None, description="Optional filters")
    min_relevancy_score: float = Field(
        default=0.0,
        description="Minimum similarity score threshold",
        ge=0.0,
        le=1.0
    )
    run_id: Optional[str] = Field(None, description="Run ID for tracking")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    # embedding_model removed - system determines from collections
```

---

## Testing

### **Unit Tests**

```python
# tests/unit/test_multi_collection_search.py

@pytest.mark.asyncio
async def test_multi_collection_search():
    """Test searching across multiple collections."""

    # Setup
    query_service = QueryService(...)

    # Execute
    results = await query_service.perform_semantic_search(
        query_text="malware analysis",
        collection_names=["threat_intel", "mitre_attack"],
        top_k=10
    )

    # Assert
    assert len(results) <= 10
    assert all(r.score >= 0.0 for r in results)
    # Results should be from both collections
    collections = {r.metadata['source_collection'] for r in results}
    assert len(collections) > 0


@pytest.mark.asyncio
async def test_collection_not_found():
    """Test handling of non-existent collection."""

    results = await query_service.perform_semantic_search(
        query_text="test",
        collection_names=["nonexistent"],
        top_k=10
    )

    # Should return empty results, not error
    assert results == []


@pytest.mark.asyncio
async def test_results_sorted_by_score():
    """Test that results are properly sorted across collections."""

    results = await query_service.perform_semantic_search(
        query_text="security incident",
        collection_names=["coll1", "coll2", "coll3"],
        top_k=20
    )

    # Verify sorted descending by score
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)
```

### **Integration Tests**

```python
# tests/integration/test_multi_collection_integration.py

@pytest.mark.integration
async def test_end_to_end_multi_collection_search():
    """Test complete flow from orchestrator to results."""

    # Setup: Create 2 collections with test documents
    await create_test_collection("test_coll_1")
    await create_test_collection("test_coll_2")
    await upload_test_documents("test_coll_1", count=5)
    await upload_test_documents("test_coll_2", count=5)

    # Execute use case with multi-collection RAG
    use_case_config = {
        "rag": {
            "enabled": True,
            "vector_collections": ["test_coll_1", "test_coll_2"],
            "top_k": 5
        }
    }

    response = await execute_use_case(
        use_case_config=use_case_config,
        query="test query"
    )

    # Verify
    assert "sources" in response
    assert len(response["sources"]) <= 5
    # Should have results from both collections
    source_collections = {
        s["metadata"]["source_collection"]
        for s in response["sources"]
    }
    assert len(source_collections) > 1
```

---

## Performance Considerations

**Optimizations:**

1. **Parallel Collection Search:**
   - Consider `asyncio.gather()` to search collections in parallel
   - Can reduce total search time significantly

```python
# Parallel approach (optional optimization)
search_tasks = [
    self.vector_repository.search_similar_in_collection(
        collection_name=c.qdrant_collection_name,
        query_vector=query_vector,
        limit=top_k * 2
    )
    for c in collections
]

results_per_collection = await asyncio.gather(*search_tasks)
all_results = [r for results in results_per_collection for r in results]
```

2. **Caching:**
   - Cache collection metadata lookups
   - Reduce database roundtrips

3. **Top-K Optimization:**
   - Request `top_k * num_collections` from each
   - Better representation across collections
   - Then merge and select global top-k

---

## Acceptance Criteria

- [x] Retrieval service accepts list of collection names
- [x] Searches all specified collections
- [x] Validates all collections use same embedding model
- [x] Merges and sorts results by score
- [x] Returns top-k across all collections
- [x] Tags results with source collection
- [x] Handles missing/inactive collections gracefully
- [x] Orchestrator passes collection list from Use Case config
- [x] Integration tests pass
- [x] Performance acceptable (< 500ms for 3 collections)

---

## Related Work

- **P3-TASK-01:** Remove models.embedding from Use Case Config
- **ADR-021:** Collection-Based Document Management (updated)
- **P5-F8:** Embedding Model Migration (future multi-model support)

---

**Status:** 📋 Future (Phase 4)
**Estimated Effort:** 2-3 days
**Target:** November 2025
