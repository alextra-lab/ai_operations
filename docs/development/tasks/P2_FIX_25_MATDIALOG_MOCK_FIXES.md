# P2-FIX-25: MatDialog Mock Fixes

**Status:** ✅ COMPLETED (2025-11-23)
**Priority:** 🟢 MEDIUM
**Estimated Effort:** 1-2 hours
**Created:** 2025-11-23
**Dependencies:** None
**Related:** P2-FIX-16 (test failures breakdown)

## 🎯 **Objective**

Fix ~4 test failures caused by incomplete MatDialogRef mocks. Create complete dialog mocks with `afterOpened` and `afterClosed` Observables.

## 📊 **Affected Tests**

- Multiple component specs using MatDialog (~4 failures)
- **Total:** ~4 failures

## 🔍 **Root Cause**

- MatDialogRef not properly mocked
- Missing `afterOpened` Subject/Observable
- Incomplete dialog mock implementation
- Tests fail with: `TypeError: this.afterOpened.next is not a function`

## 🚀 **Implementation Plan**

### Step 1: Identify Dialog Usage

Find all tests using MatDialog:

```bash
grep -r "MatDialog\|MatDialogRef" src/frontend-angular/src/app --include="*.spec.ts"
```

### Step 2: Check MatDialogRef Interface

Review Angular Material DialogRef API:

- `afterOpened: Observable<void>`
- `afterClosed: Observable<any>`
- `close(result?: any): void`
- Other methods as needed

### Step 3: Create Complete Mock

Create reusable MatDialogRef mock:

```typescript
import { Subject } from 'rxjs';

function createMatDialogRefMock<T = any>(): Partial<MatDialogRef<T>> {
  const afterOpenedSubject = new Subject<void>();
  const afterClosedSubject = new Subject<any>();

  return {
    close: jest.fn((result?: any) => {
      afterClosedSubject.next(result);
      afterClosedSubject.complete();
    }),
    afterOpened: afterOpenedSubject.asObservable(),
    afterClosed: afterClosedSubject.asObservable(),
    componentInstance: {} as T,
    disableClose: false,
    id: 'test-dialog-id',
  };
}
```

### Step 4: Update Dialog Tests

Update all tests using MatDialog:

```typescript
const mockDialogRef = createMatDialogRefMock<MyDialogComponent>();
const mockDialog = {
  open: jest.fn().mockReturnValue(mockDialogRef),
} as Partial<MatDialog>;
```

### Step 5: Test Dialog Behavior

Ensure dialog lifecycle works:

- `afterOpened` emits when dialog opens
- `afterClosed` emits when dialog closes
- `close()` method triggers `afterClosed`

## ✅ **Acceptance Criteria**

- [ ] MatDialogRef mock includes afterOpened Observable
- [ ] MatDialogRef mock includes afterClosed Observable
- [ ] All ~4 MatDialog failures resolved
- [ ] Dialog lifecycle properly mocked
- [ ] All component tests using dialogs passing
- [ ] No regressions in other tests

## 📝 **Notes**

- Use RxJS Subjects for Observable mocks
- Ensure Observables complete properly
- Mock `componentInstance` if component accesses it
- Consider creating a reusable mock factory

## 🔗 **References**

- [Angular Material Dialog API](https://material.angular.io/components/dialog/api)
- [MatDialogRef Documentation](https://material.angular.io/components/dialog/api#MatDialogRef)
- P2-FIX-16: Test Failures Breakdown (Category 9)

---

**Next Task:** P2-FIX-26 (Array/Iterable Fixes)
