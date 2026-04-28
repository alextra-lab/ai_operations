# Layered Page Layout Pattern

**Status:** Approved
**Date:** 2025-10-19
**Last Updated:** 2025-12-16
**Maintainers:** Frontend Team
**Tags:** angular, layout, css, flexbox, scrolling, ux, adr-012, adr-045

---

## Overview

This document defines the **standardized layered layout pattern** for all page components in the AI Operations Platform application. This pattern ensures **consistent scrolling behavior** across all pages in the main content area, following **ADR-012 (Hybrid CSS Strategy)**.

### **Refined Design (October 20, 2025)**

The pattern has been refined to align with Material Design principles and match the Use Cases List component:

- ✅ **Clean white header** with bottom border and subtle shadow for separation
- ✅ **Title and description** directly in page header with proper padding (no wrapper boxes)
- ✅ **Controls directly in header** without additional container nesting
- ✅ **Light grey content area** (`#fafafa`) for subtle visual distinction
- ✅ **Simplified structure** with fewer CSS classes and DOM elements

### Problem Statement

Pages rendered in the main canvas were experiencing inconsistent scrolling behavior where:

- **All layers scrolled together** (header, content, footer all moving)
- **Fixed/sticky positioning failed** due to parent `overflow-auto` constraints
- **Footer controls were cut off** or hidden below the fold
- **Layout behavior was inconsistent** across different pages

### Solution

A **flex-based layered layout** that creates an internal scroll container, allowing:

- ✅ **Layer 1 (App Header)**: Global header - managed by main layout (NEVER scrolls)
- ✅ **Layer 2 (Page Header + Controls)**: Page-specific header and controls (NEVER scrolls)
- ✅ **Layer 3 (Content Area)**: Main content area (ONLY this scrolls)
- ✅ **Layer 4 (Page Footer)**: Pagination, actions, etc. (NEVER scrolls)

---

## The Pattern

### Architecture Diagram

```text
┌─────────────────────────────────────────────────────────┐
│ MAIN LAYOUT (overflow-auto)                            │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Layer 1: APP HEADER (Fixed by main layout)         │ │
│ │ • Breadcrumbs + Quick Actions                       │ │
│ │ • [NEVER SCROLLS]                                   │ │
│ ├─────────────────────────────────────────────────────┤ │
│ │ PAGE COMPONENT CONTAINER                            │ │
│ │ ┌─────────────────────────────────────────────────┐ │ │
│ │ │ Layer 2: PAGE HEADER + CONTROLS                 │ │ │
│ │ │ • Page title + subtitle with padding           │ │ │
│ │ │ • Controls with padding (no wrapper)            │ │ │
│ │ │ • White background + bottom border              │ │ │
│ │ │ • [NEVER SCROLLS - flex: 0 0 auto]             │ │ │
│ │ ├─────────────────────────────────────────────────┤ │ │
│ │ │ Layer 3: CONTENT AREA                           │ │ │
│ │ │ • Main content (cards, lists, tables, etc.)     │ │ │
│ │ │ • [SCROLLS - flex: 1, overflow-y: auto]        │ │ │
│ │ │ •                                                │ │ │
│ │ │ •  [Scrollable Content]                         │ │ │
│ │ │ •                                                │ │ │
│ │ ├─────────────────────────────────────────────────┤ │ │
│ │ │ Layer 4: PAGE FOOTER                            │ │ │
│ │ │ • Pagination controls                           │ │ │
│ │ │ • Action buttons                                │ │ │
│ │ │ • [NEVER SCROLLS - flex: 0 0 auto]             │ │ │
│ │ └─────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation

### HTML Structure

```html
<div class="page-container">
    <!-- Layer 2: Page Header + Controls -->
    <div class="page-header-section">
        <!-- Page Title and Subtitle -->
        <div class="page-title">
            <h1>
                <mat-icon>icon_name</mat-icon>
                Page Title
            </h1>
            <p class="subtitle">Page description or additional information</p>
        </div>

        <!-- Page Controls -->
        <div class="page-controls">
            <!-- Search, filters, sorting, view toggle, etc. -->
            <mat-form-field appearance="outline">
                <mat-label>Search</mat-label>
                <input matInput placeholder="Search...">
            </mat-form-field>
            <!-- More controls -->
        </div>
    </div>

    <!-- Loading/Error States (if needed) -->
    <div *ngIf="loading" class="loading-state">
        <mat-spinner></mat-spinner>
    </div>

    <mat-card *ngIf="error" class="error-state">
        <mat-icon>error</mat-icon>
        <p>{{ error }}</p>
    </mat-card>

    <!-- Layer 3: Content Area -->
    <div class="content-area">
        <!-- Your scrollable content here -->
        <!-- Cards, lists, tables, etc. -->
    </div>

    <!-- Layer 4: Page Footer -->
    <div class="page-footer" *ngIf="showPagination">
        <mat-paginator
            [length]="totalItems"
            [pageSize]="pageSize"
            [pageSizeOptions]="pageSizeOptions"
            (page)="onPageChange($event)">
        </mat-paginator>
    </div>
</div>
```

### SCSS Styles (Following ADR-012)

```scss
// ============================================================================
// Layered Page Layout Pattern
// Following ADR-012: Hybrid Material + Tailwind + Component SCSS
// ============================================================================

.page-container {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 200px); // Adjust based on app header height
    margin: -24px -32px;         // Offset main layout padding
    padding: 0;
    overflow: hidden;            // CRITICAL: Prevent parent from scrolling
}

// Layer 2: Page Header + Controls (NEVER SCROLLS)
.page-header-section {
    flex: 0 0 auto;
    z-index: 100;
    background: white;
    border-bottom: 1px solid #e0e0e0;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);

    .page-title {
        padding: 24px 24px 16px 24px;

        h1 {
            margin: 0;
            font-size: 28px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 12px;

            mat-icon {
                font-size: 32px;
                width: 32px;
                height: 32px;
            }
        }

        .subtitle {
            margin: 8px 0 0 0;
            color: #666;
            font-size: 14px;
        }
    }

    .page-controls {
        padding: 0 24px 16px 24px;
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
        align-items: center;

        mat-form-field {
            min-width: 200px;
        }
    }
}

// Layer 3: Content Area (SCROLLS)
.content-area {
    flex: 1;                    // Take remaining space
    overflow-y: auto;           // Enable vertical scrolling
    overflow-x: hidden;         // Prevent horizontal scroll
    padding: 24px;
    min-height: 0;              // **CRITICAL** for flex child to be scrollable
    background: #fafafa;        // Light grey background
}

// Layer 4: Page Footer (NEVER SCROLLS)
.page-footer {
    flex: 0 0 auto;             // Don't grow or shrink
    z-index: 90;                // Below header
    background: white;
    border-top: 1px solid #e0e0e0;
    box-shadow: 0 -2px 4px rgba(0, 0, 0, 0.1);

    mat-paginator {
        background-color: transparent;
    }
}

// Loading/Error States
.loading-state,
.error-state {
    flex: 0 0 auto;
    margin: 16px 24px;
    padding: 24px;
    text-align: center;
}

// ============================================================================
// Responsive Behavior
// ============================================================================

@media (max-width: 768px) {
    .page-container {
        height: calc(100vh - 150px); // Adjust for mobile
        margin: -16px;
    }

    .page-header-section {
        .page-title {
            padding: 16px 16px 12px 16px;

            h1 {
                font-size: 24px;
            }
        }

        .page-controls {
            padding: 0 16px 12px 16px;
            flex-direction: column;
            align-items: stretch;

            mat-form-field {
                width: 100%;
            }
        }
    }

    .content-area {
        padding: 16px;
    }
}
```

---

## Critical CSS Properties

### 🔴 **MUST HAVE** (Pattern will fail without these)

| Property | Element | Purpose | Value |
|----------|---------|---------|-------|
| `overflow: hidden` | `.page-container` | Prevents parent scrolling | `hidden` |
| `min-height: 0` | `.content-area` | Enables flex child scrolling | `0` |
| `flex: 1` | `.content-area` | Takes remaining space | `1` |
| `overflow-y: auto` | `.content-area` | Enables content scrolling | `auto` |
| `flex: 0 0 auto` | `.page-header-section`, `.page-footer` | Prevents growing/shrinking | `0 0 auto` |

### 🟡 **RECOMMENDED** (Improves UX/consistency)

| Property | Element | Purpose | Value |
|----------|---------|---------|-------|
| `height` | `.page-container` | Constrains overall height | `calc(100vh - 200px)` |
| `z-index` | `.page-header-section` | Stacking order | `100` |
| `box-shadow` | `.page-header-section`, `.page-footer` | Visual separation | `0 2px 4px rgba(0,0,0,0.1)` |
| `background` | All layers | Clear visual separation | `white` or `#fafafa` |

---

## Controls Container Standard (December 2025)

The **Document Library** component establishes the standard for compact controls containers. All pages with search/filter panels should follow this pattern.

### Standard Controls Container Specification

```scss
.page-controls {
    padding: 0 24px 12px 24px;

    .controls-container {
        background: #f5f5f5;
        border-radius: 6px;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
        padding: 8px 16px 4px 16px;  // Compact: 8px top, 4px bottom

        h3 {
            margin: 0 !important;       // Override browser defaults
            font-size: 20px !important; // Slightly smaller than page title (24px)
            font-weight: 500;
        }

        // Hide Material form field subscript for tighter spacing
        ::ng-deep .mat-mdc-form-field-subscript-wrapper {
            display: none;
        }
    }
}
```

### Standard Template Structure

```html
<div class="page-controls">
    <div class="controls-container">
        <!-- Row 1: Section title + description (inline) -->
        <div class="flex items-center gap-2 mb-1">
            <h3 class="!m-0 text-base font-medium">Search & Filter</h3>
            <span class="text-xs text-gray-500">
                Find by filename, content, status, or classification
            </span>
        </div>

        <!-- Rows 2+: Form controls -->
        <form [formGroup]="searchForm" class="flex flex-col gap-2">
            <!-- Primary controls row -->
            <div class="flex gap-3">
                <mat-form-field appearance="outline" class="flex-1 min-w-0">
                    <!-- Search/primary input -->
                </mat-form-field>
                <!-- Additional dropdowns/selects -->
            </div>

            <!-- Secondary controls row (dates, clear button, etc.) -->
            <div class="flex gap-3 items-center">
                <!-- Secondary controls -->
            </div>
        </form>
    </div>
</div>
```

### Key Values

| Property | Value | Purpose |
|----------|-------|---------|
| Container padding | `8px 16px 4px 16px` | Compact vertical, standard horizontal |
| Container background | `#f5f5f5` | Light grey, matches ADR-012 |
| Container border-radius | `6px` | Slightly rounded corners |
| Container shadow | `0 1px 4px rgba(0, 0, 0, 0.08)` | Subtle depth |
| Section title (h3) | `20px`, weight `500` | Smaller than page title (24px) |
| Title → Form gap | `mb-1` (4px) | Tight but readable |
| Form row gap | `gap-2` (8px) | Standard row spacing |

### Reference Implementation

**File:** `src/frontend-angular/src/app/pages/documents/document-library.component.ts`

This component demonstrates the complete pattern with:

- Compact controls container
- Proper h3 sizing (20px vs 24px page title)
- Tailwind utilities for layout (`flex`, `gap-2`, `mb-1`)
- SCSS for complex states and browser default overrides
- Full ADR-012 and ADR-045 compliance

---

## Usage Examples

### Example 1: Updated Pattern (Title + Rounded Controls)

**File:** `src/frontend-angular/src/app/pages/patterns/pattern-library.component.scss`

```scss
.pattern-library-layout {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 200px);
    margin: -24px -32px;
    padding: 0;
    overflow: hidden;
}

.page-header-section {
    flex: 0 0 auto;
    z-index: 100;
    background: #f5f5f5;        // Light grey background
    padding: 24px 24px 0 24px;

    .page-title {
        margin-bottom: 16px;

        h1 {
            margin: 0;
            font-size: 28px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 12px;
            color: #333;

            mat-icon {
                font-size: 32px;
                width: 32px;
                height: 32px;
                color: #1976d2;
            }
        }

        .subtitle {
            margin: 8px 0 0 0;
            color: #666;
            font-size: 14px;
            line-height: 1.4;
        }
    }

    .page-controls {
        padding: 0 24px 16px 24px;
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
        align-items: center;
    }
}

.content-area {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 24px;
    min-height: 0;
    background: #fafafa;
}

.page-footer {
    flex: 0 0 auto;
    z-index: 90;
    background: white;
    border-top: 1px solid #e0e0e0;
    box-shadow: 0 -2px 4px rgba(0, 0, 0, 0.1);
}
```

### Example 2: Thread Detail (Conversations)

**File:** `src/frontend-angular/src/app/pages/conversations/thread-detail.component.ts`

```typescript
styles: [`
  .thread-detail-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    max-height: calc(100vh - 200px);
    overflow: hidden;
  }

  .thread-header {
    flex-shrink: 0;
    margin: 16px;
    margin-bottom: 0;
  }

  .messages-container {
    flex: 1 1 auto;
    overflow-y: auto;
    padding: 16px;
    background: #f5f5f5;
    min-height: 0;
  }

  .input-card {
    flex-shrink: 0;
    margin: 16px;
    margin-top: 0;
  }
`]
```

---

## Checklist for Applying This Pattern

Use this checklist when converting a page to the layered layout pattern:

### ✅ **HTML Structure**

- [ ] Wrap entire page in a container div (e.g., `.page-container`)
- [ ] Separate content into distinct layers (header, content, footer)
- [ ] Ensure layer order: header → (loading/error) → content → footer
- [ ] Place page title and subtitle in `.page-title` with proper padding
- [ ] Place controls directly in `.page-controls` (no wrapper container)
- [ ] Use semantic HTML and proper ARIA labels

### ✅ **CSS/SCSS**

- [ ] Set `display: flex` and `flex-direction: column` on container
- [ ] Set `overflow: hidden` on container
- [ ] Set `height: calc(100vh - XXXpx)` on container (adjust for app header)
- [ ] Set `margin` to offset main layout padding (usually `-24px -32px`)
- [ ] Set `flex: 0 0 auto` on header and footer
- [ ] Set `flex: 1` on content area
- [ ] Set `overflow-y: auto` on content area
- [ ] **CRITICAL:** Set `min-height: 0` on content area
- [ ] Add `z-index` values for proper stacking
- [ ] Use white background on page header with bottom border (`1px solid #e0e0e0`)
- [ ] Add subtle shadow (`0 2px 4px rgba(0, 0, 0, 0.1)`) to page header
- [ ] Use light grey background (`#fafafa`) for content area
- [ ] Apply proper padding to `.page-title` and `.page-controls` directly

### ✅ **Responsive Design**

- [ ] Test on mobile (< 768px)
- [ ] Adjust container height for smaller screens
- [ ] Stack controls vertically on mobile
- [ ] Ensure touch targets are adequate (44x44px minimum)

### ✅ **Accessibility**

- [ ] Header has proper heading hierarchy (h1, h2, etc.)
- [ ] Form controls have labels
- [ ] Interactive elements are keyboard accessible
- [ ] Focus indicators are visible
- [ ] ARIA labels for icons and actions

### ✅ **Testing**

- [ ] Verify header stays fixed while scrolling
- [ ] Verify footer stays visible
- [ ] Verify only content area scrolls
- [ ] Test with different content amounts (few items vs many)
- [ ] Test on different screen sizes
- [ ] Verify keyboard navigation works

---

## Common Pitfalls

### ❌ **Forgetting `min-height: 0`**

**Problem:** Content area doesn't scroll properly; content overflows container.

**Why:** Flexbox children have a default `min-height: auto`, preventing them from shrinking below their content size.

**Solution:**

```scss
.content-area {
    flex: 1;
    overflow-y: auto;
    min-height: 0; // ✅ Add this!
}
```

### ❌ **Using `position: fixed` or `position: sticky`**

**Problem:** Elements position outside the main layout container or don't work due to parent `overflow` constraints.

**Why:** Fixed/sticky positioning doesn't work well with the main layout's `overflow-auto`.

**Solution:** Use flexbox with `flex: 0 0 auto` instead:

```scss
// ❌ Don't do this
.page-header {
    position: fixed;
    top: 0;
    left: 280px;
    right: 0;
}

// ✅ Do this instead
.page-header {
    flex: 0 0 auto;
}
```

### ❌ **Not offsetting main layout padding****

**Problem:** Unwanted white space around the page; headers don't extend full width.

**Why:** Main layout adds padding that needs to be compensated for.

**Solution:**

```scss
.page-container {
    margin: -24px -32px; // Offset main layout's padding
}
```

### ❌ **Forgetting `overflow: hidden` on container**

**Problem:** Both parent and child scroll, creating double scrollbars.

**Why:** Parent container also scrolls if not explicitly prevented.

**Solution:**

```scss
.page-container {
    overflow: hidden; // ✅ Prevent container from scrolling
}
```

---

## ADR-012 Compliance

This pattern follows **ADR-012 (Hybrid Material + Tailwind + Component SCSS)**:

✅ **Material Components:**

- Uses `mat-form-field`, `mat-paginator`, `mat-icon`, `mat-card`, etc.
- Leverages Material's accessibility features
- Uses Material's CSS variable tokens for theming

✅ **Component-Scoped SCSS:**

- Styles are scoped to component using Angular's emulated encapsulation
- Uses native CSS nesting where appropriate
- CSS variables used for theme-able properties

✅ **Clear Layering:**

- Material theme tokens → Tailwind utilities → Component SCSS
- No global overrides except documented tokens

✅ **Accessibility:**

- Maintains Material's built-in a11y features
- Proper heading hierarchy
- Keyboard navigation support
- ARIA labels where needed

---

## Migration Guide

### Step 1: Identify Pages Needing Update

Run this command to find pages without the pattern:

```bash
# Search for components that might not have the layered pattern
grep -r "overflow-auto" src/frontend-angular/src/app/pages/
```

### Step 2: Apply Pattern to Each Page

1. **Backup the component** (optional but recommended)
2. **Restructure HTML** using the template above
3. **Apply SCSS styles** following the pattern
4. **Test scrolling behavior** at different screen sizes
5. **Run accessibility checks** (axe, Lighthouse)

### Step 3: Test Thoroughly

```bash
# Build and test
npm run build
npm run test

# Visual regression testing (if available)
npm run test:visual
```

### Step 4: Document Component-Specific Variations

If your page has unique requirements, document them in the component file:

```scss
// Custom variation: Added fixed toolbar within content area
.content-area {
    flex: 1;
    overflow-y: auto;
    min-height: 0;

    // Component-specific: Toolbar stays at top of scrollable area
    .content-toolbar {
        position: sticky;
        top: 0;
        z-index: 10;
        background: white;
    }
}
```

---

## Related Documentation

- **ADR-012:** Hybrid CSS Strategy (Material + Tailwind + Component SCSS)
- **Main Layout:** `src/frontend-angular/src/app/layouts/main-layout/`
- **Reference Implementations:**
  - Pattern Library: `src/frontend-angular/src/app/pages/patterns/pattern-library.component.*`
  - Thread Detail: `src/frontend-angular/src/app/pages/conversations/thread-detail.component.*`
  - Thread List: `src/frontend-angular/src/app/pages/conversations/thread-list.component.*`

---

## Questions & Support

**Q: Can I use Tailwind utilities instead of custom SCSS?**

A: Yes! ADR-012 encourages Tailwind utilities. However, for the core layout structure (flex, overflow), component SCSS is clearer and more maintainable. Use Tailwind for spacing, colors, and responsive variants.

**Q: What if my page doesn't need a footer?**

A: Simply omit Layer 4. The pattern works with or without a footer.

**Q: Can I have multiple scrollable sections?**

A: Generally no - this pattern assumes one primary scrollable area. If you need multiple scroll areas, consider using tabs or expansion panels within the content area.

**Q: How do I handle modal dialogs?**

A: Material dialogs are rendered outside the component, so they're unaffected by this pattern. They'll work normally.

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.1 | 2025-12-16 | Added Compact Controls Container Standard (Document Library reference) | Frontend Team |
| 1.0 | 2025-10-19 | Initial documentation | Frontend Team |

---

**Template Version:** 1.0
**License:** Internal Use Only
