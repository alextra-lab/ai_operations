# Task: Remove `users.role` Column - Full RBAC V2 Migration

**Status:** 📋 PENDING
**Created:** 2025-12-11
**Priority:** HIGH
**Related ADR:** ADR-060 (RBAC V2 Architecture)

## Objective

Remove the `users.role` column entirely and migrate all code to use only the `user_roles` table for role storage, per ADR-060 RBAC V2 architecture.

## Background

Currently, the system has dual role storage:
- `users.role` column (legacy/single role)
- `user_roles` table (RBAC V2 - multiple roles)

Since we're pre-release, we should fully commit to RBAC V2 and remove the legacy column.

## Scope of Changes

### 1. Database Schema Changes

**File:** `ops/database/init/000_complete_init.sql`
- [ ] Remove `role VARCHAR NOT NULL` from `users` table definition (line 139)
- [ ] Update table comment if it references the role column

**File:** Create migration script `ops/database/migrations/XXX_remove_users_role_column.sql`
- [ ] Create migration to:
  - Ensure all users have roles in `user_roles` table
  - Drop the `role` column from `users` table
  - Update any indexes/constraints that reference `role`

### 2. SQLAlchemy Model Changes

**File:** `src/shared/auth/models.py`
- [ ] Remove `role = Column(String, nullable=False, default=UserRole.USER)` from `User` class (line 71)
- [ ] Update `to_dict()` method to fetch role from `user_roles` table instead of `user.role` (line 97)
- [ ] Update `UserBase` Pydantic model - decide if `role` field should be removed or computed
- [ ] Update `UserCreate` schema - remove `role` parameter or make it optional
- [ ] Update `UserUpdate` schema - remove `role` field

**File:** `src/orchestrator/app/db/models.py`
- [ ] Check `AuthUser` model (if different from shared User) and remove role column
- [ ] Update any comments that reference `users.role` column

### 3. Service Layer Changes

**File:** `src/orchestrator/app/services/rbac_v2.py`
- [ ] Remove fallback check for `users.role` column in `get_user_roles()` (lines 66-72)
- [ ] Update function to only query `user_roles` table
- [ ] Remove `AuthUser` import if no longer needed

**File:** `src/shared/auth/manager.py`
- [ ] Remove fallback to `user.role` in `create_user_tokens()` (lines 95-100)
- [ ] Update `create_user()` method to:
  - Remove `role` parameter (line 326)
  - Create user without role column
  - Insert role into `user_roles` table instead
- [ ] Update any other methods that read/write `user.role`

### 4. Router/API Changes

**File:** `src/orchestrator/app/routers/admin_user_roles.py`
- [ ] Update `get_user()` endpoint (line 156):
  - Fetch primary system role from `user_roles` table instead of `user.role`
  - Use `get_user_system_roles()` helper or query directly
- [ ] Update `get_user_roles()` endpoint (line 193):
  - Remove `user.role` fallback (line 193-194)
  - Get system roles only from `user_roles` table
- [ ] Update `update_user_roles()` endpoint (lines 300-305):
  - Remove `user.role = request.system_roles[0]` assignment
  - Remove check for primary system role (line 324-326)
  - All roles should be managed through `user_roles` table
- [ ] Update `delete_user_role()` endpoint (line 462):
  - Remove check for primary system role
  - Allow deletion of any role from `user_roles` table

**File:** `src/orchestrator/app/routers/admin_user_roles.py`
- [ ] Update comments that mention "users.role" (line 268)

**File:** `src/orchestrator/app/auth/router.py`
- [ ] Update `create_user()` endpoint to not set `role` on User model
- [ ] Insert role into `user_roles` table after user creation
- [ ] Update any endpoints that return `user.role`

**File:** `src/orchestrator/app/routers/admin_gateway_providers.py`
- [ ] Check if any code references `user.role` (grep found line 53 but may be TokenPayload)

**File:** `src/orchestrator/app/routers/admin_gateway_metrics.py`
- [ ] Check if any code references `user.role` (grep found line 101 but may be TokenPayload)

**File:** `src/orchestrator/app/routers/use_case_validation.py`
- [ ] Check `current_user.role` usage (line 117) - may be TokenPayload, not User model

**File:** `src/orchestrator/app/routers/tools_testing.py`
- [ ] Check `current_user.role` usage (lines 126, 135) - may be TokenPayload

**File:** `src/orchestrator/app/routers/admin_audit.py`
- [ ] Check if any User model role access exists

**File:** `src/orchestrator/app/routers/orchestrator.py`
- [ ] Check `current_user.role` usage (lines 339, 594) - may be TokenPayload

**File:** `src/orchestrator/app/routers/use_cases.py`
- [ ] Check `current_user.role` usage (line 533) - may be TokenPayload

**File:** `src/orchestrator/app/services/rbac.py`
- [ ] Update `user.role == "admin"` checks (line 68)
- [ ] Update `str(user.role)` references (lines 151, 250)
- [ ] Replace with `get_user_roles()` or `get_user_system_roles()` calls

**File:** `src/orchestrator/app/auth/router.py`
- [ ] Update all `user.role` references (lines 184, 209, 212, 323, 336, 339, 658, 666)
- [ ] Replace with role from `user_roles` table

**File:** `src/orchestrator/app/auth/utils.py`
- [ ] Update `user.role` reference (line 170)

**File:** `src/orchestrator/app/routers/tools_developer.py`
- [ ] Check `current_user.role` usage (lines 40, 94, 97, 103) - may be TokenPayload

**File:** `src/orchestrator/app/routers/tools_analytics.py`
- [ ] Check `current_user.role` usage (line 185) - may be TokenPayload

### 5. Seed Script Changes

**File:** `ops/database/seed/001_seed_users.sql`
- [ ] Remove `role` from INSERT statement column list (line 52)
- [ ] Remove `role` values from all INSERT VALUES (lines 59, 69, 79, etc.)
- [ ] Keep the section that inserts roles into `user_roles` table (lines 233-251)
- [ ] Update verification section to not check `users.role`

### 6. Test Updates

**Files:** All test files that reference `user.role`
- [ ] Update test fixtures to not set `role` on User objects
- [ ] Update tests to insert roles into `user_roles` table instead
- [ ] Update assertions that check `user.role`
- [ ] Update mocks to not include `role` attribute

**Key test files to check:**
- `src/orchestrator/tests/unit/services/test_rbac_v2.py`
- `src/orchestrator/tests/unit/routers/test_admin_user_roles.py`
- `src/shared/tests/unit/test_auth_manager.py`
- `src/orchestrator/tests/unit/auth/test_router.py`
- `src/orchestrator/tests/unit/services/test_rbac.py`

### 7. Documentation Updates

**Files:**
- [ ] Update `docs/development/adrs/ADR-060-Corrected-RBAC-Architecture.md` if it references `users.role`
- [ ] Update `docs/architecture/database/SCHEMA.md`
- [ ] Update `ops/database/README.md` if it mentions `users.role`
- [ ] Update any API documentation that shows `role` in user responses

## Implementation Order

1. **Phase 1: Code Updates (Backward Compatible)**
   - Update all code to read from `user_roles` table only
   - Keep `users.role` column in schema (not used, but present)
   - Update seed scripts to not populate `users.role`
   - Test thoroughly

2. **Phase 2: Database Migration**
   - Create migration script to drop `role` column
   - Run migration on test database
   - Verify all functionality works

3. **Phase 3: Cleanup**
   - Remove any remaining references
   - Update documentation
   - Final testing

## Testing Checklist

- [ ] User creation works (roles go to `user_roles` table)
- [ ] User authentication works (tokens include roles from `user_roles`)
- [ ] User detail endpoints return correct role information
- [ ] User role management endpoints work (get/update/delete roles)
- [ ] RBAC checks work correctly (`get_user_roles()`, `has_role()`, etc.)
- [ ] Use case access control works (admin sees all use cases)
- [ ] Seed scripts create users with roles in `user_roles` table
- [ ] All existing tests pass
- [ ] Integration tests pass

## Risks & Considerations

1. **Breaking Changes:**
   - Any external code/scripts that read `users.role` will break
   - API responses that include `role` field need to compute it from `user_roles`

2. **Migration Path:**
   - Need to ensure all existing users have roles in `user_roles` table before dropping column
   - Migration script should verify data before dropping

3. **Performance:**
   - Fetching roles now requires a JOIN or separate query
   - Consider caching if performance becomes an issue

4. **Default Role:**
   - What happens if a user has no roles in `user_roles` table?
   - Should we enforce at least one system role?

## Notes

- The `TokenPayload.role` field is different - it's computed from `roles` list, not from `users.role`
- Many `current_user.role` references are actually `TokenPayload.role`, not `User.role` - verify before changing
- The `UserBase` Pydantic model has a `role` field - decide if this should be:
  - Removed entirely
  - Made optional and computed from `user_roles`
  - Kept for backward compatibility but marked deprecated
