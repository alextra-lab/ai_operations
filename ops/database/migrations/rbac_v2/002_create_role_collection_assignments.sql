-- Migration: 002_create_role_collection_assignments.sql
-- Date: 2025-12-08
-- Purpose: Create role_collection_assignments table for RBAC V2 collection access control
-- ADR: ADR-060 - Corrected RBAC Architecture
-- Phase: Phase 1 - Database Schema Updates (Task 1.1)

-- ==============================================================================
-- PART 1: Create role_collection_assignments table
-- ==============================================================================

CREATE TABLE IF NOT EXISTS role_collection_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name VARCHAR(50) NOT NULL,
    collection_id UUID NOT NULL REFERENCES collections(id) ON DELETE CASCADE,

    -- Audit fields
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Constraints
    UNIQUE(role_name, collection_id)
    -- Note: No CHECK constraint on role_name to allow dynamic custom roles
    -- Role names should match user_roles.role but not enforced at DB level
);

-- ==============================================================================
-- PART 2: Create indexes for performance
-- ==============================================================================

CREATE INDEX IF NOT EXISTS idx_role_collection_assignments_role
ON role_collection_assignments(role_name, is_active);

CREATE INDEX IF NOT EXISTS idx_role_collection_assignments_collection
ON role_collection_assignments(collection_id, is_active);

-- Index for expiration queries
CREATE INDEX IF NOT EXISTS idx_role_collection_assignments_expires
ON role_collection_assignments(expires_at)
WHERE expires_at IS NOT NULL;

-- ==============================================================================
-- PART 3: Add table and column comments for documentation
-- ==============================================================================

COMMENT ON TABLE role_collection_assignments IS
    'Assigns document collections to roles. Users inherit collection access through role memberships. Implements ADR-060 Tier 2 resource access control.';

COMMENT ON COLUMN role_collection_assignments.role_name IS
    'Role name (system role or grouping role) that gets access to this collection. Examples: admin, corpus_admin, threat_hunting, incident_response, etc.';

COMMENT ON COLUMN role_collection_assignments.collection_id IS
    'Document collection that this role can access.';

COMMENT ON COLUMN role_collection_assignments.is_active IS
    'Allows temporary revocation without deletion. Application must check this flag.';

COMMENT ON COLUMN role_collection_assignments.expires_at IS
    'Optional expiration timestamp. If NULL, assignment never expires.';

COMMENT ON COLUMN role_collection_assignments.metadata IS
    'Additional context regarding assignment (reason, ticket, etc).';

-- ==============================================================================
-- PART 4: Create updated_at trigger (matching pattern from role_use_case_assignments)
-- ==============================================================================

-- Create function if it doesn't exist
CREATE OR REPLACE FUNCTION update_role_collection_assignments_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS trg_role_collection_assignments_updated_at ON role_collection_assignments;

CREATE TRIGGER trg_role_collection_assignments_updated_at
    BEFORE UPDATE ON role_collection_assignments
    FOR EACH ROW
    EXECUTE FUNCTION update_role_collection_assignments_updated_at();

-- ==============================================================================
-- VERIFICATION
-- ==============================================================================

DO $$
DECLARE
    table_exists BOOLEAN;
    index_count INTEGER;
BEGIN
    -- Check if table exists
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'role_collection_assignments'
    ) INTO table_exists;

    -- Count indexes
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE tablename = 'role_collection_assignments';

    RAISE NOTICE 'Migration 002 verification:';

    IF table_exists THEN
        RAISE NOTICE '  - Table role_collection_assignments: OK';
    ELSE
        RAISE WARNING '  - Table role_collection_assignments: MISSING';
    END IF;

    RAISE NOTICE '  - Indexes created: %', index_count;
    RAISE NOTICE '    (Expected: 3 indexes)';

    -- Verify foreign key constraint
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'role_collection_assignments'
          AND constraint_type = 'FOREIGN KEY'
          AND constraint_name LIKE '%collection_id%'
    ) THEN
        RAISE NOTICE '  - Foreign key to collections: OK';
    ELSE
        RAISE WARNING '  - Foreign key to collections: MISSING';
    END IF;

    -- Verify unique constraint
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'role_collection_assignments'
          AND constraint_type = 'UNIQUE'
    ) THEN
        RAISE NOTICE '  - Unique constraint (role_name, collection_id): OK';
    ELSE
        RAISE WARNING '  - Unique constraint: MISSING';
    END IF;
END $$;

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Migration 002_create_role_collection_assignments completed successfully';
END $$;
