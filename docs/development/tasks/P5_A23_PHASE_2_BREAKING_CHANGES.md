# P5-A23 Phase 2: Breaking Changes Documentation

**Date:** November 29, 2025
**Status:** Phase 2 Complete - Breaking Changes Identified
**Affected Services:** `ToolPermissionService`, `ModelRegistryService`

---

## Summary

Phase 2 base service conversions are complete. The services themselves are production-ready, but **routers and dependent services** will break until they're updated to use async patterns.

---

## ✅ Completed Services (Production Ready)

### ToolPermissionService

- **File:** `src/orchestrator/app/services/tool_permission_service.py`
- **Status:** ✅ Fully async (7 methods converted)
- **Tests:** ✅ All 18 test methods converted to async
- **Breaking Changes:** All methods now require `await`

### ModelRegistryService

- **File:** `src/orchestrator/app/services/model_registry_service.py`
- **Status:** ✅ Fully async (9 methods converted)
- **Tests:** ⚠️ Fixture updated, 25 test methods need async conversion
- **Breaking Changes:** All methods now require `await`

---

## ⚠️ Breaking Changes - Routers (Phase 4 Work)

These routers will fail until converted to async:

### Tools Admin Router

- **File:** `src/orchestrator/app/routers/tools_admin.py`
- **Issues:**
  - Lines 421, 539: `permission_service.grant_permission()` - needs `await`
  - Line 463: `permission_service.list_permissions()` - needs `await`
  - Line 493: `permission_service.get_permission()` - needs `await`
  - Line 582: `permission_service.revoke_permission()` - needs `await`
  - Service instances need `AsyncSession` instead of `Session`

### Tools Developer Router

- **File:** `src/orchestrator/app/routers/tools_developer.py`
- **Issues:**
  - Line 55: `permission_service.get_allowed_tools_for_role()` - needs `await`
  - Lines 109, 112: `permission_service.check_permission()` - needs `await`
  - Service instances need `AsyncSession` instead of `Session`

### Models Router

- **File:** `src/orchestrator/app/routers/models.py`
- **Issues:**
  - Line 81: `service.list_models()` - needs `await`
  - Line 132: `service.get_model()` - needs `await`
  - Line 182: `service.recommend_model()` - needs `await`
  - Line 262: `service.get_model()` - needs `await`
  - Service instances need `AsyncSession` instead of `Session`

### Orchestrator Router

- **File:** `src/orchestrator/app/routers/orchestrator.py`
- **Issues:**
  - Line 85: `model_service.get_model()` - needs `await`
  - Service instance needs `AsyncSession` instead of `Session`

---

## ⚠️ Breaking Changes - Dependent Services (Phase 3 Work)

These services use the converted services but haven't been updated yet:

### ToolRegistrationService

- **File:** `src/orchestrator/app/services/tool_registration_service.py`
- **Issues:**
  - Line 70: `ToolService(db)` - `db` is `Session`, needs `AsyncSession`
  - Line 73: `ToolPermissionService(db)` - `db` is `Session`, needs `AsyncSession`
  - Line 530: `tool_service.create_tool()` - needs `await`
  - Line 545: `permission_service.grant_permission()` - needs `await`
  - **Status:** Phase 3 - Dependent Services (not yet started)

### ToolExecutor

- **File:** `src/orchestrator/app/services/tool_executor.py`
- **Issues:**
  - Uses `ToolService` and `ToolPermissionService` - needs async conversion
  - **Status:** Phase 3 - Dependent Services (not yet started)

### ToolHealthMonitor

- **File:** `src/orchestrator/app/services/tool_health_monitor.py`
- **Issues:**
  - Uses `ToolService` - needs async conversion
  - **Status:** Phase 3 - Dependent Services (not yet started)

---

## 🔧 Migration Guide

### For Routers (Phase 4)

1. **Change session dependency:**

   ```python
   # BEFORE
   from sqlalchemy.orm import Session
   from ..db.database import SessionLocal

   def get_db() -> Generator[Session, None, None]:
       db = SessionLocal()
       ...

   # AFTER
   from sqlalchemy.ext.asyncio import AsyncSession
   from ..db.database import get_async_db

   # Use dependency injection
   async def endpoint(db: AsyncSession = Depends(get_async_db)):
       ...
   ```

2. **Update service instantiation:**

   ```python
   # BEFORE
   service = ToolPermissionService(db)
   result = service.check_permission(...)

   # AFTER
   service = ToolPermissionService(db)  # db is now AsyncSession
   result = await service.check_permission(...)
   ```

### For Dependent Services (Phase 3)

1. **Convert service to async:**
   - Change `Session` to `AsyncSession` in `__init__`
   - Make all methods `async def`
   - Add `await` to all service method calls
   - Update all database queries to async patterns

---

## 📋 Next Steps

1. **Phase 3:** Convert dependent services (`ToolRegistrationService`, `ToolExecutor`, etc.)
2. **Phase 4:** Convert routers to async and use updated services
3. **Testing:** Update all router and service tests after conversions

---

## ✅ Production Readiness Status

- **Service Code:** ✅ Production-ready (async patterns correct)
- **Service Tests:** ✅ ToolPermissionService tests complete, ModelRegistryService tests partial
- **Router Compatibility:** ⚠️ Routers will break until Phase 4 conversion
- **Dependent Services:** ⚠️ Will break until Phase 3 conversion

**Recommendation:** Complete Phase 3 and Phase 4 before deploying these changes to avoid runtime errors.

---

**Document Owner:** Project team
**Created:** November 29, 2025
