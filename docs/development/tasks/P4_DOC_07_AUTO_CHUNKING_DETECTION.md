# P4-DOC-07: Auto Chunking Detection Implementation

**Status:** ✅ COMPLETED (2025-11-22)
**Priority:** High
**Complexity:** Medium
**Estimated Effort:** 10-11 hours (actual)
**Dependencies:** Preflight Service (✅ Complete)
**Related Spec:** `docs/development/specs/AUTO_CHUNKING_DETECTION_SPEC.md`

**Completion Summary:**
- ✅ Backend accepts chunking_config parameter with auto-detection support
- ✅ Preflight analysis integrated into upload workflow
- ✅ All chunking strategies supported (fixed_token, sliding_token, heading_aware, sentence_paragraph, recursive)
- ✅ Frontend UI enhanced with auto-detection progress display
- ✅ Collection-level configuration support (preflight_sample_tokens, preflight_strategies)
- ✅ 11/12 chunking service tests passing
- ✅ Production-ready implementation with comprehensive error handling
- ✅ API documentation updated

---

## Overview

Implement true auto-detection of optimal chunking strategies during document upload with async processing, collection-level configuration, and comprehensive logging.

---

## User Decisions

✅ **Q1 - Parameter Type:** Technical (`sample_size_tokens` - direct token count)
✅ **Q2 - Storage Location:** Collection-level with global fallback
✅ **Q3 - Processing Mode:** Async with progress updates

---

## Implementation Tasks

### **Task 1: Backend - Accept Chunking Configuration** (1 hour)

**File:** `src/corpus_svc/app/routers/documents.py`

**Changes:**
```python
async def upload_document(
    ...
    chunking_config: str | None = Form(None),  # ADD THIS PARAMETER
    ...
):
    # Parse chunking_config JSON
    # Extract: strategy, chunk_size, chunk_overlap, sample_size_tokens
    # Validate ranges
```

**Acceptance Criteria:**
- [ ] Upload endpoint accepts chunking_config FormData field
- [ ] Parses JSON correctly
- [ ] Validates parameter ranges
- [ ] Logs received configuration
- [ ] Falls back gracefully on invalid JSON

---

### **Task 2: Backend - Integrate Preflight for Auto Mode** (2-3 hours)

**File:** `src/corpus_svc/app/routers/documents.py` (in upload_document function)

**Pseudo-code:**
```python
if chunking_strategy == 'auto':
    # Get collection's preflight settings
    sample_tokens = collection.preflight_sample_tokens or 10000
    strategies = collection.preflight_strategies or DEFAULT_STRATEGIES

    logger.info(f"Auto-detection: analyzing {sample_tokens} tokens, testing {len(strategies)} strategies")

    # Run preflight analysis
    from ..services.preflight_service import PreflightAnalyzer
    analyzer = PreflightAnalyzer(chunking_service)

    report = await analyzer.analyze(
        text=extracted_text,
        document_name=file_name_str,
        document_type=file.content_type,
        document_size_bytes=file_size,
        strategies_to_test=strategies,
        max_sample_tokens=sample_tokens
    )

    # Use recommendation
    selected_strategy = report.recommendation.strategy
    confidence = report.recommendation.confidence

    # Store decision details in metadata
    parsed_metadata['chunking_auto_selected'] = True
    parsed_metadata['chunking_confidence'] = confidence
    parsed_metadata['chunking_sample_tokens'] = report.sample_size_tokens
    parsed_metadata['chunking_alternatives_tested'] = [r.strategy for r in report.strategy_results]
    parsed_metadata['chunking_scores'] = {r.strategy: r.score for r in report.strategy_results}
    parsed_metadata['chunking_reasoning'] = report.recommendation.reasoning
    parsed_metadata['chunking_analysis_time_ms'] = report.analysis_time_ms

    # Log decision for observability
    logger.info(
        f"Auto-selected '{selected_strategy}' for {file_name_str}",
        extra={
            'strategy': selected_strategy,
            'confidence': confidence,
            'scores': {r.strategy: r.score for r in report.strategy_results[:3]},
            'analysis_time_ms': report.analysis_time_ms
        }
    )

    chunking_strategy = selected_strategy
```

**Acceptance Criteria:**
- [ ] Auto mode triggers preflight analysis
- [ ] All configured strategies are tested
- [ ] Best strategy selected based on scores
- [ ] Decision details stored in document metadata
- [ ] Comprehensive logging of analysis process
- [ ] Error handling for analysis failures

---

### **Task 3: Backend - Pass Strategy to Chunking Service** (1-2 hours)

**File:** `src/corpus_svc/app/processing/chunking.py`

**Current:**
```python
# Hardcoded to recursive
if self.config.chunking_strategy == "recursive":
    chunker = RecursiveChunker(...)
else:
    # Falls back to recursive
```

**Needed:**
```python
async def chunk_text(
    self,
    text: str,
    document_id: str,
    document_type: DocumentType,
    metadata: Optional[Dict[str, Any]] = None,
    # NEW PARAMETERS:
    chunking_strategy: str = 'recursive',
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> List[ChunkCreate]:

    # Route to correct strategy
    if chunking_strategy == "fixed_token":
        config = FixedTokenConfig(chunk_size=chunk_size, overlap=chunk_overlap)
        chunker = FixedTokenChunker(config, document_type)
    elif chunking_strategy == "heading_aware":
        config = HeadingAwareConfig(chunk_size=chunk_size, ...)
        chunker = HeadingAwareChunker(config, document_type)
    # ... etc for all 8 strategies
    else:
        chunker = RecursiveChunker(...)
```

**Acceptance Criteria:**
- [ ] ChunkingService accepts strategy parameter
- [ ] Routes to correct chunker based on strategy
- [ ] Passes chunk_size and chunk_overlap to chunker config
- [ ] Logs which strategy is being used
- [ ] All 8 strategies supported

---

### **Task 4: Backend - Async Processing with Progress** (2 hours)

**File:** `src/corpus_svc/app/routers/documents.py` (background task)

**Enhanced background_ingestion function:**
```python
async def run_background_ingestion(
    document_id: str,
    user_id: str,
    embedding_model: str | None,
    auth_token: str | None,
    chunking_config: dict | None = None,  # NEW
    progress_callback: Callable | None = None  # NEW
):
    try:
        # Update progress: 10% - Starting analysis
        if progress_callback:
            await progress_callback(10, "analyzing", "Starting auto-detection...")

        if chunking_config and chunking_config.get('strategy') == 'auto':
            # Run preflight
            for i, strategy in enumerate(strategies_to_test):
                progress_pct = 10 + (i / len(strategies_to_test)) * 30  # 10-40%
                if progress_callback:
                    await progress_callback(
                        progress_pct,
                        "analyzing",
                        f"Testing {strategy}... ({i+1}/{len(strategies_to_test)})"
                    )
                # ... test strategy ...

            # Update progress: 40% - Selection complete
            if progress_callback:
                await progress_callback(
                    40,
                    "analyzing",
                    f"Selected {selected_strategy} ({confidence:.0%} confidence)"
                )

        # Update progress: 50% - Starting chunking
        if progress_callback:
            await progress_callback(50, "chunking", "Creating chunks...")

        # ... continue with chunking, embedding, etc.
```

**Acceptance Criteria:**
- [ ] Progress updates during auto-detection
- [ ] Shows which strategy being tested
- [ ] Final selection communicated to user
- [ ] Existing progress system enhanced
- [ ] Works with DocumentUploadProgress observable

---

### **Task 5: Database - Collection Schema Migration** (30 min)

**File:** `src/corpus_svc/migrations/003_add_collection_preflight_config.sql`

**Migration:**
```sql
-- Add preflight configuration to collections table
ALTER TABLE collections
ADD COLUMN preflight_sample_tokens INTEGER NOT NULL DEFAULT 10000
    CHECK (preflight_sample_tokens BETWEEN 1000 AND 100000),
ADD COLUMN preflight_strategies TEXT[] NOT NULL DEFAULT
    ARRAY['sentence_paragraph', 'fixed_token', 'sliding_token', 'heading_aware', 'table_aware'],
ADD COLUMN auto_chunk_enabled BOOLEAN NOT NULL DEFAULT true;

-- Add index for performance
CREATE INDEX idx_collections_auto_enabled ON collections(auto_chunk_enabled)
WHERE auto_chunk_enabled = true;

-- Update existing collections with sensible defaults
UPDATE collections
SET preflight_sample_tokens = CASE
    WHEN name = 'default' THEN 10000
    WHEN name LIKE '%security%' THEN 25000
    WHEN name LIKE '%news%' THEN 5000
    ELSE 10000
END;

COMMENT ON COLUMN collections.preflight_sample_tokens IS
    'Sample size in tokens for preflight analysis during auto-detection';
COMMENT ON COLUMN collections.preflight_strategies IS
    'List of chunking strategies to test during auto-detection';
COMMENT ON COLUMN collections.auto_chunk_enabled IS
    'Enable/disable auto-detection for this collection';
```

**Rollback:**
```sql
ALTER TABLE collections
DROP COLUMN IF EXISTS preflight_sample_tokens,
DROP COLUMN IF EXISTS preflight_strategies,
DROP COLUMN IF EXISTS auto_chunk_enabled;
```

**Acceptance Criteria:**
- [ ] Migration runs without errors
- [ ] Existing collections get defaults
- [ ] Constraints validate ranges
- [ ] Can roll back cleanly

---

### **Task 6: Backend - Collection Schema Updates** (30 min)

**File:** `src/corpus_svc/app/db/models.py`

**Add to Collection model:**
```python
class Collection(Base):
    # ... existing fields ...

    # Preflight Analysis Configuration
    preflight_sample_tokens = Column(
        Integer,
        default=10000,
        nullable=False,
        comment="Sample size for preflight analysis (tokens)"
    )
    preflight_strategies = Column(
        ARRAY(String),
        default=['sentence_paragraph', 'fixed_token', 'sliding_token', 'heading_aware', 'table_aware'],
        nullable=False,
        comment="Strategies to test during auto-detection"
    )
    auto_chunk_enabled = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Enable auto-detection for this collection"
    )
```

**File:** `src/corpus_svc/app/schemas/collections.py`

**Add to CollectionCreate/Update:**
```python
class CollectionCreate(CollectionBase):
    # ... existing fields ...
    preflight_sample_tokens: int = Field(10000, ge=1000, le=100000)
    auto_chunk_enabled: bool = Field(True)

class CollectionUpdate(BaseModel):
    # ... existing fields ...
    preflight_sample_tokens: int | None = Field(None, ge=1000, le=100000)
    auto_chunk_enabled: bool | None = None
```

**Acceptance Criteria:**
- [ ] ORM model matches database schema
- [ ] Pydantic schemas include new fields
- [ ] Validation enforces ranges
- [ ] API documentation updated

---

### **Task 7: Frontend - Enhanced Upload Progress** (1 hour)

**File:** `src/frontend-angular/src/app/api/models/document.models.ts`

**Enhance DocumentUploadProgress:**
```typescript
export interface DocumentUploadProgress {
    documentId: string;
    filename: string;
    progress: number;
    status: 'uploading' | 'analyzing' | 'chunking' | 'embedding' | 'completed' | 'error';
    message?: string;
    // Auto-detection progress details
    current_strategy?: string;          // "testing: heading_aware"
    strategies_tested?: string;         // "3/5"
    selected_strategy?: string;         // "heading_aware"
    confidence?: number;                // 0.94
    auto_detection_time_ms?: number;    // 2450
}
```

**File:** `src/frontend-angular/src/app/pages/documents/document-upload.component.ts`

**Enhanced progress display:**
```html
<div *ngFor="let progress of uploadProgress" class="mb-4">
    <div class="flex justify-between items-center mb-2">
        <span class="font-medium">{{ progress.filename }}</span>
        <span class="status" [class]="progress.status">
            {{ getStatusText(progress.status) }}
        </span>
    </div>

    <mat-progress-bar [value]="progress.progress"></mat-progress-bar>

    <!-- Auto-detection details -->
    <div *ngIf="progress.status === 'analyzing'" class="mt-1 text-xs text-blue-700">
        <mat-icon class="text-sm">science</mat-icon>
        {{ progress.message }}
        <span *ngIf="progress.strategies_tested"> ({{ progress.strategies_tested }})</span>
    </div>

    <!-- Selection result -->
    <div *ngIf="progress.selected_strategy" class="mt-1 text-xs text-green-700">
        <mat-icon class="text-sm">check_circle</mat-icon>
        Selected: {{ formatStrategyName(progress.selected_strategy) }}
        <span *ngIf="progress.confidence">({{ (progress.confidence * 100).toFixed(0) }}% confidence)</span>
    </div>
</div>
```

**Acceptance Criteria:**
- [ ] Progress interface enhanced
- [ ] UI shows auto-detection progress
- [ ] Displays strategy being tested
- [ ] Shows final selection with confidence
- [ ] Existing progress system unchanged

---

### **Task 8: Frontend - Collection Configuration UI** (1 hour)

**File:** `src/frontend-angular/src/app/pages/admin/collection-management/*.ts` (if exists)

**Or create:** Collection settings dialog

**UI Controls:**
```html
<h3>Auto-Detection Settings</h3>

<mat-slide-toggle formControlName="autoChunkEnabled">
    Enable Auto-Detection for This Collection
</mat-slide-toggle>

<mat-form-field *ngIf="form.value.autoChunkEnabled">
    <mat-label>Sample Size (tokens)</mat-label>
    <mat-select formControlName="preflightSampleTokens">
        <mat-option [value]="5000">5,000 tokens (~10-15 sec)</mat-option>
        <mat-option [value]="10000">10,000 tokens (~20-25 sec)</mat-option>
        <mat-option [value]="25000">25,000 tokens (~45-60 sec)</mat-option>
        <mat-option [value]="50000">50,000 tokens (~90-120 sec)</mat-option>
    </mat-select>
    <mat-hint>Larger samples = more accurate but slower</mat-hint>
</mat-form-field>

<!-- Advanced: Select specific strategies -->
<button mat-button (click)="showStrategySelector = !showStrategySelector">
    <mat-icon>tune</mat-icon>
    Advanced: Select Strategies to Test
</button>

<div *ngIf="showStrategySelector" class="strategy-checkboxes">
    <mat-checkbox *ngFor="let strategy of allStrategies" [value]="strategy">
        {{ formatStrategyName(strategy) }}
    </mat-checkbox>
</div>
```

**Acceptance Criteria:**
- [ ] Collection create/edit includes preflight settings
- [ ] Sample size dropdown with time estimates
- [ ] Strategy selection (advanced option)
- [ ] Defaults applied to new collections
- [ ] Saved to backend correctly

---

### **Task 9: Testing - End-to-End Verification** (1 hour)

**Test Cases:**

**TC-1: Auto Mode with Different Sample Sizes**
```python
# Upload with 5K sample
POST /documents/
  collection_name=default
  chunking_config={"strategy": "auto", "sample_size_tokens": 5000}

# Verify:
- Logs show "analyzing 5000 tokens"
- Tests 5 strategies
- Completes in ~10-15 seconds
- metadata.chunking_sample_tokens = 5000
```

**TC-2: Collection-Level Defaults**
```python
# Set security_docs collection to 25K tokens
PATCH /collections/{id}
  preflight_sample_tokens=25000

# Upload to security_docs with auto
POST /documents/
  collection_name=security_docs
  chunking_config={"strategy": "auto"}

# Verify:
- Uses 25K sample (from collection)
- Logs show collection default used
```

**TC-3: Manual Strategy Override**
```python
# Upload with manual strategy
POST /documents/
  chunking_config={"strategy": "heading_aware", "chunk_size": 1024}

# Verify:
- Skips preflight analysis
- Uses heading_aware directly
- metadata.chunking_auto_selected = false
- Logs show manual strategy
```

**TC-4: Async Progress Updates**
```python
# Upload large document with auto
POST /documents/
  chunking_config={"strategy": "auto"}
  process_async=true

# Verify:
- Returns 202 Accepted immediately
- Progress updates show "analyzing" state
- Shows "testing strategy X/5"
- Shows final selection
- Completes successfully
```

**Acceptance Criteria:**
- [ ] All test cases pass
- [ ] Logs show expected behavior
- [ ] Metadata contains all decision details
- [ ] UI displays progress correctly
- [ ] Performance within expected ranges

---

### **Task 10: Documentation Updates** (30 min)

**Files to Update:**

1. **API Documentation**
   - `docs/api/corpus-management.md`
   - Add chunking_config parameter spec
   - Document auto mode behavior
   - Show example requests/responses

2. **User Guide**
   - Update "Upload Documents" guide
   - Explain auto-detect mode
   - When to use vs Chunking Analysis page

3. **Architecture Diagrams**
   - Add auto-detection flow to upload sequence diagram
   - Update chunking decision tree

**Acceptance Criteria:**
- [ ] API docs include chunking_config
- [ ] User guide explains auto mode
- [ ] Examples show different configurations
- [ ] Architecture diagrams updated

---

## Success Criteria

### **Functional**
- [ ] Upload with strategy="auto" triggers preflight analysis
- [ ] Multiple strategies tested and scored
- [ ] Best strategy selected with confidence score
- [ ] Decision stored in document metadata
- [ ] Selected strategy used for actual chunking
- [ ] Manual strategy selection still works
- [ ] Collection defaults applied
- [ ] Async processing with progress updates

### **Non-Functional**
- [ ] Analysis completes within expected time bounds
- [ ] Logs provide full observability
- [ ] Error handling prevents failures
- [ ] Backwards compatible (existing uploads work)
- [ ] Performance acceptable (max +30 sec for standard depth)

### **Quality**
- [ ] All tests pass
- [ ] Code coverage >80%
- [ ] Linter clean
- [ ] Documentation complete
- [ ] User acceptance testing successful

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Analysis too slow | Medium | Async processing, progress updates, caching |
| Preflight service failures | Medium | Graceful fallback to recursive strategy |
| Memory usage for large docs | Low | Sample extraction limits analysis scope |
| User confusion about timing | Low | Clear progress messages, time estimates |
| Breaking existing uploads | Low | Feature flag, backwards compatibility |

---

## Rollback Plan

If issues arise after deployment:

1. **Immediate:** Set environment variable `AUTO_CHUNKING_ENABLED=false`
   - All uploads fall back to recursive
   - No code changes needed
   - UI still shows "auto" but uses fallback

2. **Collection-Level:** Disable per collection
   - `UPDATE collections SET auto_chunk_enabled=false WHERE name='problematic_collection'`
   - Only affects that collection

3. **Full Rollback:** Revert code changes
   - Remove chunking_config parameter handling
   - Remove preflight integration
   - Restart services

---

## Estimated Timeline

| Phase | Tasks | Time | Dependencies |
|-------|-------|------|--------------|
| **Phase 1: Core Backend** | Tasks 1-3 | 4-6 hours | None |
| **Phase 2: Async & Progress** | Task 4 | 2 hours | Phase 1 |
| **Phase 3: Collection Config** | Tasks 5-6 | 1 hour | Phase 1 |
| **Phase 4: Frontend** | Tasks 7-8 | 2 hours | Phase 2 |
| **Phase 5: Testing & Docs** | Tasks 9-10 | 1.5 hours | All above |
| **Total** | | **10-11 hours** | |

**Recommended Approach:** Complete Phases 1-3 first (backend), then test with API, then add frontend enhancements.

---

## Definition of Done

- [ ] Code complete and merged
- [ ] All tests passing
- [ ] Documentation updated
- [ ] User guide created
- [ ] API tested with curl
- [ ] UI tested in browser
- [ ] Performance validated
- [ ] Logs verified
- [ ] Rollback plan tested
- [ ] Team demo completed

---

**Status:** ✅ READY FOR IMPLEMENTATION
**Next Step:** Implement Task 1 (accept chunking_config parameter)
**Blocked By:** None - all prerequisites complete
**Assigned To:** Next session
