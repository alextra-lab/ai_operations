# Page Header + Controls Standardization (Layer 2)

**Status:** Approved
**Date:** 2025-10-19
**Last Updated:** 2025-10-19
**Maintainers:** Frontend Team, UX Team
**Tags:** angular, ux, consistency, material, adr-012, layer-2

---

## Overview

This document defines the **standardized Page Header + Controls (Layer 2)** design pattern for all pages in AI Operations Platform. This ensures **visual consistency** and **predictable user experience** across the application.

### Problem Statement

Current state shows **inconsistent Layer 2 implementations** across pages:
- ❌ Different control layouts and arrangements
- ❌ Inconsistent spacing and alignment
- ❌ Varying button styles and positions
- ❌ Mixed patterns for search, filters, and actions
- ❌ No clear visual hierarchy

### Solution

A **standardized two-row header structure** that provides:
- ✅ **Consistent visual hierarchy** (title → actions → controls)
- ✅ **Predictable control placement** across all pages
- ✅ **Responsive behavior** for mobile devices
- ✅ **Accessibility compliance** with WCAG 2.1 AA
- ✅ **ADR-012 compliance** (Material + Tailwind + Component SCSS)

---

## The Standard Pattern

### Visual Structure

```
┌─────────────────────────────────────────────────────────────┐
│ Row 1: TITLE BAR                                            │
│ ┌─────────────────────────────────┬─────────────────────┐   │
│ │ [Icon] Page Title               │  [Primary Action]   │   │
│ │ Subtitle/Description            │                     │   │
│ └─────────────────────────────────┴─────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│ Row 2: CONTROLS BAR                                         │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ [Search] [Filter 1▼] [Filter 2▼] [Sort▼] ... [Clear] │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Layout Hierarchy

```
Layer 2: Page Header + Controls
│
├── Row 1: Title Bar (flex: space-between)
│   ├── Left: Title Section
│   │   ├── Icon (optional)
│   │   ├── Page Title (h1)
│   │   └── Subtitle (p, optional)
│   │
│   └── Right: Primary Actions
│       └── Primary Action Button (max 1-2 buttons)
│
└── Row 2: Controls Bar (flex: flex-start)
    ├── Search Field (if applicable)
    ├── Filter Controls (dropdowns, selects)
    ├── View Toggle (if applicable)
    ├── Items Per Page (if applicable)
    └── Clear/Reset Button (if filters present)
```

---

## HTML Template

### Standard Implementation

```html
<div class="page-header-section">
    <!-- Row 1: Title Bar -->
    <div class="page-title-bar">
        <!-- Left: Title Section -->
        <div class="title-section">
            <h1>
                <mat-icon>icon_name</mat-icon>
                Page Title
            </h1>
            <p class="subtitle">Brief description of this page's purpose</p>
        </div>

        <!-- Right: Primary Actions -->
        <div class="primary-actions">
            <button mat-raised-button color="primary" (click)="primaryAction()">
                <mat-icon>add</mat-icon>
                Primary Action
            </button>
        </div>
    </div>

    <!-- Row 2: Controls Bar -->
    <div class="controls-bar">
        <!-- Search -->
        <mat-form-field appearance="outline" class="search-field">
            <mat-label>Search</mat-label>
            <input matInput
                   [formControl]="searchControl"
                   placeholder="Search items...">
            <mat-icon matPrefix>search</mat-icon>
        </mat-form-field>

        <!-- Filters -->
        <mat-form-field appearance="outline">
            <mat-label>Category</mat-label>
            <mat-select [formControl]="categoryControl">
                <mat-option value="">All Categories</mat-option>
                <mat-option *ngFor="let cat of categories" [value]="cat.value">
                    {{ cat.label }}
                </mat-option>
            </mat-select>
        </mat-form-field>

        <mat-form-field appearance="outline">
            <mat-label>Sort by</mat-label>
            <mat-select [formControl]="sortControl">
                <mat-option value="name">Name</mat-option>
                <mat-option value="date">Date</mat-option>
                <mat-option value="popular">Popularity</mat-option>
            </mat-select>
        </mat-form-field>

        <!-- View Toggle (if applicable) -->
        <div class="view-controls" *ngIf="hasViewToggle">
            <button mat-icon-button
                    [class.active]="viewMode === 'grid'"
                    (click)="setViewMode('grid')"
                    matTooltip="Grid View">
                <mat-icon>grid_view</mat-icon>
            </button>
            <button mat-icon-button
                    [class.active]="viewMode === 'list'"
                    (click)="setViewMode('list')"
                    matTooltip="List View">
                <mat-icon>view_list</mat-icon>
            </button>
        </div>

        <!-- Items Per Page (if applicable) -->
        <mat-form-field appearance="outline" *ngIf="hasPagination">
            <mat-label>Items per page</mat-label>
            <mat-select [formControl]="pageSizeControl">
                <mat-option *ngFor="let size of pageSizeOptions" [value]="size">
                    {{ size }}
                </mat-option>
            </mat-select>
        </mat-form-field>

        <!-- Clear Filters -->
        <button mat-stroked-button
                (click)="clearFilters()"
                class="clear-button">
            <mat-icon>clear</mat-icon>
            Clear Filters
        </button>
    </div>

    <!-- Optional: Results Summary -->
    <div class="results-summary" *ngIf="showResultsSummary">
        Showing <strong>{{ visibleCount }}</strong> of <strong>{{ totalCount }}</strong> items
    </div>
</div>
```

---

## SCSS Styles (ADR-012 Compliant)

### Standard Styles

```scss
// ============================================================================
// Layer 2: Page Header + Controls - Standard Pattern
// Following ADR-012: Hybrid Material + Tailwind + Component SCSS
// ============================================================================

.page-header-section {
    flex: 0 0 auto;                 // From layered layout pattern
    z-index: 100;
    background: white;
    border-bottom: 1px solid #e0e0e0;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);

    // Row 1: Title Bar
    .page-title-bar {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 24px 24px 16px 24px;
        gap: 24px;

        .title-section {
            flex: 1;
            min-width: 0; // Prevent flex overflow

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
                    color: var(--primary-color, #1976d2);
                }
            }

            .subtitle {
                margin: 8px 0 0 0;
                font-size: 14px;
                line-height: 1.5;
                color: rgba(0, 0, 0, 0.6);
                max-width: 600px;
            }
        }

        .primary-actions {
            flex-shrink: 0;
            display: flex;
            gap: 12px;
            align-items: flex-start;

            button {
                white-space: nowrap;
            }
        }
    }

    // Row 2: Controls Bar
    .controls-bar {
        display: flex;
        gap: 16px;
        padding: 0 24px 16px 24px;
        flex-wrap: wrap;
        align-items: center;

        mat-form-field {
            min-width: 200px;
            max-width: 300px;

            &.search-field {
                min-width: 300px;
                flex: 1;
            }
        }

        // View Toggle Controls
        .view-controls {
            display: flex;
            gap: 4px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;

            button {
                border-radius: 0;
                border: none;
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

        // Clear Button
        .clear-button {
            height: 56px;
            margin-left: auto; // Push to right if space available
        }
    }

    // Optional: Results Summary
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

// ============================================================================
// Responsive Behavior
// ============================================================================

@media (max-width: 768px) {
    .page-header-section {
        .page-title-bar {
            flex-direction: column;
            padding: 16px 16px 12px 16px;

            .title-section {
                h1 {
                    font-size: 24px;

                    mat-icon {
                        font-size: 28px;
                        width: 28px;
                        height: 28px;
                    }
                }
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

            .view-controls {
                width: 100%;
                justify-content: center;
            }

            .clear-button {
                width: 100%;
                margin-left: 0;
            }
        }

        .results-summary {
            padding: 0 16px 12px 16px;
        }
    }
}
```

---

## Component TypeScript Pattern

### Standard Component Structure

```typescript
import { Component, OnInit } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

@Component({
    selector: 'app-your-page',
    standalone: true,
    imports: [
        CommonModule,
        ReactiveFormsModule,
        MatButtonModule,
        MatFormFieldModule,
        MatInputModule,
        MatSelectModule,
        MatIconModule,
        MatTooltipModule,
        // ... other imports
    ],
    templateUrl: './your-page.component.html',
    styleUrls: ['./your-page.component.scss']
})
export class YourPageComponent implements OnInit {
    // Form controls for filters
    searchControl = new FormControl('');
    categoryControl = new FormControl('');
    sortControl = new FormControl('name');
    pageSizeControl = new FormControl(10);

    // View mode
    viewMode: 'grid' | 'list' = 'grid';

    // Configuration
    hasViewToggle = true;
    hasPagination = true;
    showResultsSummary = true;

    // Data
    categories = [
        { value: 'cat1', label: 'Category 1' },
        { value: 'cat2', label: 'Category 2' },
    ];

    pageSizeOptions = [10, 25, 50, 100];
    visibleCount = 0;
    totalCount = 0;

    ngOnInit(): void {
        // Setup search with debounce
        this.searchControl.valueChanges
            .pipe(
                debounceTime(300),
                distinctUntilChanged()
            )
            .subscribe(value => this.onSearchChange(value));

        // Setup filter subscriptions
        this.categoryControl.valueChanges
            .subscribe(() => this.applyFilters());

        this.sortControl.valueChanges
            .subscribe(() => this.applyFilters());

        this.pageSizeControl.valueChanges
            .subscribe(() => this.onPageSizeChange());
    }

    primaryAction(): void {
        // Handle primary action (e.g., create new item)
    }

    setViewMode(mode: 'grid' | 'list'): void {
        this.viewMode = mode;
        this.saveViewPreferences();
    }

    clearFilters(): void {
        this.searchControl.setValue('', { emitEvent: false });
        this.categoryControl.setValue('', { emitEvent: false });
        this.sortControl.setValue('name', { emitEvent: false });
        this.applyFilters();
    }

    private onSearchChange(value: string | null): void {
        // Implement search logic
        this.applyFilters();
    }

    private applyFilters(): void {
        // Implement filter logic
        // Update visibleCount and totalCount
    }

    private onPageSizeChange(): void {
        // Handle page size change
    }

    private saveViewPreferences(): void {
        localStorage.setItem('view-preferences', JSON.stringify({
            viewMode: this.viewMode,
            pageSize: this.pageSizeControl.value
        }));
    }
}
```

---

## Design Specifications

### Typography

| Element | Font Size | Weight | Color | Line Height |
|---------|-----------|--------|-------|-------------|
| Page Title (h1) | 28px | 500 | `rgba(0,0,0,0.87)` | 1.2 |
| Subtitle | 14px | 400 | `rgba(0,0,0,0.6)` | 1.5 |
| Form Labels | 12px | 400 | `rgba(0,0,0,0.6)` | 1 |
| Results Summary | 14px | 400 | `rgba(0,0,0,0.6)` | 1.5 |

### Spacing

| Element | Padding/Margin | Value |
|---------|---------------|-------|
| Title Bar | Padding | `24px 24px 16px 24px` |
| Controls Bar | Padding | `0 24px 16px 24px` |
| Results Summary | Padding | `0 24px 12px 24px` |
| Title Section → Icon | Gap | `12px` |
| Title → Subtitle | Margin Top | `8px` |
| Controls | Gap | `16px` |
| Primary Actions | Gap | `12px` |

### Colors

| Element | Property | Value | Variable |
|---------|----------|-------|----------|
| Background | background | `#ffffff` | `--surface-color` |
| Border | border-bottom | `#e0e0e0` | `--border-color` |
| Icon | color | `#1976d2` | `--primary-color` |
| Title | color | `rgba(0,0,0,0.87)` | `--text-primary` |
| Subtitle | color | `rgba(0,0,0,0.6)` | `--text-secondary` |
| Shadow | box-shadow | `0 2px 4px rgba(0,0,0,0.1)` | - |

### Interactive Elements

| Element | Height | Min Width | Border Radius |
|---------|--------|-----------|---------------|
| Form Fields | 56px | 200px | 4px |
| Search Field | 56px | 300px | 4px |
| Buttons (raised) | 40px | auto | 4px |
| Buttons (icon) | 40px | 40px | 4px |
| View Toggle | 40px | 40px | 0 (grouped) |

---

## Variations by Page Type

### Type 1: List/Grid Pages (e.g., Use Cases, Patterns)

**Characteristics:**
- Search field (prominent)
- Multiple filters (category, sort, etc.)
- View toggle (grid/list)
- Items per page selector
- Clear filters button

**Example:** Use Cases, Pattern Library, Document Management

```html
<div class="page-header-section">
    <div class="page-title-bar">
        <div class="title-section">
            <h1><mat-icon>folder</mat-icon>Use Cases</h1>
            <p class="subtitle">Select and execute AI-powered use cases for your SOC operations</p>
        </div>
        <div class="primary-actions">
            <button mat-raised-button color="primary">
                <mat-icon>add</mat-icon>
                Create Use Case
            </button>
        </div>
    </div>

    <div class="controls-bar">
        <mat-form-field appearance="outline" class="search-field">
            <mat-label>Search</mat-label>
            <input matInput placeholder="Search use cases...">
            <mat-icon matPrefix>search</mat-icon>
        </mat-form-field>

        <mat-form-field appearance="outline">
            <mat-label>Category</mat-label>
            <mat-select><mat-option value="">All Categories</mat-option></mat-select>
        </mat-form-field>

        <mat-form-field appearance="outline">
            <mat-label>Lifecycle State</mat-label>
            <mat-select><mat-option value="">All States</mat-option></mat-select>
        </mat-form-field>

        <mat-form-field appearance="outline">
            <mat-label>Intent Type</mat-label>
            <mat-select><mat-option value="">All Types</mat-option></mat-select>
        </mat-form-field>

        <div class="view-controls">
            <button mat-icon-button [class.active]="viewMode === 'grid'">
                <mat-icon>grid_view</mat-icon>
            </button>
            <button mat-icon-button [class.active]="viewMode === 'list'">
                <mat-icon>view_list</mat-icon>
            </button>
        </div>

        <button mat-stroked-button class="clear-button">
            <mat-icon>clear</mat-icon>
            Clear Filters
        </button>
    </div>

    <div class="results-summary">
        Showing <strong>8</strong> of <strong>9</strong> use cases
    </div>
</div>
```

### Type 2: Query/Search Pages (e.g., RAG Q&A, Query History)

**Characteristics:**
- Prominent search/query input
- Minimal filters (type, status)
- Action buttons (Apply, Clear, Refresh)
- No view toggle
- Results summary

**Example:** RAG Q&A System, Query History

```html
<div class="page-header-section">
    <div class="page-title-bar">
        <div class="title-section">
            <h1><mat-icon>question_answer</mat-icon>RAG Q&A System</h1>
            <p class="subtitle">Ask questions and get intelligent answers based on your document corpus</p>
        </div>
    </div>

    <div class="controls-bar">
        <mat-form-field appearance="outline" class="search-field">
            <mat-label>Search queries</mat-label>
            <input matInput placeholder="Search previous queries...">
            <mat-icon matPrefix>search</mat-icon>
        </mat-form-field>

        <mat-form-field appearance="outline">
            <mat-label>Intent Type</mat-label>
            <mat-select><mat-option value="">All Types</mat-option></mat-select>
        </mat-form-field>

        <mat-form-field appearance="outline">
            <mat-label>Response Status</mat-label>
            <mat-select><mat-option value="">All Statuses</mat-option></mat-select>
        </mat-form-field>

        <button mat-stroked-button (click)="applyFilters()">
            <mat-icon>check</mat-icon>
            Apply Filters
        </button>

        <button mat-stroked-button (click)="clearFilters()">
            <mat-icon>clear</mat-icon>
            Clear
        </button>

        <button mat-stroked-button (click)="refresh()">
            <mat-icon>refresh</mat-icon>
            Refresh
        </button>
    </div>
</div>
```

### Type 3: Detail/Form Pages (e.g., Use Case Execution, Thread Detail)

**Characteristics:**
- Title with context (e.g., use case name)
- Minimal controls (back button, actions)
- Status indicators
- No search/filters

**Example:** Use Case Execution, Thread Detail, Wizard

```html
<div class="page-header-section">
    <div class="page-title-bar">
        <div class="title-section">
            <h1><mat-icon>play_arrow</mat-icon>Basic Threat Analysis</h1>
            <p class="subtitle">Execute AI-powered threat analysis on security incidents</p>
        </div>
        <div class="primary-actions">
            <button mat-raised-button color="primary">
                <mat-icon>play_arrow</mat-icon>
                Execute
            </button>
            <button mat-stroked-button (click)="goBack()">
                <mat-icon>arrow_back</mat-icon>
                Back
            </button>
        </div>
    </div>

    <!-- Optional: Status/Progress Indicators -->
    <div class="controls-bar">
        <mat-chip-set>
            <mat-chip>
                <mat-icon>check_circle</mat-icon>
                Active
            </mat-chip>
            <mat-chip>
                <mat-icon>schedule</mat-icon>
                Last executed: 2 hours ago
            </mat-chip>
        </mat-chip-set>
    </div>
</div>
```

### Type 4: Dashboard/Overview Pages

**Characteristics:**
- Simple title
- Minimal controls (refresh, date range)
- Quick actions
- No search

**Example:** SOC Dashboard, Analytics

```html
<div class="page-header-section">
    <div class="page-title-bar">
        <div class="title-section">
            <h1><mat-icon>dashboard</mat-icon>Security Operations Center</h1>
            <p class="subtitle">Real-time overview of security operations and metrics</p>
        </div>
        <div class="primary-actions">
            <button mat-raised-button color="primary">
                <mat-icon>file_download</mat-icon>
                Export Report
            </button>
        </div>
    </div>

    <div class="controls-bar">
        <mat-form-field appearance="outline">
            <mat-label>Time Range</mat-label>
            <mat-select>
                <mat-option value="24h">Last 24 Hours</mat-option>
                <mat-option value="7d">Last 7 Days</mat-option>
                <mat-option value="30d">Last 30 Days</mat-option>
            </mat-select>
        </mat-form-field>

        <button mat-stroked-button (click)="refresh()">
            <mat-icon>refresh</mat-icon>
            Refresh
        </button>
    </div>
</div>
```

---

## Normalization Checklist

### Phase 1: Audit Current State

```bash
# Find all page components
find src/frontend-angular/src/app/pages -name "*.component.html" | while read file; do
    echo "=== $file ==="
    grep -A 20 "page-header\|page-title\|controls" "$file" || echo "No standard header found"
done
```

### Phase 2: Categorize Pages

| Page | Current State | Target Type | Priority |
|------|---------------|-------------|----------|
| Use Cases | ✅ Compliant | Type 1: List/Grid | - |
| Pattern Library | ✅ Compliant | Type 1: List/Grid | - |
| RAG Q&A | ⚠️ Needs Update | Type 2: Query/Search | High |
| Query History | ⚠️ Needs Update | Type 2: Query/Search | High |
| Use Case Wizard | ⚠️ Needs Update | Type 3: Detail/Form | Medium |
| Thread Detail | ⚠️ Needs Update | Type 3: Detail/Form | Medium |
| Thread List | ⚠️ Needs Update | Type 1: List/Grid | High |
| SOC Dashboard | ⚠️ Needs Update | Type 4: Dashboard | Low |
| ... | ... | ... | ... |

### Phase 3: Implementation Checklist (Per Page)

For each page requiring normalization:

#### ✅ **HTML Structure**
- [ ] Add `.page-header-section` wrapper
- [ ] Implement `.page-title-bar` with left/right sections
- [ ] Add `.title-section` with h1 and subtitle
- [ ] Add `.primary-actions` section (if applicable)
- [ ] Implement `.controls-bar` with standardized controls
- [ ] Add `.results-summary` (if applicable)
- [ ] Ensure proper semantic HTML (h1, labels, etc.)

#### ✅ **SCSS Styles**
- [ ] Import standard Layer 2 styles or copy pattern
- [ ] Verify spacing matches specification (24px, 16px, 12px)
- [ ] Ensure typography matches (28px h1, 14px subtitle)
- [ ] Add responsive breakpoints for mobile
- [ ] Verify colors use CSS variables where possible
- [ ] Test view toggle styling (if applicable)

#### ✅ **TypeScript**
- [ ] Add FormControl for each filter
- [ ] Implement debounced search (300ms)
- [ ] Add clearFilters() method
- [ ] Implement view mode toggle (if applicable)
- [ ] Add localStorage for preferences (if applicable)
- [ ] Update results summary on filter change

#### ✅ **Accessibility**
- [ ] h1 has proper text content (not just icon)
- [ ] All form fields have labels
- [ ] All icon buttons have tooltips or aria-labels
- [ ] Results summary uses proper semantic HTML
- [ ] Keyboard navigation works for all controls
- [ ] Focus indicators are visible

#### ✅ **Testing**
- [ ] Test on desktop (1920x1080, 1440x900)
- [ ] Test on tablet (768px)
- [ ] Test on mobile (375px)
- [ ] Verify search debouncing works
- [ ] Verify filters update results
- [ ] Verify clear button resets all filters
- [ ] Test with screen reader (VoiceOver/NVDA)

---

## Migration Priority

### High Priority (User-Facing, High Traffic)
1. **Use Cases Page** - ✅ Already compliant
2. **RAG Q&A System** - ⚠️ Needs normalization
3. **Query History** - ⚠️ Needs normalization
4. **Thread List** - ⚠️ Needs normalization
5. **Pattern Library** - ✅ Already compliant

### Medium Priority (Developer Tools)
6. **Use Case Wizard** - ⚠️ Needs normalization
7. **Use Case Execution** - ⚠️ Needs normalization
8. **Thread Detail** - ⚠️ Needs normalization
9. **Document Management** - ⚠️ Needs normalization

### Low Priority (Admin/Analytics)
10. **SOC Dashboard** - ⚠️ Needs normalization
11. **Analytics Pages** - ⚠️ Needs normalization
12. **Admin Pages** - ⚠️ Needs normalization

---

## Common Patterns & Components

### Reusable Control Combinations

#### Pattern: Search + Category + Sort
```html
<div class="controls-bar">
    <mat-form-field appearance="outline" class="search-field">
        <mat-label>Search</mat-label>
        <input matInput [formControl]="searchControl">
        <mat-icon matPrefix>search</mat-icon>
    </mat-form-field>

    <mat-form-field appearance="outline">
        <mat-label>Category</mat-label>
        <mat-select [formControl]="categoryControl">
            <mat-option value="">All</mat-option>
        </mat-select>
    </mat-form-field>

    <mat-form-field appearance="outline">
        <mat-label>Sort by</mat-label>
        <mat-select [formControl]="sortControl">
            <mat-option value="name">Name</mat-option>
        </mat-select>
    </mat-form-field>

    <button mat-stroked-button (click)="clearFilters()" class="clear-button">
        <mat-icon>clear</mat-icon>
        Clear Filters
    </button>
</div>
```

#### Pattern: View Toggle + Items Per Page
```html
<div class="view-controls">
    <button mat-icon-button
            [class.active]="viewMode === 'grid'"
            (click)="setViewMode('grid')">
        <mat-icon>grid_view</mat-icon>
    </button>
    <button mat-icon-button
            [class.active]="viewMode === 'list'"
            (click)="setViewMode('list')">
        <mat-icon>view_list</mat-icon>
    </button>
</div>

<mat-form-field appearance="outline">
    <mat-label>Items per page</mat-label>
    <mat-select [formControl]="pageSizeControl">
        <mat-option *ngFor="let size of [10,25,50,100]" [value]="size">
            {{ size }}
        </mat-option>
    </mat-select>
</mat-form-field>
```

---

## Visual Design Examples

### Example 1: Use Cases (Preferred Standard)

```
┌─────────────────────────────────────────────────────────────┐
│ [📁] Use Cases                        [➕ Create Use Case]  │
│ Select and execute AI-powered use cases for...              │
├─────────────────────────────────────────────────────────────┤
│ [🔍 Search] [Category▼] [State▼] [Type▼] [⊞⊟] [🗑️ Clear] │
│                                                              │
│ Showing 8 of 9 use cases                                    │
└─────────────────────────────────────────────────────────────┘
```

### Example 2: Query History

```
┌─────────────────────────────────────────────────────────────┐
│ [💬] Query History                                          │
│ View, manage, and reuse your previous searches...          │
├─────────────────────────────────────────────────────────────┤
│ [🔍 Search queries] [Type▼] [Status▼] [Apply] [Clear] [↻]  │
└─────────────────────────────────────────────────────────────┘
```

### Example 3: Thread Detail

```
┌─────────────────────────────────────────────────────────────┐
│ [💬] Incident INC-2024-001      [▶️ Continue] [← Back]     │
│ Active conversation thread for incident investigation       │
├─────────────────────────────────────────────────────────────┤
│ [✓ Active] [🕐 Last updated: 2 hours ago]                  │
└─────────────────────────────────────────────────────────────┘
```

---

## References

- **ADR-012:** Hybrid CSS Strategy (Material + Tailwind + Component SCSS)
- **Layered Layout Pattern:** `docs/development/guidelines/LAYERED_PAGE_LAYOUT_PATTERN.md`
- **Material Design:** Form field appearance, button variants
- **WCAG 2.1 AA:** Accessibility compliance
- **Existing Implementations:**
  - ✅ Use Cases: `src/frontend-angular/src/app/pages/use-case-menu/`
  - ✅ Pattern Library: `src/frontend-angular/src/app/pages/patterns/`

---

## FAQ

**Q: Should all pages use the exact same controls?**

A: No. Choose the appropriate **page type** (List/Grid, Query/Search, Detail/Form, Dashboard) and use the controls relevant to that type. The **structure and styling** should be consistent, but the **specific controls** can vary.

**Q: Can I add custom controls not in the standard?**

A: Yes, but maintain the same **visual style**, **spacing**, and **placement** within the controls bar. Document any custom controls in your component.

**Q: What if my page doesn't fit any of the 4 types?**

A: Use **Type 1 (List/Grid)** as the default fallback. It's the most flexible pattern.

**Q: Should I use Tailwind classes or SCSS?**

A: For Layer 2 structure and spacing, use **component SCSS** for clarity and maintainability (per ADR-012). Use Tailwind for micro-adjustments and responsive variants if needed.

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-10-19 | Initial standardization document | Frontend Team |

---

**Template Version:** 1.0
**License:** Internal Use Only
