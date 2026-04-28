# P2-FIX-31: Deferred Frontend Test Failures

**Status:** ⏸️ DEFERRED
**Created:** 2025-11-25
**Deferred To:** Post-Phase 7
**Current Pass Rate:** 93.1% (1252/1346 tests)

## Summary

76 frontend test failures across 15 test suites have been deferred to focus on Phase 7 (Backend Async Migration + Service Rename). These failures are component-specific issues requiring individual fixes, not global setup problems.

## Failing Test Suites (15)

| Suite | Category | Est. Effort |
|-------|----------|-------------|
| `use-case-selector-dialog.component.spec.ts` | Component | 1-2 hrs |
| `template-library.component.spec.ts` | Template | 1-2 hrs |
| `template-detail.component.spec.ts` | Template | 1-2 hrs |
| `sse-stream.service.spec.ts` | Service | 1 hr |
| `library-loader.service.spec.ts` | Service | 1 hr |
| `use-case-wizard.component.spec.ts` | Wizard | 2-3 hrs |
| `tool-registration-wizard.component.spec.ts` | Wizard | 2-3 hrs |
| `prompt-template-editor.component.spec.ts` | Template | 1-2 hrs |
| `metrics-dashboard.component.spec.ts` | Dashboard | 1-2 hrs |
| `gateway-metrics.component.spec.ts` | Dashboard | 1-2 hrs |
| `tool-management.component.spec.ts` | Admin | 2-3 hrs |
| `execution-metrics.component.spec.ts` | Dashboard | 1-2 hrs |
| `use-case-test-panel.component.spec.ts` | Component | 1-2 hrs |
| `dynamic-field.component.spec.ts` | Forms | 1 hr |
| `tool-delete-dialog.component.spec.ts` | Dialog | 1 hr |

**Total Estimated Effort:** 18-28 hours

## Root Causes

These failures are NOT global browser API issues (those were fixed). They are:

1. **Missing Service Providers** - TestBed doesn't include required services
2. **Incomplete Mocks** - Service mocks missing methods
3. **Template Compilation** - Component dependencies not properly imported
4. **Component Initialization** - Missing providers for child components

## What Was Fixed (Nov 25, 2025)

### Global Jest Setup (`setup-jest.ts`)
- ✅ Functional localStorage/sessionStorage mocks (actual storage behavior)
- ✅ WebSocket mock with static constants (CONNECTING, OPEN, CLOSING, CLOSED)
- ✅ Storage cleanup between tests

### Individual Test Fixes
- ✅ `websocket.service.spec.ts` - Preserved WebSocket constants in mock
- ✅ `enter-to-execute.directive.spec.ts` - Fixed test assertions, localStorage spies

## Recommendation

Fix these after Phase 7 completion when:
1. Service names are stable (orchestrator, corpus)
2. Async patterns are established
3. Test infrastructure can be updated holistically

## Related

- P2-FIX-16: Test Failures Breakdown (analysis)
- P2-FIX-18: Complete Service Mocks (completed)
- P2-FIX-30: Template Rendering Fixes (completed)

---

**Document Owner:** Project team
**Last Updated:** 2025-11-25
