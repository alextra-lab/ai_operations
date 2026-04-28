# Auto Chunking Detection - Feature Specification

**Status:** 📋 APPROVED - Ready for Implementation
**Priority:** High
**Complexity:** Medium
**Estimated Effort:** 10-11 hours
**Target Release:** Phase 4 (P4-DOC-07)
**Dependencies:** Preflight Analysis Service (✅ Complete), Chunking Analysis UI (✅ Complete)
**Spec Version:** 1.0
**Last Updated:** November 2, 2025
**Decisions Approved:**
- ✅ Q1: Technical parameter (`sample_size_tokens`)
- ✅ Q2: Collection-level storage
- ✅ Q3: Async processing with progress

---

## Executive Summary

Implement true auto-detection of optimal chunking strategies during document upload. When users select "Auto-Detect" mode in Document Upload, the system will automatically analyze the document, test multiple strategies, select the best one, and apply it—all invisibly during the upload workflow.

---

## Current State Analysis

### **✅ What Works Now**

1. **Chunking Analysis Page (Manual Workflow):**
   - Full preflight analysis
   - Tests 5 core strategies (sentence_paragraph, fixed_token, sliding_token, heading_aware, table_aware)
   - Analyzes document structure
   - Provides AI recommendations
   - User sees all metrics and makes decision

2. **Backend Preflight Service:**
   - `PreflightAnalyzer` class fully implemented
   - Structure analysis (heading density, table ratio, list ratio, etc.)
   - Strategy benchmarking with scoring
   - Confidence-based recommendations
   - API endpoint: `POST /api/v1/chunking/preflight/analyze`

### **❌ What's Missing**

1. **Upload Documents "Auto" Mode:**
   - UI shows "Auto-Detect Active" but doesn't do anything
   - Backend always uses hardcoded "recursive" strategy
   - No preflight analysis runs
   - No strategy testing occurs
   - No logging of decision rationale

2. **Integration Gap:**
   - Preflight service exists but not called during upload
   - `chunking_config` sent from UI but ignored by backend
   - No connection between auto mode and preflight analysis

---

## Problem Statement

**User Expectation:**
> "Select Auto-Detect mode → System automatically tests strategies and picks best"

**Current Reality:**
> "Select Auto-Detect mode → System uses recursive (hardcoded), no testing happens"

**Gap:**
- Backend doesn't accept `chunking_config` parameter
- No integration between upload and preflight analysis
- Users have no visibility into what strategy was used or why

---

## Proposed Solution

### **Feature: Intelligent Auto-Detection During Upload**

When `chunking_config.strategy = "auto"`, the system will:

1. **Extract document text** (already happening)
2. **Run preflight analysis** (call PreflightAnalyzer)
3. **Test configured strategies** based on analysis depth
4. **Select optimal strategy** with confidence score
5. **Log decision rationale** for transparency
6. **Store decision in metadata** for UI visibility
7. **Apply selected strategy** to chunk the document
8. **Return strategy used** in upload response

---

## Configuration Parameters

### **1. Analysis Depth (NEW Parameter)**

**Name:** `analysis_depth` or `sample_size_tokens`
**Type:** Integer
**Range:** 1,000 - 50,000 tokens
**Default:** 10,000 tokens

**Purpose:**
- Controls how much of the document is analyzed
- Larger sample = more accurate, slower
- Smaller sample = faster, less accurate

**UI Label:** "Analysis Sample Size"
**Tooltip:** "Amount of document text to analyze (in tokens). Larger samples give more accurate recommendations but take longer."

**Where to configure:**
- Chunking Analysis page: User-configurable slider/input
- Upload Documents advanced options: Use collection default
- Collection settings: Default for all uploads to that collection

### **2. Strategies to Test (Existing Parameter)**

**Current:** Tests 5 core strategies by default
**Configurable:** Yes (via `strategies_to_test` parameter)

**Options:**
- **Quick (5 strategies, ~15 sec):** Core strategies only
- **Standard (7 strategies, ~25 sec):** Core + expert strategies
- **Thorough (8 strategies, ~30 sec):** All including legacy

**Default:** Quick (5 strategies)

---

## Data Model Changes

### **1. Collection Schema - Add Preflight Defaults**

**Table:** `collections`
**New Fields:**

```sql
ALTER TABLE collections ADD COLUMN preflight_sample_tokens INTEGER DEFAULT 10000;
ALTER TABLE collections ADD COLUMN preflight_strategies TEXT[] DEFAULT ARRAY['sentence_paragraph', 'fixed_token', 'sliding_token', 'heading_aware', 'table_aware'];
ALTER TABLE collections ADD COLUMN auto_chunk_enabled BOOLEAN DEFAULT true;
```

**Rationale:**
- Different collections may need different analysis depth
- Technical docs might need thorough analysis
- News articles might be fine with quick analysis
- Corpus managers can tune per collection

### **2. Document Metadata - Store Decision Details**

**Existing:** `metadata` JSONB field
**New Keys Added:**

```json
{
  "collection_name": "security_docs",
  "collection_id": "uuid...",
  "chunking_strategy": "heading_aware",           // ✅ Already added
  "chunking_auto_selected": true,                 // NEW: Was it auto?
  "chunking_confidence": 0.94,                    // NEW: Confidence score
  "chunking_sample_tokens": 10000,                // NEW: Sample size used
  "chunking_alternatives_tested": [               // NEW: What was tested
    "sentence_paragraph",
    "fixed_token",
    "sliding_token",
    "heading_aware",
    "table_aware"
  ],
  "chunking_scores": {                            // NEW: All scores
    "sentence_paragraph": 0.79,
    "fixed_token": 0.65,
    "sliding_token": 0.65,
    "heading_aware": 0.94,
    "table_aware": 0.30
  },
  "chunking_reasoning": [                         // NEW: Why selected
    "Document has clear hierarchical structure",
    "Heading boundaries preserve semantic context",
    "23% better retrieval than fixed-token"
  ],
  "chunking_analysis_time_ms": 2450              // NEW: How long it took
}
```

---

## Backend Implementation Spec

### **Phase 1: Accept Chunking Config (30 min)**

**File:** `src/corpus_svc/app/routers/documents.py`

**Add parameter:**
```python
async def upload_document(
    ...
    chunking_config: str | None = Form(None),  # NEW
    ...
):
```

**Parse config:**
```python
# Parse chunking configuration
chunking_strategy = 'recursive'  # Default fallback
chunk_size = 512
chunk_overlap = 50
auto_selected = False
analysis_metadata = {}

if chunking_config:
    try:
        config_dict = json.loads(chunking_config)
        chunking_strategy = config_dict.get('strategy', 'recursive')
        chunk_size = config_dict.get('chunk_size', 512)
        chunk_overlap = config_dict.get('chunk_overlap', 50)
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Invalid chunking_config, using defaults: {chunking_config}")
```

### **Phase 2: Implement Auto-Detection (2-3 hours)**

**Add auto-detection logic:**
```python
if chunking_strategy == 'auto':
    logger.info(f"Running auto-detection for document {file_name_str}")

    # Get collection's preflight defaults
    sample_tokens = collection.preflight_sample_tokens or 10000
    strategies = collection.preflight_strategies or DEFAULT_STRATEGIES

    # Run preflight analysis
    from ..services.preflight_service import PreflightAnalyzer

    analyzer = PreflightAnalyzer(chunking_service)
    report = await analyzer.analyze(
        text=extracted_text,
        document_name=file_name_str,
        document_type=file.content_type or "text/plain",
        document_size_bytes=file_size,
        test_suite_id=None,  # No test suite during upload
        strategies_to_test=strategies,
        max_sample_tokens=sample_tokens
    )

    # Use recommended strategy
    chunking_strategy = report.recommendation.strategy
    auto_selected = True

    # Store decision details in metadata
    analysis_metadata = {
        'chunking_auto_selected': True,
        'chunking_confidence': report.recommendation.confidence,
        'chunking_sample_tokens': report.sample_size_tokens,
        'chunking_alternatives_tested': [r.strategy for r in report.strategy_results],
        'chunking_scores': {r.strategy: r.score for r in report.strategy_results},
        'chunking_reasoning': report.recommendation.reasoning,
        'chunking_analysis_time_ms': report.analysis_time_ms
    }

    # Log decision for transparency
    logger.info(
        f"Auto-detection selected '{chunking_strategy}' for {file_name_str}",
        extra={
            'document_name': file_name_str,
            'selected_strategy': chunking_strategy,
            'confidence': report.recommendation.confidence,
            'alternatives': [r.strategy for r in report.strategy_results],
            'analysis_time_ms': report.analysis_time_ms
        }
    )
else:
    # Manual strategy selection
    logger.info(f"Using manual chunking strategy: {chunking_strategy}")
```

**Merge into document metadata:**
```python
parsed_metadata.update(analysis_metadata)
parsed_metadata['chunking_strategy'] = chunking_strategy
```

### **Phase 3: Pass Strategy to Chunking Service (1 hour)**

**Current:** Hardcoded to use recursive
**Needed:** Use selected strategy

**File:** `src/corpus_svc/app/processing/chunking.py`

**Add strategy parameter to chunk_text():**
```python
async def chunk_text(
    self,
    text: str,
    document_id: str,
    document_type: DocumentType,
    metadata: Optional[Dict[str, Any]] = None,
    chunking_strategy: str = 'recursive',  # NEW
    chunk_size: int = 512,                 # NEW
    chunk_overlap: int = 50,               # NEW
) -> List[ChunkCreate]:
```

**Route to correct strategy:**
```python
if chunking_strategy == "fixed_token":
    chunker = FixedTokenChunker(config=..., document_type=document_type)
elif chunking_strategy == "heading_aware":
    chunker = HeadingAwareChunker(config=..., document_type=document_type)
# ... etc for all 8 strategies
else:
    # Fallback to recursive
    chunker = RecursiveChunker(config=..., document_type=document_type)
```

---

## UI Enhancements

### **1. Chunking Analysis Page - Add Sample Size Control**

**Location:** Step 1 (Upload Document) in advanced options

**UI Component:**
```html
<mat-form-field appearance="outline">
    <mat-label>Analysis Sample Size</mat-label>
    <mat-select formControlName="sampleSize">
        <mat-option [value]="5000">Quick (5K tokens, ~10 sec)</mat-option>
        <mat-option [value]="10000">Standard (10K tokens, ~20 sec)</mat-option>
        <mat-option [value]="25000">Thorough (25K tokens, ~45 sec)</mat-option>
        <mat-option [value]="50000">Exhaustive (50K tokens, ~90 sec)</mat-option>
    </mat-select>
    <mat-hint>Larger samples = more accurate, slower analysis</mat-hint>
</mat-form-field>
```

**Default:** 10,000 tokens (current hardcoded value)

### **2. Upload Documents Page - Show What Happened**

**After upload with auto mode, show notification:**
```
✅ Document uploaded successfully!
   Auto-Detection Result: Heading Aware strategy selected (94% confidence)
   Reasoning: Document has clear hierarchical structure
   [View Details]
```

**In Document Library card:**
```
📊 12 chunks (heading_aware) ✨
    ↑             ↑           ↑
  count       strategy    auto-selected indicator
```

---

## Logging & Observability

### **Logs to Add**

**During Upload (Auto Mode):**
```
INFO: Starting auto-detection for document 'research_paper.pdf'
INFO: Extracting sample: 10000 tokens from 45000 total tokens
INFO: Analyzing document structure...
INFO: Structure signals: heading_density=0.18, table_ratio=0.02, list_ratio=0.05
INFO: Testing strategy 'sentence_paragraph' (1/5)...
INFO: Testing strategy 'fixed_token' (2/5)...
INFO: Testing strategy 'sliding_token' (3/5)...
INFO: Testing strategy 'heading_aware' (4/5)...
INFO: Testing strategy 'table_aware' (5/5)...
INFO: Strategy scores:
      - heading_aware: 0.94 (rank #1)
      - sentence_paragraph: 0.87 (rank #2)
      - fixed_token: 0.71 (rank #3)
      - sliding_token: 0.68 (rank #4)
      - table_aware: 0.45 (rank #5)
INFO: Auto-detection selected 'heading_aware' (confidence: 94%) for research_paper.pdf
INFO: Reasoning: High heading density (18%), clear hierarchical structure
INFO: Creating 12 chunks using heading_aware strategy
INFO: Chunks created: min=256 tokens, max=1024 tokens, avg=768 tokens
```

**Metrics to Track:**
- Auto-detection usage rate
- Average confidence scores
- Most frequently selected strategies
- Analysis time distribution
- User overrides (manual after auto)

---

## Collection-Level Defaults

### **Schema: Collections Table**

**New Fields:**

```python
class Collection(Base):
    # ... existing fields ...

    # Preflight/Auto-Detection Configuration
    preflight_sample_tokens: int = Column(
        Integer,
        default=10000,
        nullable=False,
        comment="Sample size for preflight analysis (tokens)"
    )
    preflight_strategies: ARRAY = Column(
        ARRAY(String),
        default=['sentence_paragraph', 'fixed_token', 'sliding_token', 'heading_aware', 'table_aware'],
        comment="Strategies to test during auto-detection"
    )
    auto_chunk_enabled: bool = Column(
        Boolean,
        default=True,
        comment="Enable auto-detection for this collection"
    )
    preferred_chunk_size: int | None = Column(
        Integer,
        nullable=True,
        comment="Preferred chunk size for this collection (overrides strategy default)"
    )
```

### **Collection Configuration UI**

**Location:** Collection Management page

**Fields to add:**
```
Auto-Detection Settings
├── Enable Auto-Detection: [✓] Enabled
├── Sample Size: [10000] tokens
│   Options: 5K (quick), 10K (standard), 25K (thorough), 50K (exhaustive)
├── Strategies to Test: [☑] All Core Strategies (5)
│   Advanced: Select specific strategies to test
└── Preferred Chunk Size: [512] tokens (optional override)
```

**Benefits:**
- Corpus managers tune analysis depth per document type
- Legal documents: Thorough analysis (25K tokens)
- News articles: Quick analysis (5K tokens)
- Technical manuals: Test heading-aware + table-aware only
- Consistent behavior across collection

---

## Implementation Plan

### **Sprint 1: Backend Integration (4 hours)**

**Tasks:**
1. Add `chunking_config` parameter to upload endpoint
2. Parse chunking_config from FormData
3. Implement auto-detection conditional logic
4. Integrate PreflightAnalyzer call
5. Store decision metadata
6. Pass selected strategy to chunking service
7. Add comprehensive logging

**Files:**
- `src/corpus_svc/app/routers/documents.py` (upload endpoint)
- `src/corpus_svc/app/services/ingestion_service.py` (pass strategy)
- `src/corpus_svc/app/processing/chunking.py` (accept strategy parameter)

**Tests:**
- Upload with strategy="auto" → Preflight runs
- Upload with strategy="heading_aware" → Uses that strategy
- Verify metadata includes decision details
- Check logs show tested strategies

### **Sprint 2: Collection Defaults (2 hours)**

**Tasks:**
1. Add migration for collection schema changes
2. Update Collection model and schemas
3. Add collection configuration UI
4. Use collection defaults during auto-detection
5. Validate sample_tokens range

**Files:**
- `src/corpus_svc/app/db/models.py` (Collection model)
- `src/corpus_svc/app/schemas/collections.py` (CollectionCreate/Update)
- Migration file: `002_add_preflight_defaults.sql`
- Frontend: Collection management page

### **Sprint 3: UI Enhancements (1 hour)**

**Tasks:**
1. Add sample size control to Chunking Analysis page
2. Show auto-detection results after upload
3. Add sparkle indicator for auto-selected strategies
4. Update tooltips with decision reasoning

**Files:**
- `src/frontend-angular/src/app/pages/documents/chunking-analysis/chunking-analysis.component.ts`
- `src/frontend-angular/src/app/pages/documents/document-upload.component.ts`
- `src/frontend-angular/src/app/pages/documents/document-library.component.ts`

### **Sprint 4: Testing & Documentation (1 hour)**

**Tasks:**
- End-to-end test: upload → auto-detect → verify strategy
- Performance test: measure analysis overhead
- Update API documentation
- Create user guide for auto mode
- Document collection configuration

---

## Performance Considerations

### **Analysis Overhead**

**Current upload time:** ~1-3 seconds
**With auto-detection:** +5-30 seconds (depending on sample size)

| Sample Size | Strategies | Estimated Time | Use Case |
|------------|------------|----------------|----------|
| 5,000 tokens | 5 core | +10-15 sec | Quick uploads, real-time |
| 10,000 tokens | 5 core | +15-25 sec | **Standard (recommended)** |
| 25,000 tokens | 7 strategies | +30-50 sec | Important documents |
| 50,000 tokens | 8 strategies | +60-90 sec | Critical optimization |

**Mitigation:**
- Async processing option (return immediately, process in background)
- Progress updates via WebSocket/SSE
- Cache analysis results for duplicate documents
- Parallel strategy testing (test 5 strategies simultaneously)

### **Optimization Ideas**

1. **Smart Caching:**
   ```python
   # If document with same checksum analyzed before, reuse results
   cache_key = f"preflight:{checksum}:{sample_size}"
   ```

2. **Parallel Testing:**
   ```python
   # Test strategies concurrently instead of sequentially
   results = await asyncio.gather(*[
       test_strategy(s) for s in strategies
   ])
   # Time: 30 sec → 6 sec (5x faster)
   ```

3. **Progressive Analysis:**
   ```python
   # Quick pass (3 strategies, 5sec) → If unclear, deeper pass
   if max_score - min_score < 0.15:  # Close scores
       # Run thorough analysis with more strategies
   ```

---

## Success Metrics

### **Adoption Metrics**
- % of uploads using auto mode vs manual
- Average confidence scores
- User override rate (selected auto, then changed)

### **Quality Metrics**
- Hit@K improvement: auto vs recursive baseline
- MRR improvement by strategy
- Zero-result rate reduction

### **Performance Metrics**
- Average analysis time by sample size
- 95th percentile analysis time
- Cache hit rate (duplicate documents)

### **User Satisfaction**
- NPS score from Corpus Managers
- Feature usage in Chunking Analysis page
- Helpfulness of decision reasoning

---

## Migration Path

### **Backward Compatibility**

**Existing documents:**
- Already use recursive strategy
- No metadata.chunking_strategy field
- UI shows "—" for missing strategy

**After implementation:**
- New uploads populate chunking_strategy
- Old documents show legacy behavior
- Optional: Bulk re-analysis tool to backfill

### **Feature Flags**

```python
# Environment variable
AUTO_CHUNKING_ENABLED = os.getenv("AUTO_CHUNKING_ENABLED", "true")

# Collection-level override
if not collection.auto_chunk_enabled:
    logger.info(f"Auto-chunking disabled for collection '{collection.name}'")
    chunking_strategy = collection.default_chunking_strategy or 'recursive'
```

### **Rollback Plan**

If auto-detection causes issues:
1. Set `AUTO_CHUNKING_ENABLED=false`
2. All uploads fall back to recursive
3. UI still shows "Auto" but uses fallback
4. No data loss, just strategy selection changes

---

## API Contract Changes

### **Request: POST /api/v1/documents/**

**New FormData field:**
```
chunking_config: JSON string (optional)
{
  "strategy": "auto" | "recursive" | "fixed_token" | ...,
  "chunk_size": 512,
  "chunk_overlap": 50,
  "preserve_whitespace": true,
  "respect_sentence_boundaries": true
}
```

### **Response: DocumentUploadResponse**

**Enhanced with:**
```json
{
  "document_id": "uuid...",
  "status": "completed",
  "message": "Document uploaded successfully",
  "chunking_details": {              // NEW
    "strategy_used": "heading_aware",
    "auto_selected": true,
    "confidence": 0.94,
    "alternatives_tested": 5,
    "analysis_time_ms": 2450
  }
}
```

---

## Security & Validation

### **Input Validation**

```python
# Validate sample_tokens range
if sample_tokens < 1000 or sample_tokens > 100000:
    raise HTTPException(
        status_code=400,
        detail="sample_tokens must be between 1,000 and 100,000"
    )

# Validate chunk_size
if chunk_size < 64 or chunk_size > 8192:
    raise HTTPException(
        status_code=400,
        detail="chunk_size must be between 64 and 8192"
    )

# Validate strategies list
valid_strategies = [s.value for s in ChunkingStrategy]
if not all(s in valid_strategies for s in strategies_to_test):
    raise HTTPException(
        status_code=400,
        detail=f"Invalid strategy. Valid: {valid_strategies}"
    )
```

### **Rate Limiting**

Preflight analysis is CPU-intensive:
```python
# Limit auto-detection requests per user
@limiter.limit("10/minute")
async def upload_document(...):
```

### **Timeout Protection**

```python
# Prevent runaway analysis
async with asyncio.timeout(60):  # 60 second max
    report = await analyzer.analyze(...)
```

---

## Documentation Updates

### **User-Facing**

1. **Upload Documents Guide**
   - Explain Auto-Detect mode
   - When to use vs manual
   - How to interpret confidence scores

2. **Chunking Optimization Guide**
   - How auto-detection works
   - Understanding strategy selection
   - Tuning collection defaults
   - When to use Analysis page vs Auto mode

### **Developer-Facing**

1. **API Documentation**
   - chunking_config parameter spec
   - Response schema with chunking_details
   - Example requests for each strategy

2. **Architecture Documentation**
   - Auto-detection flow diagram
   - Performance characteristics
   - Caching strategy

---

## Current Parameter Summary

### **What Exists Now (Preflight Service)**

| Parameter | Current Default | Range | Purpose |
|-----------|----------------|-------|---------|
| `max_sample_tokens` | 10,000 | 1K-100K | Text sample size for analysis |
| `strategies_to_test` | 5 core strategies | 1-8 strategies | Which strategies to benchmark |

**Strategies Tested by Default:**
1. sentence_paragraph
2. fixed_token
3. sliding_token
4. heading_aware
5. table_aware

**Not tested by default (expert):**
- semantic_adaptive
- page_block
- recursive (legacy)

---

## ✅ DECISION: Technical Sample Size Parameter

### **Parameter: `sample_size_tokens`**

**Selected Approach:** Technical token-based control (Option A)
**Rationale:** Direct control over analysis scope, precise configuration

**Type:** Integer
**Range:** 1,000 - 50,000 tokens
**Default:** 10,000 tokens
**Stored In:** Collection-level with global fallback

**UI Control:**
```html
<mat-form-field appearance="outline">
    <mat-label>Sample Size (tokens)</mat-label>
    <mat-select formControlName="sampleSizeTokens">
        <mat-option [value]="5000">5,000 tokens (~10-15 sec)</mat-option>
        <mat-option [value]="10000">10,000 tokens (~20-25 sec)</mat-option>
        <mat-option [value]="25000">25,000 tokens (~45-60 sec)</mat-option>
        <mat-option [value]="50000">50,000 tokens (~90-120 sec)</mat-option>
    </mat-select>
    <mat-hint>Amount of document text to analyze. Larger = more accurate but slower.</mat-hint>
</mat-form-field>
```

---

## ✅ DECISION: Collection-Level Storage

### **Storage Location: Collection Table**

**Selected Approach:** Per-collection configuration with global fallback
**Rationale:** Different document types need different analysis depth

**Schema Changes:**
```sql
ALTER TABLE collections
ADD COLUMN preflight_sample_tokens INTEGER DEFAULT 10000,
ADD COLUMN preflight_strategies TEXT[] DEFAULT ARRAY['sentence_paragraph', 'fixed_token', 'sliding_token', 'heading_aware', 'table_aware'],
ADD COLUMN auto_chunk_enabled BOOLEAN DEFAULT true;
```

**Recommended Defaults by Collection Type:**

| Collection Type | Sample Tokens | Strategies | Rationale |
|----------------|--------------|------------|-----------|
| Default (general) | 10,000 | 5 core | Balanced approach |
| Security docs | 25,000 | 7 (core+expert) | High accuracy needed |
| News/temp docs | 5,000 | 3 (sentence, fixed, sliding) | High volume, speed matters |
| Technical manuals | 25,000 | heading_aware, table_aware focus | Structured content |
| Legal documents | 50,000 | All 8 strategies | Critical accuracy |

**User Override:** Yes, in Chunking Analysis page advanced options

---

## ✅ DECISION: Async Processing with Progress

### **Processing Mode: Background/Async**

**Selected Approach:** Asynchronous with real-time progress updates
**Rationale:** Better UX, non-blocking, handles long analysis times

**Workflow:**
```
1. User clicks "Upload"
2. API returns immediately (202 Accepted)
   {
     "document_id": "uuid...",
     "status": "analyzing",
     "message": "Running auto-detection analysis..."
   }
3. Backend runs preflight in background
4. Progress updates via existing upload progress system
5. Final status update when complete
```

**Progress States:**
```
uploading (0-10%)     → File transfer
analyzing (10-40%)    → Running preflight analysis  ← NEW
  ├─ Testing strategy 1/5... (10-18%)
  ├─ Testing strategy 2/5... (18-26%)
  ├─ Testing strategy 3/5... (26-34%)
  ├─ Testing strategy 4/5... (34-42%)
  └─ Selecting optimal... (42-50%)
chunking (50-70%)     → Creating chunks with selected strategy
embedding (70-95%)    → Creating embeddings
completed (100%)      → Done
```

**UI Updates:**
```typescript
// DocumentUploadProgress interface enhancement
interface DocumentUploadProgress {
    documentId: string;
    filename: string;
    progress: number;
    status: 'uploading' | 'analyzing' | 'chunking' | 'embedding' | 'completed' | 'error';
    message?: string;
    current_strategy?: string;      // NEW: Which strategy being tested
    strategies_tested?: number;     // NEW: e.g., "3/5"
    selected_strategy?: string;     // NEW: Final selection
    confidence?: number;            // NEW: Confidence score
}
```

**Benefits:**
- Upload returns immediately (better perceived performance)
- Users can upload multiple files while analysis runs
- Clear progress feedback
- Can cancel long-running analysis
- Existing infrastructure (BackgroundTasks, progress tracking)

---

## ✅ DECISION: Configuration Caching

### **Cache Preflight Results**

**Decision:** Yes, cache for duplicate documents
**Cache Key:** `sha256(file_content) + sample_size_tokens`
**Cache Duration:** 7 days
**Storage:** Redis or in-memory LRU cache

**Logic:**
```python
cache_key = f"preflight:{checksum}:{sample_tokens}"
cached_result = await cache.get(cache_key)

if cached_result:
    logger.info(f"Using cached preflight results for {checksum}")
    return cached_result
else:
    result = await analyzer.analyze(...)
    await cache.set(cache_key, result, ttl=604800)  # 7 days
    return result
```

**Invalidation:**
- Time-based: 7 days
- Manual: When collection preflight settings change
- Clear cache endpoint for admins

---

**Ready to create formal feature spec and roadmap update once you confirm preferences!** 📋
