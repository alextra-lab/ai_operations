# P2-FIX-22: Observable Mock Fixes

**Status:** ✅ COMPLETED (2025-11-23)
**Priority:** 🟡 HIGH
**Estimated Effort:** 2-3 hours
**Created:** 2025-11-23
**Dependencies:** None
**Related:** P2-FIX-16 (test failures breakdown), P2-FIX-18 (Complete Service Mocks)

## 🎯 **Objective**

Fix ~12 test failures caused by mocks not returning proper RxJS Observables. Ensure all service mocks return Observables using `of()` or `throwError()` wrappers.

## 📊 **Affected Tests**

- `src/app/core/auth/role.guard.spec.ts` (source.subscribe errors)
- Multiple guard/service specs (~11 additional failures)
- **Total:** ~12 failures

## 🔍 **Root Cause**

- Mocks not returning proper RxJS Observables
- Services returning plain objects instead of Observables
- Missing `of()` or `throwError()` wrappers
- Tests fail with: `TypeError: source.subscribe is not a function`

## 🚀 **Implementation Plan**

### Step 1: Identify Observable Issues

Find all tests with subscribe errors:

```bash
grep -r "subscribe is not a function" src/frontend-angular/src/app --include="*.spec.ts"
```

### Step 2: Check Service Return Types

For each failing service, verify return types:

- Check service method signatures
- Identify which methods return Observables
- Note Observable types (e.g., `Observable<User>`, `Observable<void>`)

### Step 3: Fix Mock Return Values

Update mocks to return Observables:

**Before:**

```typescript
mockService.getUser.mockReturnValue({ user_id: '123' });
```

**After:**

```typescript
import { of } from 'rxjs';
mockService.getUser.mockReturnValue(of({ user_id: '123' }));
```

### Step 4: Fix Error Cases

For error scenarios, use `throwError`:

```typescript
import { throwError } from 'rxjs';
mockService.getUser.mockReturnValue(throwError(() => new Error('Not found')));
```

### Step 5: Verify Guard Tests

Focus on guard tests (role.guard.spec.ts):

- Ensure all service methods return Observables
- Check `canActivate` return values
- Verify async guard behavior

## ✅ **Acceptance Criteria**

- [ ] All service mocks return RxJS Observables
- [ ] All ~12 Observable/subscribe failures resolved
- [ ] Role guard tests passing
- [ ] Success cases use `of()` wrapper
- [ ] Error cases use `throwError()` wrapper
- [ ] No regressions in other tests

## 📝 **Notes**

- Always import `of` and `throwError` from 'rxjs'
- Use arrow functions with `throwError`: `throwError(() => error)`
- Verify Observable types match service signatures
- Consider creating helper functions for common mock patterns

## 🔗 **References**

- [RxJS of()](https://rxjs.dev/api/index/function/of)
- [RxJS throwError()](https://rxjs.dev/api/index/function/throwError)
- P2-FIX-16: Test Failures Breakdown (Category 6)
- Role Guard: `src/app/core/auth/role.guard.ts`

---

**Next Task:** P2-FIX-23 (HTTP Mock Verification)
