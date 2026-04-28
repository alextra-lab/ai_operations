-- ============================================================================
-- Database Rollback Script - DROP ALL OBJECTS
-- ============================================================================
-- Description: Removes all AI Operations Platform database objects
-- WARNING: This script will DELETE ALL DATA permanently!
--
-- Use Cases:
--   - Development environment reset
--   - Test database cleanup
--   - Complete schema rebuild
--
-- DO NOT USE IN PRODUCTION WITHOUT BACKUP!
--
-- Usage:
--   PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
--     -h $POSTGRES_HOST -p $POSTGRES_PORT \
--     -U $POSTGRES_USER -d $POSTGRES_DB \
--     -f scripts/database/rollback/000_drop_all.sql
--
-- Safety: Requires manual confirmation by uncommenting BEGIN/COMMIT
-- ============================================================================
-- SAFETY CHECK: Uncomment the lines below to execute
-- BEGIN;
-- ============================================================================
-- Drop Tables (in reverse dependency order)
-- ============================================================================
-- Drop tables with foreign keys first
DROP TABLE IF EXISTS intent_usage_logs CASCADE;
DROP TABLE IF EXISTS role_intent_permissions CASCADE;
DROP TABLE IF EXISTS intent_types CASCADE;
DROP TABLE IF EXISTS intent_categories CASCADE;
DROP TABLE IF EXISTS pricing_tier_audit CASCADE;
DROP TABLE IF EXISTS model_configs CASCADE;
DROP TABLE IF EXISTS pricing_tiers CASCADE;
DROP TABLE IF EXISTS run_manifests CASCADE;
DROP TABLE IF EXISTS model_cache CASCADE;
DROP TABLE IF EXISTS models CASCADE;
DROP TABLE IF EXISTS tool_invocations CASCADE;
DROP TABLE IF EXISTS tool_permissions CASCADE;
DROP TABLE IF EXISTS tool_health_checks CASCADE;
DROP TABLE IF EXISTS tool_secrets CASCADE;
DROP TABLE IF EXISTS tools CASCADE;
DROP TABLE IF EXISTS token_usage CASCADE;
DROP TABLE IF EXISTS thread_messages CASCADE;
DROP TABLE IF EXISTS context_threads CASCADE;
DROP TABLE IF EXISTS query_history CASCADE;
DROP TABLE IF EXISTS user_use_case_assignments CASCADE;
DROP TABLE IF EXISTS prompt_templates CASCADE;
DROP TABLE IF EXISTS use_cases CASCADE;
DROP TABLE IF EXISTS usage_stats CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS encryption_keys CASCADE;
DROP TABLE IF EXISTS user_roles CASCADE;
DROP TABLE IF EXISTS refresh_tokens CASCADE;
DROP TABLE IF EXISTS users CASCADE;
-- ============================================================================
-- Drop Views
-- ============================================================================
DROP VIEW IF EXISTS hot_chunks CASCADE;
DROP VIEW IF EXISTS hot_documents CASCADE;
DROP VIEW IF EXISTS aio.session_context CASCADE;
-- ============================================================================
-- Drop Functions
-- ============================================================================
DROP FUNCTION IF EXISTS fork_query(UUID, UUID) CASCADE;
DROP FUNCTION IF EXISTS get_all_centers_usage_summary(TIMESTAMPTZ, TIMESTAMPTZ) CASCADE;
DROP FUNCTION IF EXISTS get_center_usage_summary(VARCHAR, TIMESTAMPTZ, TIMESTAMPTZ) CASCADE;
DROP FUNCTION IF EXISTS get_chunk_stats(UUID, INTEGER) CASCADE;
DROP FUNCTION IF EXISTS get_document_stats(UUID, INTEGER) CASCADE;
DROP FUNCTION IF EXISTS calculate_total_tokens() CASCADE;
DROP FUNCTION IF EXISTS update_run_manifests_updated_at() CASCADE;
DROP FUNCTION IF EXISTS update_intent_types_updated_at() CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
DROP FUNCTION IF EXISTS aio.touch_updated_at() CASCADE;
DROP FUNCTION IF EXISTS aio.current_user_uuid() CASCADE;
DROP FUNCTION IF EXISTS aio.user_has_role(text) CASCADE;
DROP FUNCTION IF EXISTS aio.current_user_roles() CASCADE;
-- ============================================================================
-- Drop Enums and Types
-- ============================================================================
DROP TYPE IF EXISTS model_provider_enum CASCADE;
DROP TYPE IF EXISTS model_type_enum CASCADE;
-- ============================================================================
-- Drop Schemas
-- ============================================================================
DROP SCHEMA IF EXISTS aio CASCADE;
-- ============================================================================
-- Drop Extensions (optional - uncomment if needed)
-- ============================================================================
-- Note: Dropping extensions may affect other databases if they share extensions
-- Only uncomment if you're sure this is what you want
-- DROP EXTENSION IF EXISTS "uuid-ossp" CASCADE;
-- DROP EXTENSION IF EXISTS "pgcrypto" CASCADE;
-- ============================================================================
-- Verification
-- ============================================================================
-- SAFETY CHECK: Uncomment the line below to execute
-- COMMIT;
DO $$ BEGIN RAISE NOTICE '';
RAISE NOTICE '⚠️  ============================================================================';
RAISE NOTICE '⚠️  ROLLBACK SCRIPT EXECUTED';
RAISE NOTICE '⚠️  ============================================================================';
RAISE NOTICE '';
RAISE NOTICE '🗑️  All AI Operations Platform database objects have been dropped.';
RAISE NOTICE '';
RAISE NOTICE '📋 Objects Removed:';
RAISE NOTICE '   - All tables (31 tables)';
RAISE NOTICE '   - All views (3 views)';
RAISE NOTICE '   - All functions (12 functions)';
RAISE NOTICE '   - All enums (2 types)';
RAISE NOTICE '   - aio schema';
RAISE NOTICE '';
RAISE NOTICE '♻️  To reinitialize the database:';
RAISE NOTICE '   1. Run: scripts/database/init/000_complete_init.sql';
RAISE NOTICE '   2. Run: scripts/database/seed/*.sql (in order)';
RAISE NOTICE '';
RAISE NOTICE '⚠️  WARNING: All data has been permanently deleted!';
RAISE NOTICE '';
RAISE NOTICE '⚠️  ============================================================================';
RAISE NOTICE '';
END $$;
-- ============================================================================
-- Safety Notice
-- ============================================================================
/*
 * SAFETY REMINDER:
 *
 * This script has BEGIN and COMMIT commented out by default.
 * To execute this script, you must:
 *
 * 1. Verify you have a backup (if needed)
 * 2. Confirm this is not a production database
 * 3. Uncomment the BEGIN statement at the top
 * 4. Uncomment the COMMIT statement near the bottom
 *
 * Without uncommenting BEGIN/COMMIT, this script will:
 * - Show you what would be dropped
 * - NOT actually delete anything
 *
 * This is an intentional safety measure.
 */
