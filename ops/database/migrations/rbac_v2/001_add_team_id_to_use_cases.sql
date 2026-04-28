-- Migration: 001_add_team_id_to_use_cases.sql
-- Date: 2025-12-08
-- Purpose: Add team_id column to use_cases table for RBAC V2 team isolation
-- ADR: ADR-060 - Corrected RBAC Architecture
-- Phase: Phase 1 - Database Schema Updates (Task 1.1)

-- ==============================================================================
-- PART 1: Add team_id column to use_cases table
-- ==============================================================================

DO $$
BEGIN
    -- Add team_id column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'use_cases' AND column_name = 'team_id'
    ) THEN
        ALTER TABLE use_cases
        ADD COLUMN team_id VARCHAR(100);

        RAISE NOTICE 'Added column: use_cases.team_id';
    ELSE
        RAISE NOTICE 'Column use_cases.team_id already exists';
    END IF;
END $$;

-- ==============================================================================
-- PART 2: Add index for team-based filtering
-- ==============================================================================

CREATE INDEX IF NOT EXISTS idx_use_cases_team_lifecycle
ON use_cases(team_id, lifecycle_state);

-- ==============================================================================
-- PART 3: Add column comment for documentation
-- ==============================================================================

COMMENT ON COLUMN use_cases.team_id IS
    'Developer team that owns this use case. Format: team:team_name. Used to isolate draft use cases between teams. NULL or team:default for unassigned use cases. Published use cases should have NULL team_id (visible to all).';

-- ==============================================================================
-- PART 4: Set defaults for existing use cases
-- ==============================================================================

-- Set default for existing draft use cases
DO $$
BEGIN
    UPDATE use_cases
    SET team_id = 'team:default'
    WHERE team_id IS NULL
      AND lifecycle_state = 'draft';

    IF FOUND THEN
        RAISE NOTICE 'Set team_id = team:default for existing draft use cases';
    END IF;
END $$;

-- Published use cases don't need team assignment (visible to all)
DO $$
BEGIN
    UPDATE use_cases
    SET team_id = NULL
    WHERE team_id IS NOT NULL
      AND lifecycle_state = 'published';

    IF FOUND THEN
        RAISE NOTICE 'Set team_id = NULL for published use cases';
    END IF;
END $$;

-- ==============================================================================
-- VERIFICATION
-- ==============================================================================

DO $$
DECLARE
    draft_count INTEGER;
    published_count INTEGER;
BEGIN
    -- Count draft use cases with team_id
    SELECT COUNT(*) INTO draft_count
    FROM use_cases
    WHERE lifecycle_state = 'draft' AND team_id IS NULL;

    -- Count published use cases with team_id (should be 0)
    SELECT COUNT(*) INTO published_count
    FROM use_cases
    WHERE lifecycle_state = 'published' AND team_id IS NOT NULL;

    RAISE NOTICE 'Migration 001 verification:';
    RAISE NOTICE '  - Draft use cases without team_id: %', draft_count;
    RAISE NOTICE '  - Published use cases with team_id: % (should be 0)', published_count;

    -- Verify column exists
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'use_cases' AND column_name = 'team_id'
    ) THEN
        RAISE NOTICE '  - Column use_cases.team_id: OK';
    ELSE
        RAISE WARNING '  - Column use_cases.team_id: MISSING';
    END IF;

    -- Verify index exists
    IF EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'use_cases' AND indexname = 'idx_use_cases_team_lifecycle'
    ) THEN
        RAISE NOTICE '  - Index idx_use_cases_team_lifecycle: OK';
    ELSE
        RAISE WARNING '  - Index idx_use_cases_team_lifecycle: MISSING';
    END IF;
END $$;

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Migration 001_add_team_id_to_use_cases completed successfully';
END $$;
