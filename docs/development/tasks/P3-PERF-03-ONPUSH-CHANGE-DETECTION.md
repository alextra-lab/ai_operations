# P3-PERF-03: Implement OnPush Change Detection Strategy

**Status:** 📋 DEFERRED (Phase 6)
**Updated:** 2025-10-25
**Phase Assignment:** Phase 6 - Performance & Production
**Priority:** 🟡 MEDIUM
**Estimated Effort:** 6-8 hours
**Created:** 2025-10-13
**Target Completion:** Week 2

---

## Problem Statement

The application currently uses **Default change detection** strategy for all components, which means Angular checks **every component** on **every browser event**, even if the component's data hasn't changed.

**Impact:**
- Unnecessary change detection cycles
- Reduced performance on complex pages
- Slower interaction response times
- Higher CPU usage on low-end devices

**Opportunity:**
Implementing `OnPush` change detection can improve rendering performance by **15-30%** by only checking components when their inputs actually change.

---

## Success Criteria

- [ ] OnPush strategy implemented on 20+ high-impact components
- [ ] No breaking changes to component functionality
- [ ] Measurable improvement in change detection performance
- [ ] Component architecture follows OnPush best practices
- [ ] Team trained on OnPush patterns

---

## Background: OnPush Change Detection

### Default Strategy (Current)
```typescript
@Component({
  selector: 'app-my-component',
  // changeDetection: ChangeDetectionStrategy.Default (implicit)
})
```

Angular checks this component:
- ✓ On every browser event (click, keypress, etc.)
- ✓ On every timer/interval
- ✓ On every HTTP request completion
- ✓ Even if component inputs haven't changed

### OnPush Strategy (Target)
```typescript
@Component({
  selector: 'app-my-component',
  changeDetection: ChangeDetectionStrategy.OnPush
})
```

Angular checks this component ONLY when:
- ✓ Input properties change (by reference)
- ✓ Component emits an event
- ✓ Observables emit (when using async pipe)
- ✓ Manually triggered with `ChangeDetectorRef.markForCheck()`

---

## Component Priority Matrix

### Priority 1: High-Impact, Low-Risk (Implement First)

Stateless/presentational components with simple inputs:

1. **SourceCitationComponent** (`src/app/components/source-citation/`)
   - Simple input: citation object
   - No internal state
   - **Estimated effort:** 15 min

2. **ExecutionMetricsComponent** (`src/app/components/execution-metrics/`)
   - Input: metrics object
   - Display-only component
   - **Estimated effort:** 20 min

3. **ModelSelectorComponent** (`src/app/components/model-selector/`)
   - Input: available models
   - Output: selection event
   - **Estimated effort:** 20 min

4. **CardComponent** (shared components)
   - Generic display component
   - **Estimated effort:** 15 min

### Priority 2: Medium-Impact, Medium-Risk

Components with some state but mostly input-driven:

5. **DashboardComponent** (`src/app/pages/dashboard/`)
   - Loads data once
   - Mostly static display
   - **Estimated effort:** 30 min

6. **DocumentLibraryComponent** (`src/app/pages/documents/`)
   - Table/list display
   - Pagination (needs careful handling)
   - **Estimated effort:** 45 min

7. **UsageAnalyticsComponent** (`src/app/pages/analytics/`)
   - Chart components
   - Refresh on demand
   - **Estimated effort:** 45 min

8. **TemplateLibraryComponent** (`src/app/pages/templates/`)
   - List/grid display
   - **Estimated effort:** 30 min

### Priority 3: Complex Components (Implement Last)

Components with significant state management:

9. **LlmContentRendererComponent** (`src/app/components/llm-content-renderer/`)
   - Complex rendering logic
   - Multiple sub-renderers
   - **Estimated effort:** 1 hour

10. **UseCaseExecutionComponent** (`src/app/pages/use-case-execution/`)
    - Dynamic forms
    - Real-time updates
    - **Estimated effort:** 1.5 hours

11. **SemanticSearchComponent** (`src/app/pages/query/`)
    - Search input
    - Result streaming
    - **Estimated effort:** 1 hour

### Do NOT Convert (Anti-patterns for OnPush)

- **LoginComponent**: Form-heavy, complex validation
- **Dynamic form components**: Heavy state management
- **Real-time streaming components**: Unless using observables exclusively

---

## Implementation Pattern

### Basic OnPush Pattern

```typescript
import {
  Component,
  Input,
  ChangeDetectionStrategy,
  ChangeDetectorRef
} from '@angular/core';

@Component({
  selector: 'app-example',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div>{{ data.value }}</div>
  `
})
export class ExampleComponent {
  @Input() data!: MyData;

  // If you need manual change detection:
  constructor(private cdr: ChangeDetectorRef) {}

  updateData(): void {
    // After async operations, trigger change detection
    this.someAsyncOperation().then(() => {
      this.cdr.markForCheck();
    });
  }
}
```

### OnPush with Observables

```typescript
@Component({
  selector: 'app-observable-example',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <!-- async pipe automatically handles change detection -->
    <div *ngIf="data$ | async as data">
      {{ data.value }}
    </div>
  `
})
export class ObservableExampleComponent {
  @Input() dataId!: string;
  data$!: Observable<MyData>;

  ngOnInit(): void {
    this.data$ = this.dataService.getData(this.dataId);
  }
}
```

### OnPush with Signals (Angular 18)

```typescript
@Component({
  selector: 'app-signal-example',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <!-- Signals automatically trigger change detection -->
    <div>{{ count() }}</div>
  `
})
export class SignalExampleComponent {
  count = signal(0);

  increment(): void {
    this.count.update(c => c + 1);
  }
}
```

---

## Implementation Steps

### Phase 1: Preparation (1 hour)
1. [ ] Review all components and categorize by priority
2. [ ] Set up performance baseline measurements
3. [ ] Create OnPush testing checklist
4. [ ] Document OnPush patterns for team

### Phase 2: Priority 1 Components (2 hours)
5. [ ] SourceCitationComponent → OnPush
6. [ ] ExecutionMetricsComponent → OnPush
7. [ ] ModelSelectorComponent → OnPush
8. [ ] Shared presentational components → OnPush
9. [ ] Test each component after conversion

### Phase 3: Priority 2 Components (3 hours)
10. [ ] DashboardComponent → OnPush
11. [ ] DocumentLibraryComponent → OnPush
12. [ ] UsageAnalyticsComponent → OnPush
13. [ ] TemplateLibraryComponent → OnPush
14. [ ] Test each component after conversion

### Phase 4: Priority 3 Components (2 hours)
15. [ ] LlmContentRendererComponent → OnPush (if feasible)
16. [ ] UseCaseExecutionComponent → OnPush (carefully)
17. [ ] SemanticSearchComponent → OnPush (with observables)
18. [ ] Extensive testing of complex components

### Phase 5: Validation & Documentation (1 hour)
19. [ ] Run full E2E test suite
20. [ ] Performance benchmark comparison
21. [ ] Document OnPush patterns used
22. [ ] Team knowledge sharing session

---

## Common OnPush Pitfalls & Solutions

### Pitfall 1: Mutating Objects
```typescript
// ❌ BAD: Won't trigger change detection
this.data.value = newValue;

// ✅ GOOD: Create new object reference
this.data = { ...this.data, value: newValue };
```

### Pitfall 2: Array Mutations
```typescript
// ❌ BAD: Won't trigger change detection
this.items.push(newItem);

// ✅ GOOD: Create new array reference
this.items = [...this.items, newItem];
```

### Pitfall 3: Async Operations Without Detection
```typescript
// ❌ BAD: View won't update
async loadData(): Promise<void> {
  this.data = await this.service.getData();
}

// ✅ GOOD: Manually mark for check
async loadData(): Promise<void> {
  this.data = await this.service.getData();
  this.cdr.markForCheck();
}

// ✅ BETTER: Use observables with async pipe
data$ = this.service.getData$();
```

### Pitfall 4: Event Handlers
```typescript
// ✅ Event handlers in template automatically trigger detection
template: `<button (click)="handleClick()">Click</button>`

// ❌ Programmatic event listeners don't
ngOnInit(): void {
  this.element.addEventListener('custom-event', () => {
    this.value = 'changed'; // Won't update view
  });
}

// ✅ Use markForCheck for programmatic events
this.element.addEventListener('custom-event', () => {
  this.value = 'changed';
  this.cdr.markForCheck();
});
```

---

## Testing Checklist Per Component

For each component converted to OnPush:

### Functional Testing
- [ ] All inputs render correctly
- [ ] All outputs emit correctly
- [ ] User interactions work as expected
- [ ] Async operations update the view
- [ ] No "ExpressionChangedAfterItHasBeenCheckedError"

### Performance Testing
- [ ] Component renders in < 16ms (60 FPS)
- [ ] No unnecessary re-renders in console
- [ ] Change detection count reduced (use Angular DevTools)

### Edge Case Testing
- [ ] Null/undefined inputs handled
- [ ] Rapid input changes work correctly
- [ ] Component works in different route contexts

---

## Performance Measurement

### Before Implementation
```bash
# Open Angular DevTools
# Navigate to page
# Enable "Change Detection" profiler
# Perform user actions
# Record number of checks per component
```

### After Implementation
```bash
# Repeat same measurement
# Compare change detection counts
# Document improvement percentage
```

**Expected Results:**
- Priority 1 components: 80-90% reduction in checks
- Priority 2 components: 50-70% reduction in checks
- Priority 3 components: 30-50% reduction in checks

---

## Rollback Plan

If a component exhibits issues after OnPush conversion:

1. **Immediately revert** to Default strategy:
   ```typescript
   changeDetection: ChangeDetectionStrategy.Default
   ```

2. **Document the issue** and specific failure case

3. **Analyze root cause:**
   - Object mutation?
   - Missing ChangeDetectorRef.markForCheck()?
   - Observable not using async pipe?

4. **Re-attempt** with proper fix

---

## Related Tasks

- **Prerequisite:** None (can run in parallel with P3-PERF-01)
- **Complements:** P3-PERF-01 (Lazy loading)
- **Future:** Consider migrating to Signals for even better performance

---

## Resources

- [Angular OnPush Documentation](https://angular.io/api/core/ChangeDetectionStrategy)
- [Angular Performance Guide](https://angular.io/guide/change-detection)
- [OnPush Best Practices](https://blog.angular-university.io/onpush-change-detection-how-it-works/)

---

## Acceptance Criteria

- ✅ At least 20 components converted to OnPush
- ✅ All converted components pass functional tests
- ✅ No "ExpressionChangedAfterItHasBeenCheckedError" errors
- ✅ Measurable performance improvement (15%+ reduction in change detection)
- ✅ Team documentation on OnPush patterns created
- ✅ Code review guidelines updated with OnPush requirements
- ✅ Angular DevTools profiling shows reduced check counts

---

**Assignee:** TBD
**Reviewer:** TBD
**Performance Impact:** 15-30% improvement in change detection speed
