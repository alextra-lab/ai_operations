# ADR-045: Query Developer Tools Architecture

**Status:** ✅ IMPLEMENTED
**Date:** 2025-10-26
**Implementation Completed:** 2025-11-01
**Decision Makers:** Architecture Team
**Related:** ADR-012 (Hybrid CSS), ADR-023 (Sampling Presets), ADR-043 (Conversations as QUERY Pattern), LAYERED_PAGE_LAYOUT_PATTERN

## Implementation Summary

**Status:** ✅ ALL PHASES COMPLETE (P4-TOOLS-01 through P4-TOOLS-08)
**Timeline:** October 26 - November 1, 2025 (6 days)
**Total Effort:** ~24 days (distributed across features)

### Delivered Features

| Phase | Feature | Status | Completion Date | Tests | Coverage |
|-------|---------|--------|----------------|-------|----------|
| **P4-TOOLS-01** | Shared Components | ✅ COMPLETE | Oct 30, 2025 | - | - |
| **P4-TOOLS-02** | Semantic Search Enhancement | ✅ COMPLETE | Oct 30, 2025 | - | - |
| **P4-TOOLS-03** | RAG Q&A Enhancement | ✅ COMPLETE | Oct 31, 2025 | 35 | 80%+ |
| **P4-TOOLS-04** | Unified Interface | ✅ COMPLETE | Oct 31, 2025 | 45 | 93%+ |
| **P4-TOOLS-05** | Parameter Injection | ✅ COMPLETE | Oct 31, 2025 | 26 | - |
| **P4-TOOLS-06** | UC Execution Refactor | ✅ COMPLETE | Oct 31, 2025 | 56 | 93%+ |
| **P4-TOOLS-07** | Metrics Dashboard | ✅ COMPLETE | Nov 1, 2025 | 79 | 88%+ |
| **P4-TOOLS-08** | Testing & Documentation | ✅ COMPLETE | Nov 1, 2025 | 28 | 92.75% |

**Total Tests:** 269 tests passing
**Average Coverage:** 89.4%
**User Guide:** 800+ lines comprehensive documentation

### Key Deliverables

**Frontend Components (Reusable):**

- ✅ `QueryResultsPanelComponent` - 28 tests, 92.75% coverage
- ✅ `ParameterConfigPanelComponent` - Full parameter controls
- ✅ `MetricsDashboardComponent` - 3 chart types, recommendations
- ✅ `StructuredOutputRendererComponent` - 4 visualizers
- ✅ `AutoScrollService` - Smart streaming behavior
- ✅ `EnterToExecuteDirective` - Keyboard shortcuts
- ✅ `UseCaseSelectorDialogComponent` - Parameter injection workflow

**Pages & Tabs:**

- ✅ `QueryDeveloperToolsComponent` - Unified interface with 3 tabs
- ✅ `SemanticSearchTabComponent` - VectorDB-only testing
- ✅ `RagQaTabComponent` - Full RAG pipeline testing
- ✅ `UseCaseTesterTabComponent` - Placeholder for Phase 5

**Services:**

- ✅ `SharedConfigService` - Cross-tab state (18 tests)
- ✅ `MetricsService` - Analytics and recommendations

**Documentation:**

- ✅ `QUERY_DEVELOPER_TOOLS.md` - 800+ line comprehensive user guide
- ✅ `ADR-045` - This architecture decision record
- ✅ API documentation updates (parameter injection metadata)

### Architecture Compliance

- ✅ **ADR-012** - Hybrid CSS (Material + Tailwind + SCSS)
- ✅ **ADR-023** - Sampling Presets (STRICT/BALANCED/CREATIVE/CUSTOM)
- ✅ **ADR-043** - Conversations as QUERY Pattern
- ✅ **WCAG 2.1 AA** - Accessibility compliant
- ✅ **OnPush Change Detection** - Performance optimized

---

## Context

### Problem Statement

Current implementation has three separate tools for query testing and tuning:

1. **Semantic Search** (`/query/semantic-search`) - Test vector retrieval
2. **RAG Q&A** (`/query/rag-qa`) - Test RAG pipeline with LLM
3. **Use Case Execution** (`/use-cases/execute/:id`) - Execute configured Use Cases

**Issues with Current State:**

1. **Fragmented Developer Experience**
   - Three separate pages with inconsistent UX
   - No way to compare configurations side-by-side
   - Parameters discovered in testing can't be applied to Use Cases
   - Each page reinvents similar controls

2. **Missing Iterative Development Workflow**
   - Use Case wizard requires knowing all parameters upfront
   - No "test → tune → apply" workflow
   - Developers must guess optimal parameters
   - No way to validate changes before publishing

3. **Limited Parameter Exposure**
   - UI doesn't expose configurable parameters (top_k, similarity_threshold, sampling presets)
   - Backend supports parameter overrides via `context` dictionary (see `FUTURE_FEATURE_PARAMETER_CONFIGURATION.md`)
   - No guidance on ADR-023 sampling presets
   - Vector DB tuning parameters (ef_search, collections) not accessible

4. **Inconsistent Layout Patterns**
   - Semantic Search and RAG Q&A use Layered Layout but with variations
   - Action buttons in Layer 2 (controls) instead of Layer 4 (footer)
   - No collapsible controls pattern
   - Use Case Execution uses outdated tab-based layout

5. **No Metrics-Driven Optimization**
   - Metrics exist (ExecutionMetrics schema) but not surfaced for tuning
   - No repeatability testing
   - No parameter recommendations based on results
   - No cost/performance trade-off visibility

### User Needs

**Use Case Developers (corpus_admin, use_case_publisher):**

- Test RAG configurations before committing to Use Case
- Tune parameters iteratively with live feedback
- Apply discovered parameters to draft Use Cases
- Compare different configurations side-by-side

**Corpus Administrators:**

- Verify semantic search after uploading documents
- Test collection health and chunking strategies
- Evaluate similarity thresholds for different document types
- Validate vector DB performance

**System Administrators:**

- Benchmark query performance
- Test sampling presets (ADR-023)
- Evaluate model selection trade-offs
- Monitor token usage projections

---

## Decision

We implement a **unified Query Developer Tools** interface that consolidates semantic search, RAG Q&A, and Use Case testing into a single, cohesive developer experience with parameter injection workflow.

### 1. Unified Interface Architecture

**Single Page with Tabs:**

```
/dev/query-tools

Tabs:
  [Semantic Search] - Vector retrieval testing
  [RAG Q&A]         - Full RAG pipeline testing
  [Use Case Tester] - Test with Use Case context
```

**Why Tabs Over Separate Pages:**

- Shared configuration state (model, parameters)
- Easy comparison between retrieval-only vs full RAG
- Single entry point for all query development
- Consistent parameter panel across tabs

### 2. Enhanced Layered Page Layout

**Implementation of 4-Layer Pattern:**

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: APP HEADER (main layout)                       │
├─────────────────────────────────────────────────────────┤
│ Layer 2: PAGE HEADER + CONTROLS (collapsible, compact) │
│ • Page title + tabs                                     │
│ • Collapsible configuration panel:                      │
│   - Model selector                                      │
│   - Sampling preset (ADR-023)                           │
│   - RAG parameters (top_k, threshold)                   │
│   - Vector DB settings (collections, ef_search)         │
│   - Query input with Enter-to-execute                   │
├─────────────────────────────────────────────────────────┤
│ Layer 3: CONTENT AREA (scrollable, maximum space)      │
│ • Conversation-style results display                    │
│ • Auto-scroll on streaming responses                    │
│ • Metrics cards                                         │
│ • Source citations with similarity scores               │
├─────────────────────────────────────────────────────────┤
│ Layer 4: PAGE FOOTER (fixed, thin, always visible)     │
│ • [Execute] [Reset] [Export Config] buttons            │
│ • [Apply to Use Case] dropdown                          │
│ • [✓ Enter to Execute] checkbox                         │
│ • Status: Last execution time, tokens used              │
└─────────────────────────────────────────────────────────┘
```

### 2.a Mode-Aware Reuse (No Overreach)

Reusable components MUST adapt by mode rather than forcing unrelated
controls into a page:

- ParameterConfigPanelComponent
  - mode="semantic": VectorDB-only controls. Hide LLM model/sampling entirely.
  - mode="rag": Show VectorDB + LLM model + sampling + prompts.
  - mode="usecase": UC-centric overrides only.

- QueryResultsPanelComponent: Single conversation-style renderer reused for
  RAG Q&A, Conversations, and Use Case Execution (streaming, sources, metrics).

Rule: Reuse when the semantics match; otherwise adapt via inputs/slots/mode.

**Key Enhancements:**

1. **Collapsible Layer 2**
   - Configuration panel can be collapsed to maximize results space
   - Tighter spacing (12px padding instead of 20px+)
   - Grid layout for parameter controls
   - Auto-expand when parameters invalid

2. **Layer 4 Footer** (NEW)
   - Fixed to bottom, always visible (64px height)
   - Primary actions immediately accessible
   - Status information visible without scrolling
   - Replaces action buttons in Layer 2

3. **Auto-Scroll Streaming**
   - Scroll to latest message when streaming starts
   - Continue auto-scrolling as chunks arrive
   - Stop if user scrolls up (reading previous content)
   - Resume when user scrolls back to bottom

4. **Enter-to-Execute**
   - Enter key executes query (Shift+Enter for newline)
   - Toggleable with checkbox (preference saved to localStorage)
   - Visual hint shows current behavior
   - Disabled during execution

### 3. Parameter Configuration System

**Expose All Tunable Parameters:**

#### A. Model Configuration

```typescript
interface ModelConfig {
  llm_model: string;           // Dropdown from model registry
  embedding_model: string;     // System default or override
  sampling_preset: SamplingPreset; // strict | balanced | creative | custom
  temperature?: number;        // Only if preset = custom
  max_tokens?: number;
  top_p?: number;
}
```

Note: Model configuration is NOT displayed in mode="semantic".

#### B. RAG Parameters

```typescript
interface RAGParams {
  enabled: boolean;
  vector_collections: string[];  // Multi-select from available collections
  top_k: number;                 // Slider: 1-100, default 10
  similarity_threshold: number;  // Slider: 0.0-1.0, default 0.6
  hybrid_bm25: boolean;          // Checkbox
}
```

#### C. Vector DB Settings (Advanced)

```typescript
interface VectorDBSettings {
  ef_search: number;             // HNSW search quality (default 128)
  distance_metric: string;       // COSINE | EUCLIDEAN | DOT_PRODUCT
  score_normalization: boolean;  // Normalize across collections
}
```

**UI Organization:**

- Basic params visible by default
- Advanced settings in collapsible expansion panel
- Preset recommendations shown for each tab
- Warnings for high-entropy configurations (ADR-023)

### 4. Parameter Injection Workflow

**Core Feature: Apply discovered parameters to Use Cases**

#### Workflow Options

**Option 1: Update Existing Draft**

```
1. User tests parameters in Query Developer Tools
2. Clicks "Apply to Use Case" → "Update Existing Draft"
3. Dropdown shows user's draft Use Cases (filtered)
4. Parameters injected into selected draft
5. User can navigate to wizard to review/publish
```

**Option 2: Clone & Apply**

```
1. User selects published Use Case from dropdown
2. System prompts: "Clone to draft to modify?"
3. Backend clones UC → injects parameters → returns draft
4. User reviews in wizard → submits for review
```

**Option 3: Create New Use Case**

```
1. Click "Create New Use Case"
2. Opens wizard with pre-filled:
   - Model configuration
   - RAG parameters
   - Sampling preset
   - System prompt (from test queries)
3. User completes required fields → saves draft
```

#### Permission Model

```python
def can_inject_parameters(user: TokenPayload, use_case: UseCase) -> bool:
    """Permission check for parameter injection."""
    # Must have corpus_admin or admin role
    if user.role not in ["admin", "corpus_admin", "use_case_publisher"]:
        return False

    # Can only update DRAFT use cases
    if use_case.lifecycle_state != "draft":
        return False

    # Must be creator (or admin override)
    if use_case.created_by_user_id != user.user_id and user.role != "admin":
        return False

    return True
```

**Security Constraints:**

- ✅ Can inject into own draft Use Cases
- ✅ Can clone any published UC, then inject into draft clone
- ❌ Cannot modify published Use Cases directly (architectural protection)
- ✅ Audit trail records parameter source and tuner

### 5. Reusable Components

**Share Code Across Features:**

#### A. QueryResultsPanelComponent

```typescript
// Reuses conversation UI from thread-detail.component
@Component({
  selector: 'app-query-results-panel',
  // Message bubbles, streaming, LLMContentRenderer
})
export class QueryResultsPanelComponent {
  @Input() messages: Message[];
  @Input() sources: SourceMetadata[];
  @Input() metrics: ExecutionMetrics;
  @Input() autoScroll: boolean = true;
}
```

#### B. ParameterConfigPanelComponent

```typescript
// Shared configuration panel
@Component({
  selector: 'app-parameter-config-panel',
  // Model, sampling, RAG, vector DB controls
})
export class ParameterConfigPanelComponent {
  @Input() showAdvanced: boolean = false;
  @Output() configChanged = new EventEmitter<QueryConfig>();
}
```

#### C. AutoScrollService

```typescript
// Manages auto-scroll behavior during streaming
@Injectable()
export class AutoScrollService {
  handleStreamingStart(container: ElementRef): void;
  handleStreamingChunk(container: ElementRef): void;
  detectUserScroll(container: ElementRef): boolean;
}
```

### 6. Use Case Execution Modernization

**Align with Query Developer Tools Pattern:**

- Remove tab-based layout
- Apply Layered Layout with Layer 4 footer
- Reuse QueryResultsPanelComponent
- Add structured output renderer for configured formats
- Showcase: "This is what configured output looks like"

**Before:**

```
[Inputs Tab] [Results Tab] [Metrics Tab] [Sources Tab]
```

### 7. Navigation & IA

- Create a top-level "Developer Tools" area ("/dev/query-tools"). Retire
  legacy "Query Interface" entry points and redirect to Developer Tools.
- Semantic Search appears once (under Developer Tools) with role-aware UI:
  - UC Developer: show "Apply to Use Case", prompt helpers, export config.
  - Corpus Admin: show corpus health links and collection shortcuts.
- Admin pages can deep-link into Semantic Search with pre-filled params
  (collection, top_k, threshold) instead of duplicating pages.

**After:**

```
┌─────────────────────────────────────────────────────┐
│ Layer 2: Use Case selector + input parameters      │
├─────────────────────────────────────────────────────┤
│ Layer 3: Results (conversation-style, scrollable)  │
│  • Structured output renderer                      │
│  • Sources with citations                          │
│  • Metrics inline                                  │
├─────────────────────────────────────────────────────┤
│ Layer 4: [Execute] [Reset] [Export] actions        │
└─────────────────────────────────────────────────────┘
```

---

## Consequences

### Positive

✅ **Unified Developer Experience**

- Single entry point for all query development
- Consistent UX across semantic search, RAG, and UC testing
- Shared configuration state reduces context switching

✅ **Iterative Use Case Development**

- Test → tune → apply workflow finally implemented
- Developers can validate before publishing
- Reduces trial-and-error cycles
- Lower barrier to entry for UC development

✅ **Parameter Transparency**

- All tunable parameters exposed in UI
- Backend's `context` override support fully utilized
- ADR-023 sampling presets properly surfaced
- Vector DB tuning accessible to advanced users

✅ **Metrics-Driven Optimization**

- Performance stats visible during testing
- Repeatability testing possible
- Cost projections available
- Parameter recommendations based on actual results

✅ **Code Reuse**

- Conversation UI components shared
- Auto-scroll logic centralized
- Parameter panel reusable across features
- Reduced duplication

✅ **Enterprise Governance**

- Permission model respects lifecycle states
- Audit trail for parameter changes
- Published UCs protected from direct modification
- Clone-based evolution workflow

### Negative

⚠️ **Initial Development Effort**

- Significant refactoring of existing pages
- New parameter injection workflow
- Permission logic complexity
- Auto-scroll implementation

⚠️ **Migration Complexity**

- Users familiar with separate pages
- Need documentation and training
- Navigation structure changes
- Bookmarks may break

⚠️ **Permission Edge Cases**

- "Why can't I update this UC?" confusion
- Clone workflow may not be obvious
- Need clear error messages and guidance

### Mitigations

**Development Phasing:**

1. Build shared components first (reduce duplication)
2. Refactor existing pages to use shared components
3. Add unified interface with tabs
4. Add parameter injection last (depends on previous)

**User Communication:**

- Update documentation with new workflow
- Add in-app help tooltips
- Clear error messages for permission issues
- Migration guide for existing workflows

**Permission Clarity:**

- Show permission requirements in UI
- Explain why UC is read-only
- Offer "Clone to Edit" button prominently
- Visual indicators for draft vs published

---

## Implementation Plan

### Phase 1: Shared Components (4-5 days)

**P4-TOOLS-01: Core Shared Components**

**Deliverables:**

- QueryResultsPanelComponent (reuse conversation UI)
- ParameterConfigPanelComponent (collapsible, with all params)
- AutoScrollService (streaming auto-scroll logic)
- EnterToExecuteDirective (keyboard handler)
- Layer 4 footer pattern implementation
- Unit tests (80%+ coverage)

**Technical Decisions:**

- Use Material Expansion Panels for collapsible controls
- localStorage for user preferences (enter-to-execute, collapsed state)
- RxJS for auto-scroll event handling
- Shared CSS in component styles (not global)

---

### Phase 2: Refactor Existing Pages (4 days)

**P4-TOOLS-02: Semantic Search Enhancement**

**Deliverables:**

- Add parameter controls (top_k, threshold, collections, ef_search)
- Implement Layer 4 footer with actions
- Add collapsible configuration panel
- Integrate AutoScrollService
- Export configuration button
- Unit tests

**P4-TOOLS-03: RAG Q&A Enhancement** ✅ COMPLETE (Oct 31, 2025)

**Deliverables:**

- ✅ Add sampling preset selector (ADR-023)
- ✅ Add LLM parameter overrides (temperature, top_p, max_tokens)
- ✅ Show high-entropy warnings
- ✅ Implement Layer 4 footer
- ✅ Add model selection from registry
- ✅ Unit tests (35 tests, 80%+ coverage)
- ✅ Configuration export functionality

---

### Phase 3: Unified Interface (3 days)

**P4-TOOLS-04: Query Developer Tools Page**

**Deliverables:**

- New `/dev/query-tools` route
- Tab interface (Semantic Search, RAG Q&A, Use Case Tester)
- Shared configuration state across tabs
- Navigation updates
- Integration with existing refactored pages
- Documentation

---

### Phase 4: Parameter Injection (4-5 days)

**P4-TOOLS-05: Use Case Parameter Injection**

**Deliverables:**

- "Apply to Use Case" dropdown in Layer 4
- Use Case selector dialog with smart filtering
- Permission checker service
- Update draft workflow (direct injection)
- Clone & apply workflow (for published UCs)
- Create new UC workflow (pre-fill wizard)
- Parameter diff viewer
- Backend permission validation updates
- Audit trail metadata
- Integration tests

**Backend Changes:**

```python
# Add metadata fields for parameter tracking
use_case.metadata = {
    "parameter_source": "query_developer_tools",
    "tuned_by_user_id": "...",
    "tuned_at": "2025-10-26T...",
    "source_test_queries": ["query1", "query2"]
}

# Enhanced permission check
def can_update_use_case(user, use_case):
    # Existing checks + parameter injection validation
```

---

### Phase 5: UC Execution Modernization (3 days)

**P4-TOOLS-06: Use Case Execution Refactor**

**Deliverables:**

- Remove tab-based layout
- Apply Layered Layout (Layers 2-4)
- Reuse QueryResultsPanelComponent
- Add structured output renderer
- Layer 4 footer with actions
- Integration tests

---

### Phase 6: Advanced Features (3-4 days)

**P4-TOOLS-07: Metrics & Testing Dashboard**

**Deliverables:**

- Metrics summary panel (expandable)
- Performance charts (latency, tokens over time)
- Consistency score calculator (repeatability)
- Cost projection calculator
- Parameter recommendations based on metrics
- Export metrics as CSV/JSON
- Repeatability test runner (run same query N times)

---

### Phase 7: Testing & Documentation (3-4 days)

**P4-TOOLS-08: Testing & Documentation**

**Deliverables:**

- Unit tests for all new components (80%+ coverage)
- Integration tests for workflows (E2E)
- Accessibility testing (WCAG 2.1 AA)
- Update LAYERED_PAGE_LAYOUT_PATTERN.md:
  - Collapsible Layer 2 example
  - Layer 4 footer pattern
  - Auto-scroll streaming pattern
- Create user guide: "Query Developer Tools"
- Update UI_DEVELOPMENT_PLAN.md
- API documentation updates
- Migration guide for users

---

## Total Effort Estimate

| Phase | Days | Model | Status |
|-------|------|-------|--------|
| P4-TOOLS-01: Shared Components | 4-5 | 🟣 Claude 4.5 | ✅ COMPLETE |
| P4-TOOLS-02: Semantic Search | 2 | 🔵 Auto | ✅ COMPLETE |
| P4-TOOLS-03: RAG Q&A | 2 | 🔵 Auto | ✅ COMPLETE |
| P4-TOOLS-04: Unified Interface | 3 | 🔵 Auto | 📋 PLANNED |
| P4-TOOLS-05: Parameter Injection | 4-5 | 🟣 Claude 4.5 | 📋 PLANNED |
| P4-TOOLS-06: UC Execution Refactor | 3 | 🔵 Auto | 📋 PLANNED |
| P4-TOOLS-07: Metrics Dashboard | 3-4 | 🔵 Auto | 📋 PLANNED |
| P4-TOOLS-08: Testing & Docs | 3-4 | 🔵 Auto | 📋 PLANNED |
| **TOTAL** | **24-30 days** | **30% Reasoning / 70% Auto** | **3/8 Complete** |

**Reasoning Model Days:** 8-10 days (~33%)
**Auto Days:** 16-20 days (~67%)

---

## Alternative Considered

### Option A: Keep Separate Pages, Add Parameters

**Not chosen because:**

- Fragmented experience persists
- Duplicate parameter controls across 3 pages
- No shared configuration state
- Harder to compare configurations

### Option B: Single Page, No Tabs

**Not chosen because:**

- Too much complexity on one screen
- Semantic-only users forced to see RAG controls
- Harder to focus on specific testing scenario

### Option C: Parameter Injection to Published UCs

**Not chosen because:**

- Violates ADR-018 (Use Case immutability)
- Breaks audit trail
- Risk of breaking production UCs
- Clone workflow provides safer evolution path

---

## Acceptance Criteria

- [ ] Query Developer Tools page created at `/dev/query-tools`
- [ ] Three tabs functional: Semantic Search, RAG Q&A, Use Case Tester
- [ ] All tunable parameters exposed in UI
- [ ] Sampling presets (ADR-023) properly implemented
- [ ] Layer 4 footer pattern established and documented
- [ ] Auto-scroll during streaming responses works
- [ ] Enter-to-execute with Shift+Enter override
- [ ] "Apply to Use Case" workflow implemented:
  - [ ] Update existing draft
  - [ ] Clone & apply to published UC
  - [ ] Create new UC from config
- [ ] Permission checks enforce draft-only modification
- [ ] Audit trail records parameter source
- [ ] QueryResultsPanelComponent reusable across features
- [ ] Use Case Execution modernized to match pattern
- [ ] Documentation updated (LAYERED_PAGE_LAYOUT_PATTERN.md, user guides)
- [ ] 80%+ test coverage for new components
- [ ] WCAG 2.1 AA accessibility compliance
- [ ] Integration tests cover all workflows

---

## References

- **ADR-012:** Hybrid CSS Strategy (Material + Tailwind + Component SCSS)
- **ADR-023:** Sampling Presets and Guardrails
- **ADR-043:** Conversations as QUERY Pattern
- **ADR-018:** Use Case Owned Architecture (immutability)
- **ADR-020:** Use Case Publisher Role (permissions)
- **ADR-041:** Role-Based Use Case Permissions
- **LAYERED_PAGE_LAYOUT_PATTERN.md:** Layout guidelines
- **FUTURE_FEATURE_PARAMETER_CONFIGURATION.md:** Backend parameter support
- **Thread Detail Component:** `src/frontend-angular/src/app/pages/conversations/thread-detail.component.ts`
- **Use Case Wizard:** `src/frontend-angular/src/app/pages/use-cases/use-case-wizard.component.ts`

---

## Future Enhancements

**Phase 8+ (Future):**

1. **A/B Testing Framework**
   - Compare two configurations side-by-side
   - Statistical significance testing
   - Visual diff of results

2. **Saved Test Suites**
   - Save query + config combinations
   - Run as regression tests
   - Benchmark against baselines

3. **Model Comparison**
   - Test same query across multiple models
   - Cost vs quality trade-off analysis
   - Automatic model recommendation

4. **Collaborative Tuning**
   - Share configurations with team
   - Comment on parameter choices
   - Approval workflow for parameter changes

5. **Adaptive Parameter Suggestions**
   - ML-driven parameter recommendations
   - Learn from successful queries
   - Auto-tune based on metrics

---

**Status:** ✅ ACCEPTED
**Implementation Start:** Phase 4 (November 2025)
**Priority:** High (critical for Use Case development workflow)
**Effort:** 24-30 days
**Risk:** Medium (significant refactoring, new patterns)
