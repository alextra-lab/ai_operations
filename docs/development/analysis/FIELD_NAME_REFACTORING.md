# Field Name Refactoring Summary

**Date:** October 8, 2025
**Status:** ✅ COMPLETE (Pending Testing)

## Overview

Comprehensive refactoring to fix field name mismatches between frontend and backend, ensuring the UI properly displays query history data.

## Changes Made

### 1. Database Migration (010)

**File:** `ops/migrations/sql/010_rename_execution_time_to_processing_time.sql`

- Renamed column `execution_time_ms` → `processing_time_ms`
- Added descriptive comment explaining the field's purpose

```sql
ALTER TABLE query_history
RENAME COLUMN execution_time_ms TO processing_time_ms;
```

### 2. Backend Updates

#### Database Model
**File:** `src/orchestrator/app/db/models.py`
- Updated `QueryHistory.execution_time_ms` → `QueryHistory.processing_time_ms`

#### Schemas
**File:** `src/orchestrator/app/schemas/query_history.py`
- Updated all schema classes: `QueryHistoryCreate`, `QueryHistoryUpdate`, `QueryHistoryResponse`
- Changed field name and description to reflect "Total processing time in milliseconds"

#### Service Layer
**File:** `src/orchestrator/app/services/history_service.py`
- Updated all references from `execution_time_ms` to `processing_time_ms` (7 occurrences)

#### Orchestrator Controller
**File:** `src/orchestrator/app/orchestrator/controller.py`
- Updated timing metric calculation to use `processing_time_ms`

### 3. Frontend Updates

#### TypeScript Models
**File:** `src/frontend-angular/src/app/api/models/query.models.ts`

**Complete rewrite of `QueryHistory` interface to match backend:**

| Old Frontend Field | New Backend Field | Purpose |
|-------------------|-------------------|---------|
| `query` | `query_text` | The actual query text |
| `query_type` | `intent_type` | Intent classification |
| `status` | `response_status` | Query processing status |
| `processing_time_ms` | `processing_time_ms` | ✅ Already correct |
| `metadata` | `metadata_json` | Additional metadata |
| *(not present)* | `run_id` | Unique execution identifier |
| *(not present)* | `use_case_id` | Associated use case UUID |
| *(not present)* | `use_case_name` | Use case name |
| *(not present)* | `response_text` | LLM response text |
| *(not present)* | `metrics` | Execution metrics object |
| *(not present)* | `sources` | Retrieved sources |
| *(not present)* | `citations` | Source citations |
| *(not present)* | `thread_id` | Conversation thread ID |
| *(not present)* | `fork_count` | Number of query forks |

#### Component Template & Logic
**File:** `src/frontend-angular/src/app/pages/query/query-history.component.ts`

**Template Changes:**
- `query.query` → `query.query_text`
- `query.query_type` → `query.intent_type`
- `query.status` → `query.response_status`
- `query.metadata` → `query.metadata_json`
- `query.results_count` → `query.use_case_name` (replaced with more useful info)

**TypeScript Logic Changes:**
- Updated `getQueryTypeIcon()` to accept optional `intentType?: string`
- Added support for backend intent types: `QUERY`, `SUMMARIZATION`, `ANALYSIS`
- Updated `reuseQuery()` to use `query.query_text` and `query.intent_type`
- Updated `forkQuery()` to use `query.query_text` and `query.metadata_json`
- Updated `deleteQuery()` confirmation to use `query.query_text`

## Field Name Semantics

### `processing_time_ms` (formerly `execution_time_ms`)

**Type:** Integer (milliseconds)
**Purpose:** Total end-to-end processing time

**What it includes:**
- Authentication verification
- Intent parsing
- LLM-Guard validation
- Context retrieval (RAG)
- Prompt assembly
- LLM request routing
- Response formatting

**What it excludes:**
- Network latency to/from external APIs
- Database persistence time
- Serialization overhead

**Calculated as:**
```python
start_time = time.time()
# ... entire orchestration workflow ...
processing_time_ms = int((time.time() - start_time) * 1000)
```

## Testing Instructions

### 1. Apply Database Migration

```bash
# Activate virtual environment
source venv/bin/activate

# Load test environment variables
export $(grep -v '^#' config/env/env.test | xargs)

# Start test services
bash ops/testing/init_test_environment.sh

# Run migrations (if not run by init script)
python ops/migrations/runner.py
```

### 2. Verify Backend API

```bash
# Check OpenAPI spec for correct field names
curl -s http://localhost:8006/openapi.json | jq '.components.schemas.QueryHistoryResponse.properties' | grep -E "(query_text|intent_type|response_status|processing_time_ms)"

# Test query history endpoint
curl -s -X GET "http://localhost:8006/api/v1/query-history?limit=5" \
  -H "Authorization: Bearer <TOKEN>" | jq '.items[0]'
```

### 3. Verify Frontend Display

1. Start Angular dev server: `ng serve`
2. Navigate to Query History page
3. Verify that query cards display:
   - Query text (not blank)
   - Intent type (e.g., "QUERY", "SUMMARIZATION")
   - Response status (e.g., "success", "failed")
   - Processing time (e.g., "1250ms")
   - Use case name (if available)

## Success Criteria

- [x] Database migration created (010)
- [x] Backend model updated
- [x] Backend schemas updated
- [x] Backend service updated
- [x] Backend orchestrator updated
- [x] Frontend model updated
- [x] Frontend component template updated
- [x] Frontend component logic updated
- [ ] Migration applied successfully
- [ ] API returns correct field names
- [ ] UI displays query history correctly

## Breaking Changes

### API Contract Changes

The following field names have changed in the `QueryHistoryResponse` schema:

1. **For frontend clients:** Update all references from old field names to new backend field names
2. **Backward compatibility:** None - this is a breaking change requiring frontend updates

### Migration Path

1. Apply database migration 010
2. Deploy updated backend code
3. Deploy updated frontend code
4. Clear any cached API responses in clients

## Notes

- The frontend model now fully matches the backend schema
- Added support for additional backend fields (use_case_name, sources, citations, etc.)
- Removed frontend-only fields that aren't supported by backend (results_count)
- `processing_time_ms` is a better semantic name than `execution_time_ms`
