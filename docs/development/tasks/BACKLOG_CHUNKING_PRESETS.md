# Backlog: Chunking Presets Feature

**Status:** ⏸️ DEFERRED
**Priority:** Low
**Phase:** P7+ (Post-MVP)
**Created:** November 30, 2025
**Source:** P6-STAB-01 UI Walkthrough Assessment

---

## Summary

Implement user-saved chunking configuration presets in corpus_svc. Currently, the orchestrator proxy routes and frontend UI exist but the backend implementation is missing.

---

## Background

### Why Deferred

The **auto-chunking workflow** (`PreflightAnalyzer`) is the primary feature and is **fully implemented**:

- Dynamically benchmarks 5+ chunking strategies per document
- Analyzes document structure (headings, tables, code blocks, equations)
- Recommends optimal strategy with confidence score
- Collection-level preflight settings supported

**Chunking Presets** are a **convenience/power-user feature** for:

- Skipping preflight analysis for known document types
- Batch processing with consistent settings
- Team-shared configurations

### Current State

| Layer | Status |
|-------|--------|
| Frontend UI (`chunking-analysis.component.ts`) | ✅ Button exists, shows "coming soon" |
| Frontend Service (`preflight.service.ts`) | ✅ Methods implemented |
| Frontend Models (`preflight.models.ts`) | ✅ `ChunkingPreset` interface defined |
| Orchestrator Proxy (`chunking.py`) | ✅ Proxy routes to corpus_svc |
| Unit Tests (`test_chunking_router.py`) | ✅ Tests exist |
| **Corpus Service** | ❌ **NOT IMPLEMENTED** |

### Graceful Degradation

The frontend handles the missing endpoint gracefully:

- `savePreset()` shows snackbar: "Save preset feature coming soon"
- `getPresets()` catches 404 and returns empty array
- No user-facing errors

---

## Requirements

### Data Model

```typescript
interface ChunkingPreset {
  id: string;           // UUID
  name: string;         // e.g., "Legal Documents - High Precision"
  description?: string;
  config: {
    strategy: ChunkingStrategy;
    chunk_size?: number;
    chunk_overlap?: number;
    heading_levels?: number[];
    min_chunk_size?: number;
    max_chunk_size?: number;
    preserve_whitespace?: boolean;
    respect_sentence_boundaries?: boolean;
  };
  created_by: string;   // User ID
  created_at: string;
  updated_at: string;
  usage_count: number;
  is_shared: boolean;   // Team-visible vs personal
}
```

### API Endpoints (in corpus_svc)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chunking/presets` | Create preset |
| GET | `/api/v1/chunking/presets` | List presets (user's + shared) |
| GET | `/api/v1/chunking/presets/{id}` | Get preset by ID |
| PUT | `/api/v1/chunking/presets/{id}` | Update preset |
| DELETE | `/api/v1/chunking/presets/{id}` | Delete preset |

### Database Schema

```sql
CREATE TABLE chunking_presets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    config JSONB NOT NULL,
    created_by UUID NOT NULL REFERENCES users(id),
    is_shared BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_chunking_presets_created_by ON chunking_presets(created_by);
CREATE INDEX idx_chunking_presets_shared ON chunking_presets(is_shared) WHERE is_shared = TRUE;
```

---

## Implementation Tasks

### Phase 1: Backend (corpus_svc)

1. [ ] Create `ChunkingPreset` SQLAlchemy model
2. [ ] Create `chunking_presets` table migration
3. [ ] Create `ChunkingPresetRepository` with CRUD operations
4. [ ] Add routes to `corpus_svc/app/routers/chunking.py`
5. [ ] Add user ownership/sharing logic

### Phase 2: Integration

6. [ ] Verify orchestrator proxy routes work
7. [ ] Update frontend to remove "coming soon" message
8. [ ] Add preset selection to document upload flow

### Phase 3: Enhancement (Optional)

9. [ ] Add "Apply preset" to preflight results
10. [ ] Add preset usage analytics
11. [ ] Add preset import/export

---

## Effort Estimate

| Task | Effort |
|------|--------|
| Database schema + model | 0.5 day |
| Repository + routes | 1 day |
| Integration testing | 0.5 day |
| Frontend updates | 0.5 day |
| **Total** | **2-3 days** |

---

## Files to Modify

### Corpus Service (New)

- `src/corpus_svc/app/db/models/chunking_preset.py`
- `src/corpus_svc/app/repositories/chunking_preset_repository.py`
- `src/corpus_svc/app/schemas/chunking_preset.py`
- `scripts/migrations/XXX_add_chunking_presets.sql`

### Corpus Service (Modify)

- `src/corpus_svc/app/routers/chunking.py` - Add preset routes

### Frontend (Modify)

- `src/frontend-angular/src/app/pages/documents/chunking-analysis/chunking-analysis.component.ts` - Remove "coming soon"

---

## Acceptance Criteria

- [ ] User can save current chunking configuration as a named preset
- [ ] User can list their presets and shared team presets
- [ ] User can apply a preset to skip preflight analysis
- [ ] User can delete their own presets
- [ ] Usage count tracked for analytics
- [ ] Existing auto-chunking workflow unaffected

---

## References

- Session: `docs/development/sessions/2025-11-30-p6-stab-01-ui-walkthrough.md`
- Frontend Model: `src/frontend-angular/src/app/api/models/preflight.models.ts`
- Orchestrator Proxy: `src/orchestrator/app/routers/chunking.py` (lines 234-296)
- Auto-chunking: `src/corpus_svc/app/services/preflight_service.py`

---

**Note:** This feature should only be prioritized if users request it. The auto-chunking workflow handles most use cases.
