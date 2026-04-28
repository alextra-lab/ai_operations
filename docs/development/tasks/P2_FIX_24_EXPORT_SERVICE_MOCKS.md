# P2-FIX-24: Export Service Mocks

**Status:** ✅ COMPLETED (2025-11-23)
**Priority:** 🟡 HIGH
**Estimated Effort:** 2-3 hours
**Created:** 2025-11-23
**Dependencies:** None
**Related:** P2-FIX-16 (test failures breakdown), P2-FIX-19 (Browser API Mocks)

## 🎯 **Objective**

Fix ~18 test failures in export toolbar component by creating a complete ExportService mock with all required methods. The component depends on multiple export methods that are currently missing from mocks.

## 📊 **Affected Tests**

- `src/app/components/export-toolbar/export-toolbar.component.spec.ts` (18 failures)
- **Total:** ~18 failures

## 🔍 **Root Cause**

- ExportService not fully mocked
- Missing method implementations in mocks
- Component depends on multiple export methods
- Tests fail with:
  - `TypeError: service.exportAsJSON is not a function`
  - `TypeError: service.downloadFile is not a function`
  - `TypeError: service.copyToClipboard is not a function`
  - `TypeError: service.copyMarkdownToClipboard is not a function`

## 🚀 **Implementation Plan**

### Step 1: Read ExportService Interface

Check the actual ExportService implementation:

```bash
find src/frontend-angular/src/app -name "*export*.service.ts" -type f
```

### Step 2: Identify All Methods

List all ExportService methods:

- `exportAsJSON()`
- `downloadFile()`
- `copyToClipboard()`
- `copyMarkdownToClipboard()`
- Any other export-related methods

### Step 3: Create Complete Mock

Update export-toolbar component test:

```typescript
const mockExportService = {
  exportAsJSON: jest.fn(),
  downloadFile: jest.fn(),
  copyToClipboard: jest.fn(),
  copyMarkdownToClipboard: jest.fn(),
  // ... all other methods
} as Partial<ExportService>;
```

### Step 4: Set Mock Return Values

Provide appropriate return values:

```typescript
mockExportService.exportAsJSON.mockResolvedValue(undefined);
mockExportService.downloadFile.mockResolvedValue(undefined);
mockExportService.copyToClipboard.mockResolvedValue(true);
mockExportService.copyMarkdownToClipboard.mockResolvedValue(true);
```

### Step 5: Update Component Tests

Fix all failing tests in export-toolbar.component.spec.ts:

- Ensure all methods are mocked
- Set appropriate return values
- Verify method calls in assertions

## ✅ **Acceptance Criteria**

- [ ] ExportService mock includes all required methods
- [ ] All ~18 export service failures resolved
- [ ] Export toolbar component tests passing
- [ ] All export methods properly mocked
- [ ] Mock return values match service behavior
- [ ] No regressions in other tests

## 📝 **Notes**

- Check if ExportService methods return Promises or Observables
- Mock clipboard operations may need special handling
- File download mocks may need to mock `document.createElement`
- Consider mocking browser APIs (clipboard, download) separately

## 🔗 **References**

- P2-FIX-16: Test Failures Breakdown (Category 8)
- Export Toolbar Component: `src/app/components/export-toolbar/export-toolbar.component.ts`
- Export Service: Check for export service implementation

---

**Next Task:** P2-FIX-25 (MatDialog Mock Fixes)
