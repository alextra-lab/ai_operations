-- Migration: 003_migrate_users_to_user_roles.sql
-- Date: 2025-12-08
-- Purpose: Migrate existing users.role to user_roles table for RBAC V2
-- ADR: ADR-060 - Corrected RBAC Architecture
-- Phase: Phase 1 - Database Schema Updates (Task 1.1)
-- Note: This maintains backward compatibility - users.role column is NOT dropped yet
--       (will be removed in Phase 5 after stable production deployment)

-- ==============================================================================
-- PART 1: Migrate existing users.role to user_roles table
-- ==============================================================================

DO $$
DECLARE
    migrated_count INTEGER;
    skipped_count INTEGER;
BEGIN
    -- Insert users.role into user_roles table (if not already present)
    INSERT INTO user_roles (id, user_id, role, granted_by, granted_at, metadata)
    SELECT
        gen_random_uuid(),
        id as user_id,
        role,
        NULL as granted_by,  -- System migration
        created_at as granted_at,
        jsonb_build_object(
            'migrated_from', 'users.role',
            'migration_date', NOW()::text,
            'migration_version', '003'
        ) as metadata
    FROM users
    WHERE role IS NOT NULL
      AND role != ''
      AND NOT EXISTS (
          SELECT 1 FROM user_roles ur
          WHERE ur.user_id = users.id
            AND ur.role = users.role
      );

    GET DIAGNOSTICS migrated_count = ROW_COUNT;

    IF migrated_count > 0 THEN
        RAISE NOTICE 'Migrated % users from users.role to user_roles table', migrated_count;
    ELSE
        RAISE NOTICE 'No new users to migrate (all roles already in user_roles)';
    END IF;

    -- Count users that were skipped (already have role in user_roles)
    SELECT COUNT(*) INTO skipped_count
    FROM users u
    WHERE u.role IS NOT NULL
      AND u.role != ''
      AND EXISTS (
          SELECT 1 FROM user_roles ur
          WHERE ur.user_id = u.id
            AND ur.role = u.role
      );

    IF skipped_count > 0 THEN
        RAISE NOTICE 'Skipped % users (roles already exist in user_roles)', skipped_count;
    END IF;
END $$;

-- ==============================================================================
-- PART 2: Verify migration success
-- ==============================================================================

DO $$
DECLARE
    total_users INTEGER;
    migrated_users INTEGER;
    users_with_roles INTEGER;
    verification_passed BOOLEAN := TRUE;
BEGIN
    -- Count total users with roles
    SELECT COUNT(*) INTO total_users
    FROM users
    WHERE role IS NOT NULL
      AND role != '';

    -- Count distinct users with roles in user_roles (from migration)
    SELECT COUNT(DISTINCT user_id) INTO migrated_users
    FROM user_roles
    WHERE metadata->>'migrated_from' = 'users.role';

    -- Count all users with any role in user_roles
    SELECT COUNT(DISTINCT user_id) INTO users_with_roles
    FROM user_roles;

    RAISE NOTICE 'Migration 003 verification:';
    RAISE NOTICE '  - Total users with role in users.role: %', total_users;
    RAISE NOTICE '  - Users migrated (from users.role): %', migrated_users;
    RAISE NOTICE '  - Total users with roles in user_roles: %', users_with_roles;

    -- Verify: All users with roles should have entries in user_roles
    -- (Note: Some users might have been manually added to user_roles before migration)
    IF migrated_users < total_users THEN
        -- Check if the difference is due to users already having roles
        DECLARE
            users_without_migration INTEGER;
        BEGIN
            SELECT COUNT(*) INTO users_without_migration
            FROM users u
            WHERE u.role IS NOT NULL
              AND u.role != ''
              AND NOT EXISTS (
                  SELECT 1 FROM user_roles ur
                  WHERE ur.user_id = u.id
                    AND ur.role = u.role
              );

            IF users_without_migration > 0 THEN
                RAISE WARNING 'Migration incomplete: % users with roles not found in user_roles', users_without_migration;
                verification_passed := FALSE;
            ELSE
                RAISE NOTICE '  - All users with roles have entries in user_roles (some pre-existing)';
            END IF;
        END;
    ELSE
        RAISE NOTICE '  - Migration successful: All users migrated';
    END IF;

    -- Check for common system roles
    DECLARE
        system_roles_count INTEGER;
    BEGIN
        SELECT COUNT(DISTINCT user_id) INTO system_roles_count
        FROM user_roles
        WHERE role IN ('admin', 'corpus_admin', 'use_case_admin', 'tools_admin', 'conversations', 'role_admin', 'user', 'service');

        RAISE NOTICE '  - Users with system roles in user_roles: %', system_roles_count;
    END;

    IF verification_passed THEN
        RAISE NOTICE '  - Verification: PASSED';
    ELSE
        RAISE EXCEPTION 'Migration verification failed - see warnings above';
    END IF;
END $$;

-- ==============================================================================
-- PART 3: Create index for performance (if not exists)
-- ==============================================================================

-- Index on user_id for fast lookups
CREATE INDEX IF NOT EXISTS idx_user_roles_user_id_migration
ON user_roles(user_id);

-- Index on role for role-based queries
CREATE INDEX IF NOT EXISTS idx_user_roles_role_migration
ON user_roles(role);

-- ==============================================================================
-- NOTES
-- ==============================================================================

-- IMPORTANT: The users.role column is NOT dropped in this migration.
-- It will be removed in Phase 5 (Cleanup & Documentation) after:
-- 1. Production deployment is stable
-- 2. All code has been updated to use user_roles table
-- 3. Verification period (1 week) has passed
--
-- This maintains backward compatibility during the transition period.

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Migration 003_migrate_users_to_user_roles completed successfully';
    RAISE NOTICE 'NOTE: users.role column is preserved for backward compatibility';
    RAISE NOTICE '      It will be removed in Phase 5 after stable production deployment';
END $$;
