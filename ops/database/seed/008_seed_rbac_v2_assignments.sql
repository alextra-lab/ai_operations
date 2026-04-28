-- ============================================================================
-- Seed Data: RBAC V2 Team Memberships (ADR-060)
-- ============================================================================
-- Description: Assigns users to developer teams for draft use case isolation
-- Prerequisites: 000_complete_init.sql, 001_seed_users.sql must be run first
--
-- RBAC V2 Architecture (ADR-060):
--   - Tier 1: System Roles (stored in users.role)
--   - Tier 2: Grouping Roles (stored in user_roles.role)
--   - Tier 3: Developer Teams (stored in user_roles.role with 'team:' prefix)
--
-- Team Structure:
--   - team:csirt_security - CSIRT Security Team (incident response use cases)
--   - team:soc_governance - SOC Governance Team (compliance/governance use cases)
--   - team:development - Development Team (development/testing use cases)
--
-- Team Memberships:
--   - team:csirt_security: analyst1, analyst2, conv_analyst
--   - team:soc_governance: uc_publisher, publisher2
--   - team:development: corpus_manager, corpus_dev
--
-- Usage:
--   PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
--     -h $POSTGRES_HOST -p $POSTGRES_PORT \
--     -U $POSTGRES_USER -d $POSTGRES_DB \
--     -f ops/database/seed/008_seed_rbac_v2_assignments.sql
-- ============================================================================

BEGIN;

-- ============================================================================
-- Create Team Memberships (Tier 3: Developer Teams)
-- ============================================================================
-- Team memberships are stored in user_roles table with 'team:' prefix
-- These provide draft use case isolation between teams

INSERT INTO user_roles (user_id, role, granted_by, granted_at, metadata)
VALUES
  -- team:csirt_security - CSIRT Security Team
  (
    (SELECT id FROM users WHERE username = 'analyst1'),
    'team:csirt_security',
    NULL,
    NOW(),
    '{"seed_script":"008","team_display_name":"CSIRT Security Team"}'::jsonb
  ),
  (
    (SELECT id FROM users WHERE username = 'analyst2'),
    'team:csirt_security',
    NULL,
    NOW(),
    '{"seed_script":"008","team_display_name":"CSIRT Security Team"}'::jsonb
  ),
  (
    (SELECT id FROM users WHERE username = 'conv_analyst'),
    'team:csirt_security',
    NULL,
    NOW(),
    '{"seed_script":"008","team_display_name":"CSIRT Security Team"}'::jsonb
  ),

  -- team:soc_governance - SOC Governance Team
  (
    (SELECT id FROM users WHERE username = 'uc_publisher'),
    'team:soc_governance',
    NULL,
    NOW(),
    '{"seed_script":"008","team_display_name":"SOC Governance Team"}'::jsonb
  ),
  (
    (SELECT id FROM users WHERE username = 'publisher2'),
    'team:soc_governance',
    NULL,
    NOW(),
    '{"seed_script":"008","team_display_name":"SOC Governance Team"}'::jsonb
  ),

  -- team:development - Development Team
  (
    (SELECT id FROM users WHERE username = 'corpus_manager'),
    'team:development',
    NULL,
    NOW(),
    '{"seed_script":"008","team_display_name":"Development Team"}'::jsonb
  ),
  (
    (SELECT id FROM users WHERE username = 'corpus_dev'),
    'team:development',
    NULL,
    NOW(),
    '{"seed_script":"008","team_display_name":"Development Team"}'::jsonb
  )
ON CONFLICT (user_id, role) DO NOTHING;

COMMIT;

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
DECLARE
    team_membership_count INTEGER;
    csirt_count INTEGER;
    governance_count INTEGER;
    development_count INTEGER;
BEGIN
    -- Count total team memberships
    SELECT COUNT(*) INTO team_membership_count
    FROM user_roles
    WHERE role LIKE 'team:%'
      AND metadata->>'seed_script' = '008';

    -- Count by team
    SELECT COUNT(*) INTO csirt_count
    FROM user_roles
    WHERE role = 'team:csirt_security'
      AND metadata->>'seed_script' = '008';

    SELECT COUNT(*) INTO governance_count
    FROM user_roles
    WHERE role = 'team:soc_governance'
      AND metadata->>'seed_script' = '008';

    SELECT COUNT(*) INTO development_count
    FROM user_roles
    WHERE role = 'team:development'
      AND metadata->>'seed_script' = '008';

    RAISE NOTICE '✅ Team memberships seeded successfully!';
    RAISE NOTICE '   - Total team memberships: %', team_membership_count;
    RAISE NOTICE '';
    RAISE NOTICE '👥 Team Assignments:';
    RAISE NOTICE '   - team:csirt_security: % members', csirt_count;
    RAISE NOTICE '   - team:soc_governance: % members', governance_count;
    RAISE NOTICE '   - team:development: % members', development_count;
    RAISE NOTICE '';
    RAISE NOTICE '📝 Note: Team memberships enable draft use case isolation.';
    RAISE NOTICE '   Published use cases are visible to all users (team_id = NULL).';
    RAISE NOTICE '   Draft use cases are visible only to team members.';
END $$;

-- Display team memberships
SELECT
    ur.role AS team,
    u.username,
    u.full_name,
    u.role AS system_role,
    ur.granted_at
FROM user_roles ur
JOIN users u ON ur.user_id = u.id
WHERE ur.role LIKE 'team:%'
  AND ur.metadata->>'seed_script' = '008'
ORDER BY ur.role, u.username;
