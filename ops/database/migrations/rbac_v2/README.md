# RBAC V2 Migrations

**Purpose:** Database schema changes for RBAC V2 architecture (ADR-060)
**Date:** 2025-12-08
**Status:** Ready for execution
**Phase:** Phase 1 - Database Schema Updates

---

## Overview

These migrations implement the corrected two-tier RBAC architecture with team-based use case development and default-deny resource access.

**Related Documentation:**

- [ADR-060: Corrected RBAC Architecture](../../../../docs/development/adrs/ADR-060-Corrected-RBAC-Architecture.md)
- [RBAC V2 Implementation Plan](../../../../docs/development/plans/RBAC_V2_IMPLEMENTATION_PLAN.md)

---

## Migration Files

### 001_add_team_id_to_use_cases.sql

**Purpose:** Add team_id column to use_cases table for team isolation

**Changes:**

- Adds `team_id VARCHAR(100)` column to `use_cases` table
- Creates index `idx_use_cases_team_lifecycle` on (team_id, lifecycle_state)
- Sets default value `'team:default'` for existing use cases
- Adds column comment explaining team format

**Impact:** Non-breaking - existing use cases remain functional

**Execution Time:** ~100ms

---

### 002_create_role_collection_assignments.sql

**Purpose:** Create table for assigning document collections to roles

**Changes:**

- Creates `role_collection_assignments` table
- Adds indexes for role and collection lookups
- Adds foreign key to collections table
- Adds column comments

**Schema:**

```sql
CREATE TABLE role_collection_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name VARCHAR(50) NOT NULL,
    collection_id UUID NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(role_name, collection_id)
);
```

**Impact:** Additive - no existing data affected

**Execution Time:** ~50ms

---

### 003_migrate_users_to_user_roles.sql

**Purpose:** Migrate existing users.role column to user_roles table

**Changes:**

- Copies existing role data from `users.role` to `user_roles` table
- Preserves backward compatibility (does NOT drop users.role column yet)
- Idempotent - safe to run multiple times
- Skips users already migrated

**Migration Logic:**

```sql
INSERT INTO user_roles (user_id, role, granted_by, granted_at, metadata)
SELECT
    id,
    role,
    NULL,  -- System migration
    created_at,
    '{}'::jsonb
FROM users
WHERE role IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM user_roles ur
      WHERE ur.user_id = users.id
      AND ur.role = users.role
  );
```

**Impact:** Non-breaking - users.role column kept for backward compatibility

**Execution Time:** ~500ms (depends on user count)

**Note:** The `users.role` column will be dropped in Phase 5 (Cleanup) after verifying everything works in production.

---

## Execution Order

**IMPORTANT:** Run migrations in sequential order:

1. `001_add_team_id_to_use_cases.sql`
2. `002_create_role_collection_assignments.sql`
3. `003_migrate_users_to_user_roles.sql`

---

## Running Migrations

### Automated Execution

Use the provided shell script to run all migrations:

```bash
# From project root
cd ops/database/migrations/rbac_v2
./run_migrations.sh
```

The script will:

- Load environment variables from `config/env/.env`
- Execute migrations in order
- Verify each migration succeeded
- Provide detailed output

### Manual Execution

```bash
# Load environment variables
export $(grep -v '^#' config/env/.env | xargs)

# Run each migration
PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
  -h $POSTGRES_HOST -p $POSTGRES_PORT \
  -U $POSTGRES_USER -d $POSTGRES_DB \
  -f 001_add_team_id_to_use_cases.sql

PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
  -h $POSTGRES_HOST -p $POSTGRES_PORT \
  -U $POSTGRES_USER -d $POSTGRES_DB \
  -f 002_create_role_collection_assignments.sql

PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
  -h $POSTGRES_HOST -p $POSTGRES_PORT \
  -U $POSTGRES_USER -d $POSTGRES_DB \
  -f 003_migrate_users_to_user_roles.sql
```

### Testing Migrations

Use the test script to verify migrations in a test environment:

```bash
# From project root
cd ops/database/migrations/rbac_v2
./test_migrations.sh
```

The test script will:

- Use test database credentials from `config/env/env.test`
- Run all migrations
- Verify schema changes
- Check data integrity

---

## Verification

### After Running Migrations

```sql
-- 1. Verify team_id column exists
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'use_cases' AND column_name = 'team_id';

-- 2. Verify role_collection_assignments table exists
SELECT table_name
FROM information_schema.tables
WHERE table_name = 'role_collection_assignments';

-- 3. Verify user role migration
SELECT
    COUNT(*) as total_users,
    COUNT(DISTINCT ur.user_id) as users_with_roles,
    COUNT(*) FILTER (WHERE u.role IS NOT NULL) as users_with_old_role
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id;

-- Should show: total_users = users_with_roles (all migrated)

-- 4. Check existing use cases have default team
SELECT team_id, COUNT(*)
FROM use_cases
GROUP BY team_id;

-- Should show: team:default with count of existing use cases
```

---

## Rollback

### Emergency Rollback

If issues arise, rollback in reverse order:

```sql
-- Rollback 003: Remove migrated role data (optional - doesn't break anything)
DELETE FROM user_roles WHERE granted_by IS NULL;

-- Rollback 002: Drop role_collection_assignments table
DROP TABLE IF EXISTS role_collection_assignments CASCADE;

-- Rollback 001: Remove team_id column
ALTER TABLE use_cases DROP COLUMN IF EXISTS team_id;
DROP INDEX IF EXISTS idx_use_cases_team_lifecycle;
```

**Note:** These rollbacks are safe because:

- Migration 003 doesn't delete original data (users.role column preserved)
- Migration 002 is additive (new table)
- Migration 001 is additive (new column with default value)

---

## Impact Assessment

### Breaking Changes

**None** - All migrations are backward compatible.

### Data Changes

- Existing use cases: Assigned to `team:default`
- Existing users: Role data copied to `user_roles` table
- New table: `role_collection_assignments` (empty)

### Performance Impact

**Minimal:**

- New indexes add ~1-2ms to write operations
- Query performance unchanged or improved (team filtering)
- Migration execution: < 1 second total

---

## Next Steps

After successful migration:

1. ✅ Verify all migrations completed successfully
2. ⏳ Deploy backend RBAC V2 service (`src/orchestrator/app/services/rbac_v2.py`)
3. ⏳ Deploy updated use case management APIs
4. ⏳ Deploy frontend role management UI updates
5. ⏳ Test team isolation functionality
6. ⏳ Monitor logs for any RBAC-related errors

---

## Troubleshooting

### Migration 001 Fails

**Error:** `column "team_id" already exists`

**Solution:** Migration is idempotent - this is expected if run multiple times. Safe to continue.

### Migration 002 Fails

**Error:** `relation "role_collection_assignments" already exists`

**Solution:** Migration is idempotent - table already created. Safe to continue.

### Migration 003 Fails

**Error:** `duplicate key value violates unique constraint`

**Solution:** User roles already migrated. Safe to continue.

### Verification Shows Incomplete Migration

```sql
-- Check which users weren't migrated
SELECT u.id, u.username, u.role
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id AND ur.role = u.role
WHERE u.role IS NOT NULL AND ur.id IS NULL;
```

**Solution:** Re-run migration 003 - it's idempotent and will only migrate missing users.

---

## Support

**Questions or Issues:**

- Check [ADR-060](../../../../docs/development/adrs/ADR-060-Corrected-RBAC-Architecture.md) for architecture details
- Check [RBAC V2 Implementation Plan](../../../../docs/development/plans/RBAC_V2_IMPLEMENTATION_PLAN.md) for full context
- Review [Testing Guide](../../../../docs/testing/TESTING_GUIDE.md) for test procedures

---

**Last Updated:** 2025-12-09
**Status:** Ready for Production
**Tested:** ✅ Development, ⏳ Staging, ⏳ Production
