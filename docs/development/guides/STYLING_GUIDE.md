# Angular Styling Guide - Hybrid CSS Strategy

**Status:** Active
**Last Updated:** 2025-10-12
**Related:** [ADR-012 Hybrid CSS Strategy](../adrs/ADR-012-Hybrid-CSS-Strategy.md)

---

## Overview

AI Operations Platform (AIOP) UI follows a **Hybrid CSS Strategy** combining:

1. **Angular Material** - Accessible UI primitives and design system tokens
2. **Tailwind CSS v3** - Utility-first classes for layout, spacing, and rapid iteration
3. **Component SCSS** - Complex state logic, transitions, and accessibility overrides

### Philosophy

> **Use the right tool for the job:**
> - Tailwind for **layout and spacing** (fast, consistent)
> - Material for **components and tokens** (accessible, tested)
> - SCSS for **complex logic** (transitions, media queries, state)

---

## CSS Architecture

### Layer Order (Critical)

Defined in `src/styles.scss`:

```scss
// 1. Material Theme & System Variables
@use '@angular/material' as mat;
@include mat.core();
// ... theme definition ...

// 2. Tailwind Directives
@tailwind base;
@tailwind components;
@tailwind utilities;

// 3. Third-Party Library Styles
@import 'katex/dist/katex.min.css';

// 4. Global App Overrides
html, body { ... }
```

**Why this order?**
- Material provides base theme and CSS variables
- Tailwind utilities can override component styles when needed
- App overrides have final say

---

## Material Design Token Mapping

Tailwind is configured to consume Material's CSS variables for consistency.

### Available Color Utilities

```html
<!-- Primary colors -->
<div class="bg-primary text-on-primary">...</div>
<div class="bg-primary-container text-on-primary-container">...</div>

<!-- Surface colors -->
<div class="bg-surface text-on-surface">...</div>
<div class="bg-surface-container">...</div>

<!-- Semantic colors -->
<div class="bg-error text-on-error">...</div>
<div class="border-outline">...</div>
```

### Material Spacing Scale

Use `mat-*` prefixed spacing classes:

```html
<div class="p-mat-4 gap-mat-2">  <!-- 16px padding, 8px gap -->
<div class="m-mat-6">            <!-- 24px margin -->
```

Or use standard Tailwind spacing (4px base unit):

```html
<div class="p-4 gap-2">  <!-- 16px padding, 8px gap -->
<div class="m-6">        <!-- 24px margin -->
```

### Material Typography

```html
<h1 class="text-headline-large">Headline</h1>
<h2 class="text-headline-medium">Subheading</h2>
<p class="text-body-large">Body text</p>
<span class="text-label-medium">Label</span>
```

---

## Component Refactoring Pattern

### Before (SCSS-heavy approach)

**HTML:**
```html
<div class="toolbar">
  <div class="toolbar-left">
    <button class="sidebar-toggle">Menu</button>
    <div class="breadcrumb">...</div>
  </div>
  <div class="toolbar-spacer"></div>
  <div class="toolbar-right">
    <div class="user-info">
      <span class="user-name">User</span>
      <span class="user-roles">admin</span>
    </div>
  </div>
</div>
```

**SCSS (60+ lines):**
```scss
.toolbar {
  display: flex;
  align-items: center;
  padding: 0 16px;
  height: 64px;

  .toolbar-left {
    display: flex;
    align-items: center;
    gap: 16px;
    flex: 1;

    .breadcrumb {
      flex: 1;
      min-width: 0;
    }
  }

  .toolbar-spacer {
    flex: 1;
  }

  .toolbar-right {
    display: flex;
    gap: 16px;

    .user-info {
      display: flex;
      flex-direction: column;
      text-align: right;

      .user-name {
        font-weight: 500;
        font-size: 14px;
      }

      .user-roles {
        font-size: 12px;
        opacity: 0.7;
      }
    }
  }
}

@media (max-width: 768px) {
  .toolbar {
    .toolbar-left .breadcrumb {
      display: none;
    }
    .toolbar-right .user-info .user-roles {
      display: none;
    }
  }
}
```

### After (Hybrid approach)

**HTML (Tailwind utilities):**
```html
<div class="toolbar flex items-center px-4 h-16">
  <div class="flex items-center gap-4 flex-1 min-w-0">
    <button class="sidebar-toggle">Menu</button>
    <div class="breadcrumb flex-1 min-w-0 hidden md:block">...</div>
  </div>

  <div class="flex items-center gap-4">
    <div class="user-info flex flex-col text-right">
      <span class="user-name font-medium text-sm">User</span>
      <span class="user-roles text-xs opacity-70 hidden sm:block">admin</span>
    </div>
  </div>
</div>
```

**SCSS (Minimal - transitions only):**
```scss
.toolbar {
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

@media (prefers-reduced-motion: reduce) {
  .toolbar {
    transition: none;
  }
}
```

**Result:** ~60 lines → ~15 lines (75% reduction)

---

## When to Use What

### ✅ Use Tailwind For

**Layout & Flexbox:**
```html
<div class="flex flex-col gap-4">
<div class="grid grid-cols-2 gap-6">
<div class="flex items-center justify-between">
```

**Spacing:**
```html
<div class="p-4 m-2">           <!-- Padding 16px, margin 8px -->
<div class="px-6 py-4">         <!-- Horizontal 24px, vertical 16px -->
<div class="mt-8 space-y-4">    <!-- Top margin 32px, stack children with 16px gap -->
```

**Typography:**
```html
<h1 class="text-2xl font-bold leading-tight">
<p class="text-sm text-gray-600 italic">
<span class="font-medium uppercase tracking-wide">
```

**Responsive Design:**
```html
<div class="flex flex-col md:flex-row">  <!-- Column on mobile, row on desktop -->
<div class="hidden lg:block">             <!-- Hidden until large screens -->
<div class="text-sm md:text-base lg:text-lg">
```

**Colors & Backgrounds:**
```html
<div class="bg-primary text-white">
<div class="bg-surface border border-outline">
<div class="text-error bg-error-container">
```

**Sizing:**
```html
<div class="w-full h-screen">
<div class="max-w-4xl mx-auto">
<div class="min-h-96">
```

### ✅ Use Material Components For

**UI Primitives:**
```html
<mat-button>Click Me</mat-button>
<mat-icon>settings</mat-icon>
<mat-form-field>...</mat-form-field>
<mat-sidenav>...</mat-sidenav>
<mat-toolbar color="primary">...</mat-toolbar>
```

**Why?** Material components have:
- Accessibility built-in (ARIA, keyboard navigation)
- Consistent behavior across browsers
- Comprehensive testing
- Theme integration

### ✅ Use SCSS For

**Transitions & Animations:**
```scss
.sidebar {
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-enter {
  animation: fadeIn 0.3s ease-in;
}
```

**Complex State Logic:**
```scss
.card {
  &:hover:not([disabled]) {
    transform: translateY(-2px);
    box-shadow: var(--mat-elevation-4);
  }
}
```

**Pseudo-elements:**
```scss
.badge::after {
  content: attr(data-count);
  position: absolute;
  top: -8px;
  right: -8px;
}
```

**Media Query State Changes:**
```scss
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    z-index: 1001;
  }
}
```

**Accessibility Overrides:**
```scss
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}

@media (prefers-contrast: high) {
  .card {
    border-width: 2px;
  }
}
```

---

## Practical Examples

### Example 1: Card Component

```html
<!-- HTML with Tailwind utilities -->
<div class="card flex flex-col gap-4 p-6 bg-surface rounded-lg border border-outline">
  <header class="flex items-center justify-between">
    <h2 class="text-title-large font-medium">Card Title</h2>
    <button mat-icon-button class="ml-auto">
      <mat-icon>more_vert</mat-icon>
    </button>
  </header>

  <div class="content flex-1">
    <p class="text-body-medium text-on-surface-variant">
      Card content goes here with proper typography.
    </p>
  </div>

  <footer class="flex gap-2 justify-end">
    <button mat-button>Cancel</button>
    <button mat-raised-button color="primary">Confirm</button>
  </footer>
</div>
```

```scss
// SCSS - Only for hover state and transition
.card {
  transition: all 0.2s ease;

  &:hover {
    box-shadow: var(--mat-elevation-2);
  }
}
```

### Example 2: Responsive Grid

```html
<!-- 1 column mobile, 2 tablet, 3 desktop -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-4">
  <div class="card">Card 1</div>
  <div class="card">Card 2</div>
  <div class="card">Card 3</div>
</div>
```

No SCSS needed! Pure Tailwind.

### Example 3: Form Layout

```html
<form class="flex flex-col gap-6 max-w-2xl mx-auto p-6">
  <!-- Form fields stacked with consistent spacing -->
  <mat-form-field class="w-full">
    <mat-label>Username</mat-label>
    <input matInput type="text" />
  </mat-form-field>

  <mat-form-field class="w-full">
    <mat-label>Email</mat-label>
    <input matInput type="email" />
  </mat-form-field>

  <!-- Button group -->
  <div class="flex gap-4 justify-end">
    <button mat-button type="button">Cancel</button>
    <button mat-raised-button color="primary" type="submit">Submit</button>
  </div>
</form>
```

---

## Responsive Design

### Tailwind Breakpoints

| Breakpoint | Min Width | Prefix | Example |
|------------|-----------|--------|---------|
| Mobile     | 0px       | (none) | `flex` |
| Small      | 640px     | `sm:`  | `sm:hidden` |
| Medium     | 768px     | `md:`  | `md:flex-row` |
| Large      | 1024px    | `lg:`  | `lg:grid-cols-3` |
| XL         | 1280px    | `xl:`  | `xl:max-w-7xl` |
| 2XL        | 1536px    | `2xl:` | `2xl:text-lg` |

### Mobile-First Approach

```html
<!-- Column on mobile, row on medium+ -->
<div class="flex flex-col md:flex-row gap-4">
  <div class="w-full md:w-1/2">Left</div>
  <div class="w-full md:w-1/2">Right</div>
</div>

<!-- Hide on mobile, show on tablet+ -->
<div class="hidden md:block">Desktop-only content</div>

<!-- Show on mobile, hide on tablet+ -->
<div class="block md:hidden">Mobile-only content</div>
```

### Responsive Spacing

```html
<!-- Smaller padding on mobile, larger on desktop -->
<div class="p-4 md:p-6 lg:p-8">
  Content with responsive padding
</div>

<!-- Responsive text sizes -->
<h1 class="text-2xl md:text-3xl lg:text-4xl">
  Responsive Heading
</h1>
```

---

## Accessibility Guidelines

### Required Practices

1. **Use semantic HTML:**
   ```html
   <header>, <nav>, <main>, <aside>, <footer>
   ```

2. **Provide ARIA labels for icon buttons:**
   ```html
   <button mat-icon-button aria-label="Close dialog">
     <mat-icon>close</mat-icon>
   </button>
   ```

3. **Maintain focus indicators:**
   ```html
   <!-- Tailwind has focus utilities -->
   <button class="focus:ring-2 focus:ring-primary focus:outline-none">
   ```

4. **Respect user preferences:**
   ```scss
   @media (prefers-reduced-motion: reduce) {
     * {
       transition: none !important;
     }
   }

   @media (prefers-contrast: high) {
     .border {
       border-width: 2px;
     }
   }
   ```

5. **Ensure color contrast:**
   - Material tokens provide WCAG-compliant contrast
   - Use `text-on-primary` with `bg-primary`
   - Use `text-on-surface` with `bg-surface`

6. **Support keyboard navigation:**
   ```html
   <div tabindex="0" (keydown.enter)="handleAction()">
   ```

---

## Common Patterns

### Pattern: Full-height Layout with Sticky Header

```html
<div class="flex flex-col h-screen">
  <header class="sticky top-0 z-50 h-16 bg-surface border-b">
    <!-- Fixed height header -->
  </header>

  <main class="flex-1 overflow-auto p-6">
    <!-- Scrollable main content -->
  </main>
</div>
```

### Pattern: Sidebar with Toggle

```html
<div class="flex h-screen">
  <aside class="sidebar w-64 bg-surface-container"
         [class.collapsed]="isCollapsed">
    <!-- Sidebar content -->
  </aside>

  <main class="flex-1 overflow-auto p-6"
        [style.margin-left]="getSidebarWidth()">
    <!-- Main content adjusts when sidebar toggles -->
  </main>
</div>
```

```scss
.sidebar {
  transition: width 0.3s ease;

  &.collapsed {
    width: 64px;
  }
}
```

### Pattern: Centered Content Container

```html
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
  <!-- Content max-width with responsive padding -->
</div>
```

### Pattern: Loading State

```html
<div class="flex items-center justify-center h-64">
  <mat-spinner diameter="40"></mat-spinner>
</div>
```

### Pattern: Empty State

```html
<div class="flex flex-col items-center justify-center h-96 gap-4">
  <mat-icon class="text-6xl text-gray-400">inbox</mat-icon>
  <h3 class="text-headline-small text-on-surface-variant">No items found</h3>
  <p class="text-body-medium text-on-surface-variant">
    Try adjusting your filters
  </p>
</div>
```

---

## Performance Considerations

### CSS Bundle Size

**Target:** ≤90KB (gzip)
**Current:** 90.28KB raw, 11.03KB gzip ✅

### Optimization Tips

1. **Use Tailwind's JIT mode** (already configured)
   - Only generates classes you actually use
   - Dramatically reduces bundle size

2. **Avoid arbitrary values when possible:**
   ```html
   <!-- ❌ Avoid -->
   <div class="w-[372px] p-[13px]">

   <!-- ✅ Prefer -->
   <div class="w-96 p-4">
   ```

3. **Leverage component encapsulation:**
   ```scss
   // Component SCSS is scoped automatically
   :host {
     display: block;
     // Styles only apply to this component
   }
   ```

4. **Minimize custom SCSS:**
   - Every custom rule adds to bundle size
   - Use Tailwind utilities when possible
   - Extract common patterns to utilities

---

## Migration Checklist

When refactoring an existing component:

- [ ] Read component HTML and SCSS
- [ ] Identify layout patterns (flex, grid, spacing)
- [ ] Replace layout CSS with Tailwind utilities in HTML
- [ ] Update responsive breakpoints to Tailwind's mobile-first approach
- [ ] Keep transitions, animations, and complex state in SCSS
- [ ] Test accessibility (keyboard navigation, screen reader, contrast)
- [ ] Test responsive behavior (mobile, tablet, desktop)
- [ ] Test theme switching (if applicable)
- [ ] Verify no visual regressions
- [ ] Check bundle size impact
- [ ] Update component documentation if needed
- [ ] Commit with clear message

---

## Reference Component

See **`layouts/main-layout`** as the reference implementation:
- HTML: Tailwind for layout, spacing, responsive
- SCSS: Minimal (102 lines, down from 200)
- Result: Same functionality, better maintainability

**Files:**
- `src/app/layouts/main-layout/main-layout.component.html`
- `src/app/layouts/main-layout/main-layout.component.scss`

---

## Resources

- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Angular Material Theming Guide](https://material.angular.dev/guide/theming)
- [Angular Material System Variables](https://material.angular.dev/guide/system-variables)
- [ADR-012: Hybrid CSS Strategy](../adrs/ADR-012-Hybrid-CSS-Strategy.md)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

---

## Support

For questions or issues with the styling strategy:
1. Review this guide and ADR-012
2. Check the main-layout reference implementation
3. Consult with frontend team leads
4. Open an issue in the project repository

---

**Version:** 1.0
**Maintained by:** Frontend Guild
