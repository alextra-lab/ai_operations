# Execution Metrics Backend/Frontend Alignment Analysis

## Summary
The execution-metrics component HTML template references fields that **DO NOT EXIST** in the backend response schema. The frontend needs to be updated to match the backend's actual data structure.

## Backend Schema (Source of Truth)
**File:** `src/orchestrator/app/schemas/response.py`

### RetrievalMetrics
```python
- top_k: int
- hits: int
- avg_similarity: float
- min_similarity: float
- max_similarity: float
- source_count: int
```

### GuardMetrics
```python
- risk_score: float
- modified: bool
- details: Dict  # Generic dictionary for scanner results
```

### ModelMetrics
```python
- model_id: str
- tokens_in: int
- tokens_out: int
- total_tokens: int
- processing_time: float  # In SECONDS
- metadata: Dict  # Generic dictionary for additional data
```

### ConsolidatedMetrics
```python
- retrieval: Optional[RetrievalMetrics]
- guard: Optional[GuardMetrics]
- model: Optional[ModelMetrics]
- confidence_score: float
- calculation_method: str
```

---

## Frontend HTML Template Issues
**File:** `src/frontend-angular/src/app/components/execution-metrics/execution-metrics.component.html`

### ❌ INCORRECT: Fields that don't exist in backend

#### Line 12: Overall Status
```html
{{ metrics.overall_status | titlecase }} execution with
```
**Problem:** Backend doesn't provide `overall_status` field in ConsolidatedMetrics
**Solution:** Component derives this from confidence_score (already implemented in TS, but HTML is wrong)
**Fix:** Change to `{{ overallStatusClass | titlecase }}`

#### Lines 58, 63, 68: Retrieval Metrics
```html
<div class="stat-label">Retrieval Time</div>
<div class="stat-value">{{ formatDuration(metrics.retrieval.retrieval_time_ms) }}</div>

<div class="stat-label">Documents Searched</div>
<div class="stat-value">{{ metrics.retrieval.total_documents_searched }}</div>

<div class="stat-label">Filtered Documents</div>
<div class="stat-value">{{ metrics.retrieval.filtered_documents }}</div>
```
**Problem:** Backend RetrievalMetrics doesn't have:
- `retrieval_time_ms`
- `total_documents_searched`
- `filtered_documents`

**Solution:** Remove these fields OR request backend team to add them

#### Line 104: Guard Processing Time
```html
<div class="stat-label">Processing Time</div>
<div class="stat-value">{{ formatDuration(metrics.guard.processing_time_ms) }}</div>
```
**Problem:** Backend GuardMetrics doesn't have `processing_time_ms`
**Solution:** Remove this field OR request backend team to add it

#### Lines 110-143: Guard Details
```html
<div class="guard-details" *ngIf="hasGuardDetails">
    <div class="detail-item" *ngIf="hasContentFiltered">...</div>
    <div class="detail-item" *ngIf="hasPIIDetected">...</div>
    ...
</div>
```
**Problem:** Component methods reference properties that need to be parsed from `details` dict
**Current TypeScript:** These getter methods are NOT implemented
**Solution:** Either:
1. Add getter methods to parse from `metrics.guard.details`
2. Request backend to provide structured GuardDetails object

#### Lines 184, 190, 195, 200: Model Metrics
```html
<div class="stat-label">Latency</div>
<div class="stat-value">{{ formatDuration(metrics.model.latency_ms) }}</div>

<div class="stat-label">Temperature</div>
<div class="stat-value">{{ metrics.model.temperature }}</div>

<div class="stat-label">Max Tokens</div>
<div class="stat-value">{{ formatTokens(metrics.model.max_tokens) }}</div>

<div class="stat-item" *ngIf="hasCostEstimate">
    <div class="stat-label">Cost Estimate</div>
    <div class="stat-value">{{ formatCost(metrics.model.cost_estimate) }}</div>
</div>
```
**Problem:** Backend ModelMetrics doesn't have:
- `latency_ms` (has `processing_time` in seconds)
- `temperature`
- `max_tokens`
- `cost_estimate`

**Solution:** These might be in `metadata` dict, need to parse them OR use what's available

---

## Recommended Fixes

### Option 1: Align Frontend with Backend (Recommended)
**Remove non-existent fields and only display what backend provides:**

#### RetrievalMetrics - Keep Only:
- Documents Retrieved: `{{ metrics.retrieval.hits }} / {{ metrics.retrieval.top_k }}`
- Avg Similarity: `{{ formatSimilarity(metrics.retrieval.avg_similarity) }}`
- Similarity Range: `{{ formatSimilarity(metrics.retrieval.min_similarity) }} - {{ formatSimilarity(metrics.retrieval.max_similarity) }}`
- Source Count: `{{ metrics.retrieval.source_count }}`

#### GuardMetrics - Keep Only:
- Risk Score: `{{ formatRiskScore(metrics.guard.risk_score) }}`
- Content Modified: `{{ metrics.guard.modified ? 'Yes' : 'No' }}`

#### ModelMetrics - Keep Only:
- Model: `{{ metrics.model.model_id }}`
- Input Tokens: `{{ formatTokens(metrics.model.tokens_in) }}`
- Output Tokens: `{{ formatTokens(metrics.model.tokens_out) }}`
- Total Tokens: `{{ formatTokens(metrics.model.total_tokens) }}`
- Processing Time: `{{ formatDuration(metrics.model.processing_time * 1000) }}`

### Option 2: Request Backend Updates
**Ask backend team to add these fields to their schemas:**
- RetrievalMetrics: `retrieval_time_ms`, `total_documents_searched`, `filtered_documents`
- GuardMetrics: `processing_time_ms`, structured `guard_details` object
- ModelMetrics: `latency_ms`, `temperature`, `max_tokens`, `cost_estimate`

### Option 3: Parse from metadata/details dictionaries
**If the data exists in `metadata` or `details` dicts, add TypeScript getters:**
```typescript
get hasGuardDetails(): boolean {
    return this.metrics.guard?.details != null;
}

get hasContentFiltered(): boolean {
    return this.metrics.guard?.details?.content_filtered === true;
}

get hasCostEstimate(): boolean {
    return this.metrics.model?.metadata?.cost_estimate != null;
}
```

---

## Current Status

✅ **Correctly Aligned (Fixed 2025-12-10):**
- Basic retrieval metrics (top_k, hits, similarities, source_count)
- Basic guard metrics (risk_score, modified)
- Basic model metrics (model_id, tokens, processing_time)
- Cost estimation (now properly async and displays calculated values)
- Source document metadata (all fields now display correctly)

✅ **All Issues Resolved:**
- Frontend schemas match backend schemas
- Cost breakdown displays actual calculated values (including $0.0000)
- Source document metadata (document_type, chunk_index, created_at, classification, author, url) all display correctly
- Model Performance widget layout improved for readability

❌ **Previously Misaligned (Now Fixed):**
- `metrics.overall_status` → Should use `overallStatusClass`
- `metrics.retrieval.retrieval_time_ms` → Doesn't exist
- `metrics.retrieval.total_documents_searched` → Doesn't exist
- `metrics.retrieval.filtered_documents` → Doesn't exist
- `metrics.guard.processing_time_ms` → Doesn't exist
- `metrics.guard` detailed security flags → Need parsing from `details`
- `metrics.model.latency_ms` → Backend has `processing_time` in seconds
- `metrics.model.temperature` → Doesn't exist
- `metrics.model.max_tokens` → Doesn't exist
- `metrics.model.cost_estimate` → Doesn't exist

---

## Recommendation

**I recommend Option 1**: Align the frontend with the backend's current schema. This ensures the UI displays accurate data and avoids runtime errors when accessing undefined properties.

The enhanced metrics display is good UX, but we should only show data that actually exists in the backend response.
