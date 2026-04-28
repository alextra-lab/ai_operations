# API Contract Mismatches - Frontend vs Backend

**Date:** October 8, 2025
**Status:** 🚨 CRITICAL - UI Cannot Display Data

## Overview

The frontend and backend have significant schema mismatches across multiple endpoints, causing:
- Search results to display as "NaN% relevant" and "NaN% confidence"
- Query history save failures (422 Unprocessable Entity)
- TypeErrors when accessing undefined properties

## 1. Search Results Schema Mismatch

### Backend Response (Retrieval Service)
**Endpoint:** `POST /api/v1/query/semantic-search`
**Schema:** `QueryResponse` containing `QueryResultItem[]`

```json
{
  "query_id": "uuid",
  "query_text": "search query",
  "search_type": "semantic",
  "results": [
    {
      "document_id": "uuid",
      "chunk_id": "uuid",
      "score": 0.85,
      "text_snippet": "...",
      "full_text": "...",
      "document_title": "Title",
      "document_source": "source",
      "document_metadata": {
        "author": "...",
        "classification": "..."
      },
      "chunk_metadata": {}
    }
  ],
  "total_results": 4,
  "processing_time_ms": 12.5
}
```

### Frontend Expects (SearchResult interface)
```typescript
{
  id: string;                    // ❌ Backend sends document_id + chunk_id
  title: string;                 // ❌ Backend sends document_title
  content: string;               // ❌ Backend sends text_snippet or full_text
  snippet: string;               // ❌ Backend sends text_snippet
  relevance_score: number;       // ❌ Backend sends score
  confidence: number;            // ❌ Backend DOESN'T SEND THIS
  metadata: {
    author: string;              // ❌ Backend sends document_metadata (nested differently)
    source: string;              // ❌ Backend sends document_source (root level)
  }
}
```

### Field Mapping Required

| Frontend Field | Backend Field | Type | Fix |
|---|---|---|---|
| `id` | `chunk_id` or `document_id` | string | Use chunk_id |
| `title` | `document_title` | string | Rename |
| `content` | `full_text` | string | Rename |
| `snippet` | `text_snippet` | string | Rename |
| `relevance_score` | `score` | number | Rename |
| `confidence` | *(missing)* | number | Calculate or default to score |
| `metadata.author` | `document_metadata.author` | string | Flatten from nested |
| `metadata.source` | `document_source` | string | Move from root |
| `metadata.classification` | `document_metadata.classification` | string | Flatten from nested |

## 2. Query History Save Mismatch

### Frontend Sends (OLD - Fixed in semantic-search.component.ts)
```typescript
{
  query: "...",          // ❌ Should be query_text
  query_type: "...",     // ❌ Should be intent_type
  status: "COMPLETED"    // ❌ Should be response_status: "success"
}
```

### Backend Expects (QueryHistoryCreate)
```json
{
  "query_text": "string (required)",
  "run_id": "string (required)",
  "user_id": "uuid (required)",
  "response_status": "string (required)",
  "intent_type": "string (optional)",
  "use_case_id": "uuid (optional)",
  "metadata": "object (optional)"
}
```

**Status:** ✅ Partially Fixed - but missing user_id from auth context

## 3. Query History Display Mismatch

**Status:** ✅ FIXED

- Updated `QueryHistory` interface to match backend
- Updated component template to use correct field names
- Renamed `execution_time_ms` → `processing_time_ms` in backend

## Solutions Required

### Option A: Update Frontend to Match Backend (Recommended)

**Pros:**
- Backend schema is correct and well-documented
- Single source of truth (OpenAPI spec)
- Less code to change

**Cons:**
- Need to update multiple frontend components
- May break other parts of UI

### Option B: Add Response Transformation Layer

**Pros:**
- UI components don't need to change
- Gradual migration possible

**Cons:**
- Maintains technical debt
- Extra transformation overhead
- Two schemas to maintain

### Recommended Approach: Hybrid

1. **Transform in Service Layer** - Add mapping function in `query.service.ts`
2. **Update Models Gradually** - Migrate components one by one
3. **Document Both Schemas** - Keep mapping visible for debugging

## Immediate Fix Implementation

### Step 1: Add Response Transformer

Create a helper function in `query.service.ts`:

```typescript
private transformSearchResult(backendResult: any): SearchResult {
  return {
    id: backendResult.chunk_id || backendResult.document_id,
    title: backendResult.document_title || 'Untitled',
    content: backendResult.full_text || backendResult.text_snippet || '',
    snippet: backendResult.text_snippet || '',
    relevance_score: backendResult.score || 0,
    confidence: backendResult.score || 0,  // Use score as confidence if not provided
    source_type: 'CHUNK',  // Default
    document_id: backendResult.document_id,
    chunk_index: parseInt(backendResult.chunk_id.split('-').pop() || '0'),
    metadata: {
      author: backendResult.document_metadata?.author || 'Unknown',
      source: backendResult.document_source || '',
      classification: backendResult.document_metadata?.classification || '',
      tags: backendResult.document_metadata?.tags || [],
      ...backendResult.document_metadata
    }
  };
}
```

### Step 2: Apply Transformation

Update the search method to transform responses before returning.

## Testing Checklist

- [ ] Search results display correctly
- [ ] Relevance scores show actual numbers (not NaN)
- [ ] Confidence scores show actual numbers (not NaN)
- [ ] Document titles display
- [ ] Metadata (author, source, classification) displays
- [ ] Query history saves without errors
- [ ] Query history displays correctly

## Files to Update

1. ✅ `src/orchestrator/app/schemas/query_history.py` - execution_time_ms → processing_time_ms
2. ✅ `src/frontend-angular/src/app/api/models/query.models.ts` - QueryHistory interface
3. ✅ `src/frontend-angular/src/app/pages/query/query-history.component.ts` - Template field names
4. ✅ `src/frontend-angular/src/app/pages/query/semantic-search.component.ts` - saveSearchToHistory()
5. 🔄 `src/frontend-angular/src/app/api/services/query.service.ts` - Add response transformer
6. 🔄 `src/frontend-angular/src/app/pages/query/semantic-search.component.ts` - Apply transformer

## Root Cause

The frontend was developed with an **assumed API contract** that doesn't match the actual backend implementation. This likely happened due to:
- Development happening in parallel
- No shared API specification
- Missing integration tests

## Prevention

1. Generate TypeScript interfaces from OpenAPI spec
2. Add integration tests that validate API contracts
3. Use tools like `openapi-typescript` for type-safe clients
