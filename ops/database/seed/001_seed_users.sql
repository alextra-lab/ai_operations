-- ============================================================================
-- Seed Data: Default Users (UPDATED for RBAC V2 - All System Roles)
-- ============================================================================
-- Description: Creates demo users for all 10 system roles (RBAC V2, ADR-060)
-- Prerequisites: 000_complete_init.sql must be run first
--
-- System Roles (10 total):
--   - admin                      → Full system access
--   - corpus_admin               → Document/use case development
--   - developer                  → Team-scoped use case development
--   - use_case_admin             → Use case super admin (all teams)
--   - tools_admin                → MCP/tools management
--   - role_admin                 → Role management
--   - use_case_publisher         → Use case approval/publishing
--   - conversations_privileged   → Conversations feature access
--   - user                       → Standard end-user
--   - service                    → API automation
--
-- Original Users (6):
--   - admin (admin) - Full system administrator
--   - corpus_manager (corpus_admin) - Document and use case developer
--   - uc_publisher (use_case_publisher) - Use case reviewer/publisher
--   - conv_analyst (conversations_privileged) - Conversations access
--   - service_account (service) - API automation
--   - testuser (user) - Standard end-user
--
-- New Demo Users (11):
--   - admin2 (admin) - Additional admin for demo
--   - corpus_dev (corpus_admin) - Additional corpus admin
--   - developer1 (developer) - Team-scoped use case developer
--   - developer2 (developer) - Team-scoped use case developer
--   - uc_admin (use_case_admin) - Use case super admin (all teams)
--   - tools_manager (tools_admin) - MCP/tools management
--   - role_manager (role_admin) - Role management
--   - publisher2 (use_case_publisher) - Additional publisher
--   - analyst_conv (conversations_privileged) - Additional conversations user
--   - analyst1 (user) - Standard user for RBAC demo
--   - analyst2 (user) - Standard user for RBAC demo
--
-- Usage:
--   PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
--     -h $POSTGRES_HOST -p $POSTGRES_PORT \
--     -U $POSTGRES_USER -d $POSTGRES_DB \
--     -f ops/database/seed/001_seed_users.sql
--
-- Note: Default password 'adminpassword' MUST be changed in production!
-- ============================================================================
BEGIN;
-- Insert default users (Layer 1: System Roles)
INSERT INTO users (
        username,
        full_name,
        email,
        hashed_password,
        role,
        is_active,
        center_id,
        user_metadata
    )
VALUES (
        'admin',
        'System Administrator',
        'admin@example.com',
        '$2b$12$tfGexjAaqWbPYand3DPqouy9d5adFeksdPVk1aOQInD/XhdCwZY/6',
        -- Default: 'adminpassword'
        'admin',
        TRUE,
        'headquarters',
        '{"role_description": "System administrator with full access", "created_by": "system_init"}'::jsonb
    ),
    (
        'corpus_manager',
        'Corpus Manager',
        'corpus@example.com',
        '$2b$12$tfGexjAaqWbPYand3DPqouy9d5adFeksdPVk1aOQInD/XhdCwZY/6',
        -- Default: 'adminpassword'
        'corpus_admin',
        TRUE,
        'headquarters',
        '{"role_description": "Document and use case development administrator", "created_by": "system_init"}'::jsonb
    ),
    (
        'uc_publisher',
        'Use Case Publisher',
        'publisher@example.com',
        '$2b$12$tfGexjAaqWbPYand3DPqouy9d5adFeksdPVk1aOQInD/XhdCwZY/6',
        -- Default: 'adminpassword'
        'use_case_publisher',
        TRUE,
        'headquarters',
        '{"role_description": "Use case reviewer and publisher", "created_by": "system_init"}'::jsonb
    ),
    (
        'conv_analyst',
        'Conversations Analyst',
        'conv_analyst@example.com',
        '$2b$12$tfGexjAaqWbPYand3DPqouy9d5adFeksdPVk1aOQInD/XhdCwZY/6',
        -- Default: 'adminpassword'
        'conversations_privileged',
        TRUE,
        'soc_team',
        '{"role_description": "Privileged conversations feature access", "created_by": "system_init"}'::jsonb
    ),
    (
        'service_account',
        'Service Account',
        'service@example.com',
        '$2b$12$tfGexjAaqWbPYand3DPqouy9d5adFeksdPVk1aOQInD/XhdCwZY/6',
        -- Default: 'adminpassword'
        'service',
        TRUE,
        'api_automation',
        '{"role_description": "API automation service account", "created_by": "system_init"}'::jsonb
    ),
    (
        'testuser',
        'Test User',
        'testuser@example.com',
        '$2b$12$tfGexjAaqWbPYand3DPqouy9d5adFeksdPVk1aOQInD/XhdCwZY/6',
        -- Default: 'adminpassword'
        'user',
        TRUE,
        'test_center',
        '{"role_description": "Standard end-user for testing", "created_by": "system_init"}'::jsonb
    ),
    -- Additional demo users (RBAC V2 - covering all system roles)
    (
        'admin2',
        'Admin 2',
        'admin2@example.com',
        '$2b$12$tfGexjAaqWbPYand3DPqouy9d5adFeksdPVk1aOQInD/XhdCwZY/6',
        -- Default: 'adminpassword'
        'admin',
        TRUE,
        'headquarters',
        '{"role_description": "Additional admin for demo", "created_by": "system_init", "seed_script": "001"}'::jsonb
    ),
    (
        'corpus_dev',
        'Corpus Developer',
        'corpus_dev@example.com',
        '$2b$12$tfGexjAaqWbPYand3DPqouy9d5adFeksdPVk1aOQInD/XhdCwZY/6',
        -- Default: 'adminpassword'
        'corpus_admin',
        TRUE,
        'development_team',
        '{"role_description": "Additional corpus admin", "created_by": "system_init", "seed_script": "001"}'::jsonb
    ),
    (
        'developer1',
        'Developer 1',
        'developer1@example.com',
        '$2b$12$tfGexjAaqWbPYand3DPqouy9d5adFeksdPVk1aOQInD/XhdCwZY/6',
        -- Default: 'adminpassword'
        'developer',
        TRUE,
        'development_team',
        '{"role_description": "Team-scoped use case developer", "created_by": "system_init", "seed_script": "001"}'::jsonb
    ),
    (
        'developer2',
        'Developer 2',
        'developer2@example.com',
        '$2b$12$tfGexjAaqWbPYand3DPqouy9d5adFeksdPVk1aOQInD/XhdCwZY/6',
        -- Default: 'adminpassword'
        'developer',
        TRUE,
        'soc_team',
        '{"role_description": "Team-scoped use case developer", "created_by": "system_init", "seed_script": "001"}'::jsonb
    ),
    (
        'uc_admin',
        'Use Case Admin',
        'uc_admin@example.com',
        '$2b$12$tfGexjAaqWbPYand3DPqouy9d5adFeksdPVk1aOQInD/XhdCwZY/6',
        -- Default: 'adminpassword'
        'use_case_admin',
        TRUE,
        'headquarters',
        '{"role_description": "Use case super admin (all teams)", "created_by": "system_init", "seed_script": "001"}'::jsonb
    ),
    (
        'tools_manager',
        'Tools Manager',
        'tools_manager@example.com',
        '$2b$12$tfGexjAaqWbPYand3DPqouy9d5adFeksdPVk1aOQInD/XhdCwZY/6',
        -- Default: 'adminpassword'
        'tools_admin',
        TRUE,
        'headquarters',
        '{"role_description": "MCP/tools management", "created_by": "system_init", "seed_script": "001"}'::jsonb
    ),
    (
        'role_manager',
        'Role Manager',
        'role_manager@example.com',
        '$2b$12$tfGexjAaqWbPYand3DPqouy9d5adFeksdPVk1aOQInD/XhdCwZY/6',
        -- Default: 'adminpassword'
        'role_admin',
        TRUE,
        'headquarters',
        '{"role_description": "Role management", "created_by": "system_init", "seed_script": "001"}'::jsonb
    ),
    (
        'publisher2',
        'Publisher 2',
        'publisher2@example.com',
        '$2b$12$tfGexjAaqWbPYand3DPqouy9d5adFeksdPVk1aOQInD/XhdCwZY/6',
        -- Default: 'adminpassword'
        'use_case_publisher',
        TRUE,
        'governance_team',
        '{"role_description": "Additional publisher", "created_by": "system_init", "seed_script": "001"}'::jsonb
    ),
    (
        'analyst_conv',
        'Analyst Conversations',
        'analyst_conv@example.com',
        '$2b$12$tfGexjAaqWbPYand3DPqouy9d5adFeksdPVk1aOQInD/XhdCwZY/6',
        -- Default: 'adminpassword'
        'conversations_privileged',
        TRUE,
        'soc_team',
        '{"role_description": "Additional conversations user", "created_by": "system_init", "seed_script": "001"}'::jsonb
    ),
    (
        'analyst1',
        'SOC Analyst 1',
        'analyst1@example.com',
        '$2b$12$tfGexjAaqWbPYand3DPqouy9d5adFeksdPVk1aOQInD/XhdCwZY/6',
        -- Default: 'adminpassword'
        'user',
        TRUE,
        'soc_team',
        '{"role_description": "Standard user for RBAC demo", "created_by": "system_init", "seed_script": "001"}'::jsonb
    ),
    (
        'analyst2',
        'SOC Analyst 2',
        'analyst2@example.com',
        '$2b$12$tfGexjAaqWbPYand3DPqouy9d5adFeksdPVk1aOQInD/XhdCwZY/6',
        -- Default: 'adminpassword'
        'user',
        TRUE,
        'soc_team',
        '{"role_description": "Standard user for RBAC demo", "created_by": "system_init", "seed_script": "001"}'::jsonb
    ) ON CONFLICT (username) DO NOTHING;
-- ============================================================================
-- Insert System Roles into user_roles table (RBAC V2)
-- ============================================================================
-- Per ADR-060, system roles are stored in user_roles table (not just users.role column)
-- This ensures get_user_roles() can find roles from the primary RBAC V2 storage
INSERT INTO user_roles (user_id, role, granted_by, granted_at, metadata)
SELECT id AS user_id,
    role,
    NULL AS granted_by,
    NOW() AS granted_at,
    jsonb_build_object(
        'seed_script',
        '001',
        'system_role',
        true,
        'created_by',
        'system_init'
    ) AS metadata
FROM users
WHERE username IN (
        'admin',
        'admin2',
        'corpus_manager',
        'corpus_dev',
        'developer1',
        'developer2',
        'uc_admin',
        'tools_manager',
        'role_manager',
        'uc_publisher',
        'publisher2',
        'conv_analyst',
        'analyst_conv',
        'service_account',
        'testuser',
        'analyst1',
        'analyst2'
    )
    AND role IS NOT NULL ON CONFLICT (user_id, role) DO NOTHING;
COMMIT;
-- ============================================================================
-- Verification
-- ============================================================================
DO $$
DECLARE user_count INTEGER;
role_count INTEGER;
BEGIN
SELECT COUNT(*) INTO user_count
FROM users
WHERE username IN (
        'admin',
        'admin2',
        'corpus_manager',
        'corpus_dev',
        'developer1',
        'developer2',
        'uc_admin',
        'tools_manager',
        'role_manager',
        'uc_publisher',
        'publisher2',
        'conv_analyst',
        'analyst_conv',
        'service_account',
        'testuser',
        'analyst1',
        'analyst2'
    );
SELECT COUNT(DISTINCT role) INTO role_count
FROM users
WHERE username IN (
        'admin',
        'admin2',
        'corpus_manager',
        'corpus_dev',
        'developer1',
        'developer2',
        'uc_admin',
        'tools_manager',
        'role_manager',
        'uc_publisher',
        'publisher2',
        'conv_analyst',
        'analyst_conv',
        'service_account',
        'testuser',
        'analyst1',
        'analyst2'
    );
RAISE NOTICE '✅ Demo users seeded successfully!';
RAISE NOTICE '   - Total users created: %',
user_count;
RAISE NOTICE '   - System roles covered: %',
role_count;
RAISE NOTICE '';
RAISE NOTICE '⚠️  SECURITY WARNING:';
RAISE NOTICE '   - Default password for all users: adminpassword';
RAISE NOTICE '   - Change passwords immediately in production!';
RAISE NOTICE '';
RAISE NOTICE '👤 User Accounts (RBAC V2 - All 10 System Roles):';
RAISE NOTICE '   Administrators: admin, admin2';
RAISE NOTICE '   Corpus Admins: corpus_manager, corpus_dev';
RAISE NOTICE '   Developers: developer1, developer2 (team-scoped)';
RAISE NOTICE '   Use Case Admin: uc_admin (all teams)';
RAISE NOTICE '   Tools Admin: tools_manager';
RAISE NOTICE '   Role Admin: role_manager';
RAISE NOTICE '   Publishers: uc_publisher, publisher2';
RAISE NOTICE '   Conversation Users: conv_analyst, analyst_conv';
RAISE NOTICE '   Standard Users: testuser, analyst1, analyst2';
RAISE NOTICE '   Service Account: service_account';
RAISE NOTICE '';
RAISE NOTICE '📝 Note: Team memberships will be assigned in 008_seed_rbac_v2_assignments.sql';
RAISE NOTICE '';
RAISE NOTICE '✅ System roles have been inserted into user_roles table (RBAC V2)';
END $$;
-- Display created users
SELECT username,
    full_name,
    role AS system_role,
    center_id,
    is_active,
    created_at
FROM users
WHERE username IN (
        'admin',
        'admin2',
        'corpus_manager',
        'corpus_dev',
        'developer1',
        'developer2',
        'uc_admin',
        'tools_manager',
        'role_manager',
        'uc_publisher',
        'publisher2',
        'conv_analyst',
        'analyst_conv',
        'service_account',
        'testuser',
        'analyst1',
        'analyst2'
    )
ORDER BY CASE
        role
        WHEN 'admin' THEN 1
        WHEN 'corpus_admin' THEN 2
        WHEN 'developer' THEN 3
        WHEN 'use_case_admin' THEN 4
        WHEN 'tools_admin' THEN 5
        WHEN 'role_admin' THEN 6
        WHEN 'use_case_publisher' THEN 7
        WHEN 'conversations_privileged' THEN 8
        WHEN 'service' THEN 9
        WHEN 'user' THEN 10
    END,
    username;
