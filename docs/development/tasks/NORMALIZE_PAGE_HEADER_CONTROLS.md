# Task: Normalize Page Header + Controls Across All Pages

**Task ID:** NORMALIZE-LAYER2-001
**Status:** 📋 DEFERRED (Phase 6)
**Priority:** Medium
**Estimated Effort:** 8-12 hours
**Created:** 2025-10-19
**Updated:** 2025-10-25
**Phase Assignment:** Phase 6 - Performance & Production
**Assignee:** TBD

---

## Objective

Normalize the **Layer 2 (Page Header + Controls)** section across all pages in the AI Operations Platform application to ensure:

- ✅ **Visual consistency** across all user-facing pages
- ✅ **Predictable UX** - users know where to find controls
- ✅ **ADR-012 compliance** - proper use of Material + Tailwind + SCSS
- ✅ **Accessibility** - WCAG 2.1 AA compliance

---

## Background

**Current Problem:**

- Layer 2 implementations are **inconsistent** across pages
- Different control layouts, spacing, and styling
- Unpredictable user experience
- Accessibility issues in some implementations

**Reference Documentation:**

- 📄 **Pattern Guide:** `docs/development/guidelines/PAGE_HEADER_CONTROLS_STANDARD.md`
- 📄 **Layout Guide:** `docs/development/guidelines/LAYERED_PAGE_LAYOUT_PATTERN.md`
- 📄 **ADR-012:** Hybrid CSS Strategy

**Reference Implementations (Already Compliant):**

- ✅ **Use Cases Page:** `src/frontend-angular/src/app/pages/use-case-menu/`
- ✅ **Pattern Library:** `src/frontend-angular/src/app/pages/patterns/`

---

## Scope

### Pages Requiring Normalization

#### 🔴 **High Priority** (Complete First)

| # | Page | Path | Type | Current Issues |
|---|------|------|------|----------------|
| 1 | RAG Q&A System | `src/frontend-angular/src/app/pages/query/rag-qa.component.*` | Query/Search | Non-standard controls layout |
| 2 | Query History | `src/frontend-angular/src/app/pages/query/query-history.component.*` | Query/Search | Non-standard controls layout |
| 3 | Thread List | `src/frontend-angular/src/app/pages/conversations/thread-list.component.*` | List/Grid | Missing standard header structure |
| 4 | My Use Cases | `src/frontend-angular/src/app/pages/use-cases/use-case-list.component.*` | List/Grid | Verify compliance |

#### 🟡 **Medium Priority** (Complete Second)

| # | Page | Path | Type | Current Issues |
|---|------|------|------|----------------|
| 5 | Use Case Wizard | `src/frontend-angular/src/app/pages/use-cases/use-case-wizard.component.*` | Detail/Form | Header needs restructuring |
| 6 | Use Case Execution | `src/frontend-angular/src/app/pages/use-case-execution/use-case-execution.component.*` | Detail/Form | Header needs restructuring |
| 7 | Thread Detail | `src/frontend-angular/src/app/pages/conversations/thread-detail.component.*` | Detail/Form | Verify compliance |
| 8 | Document Management | `src/frontend-angular/src/app/pages/documents/document-list.component.*` | List/Grid | Missing standard header |

#### 🟢 **Low Priority** (Complete Last)

| # | Page | Path | Type | Current Issues |
|---|------|------|------|----------------|
| 9 | SOC Dashboard | `src/frontend-angular/src/app/pages/dashboard/soc-dashboard.component.*` | Dashboard | Custom layout acceptable |
| 10 | Analytics | `src/frontend-angular/src/app/pages/analytics/` | Dashboard | Custom layout acceptable |
| 11 | Admin Pages | `src/frontend-angular/src/app/pages/admin/` | Various | Low traffic pages |

---

## Implementation Steps

### Step 1: Audit Current State (1 hour)

```bash
# Navigate to frontend directory
cd src/frontend-angular/src/app/pages

# List all page components
find . -name "*.component.html" -o -name "*.component.ts" | sort

# For each page, document:
# 1. Current header structure
# 2. Current controls layout
# 3. Issues identified
# 4. Page type classification
```

**Output:** Create a spreadsheet or markdown table with audit results.

### Step 2: Normalize High Priority Pages (4-6 hours)

For **each high-priority page**, follow this workflow:

#### A. Backup Current Implementation

```bash
# Create backup branch
git checkout -b normalize-layer2-[page-name]

# Copy current files to backup
cp [component].html [component].html.backup
cp [component].scss [component].scss.backup
cp [component].ts [component].ts.backup
```

#### B. Update HTML Structure

**Before:** (Example - RAG Q&A)

```html
<div class="rag-qa-container">
    <h1>RAG Q&A System</h1>
    <p>Ask questions...</p>

    <div class="model-selection">
        <mat-form-field>
            <mat-label>Select Model</mat-label>
            <mat-select>...</mat-select>
        </mat-form-field>
    </div>

    <div class="query-history">
        <input type="text" placeholder="Search queries">
        <!-- filters -->
    </div>
</div>
```

**After:** (Standardized)

```html
<div class="page-container">
    <!-- Layer 2: Page Header + Controls -->
    <div class="page-header-section">
        <div class="page-title-bar">
            <div class="title-section">
                <h1>
                    <mat-icon>question_answer</mat-icon>
                    RAG Q&A System
                </h1>
                <p class="subtitle">Ask questions and get intelligent answers based on your document corpus</p>
            </div>
        </div>

        <div class="controls-bar">
            <mat-form-field appearance="outline" class="search-field">
                <mat-label>Search queries</mat-label>
                <input matInput [formControl]="searchControl">
                <mat-icon matPrefix>search</mat-icon>
            </mat-form-field>

            <mat-form-field appearance="outline">
                <mat-label>Intent Type</mat-label>
                <mat-select [formControl]="intentTypeControl">
                    <mat-option value="">All Types</mat-option>
                </mat-select>
            </mat-form-field>

            <mat-form-field appearance="outline">
                <mat-label>Response Status</mat-label>
                <mat-select [formControl]="statusControl">
                    <mat-option value="">All Statuses</mat-option>
                </mat-select>
            </mat-form-field>

            <button mat-stroked-button (click)="clearFilters()" class="clear-button">
                <mat-icon>clear</mat-icon>
                Clear
            </button>

            <button mat-stroked-button (click)="refresh()">
                <mat-icon>refresh</mat-icon>
                Refresh
            </button>
        </div>
    </div>

    <!-- Layer 3: Content Area -->
    <div class="content-area">
        <!-- Existing content -->
    </div>

    <!-- Layer 4: Footer (if needed) -->
</div>
```

#### C. Update SCSS

Copy the standard Layer 2 styles from `PAGE_HEADER_CONTROLS_STANDARD.md`:

```scss
// ============================================================================
// Layer 2: Page Header + Controls - Standard Pattern
// Following ADR-012 & PAGE_HEADER_CONTROLS_STANDARD.md
// ============================================================================

.page-header-section {
    flex: 0 0 auto;
    z-index: 100;
    background: white;
    border-bottom: 1px solid #e0e0e0;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);

    .page-title-bar {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 24px 24px 16px 24px;
        gap: 24px;

        .title-section {
            flex: 1;
            min-width: 0;

            h1 {
                margin: 0;
                font-size: 28px;
                font-weight: 500;
                line-height: 1.2;
                color: rgba(0, 0, 0, 0.87);
                display: flex;
                align-items: center;
                gap: 12px;

                mat-icon {
                    font-size: 32px;
                    width: 32px;
                    height: 32px;
                    color: #1976d2;
                }
            }

            .subtitle {
                margin: 8px 0 0 0;
                font-size: 14px;
                line-height: 1.5;
                color: rgba(0, 0, 0, 0.6);
            }
        }

        .primary-actions {
            flex-shrink: 0;
            display: flex;
            gap: 12px;
        }
    }

    .controls-bar {
        display: flex;
        gap: 16px;
        padding: 0 24px 16px 24px;
        flex-wrap: wrap;
        align-items: center;

        mat-form-field {
            min-width: 200px;

            &.search-field {
                min-width: 300px;
                flex: 1;
                max-width: 500px;
            }
        }

        .view-controls {
            display: flex;
            gap: 4px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;

            button {
                border-radius: 0;
                background: white;
                transition: all 0.2s ease;

                &:hover {
                    background: #f5f5f5;
                }

                &.active {
                    background: #1976d2;
                    color: white;

                    mat-icon {
                        color: white;
                    }
                }
            }
        }

        .clear-button {
            height: 56px;
        }
    }

    .results-summary {
        padding: 0 24px 12px 24px;
        font-size: 14px;
        color: rgba(0, 0, 0, 0.6);

        strong {
            color: rgba(0, 0, 0, 0.87);
            font-weight: 500;
        }
    }
}

// Mobile responsive
@media (max-width: 768px) {
    .page-header-section {
        .page-title-bar {
            flex-direction: column;
            padding: 16px 16px 12px 16px;

            .title-section h1 {
                font-size: 24px;
            }

            .primary-actions {
                width: 100%;
                button {
                    flex: 1;
                }
            }
        }

        .controls-bar {
            flex-direction: column;
            padding: 0 16px 12px 16px;
            align-items: stretch;

            mat-form-field {
                width: 100%;
                min-width: 100%;
                max-width: 100%;
            }

            .clear-button {
                width: 100%;
            }
        }
    }
}
```

#### D. Update TypeScript

Add necessary FormControls and methods:

```typescript
// Add to component class
searchControl = new FormControl('');
categoryControl = new FormControl('');
sortControl = new FormControl('name');
viewMode: 'grid' | 'list' = 'grid';
pageSizeControl = new FormControl(10);

ngOnInit(): void {
    // Setup search with debounce
    this.searchControl.valueChanges
        .pipe(
            debounceTime(300),
            distinctUntilChanged()
        )
        .subscribe(() => this.applyFilters());

    // Other filter subscriptions
    this.categoryControl.valueChanges.subscribe(() => this.applyFilters());
    this.sortControl.valueChanges.subscribe(() => this.applyFilters());
}

clearFilters(): void {
    this.searchControl.setValue('', { emitEvent: false });
    this.categoryControl.setValue('', { emitEvent: false });
    this.sortControl.setValue('name', { emitEvent: false });
    this.applyFilters();
}

setViewMode(mode: 'grid' | 'list'): void {
    this.viewMode = mode;
    // Save preference
}
```

#### E. Test & Verify

Run the verification checklist from `PAGE_HEADER_CONTROLS_STANDARD.md`.

#### F. Commit Changes

```bash
# Review changes
git diff

# Add changed files
git add [component files]

# Commit with descriptive message
git commit -m "Normalize Layer 2: [Page Name] - Apply standard header/controls pattern

- Restructured HTML to use standard page-header-section
- Applied standard SCSS styles per ADR-012
- Added FormControls for filters
- Implemented debounced search
- Added accessibility labels
- Tested responsive behavior

Refs: PAGE_HEADER_CONTROLS_STANDARD.md, ADR-012"
```

### Step 3: Normalize Medium Priority Pages (3-4 hours)

Repeat Step 2 workflow for medium-priority pages.

### Step 4: Normalize Low Priority Pages (2-3 hours)

Repeat Step 2 workflow for low-priority pages.

### Step 5: Create Shared Component (Optional - 2 hours)

If patterns are highly repetitive, consider creating a **shared Page Header component**:

```typescript
// src/frontend-angular/src/app/shared/components/page-header/page-header.component.ts
@Component({
    selector: 'app-page-header',
    standalone: true,
    template: `
        <div class="page-header-section">
            <div class="page-title-bar">
                <div class="title-section">
                    <h1>
                        <mat-icon *ngIf="icon">{{ icon }}</mat-icon>
                        {{ title }}
                    </h1>
                    <p class="subtitle" *ngIf="subtitle">{{ subtitle }}</p>
                </div>
                <div class="primary-actions">
                    <ng-content select="[actions]"></ng-content>
                </div>
            </div>

            <div class="controls-bar" *ngIf="hasControls">
                <ng-content select="[controls]"></ng-content>
            </div>

            <div class="results-summary" *ngIf="resultsSummary">
                {{ resultsSummary }}
            </div>
        </div>
    `,
    styleUrls: ['./page-header.component.scss']
})
export class PageHeaderComponent {
    @Input() title!: string;
    @Input() subtitle?: string;
    @Input() icon?: string;
    @Input() hasControls = true;
    @Input() resultsSummary?: string;
}
```

**Usage:**

```html
<app-page-header
    title="Use Cases"
    subtitle="Select and execute AI-powered use cases"
    icon="folder">

    <div actions>
        <button mat-raised-button color="primary">
            <mat-icon>add</mat-icon>
            Create Use Case
        </button>
    </div>

    <div controls>
        <!-- Your filter controls here -->
    </div>
</app-page-header>
```

---

## Detailed Page-by-Page Instructions

### 1. RAG Q&A System (High Priority)

**File:** `src/frontend-angular/src/app/pages/query/rag-qa.component.*`

**Current Issues:**

- Non-standard header layout
- Controls mixed with content
- Missing consistent styling

**Target Type:** Type 2 (Query/Search)

**Required Changes:**

1. **HTML Restructure:**

```html
<div class="rag-qa-container">
    <!-- Add standard Layer 2 -->
    <div class="page-header-section">
        <div class="page-title-bar">
            <div class="title-section">
                <h1>
                    <mat-icon>question_answer</mat-icon>
                    RAG Q&A System
                </h1>
                <p class="subtitle">Ask questions and get intelligent answers based on your document corpus</p>
            </div>
        </div>

        <div class="controls-bar">
            <!-- Model Selection -->
            <mat-form-field appearance="outline">
                <mat-label>Choose the LLM model for answering your question</mat-label>
                <mat-select [formControl]="modelControl">
                    <mat-option value="gpt-4">GPT-4</mat-option>
                    <!-- other models -->
                </mat-select>
            </mat-form-field>
        </div>
    </div>

    <!-- Layer 3: Content area with query interface -->
    <div class="content-area">
        <!-- Existing Q&A interface -->
    </div>
</div>
```

2. **Add to SCSS:**

```scss
// Import standard Layer 2 styles
@import '../../../styles/components/page-header-standard.scss';

// OR copy the standard pattern directly
.page-header-section {
    // ... standard styles from guideline
}
```

3. **Update TypeScript:**

```typescript
modelControl = new FormControl('');
```

---

### 2. Query History (High Priority)

**File:** `src/frontend-angular/src/app/pages/query/query-history.component.*`

**Current Issues:**

- Non-standard controls layout
- Inconsistent button styling
- Missing results summary

**Target Type:** Type 2 (Query/Search)

**Required Changes:**

1. **HTML Restructure:**

```html
<div class="query-history-container">
    <div class="page-header-section">
        <div class="page-title-bar">
            <div class="title-section">
                <h1>
                    <mat-icon>history</mat-icon>
                    Query History
                </h1>
                <p class="subtitle">View, manage, and reuse your previous searches and Q&A sessions</p>
            </div>
        </div>

        <div class="controls-bar">
            <mat-form-field appearance="outline" class="search-field">
                <mat-label>Search queries</mat-label>
                <input matInput [formControl]="searchControl" placeholder="Search by query text...">
                <mat-icon matPrefix>search</mat-icon>
            </mat-form-field>

            <mat-form-field appearance="outline">
                <mat-label>Intent Type</mat-label>
                <mat-select [formControl]="intentTypeControl">
                    <mat-option value="">All Types</mat-option>
                </mat-select>
            </mat-form-field>

            <mat-form-field appearance="outline">
                <mat-label>Response Status</mat-label>
                <mat-select [formControl]="statusControl">
                    <mat-option value="">All Statuses</mat-option>
                </mat-select>
            </mat-form-field>

            <button mat-stroked-button (click)="clearFilters()" class="clear-button">
                <mat-icon>clear</mat-icon>
                Clear
            </button>

            <button mat-stroked-button (click)="refresh()">
                <mat-icon>refresh</mat-icon>
                Refresh
            </button>
        </div>
    </div>

    <div class="content-area">
        <!-- Existing history table/list -->
    </div>
</div>
```

---

### 3. Thread List (High Priority)

**File:** `src/frontend-angular/src/app/pages/conversations/thread-list.component.*`

**Current Issues:**

- Simple header structure
- Missing standardized controls bar
- No view toggle option

**Target Type:** Type 1 (List/Grid)

**Required Changes:**

1. **HTML Restructure:**

```html
<div class="thread-list-container">
    <div class="page-header-section">
        <div class="page-title-bar">
            <div class="title-section">
                <h1>
                    <mat-icon>forum</mat-icon>
                    Conversation Threads
                </h1>
                <p class="subtitle">Manage and continue your multi-turn conversations</p>
            </div>
            <div class="primary-actions">
                <button mat-raised-button color="primary" (click)="createNewThread()">
                    <mat-icon>add</mat-icon>
                    New Thread
                </button>
            </div>
        </div>

        <div class="controls-bar">
            <mat-form-field appearance="outline" class="search-field">
                <mat-label>Search threads</mat-label>
                <input matInput [formControl]="searchControl">
                <mat-icon matPrefix>search</mat-icon>
            </mat-form-field>

            <mat-form-field appearance="outline">
                <mat-label>Filter by DiscussionID</mat-label>
                <mat-select [formControl]="discussionIdControl">
                    <mat-option value="">All Discussions</mat-option>
                </mat-select>
            </mat-form-field>

            <mat-form-field appearance="outline">
                <mat-label>Sort by</mat-label>
                <mat-select [formControl]="sortControl">
                    <mat-option value="recent">Most Recent</mat-option>
                    <mat-option value="oldest">Oldest First</mat-option>
                </mat-select>
            </mat-form-field>

            <button mat-stroked-button (click)="clearFilters()" class="clear-button">
                <mat-icon>clear</mat-icon>
                Clear Filters
            </button>
        </div>

        <div class="results-summary">
            Found <strong>{{ totalThreads }}</strong> conversation threads
        </div>
    </div>

    <div class="content-area">
        <!-- Existing thread table -->
    </div>

    <div class="page-footer">
        <mat-paginator></mat-paginator>
    </div>
</div>
```

---

### 4. Use Case Wizard (Medium Priority)

**File:** `src/frontend-angular/src/app/pages/use-cases/use-case-wizard.component.*`

**Current Issues:**

- Progress indicator in header
- Non-standard layout

**Target Type:** Type 3 (Detail/Form)

**Required Changes:**

1. **HTML Restructure:**

```html
<div class="wizard-container">
    <div class="page-header-section">
        <div class="page-title-bar">
            <div class="title-section">
                <h1>
                    <mat-icon>add_circle</mat-icon>
                    Create New Use Case
                </h1>
                <p class="subtitle">Step {{ currentStep }} of {{ totalSteps }}: {{ getStepTitle() }}</p>
            </div>
            <div class="primary-actions">
                <button mat-stroked-button (click)="cancel()">
                    <mat-icon>close</mat-icon>
                    Cancel
                </button>
            </div>
        </div>

        <!-- Progress Indicator in Controls Bar -->
        <div class="controls-bar">
            <div class="wizard-progress">
                <div class="step"
                     *ngFor="let step of [1,2,3,4,5]"
                     [class.active]="currentStep === step"
                     [class.completed]="currentStep > step">
                    <div class="step-number">{{ step }}</div>
                    <div class="step-label">{{ getStepName(step) }}</div>
                </div>
            </div>
        </div>
    </div>

    <div class="content-area">
        <!-- Wizard step content -->
    </div>

    <div class="page-footer">
        <button mat-stroked-button (click)="previousStep()" [disabled]="currentStep === 1">
            <mat-icon>chevron_left</mat-icon>
            Previous
        </button>
        <button mat-raised-button color="primary" (click)="nextStep()">
            {{ currentStep === totalSteps ? 'Create' : 'Next' }}
            <mat-icon>chevron_right</mat-icon>
        </button>
    </div>
</div>
```

---

## Validation & Testing

### Automated Checks

Create a test script to validate compliance:

```bash
#!/bin/bash
# ops/testing/validate_layer2_compliance.sh

echo "🔍 Validating Layer 2 Compliance..."
echo ""

# Check for standard class names
for file in src/frontend-angular/src/app/pages/**/*.component.html; do
    echo "Checking $file..."

    # Check for page-header-section
    if ! grep -q "page-header-section" "$file"; then
        echo "  ❌ Missing page-header-section"
    else
        echo "  ✅ Has page-header-section"
    fi

    # Check for page-title-bar
    if ! grep -q "page-title-bar" "$file"; then
        echo "  ❌ Missing page-title-bar"
    else
        echo "  ✅ Has page-title-bar"
    fi

    # Check for controls-bar
    if ! grep -q "controls-bar" "$file"; then
        echo "  ⚠️  Missing controls-bar (may be intentional)"
    else
        echo "  ✅ Has controls-bar"
    fi

    echo ""
done

echo "✅ Validation complete"
```

### Manual Testing Checklist

For each normalized page:

- [ ] **Visual Verification:**
  - [ ] Title bar has proper spacing (24px padding)
  - [ ] Icon is 32x32px and properly colored
  - [ ] Subtitle is present and styled correctly
  - [ ] Primary action button on the right
  - [ ] Controls bar has consistent 16px gaps
  - [ ] All controls are properly aligned

- [ ] **Functional Verification:**
  - [ ] Search field has debounce (300ms)
  - [ ] All filters update results correctly
  - [ ] Clear Filters button resets all controls
  - [ ] View toggle switches views (if applicable)
  - [ ] Items per page updates pagination (if applicable)
  - [ ] Results summary updates with filters

- [ ] **Responsive Verification:**
  - [ ] Desktop (1920x1080): All controls visible, no wrapping
  - [ ] Laptop (1440x900): Proper wrapping if needed
  - [ ] Tablet (768px): Stacked layout
  - [ ] Mobile (375px): Full width controls

- [ ] **Accessibility Verification:**
  - [ ] h1 has text content (not just icon)
  - [ ] All form fields have labels
  - [ ] All icon buttons have tooltips or aria-labels
  - [ ] Tab order is logical
  - [ ] Focus indicators are visible
  - [ ] Screen reader announces page title and controls

---

## Success Criteria

### Per-Page Success

- ✅ HTML follows standard template structure
- ✅ SCSS uses standard styles (copied or imported)
- ✅ TypeScript has necessary FormControls and methods
- ✅ All checklist items pass
- ✅ No visual regressions
- ✅ Accessibility score maintained or improved

### Overall Success

- ✅ **80%+ of pages** using standard Layer 2 pattern
- ✅ **All high-priority pages** normalized
- ✅ **User testing** shows improved predictability
- ✅ **Accessibility audit** passes (axe, Lighthouse)
- ✅ **Documentation updated** with final state

---

## Rollout Plan

### Week 1: High Priority Pages

- Day 1-2: RAG Q&A System, Query History
- Day 3: Thread List
- Day 4: Testing and fixes
- Day 5: Code review and merge

### Week 2: Medium Priority Pages

- Day 1-2: Use Case Wizard, Use Case Execution
- Day 3: Thread Detail, Document Management
- Day 4-5: Testing, fixes, and code review

### Week 3: Low Priority + Finalization

- Day 1-2: Dashboard and Analytics pages
- Day 3: Admin pages
- Day 4: Final testing and documentation updates
- Day 5: Create shared component (if beneficial)

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Breaking existing functionality | High | Medium | Thorough testing; feature flags for gradual rollout |
| User confusion during transition | Medium | Low | Normalize high-traffic pages first; maintain consistency |
| CSS conflicts with existing styles | Medium | Medium | Use component encapsulation; test thoroughly |
| Accessibility regressions | High | Low | Run axe/Lighthouse after each change |
| Increased bundle size | Low | Low | Standard pattern should reduce CSS duplication |

---

## Monitoring & Metrics

### Before Normalization

- [ ] Screenshot all pages (Layer 2 section)
- [ ] Measure CSS bundle size for each component
- [ ] Run Lighthouse accessibility audit
- [ ] Document current user feedback/issues

### After Normalization

- [ ] Screenshot all normalized pages
- [ ] Measure new CSS bundle sizes (should be similar or smaller)
- [ ] Re-run Lighthouse accessibility audit (should improve)
- [ ] Gather user feedback on consistency

---

## Deliverables

### Code Changes

- [ ] Updated HTML templates for all pages
- [ ] Updated SCSS styles for all pages
- [ ] Updated TypeScript components
- [ ] All tests passing
- [ ] No linter errors

### Documentation

- [ ] Update `PAGE_HEADER_CONTROLS_STANDARD.md` with any learnings
- [ ] Create before/after screenshots document
- [ ] Update `UI_DEVELOPMENT_PLAN.md` with completion status
- [ ] Create session log in `docs/development/sessions/`

### Testing

- [ ] All automated tests passing
- [ ] Manual testing completed for all pages
- [ ] Accessibility audit completed
- [ ] Responsive testing completed

---

## Quick Reference: Page Type Selection

| If your page... | Use Type | Key Controls |
|----------------|----------|--------------|
| Shows a list/grid of items | Type 1: List/Grid | Search, Category, Sort, View Toggle, Items/Page, Clear |
| Is primarily for search/query | Type 2: Query/Search | Search, Filters, Apply, Clear, Refresh |
| Shows details or is a form | Type 3: Detail/Form | Title with context, Back button, Action buttons |
| Is a dashboard/overview | Type 4: Dashboard | Time range, Refresh, Export |

---

## Example Commits

### Good Commit Message

```
Normalize Layer 2: RAG Q&A System

- Restructured header to use standard page-header-section
- Added page-title-bar with icon and subtitle
- Moved model selection to controls-bar
- Applied standard SCSS styles per ADR-012
- Added FormControl for model selection
- Improved accessibility with proper labels
- Tested responsive behavior on mobile/tablet

Refs: #NORMALIZE-LAYER2-001
Follows: PAGE_HEADER_CONTROLS_STANDARD.md, ADR-012
```

### Bad Commit Message

```
Updated RAG page
```

---

## Support & Questions

**Q: What if my page doesn't fit any of the 4 types exactly?**

A: Choose the **closest type** and adapt. Document any variations in your component's SCSS with comments explaining why.

**Q: Can I skip the subtitle if my page title is self-explanatory?**

A: Yes, subtitles are **optional**. However, they improve UX by providing context.

**Q: Should I create a shared component for Layer 2?**

A: **After** normalizing all pages, evaluate if a shared component would reduce duplication. Don't create it preemptively.

**Q: What if I find issues with the standard pattern?**

A: Document the issue, propose an improvement, and update `PAGE_HEADER_CONTROLS_STANDARD.md` after team review.

---

## Related Documentation

- 📄 **Page Header Controls Standard:** `docs/development/guidelines/PAGE_HEADER_CONTROLS_STANDARD.md`
- 📄 **Layered Layout Pattern:** `docs/development/guidelines/LAYERED_PAGE_LAYOUT_PATTERN.md`
- 📄 **ADR-012:** Hybrid CSS Strategy
- 📄 **UI Development Plan:** `docs/development/plans/UI_DEVELOPMENT_PLAN.md`

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-10-19 | Initial task document | Frontend Team |

---

**Status:** Ready for execution in separate thread
**Next Step:** Create new thread with instruction: "Execute task NORMALIZE-LAYER2-001 following docs/development/tasks/NORMALIZE_PAGE_HEADER_CONTROLS.md"
