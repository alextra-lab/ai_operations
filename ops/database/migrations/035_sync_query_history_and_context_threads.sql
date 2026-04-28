-- Migration: 002_sync_query_history_and_context_threads.sql
-- Date: 2025-11-30
-- Purpose: Sync database schema with SQLAlchemy models for query_history and context_threads
-- Issue: P6-STAB-01 UI walkthrough found 500 errors due to missing columns

-- ==============================================================================
-- PART 1: query_history - rename execution_time_ms to processing_time_ms
-- ==============================================================================

DO $$
BEGIN
    -- Check if execution_time_ms exists and processing_time_ms doesn't
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'query_history' AND column_name = 'execution_time_ms'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'query_history' AND column_name = 'processing_time_ms'
    ) THEN
        ALTER TABLE query_history RENAME COLUMN execution_time_ms TO processing_time_ms;
        RAISE NOTICE 'Renamed query_history.execution_time_ms to processing_time_ms';
    ELSIF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'query_history' AND column_name = 'processing_time_ms'
    ) THEN
        RAISE NOTICE 'Column query_history.processing_time_ms already exists';
    ELSE
        -- Column doesn't exist at all, create it
        ALTER TABLE query_history ADD COLUMN processing_time_ms INTEGER;
        RAISE NOTICE 'Added query_history.processing_time_ms column';
    END IF;
END $$;

-- ==============================================================================
-- PART 2: context_threads - add missing columns
-- ==============================================================================

-- Add discussion_id column (for incident/ticket correlation)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'context_threads' AND column_name = 'discussion_id'
    ) THEN
        ALTER TABLE context_threads ADD COLUMN discussion_id VARCHAR(255);
        RAISE NOTICE 'Added context_threads.discussion_id column';
    END IF;
END $$;

-- Add use_case_id column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'context_threads' AND column_name = 'use_case_id'
    ) THEN
        ALTER TABLE context_threads ADD COLUMN use_case_id UUID;
        RAISE NOTICE 'Added context_threads.use_case_id column';
    END IF;
END $$;

-- Add use_case_name column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'context_threads' AND column_name = 'use_case_name'
    ) THEN
        ALTER TABLE context_threads ADD COLUMN use_case_name VARCHAR(255);
        RAISE NOTICE 'Added context_threads.use_case_name column';
    END IF;
END $$;

-- Add source column (ui, api, soar)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'context_threads' AND column_name = 'source'
    ) THEN
        ALTER TABLE context_threads ADD COLUMN source VARCHAR(50) NOT NULL DEFAULT 'ui';
        RAISE NOTICE 'Added context_threads.source column';
    END IF;
END $$;

-- Add context_size_tokens column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'context_threads' AND column_name = 'context_size_tokens'
    ) THEN
        ALTER TABLE context_threads ADD COLUMN context_size_tokens INTEGER NOT NULL DEFAULT 0;
        RAISE NOTICE 'Added context_threads.context_size_tokens column';
    END IF;
END $$;

-- Add max_context_tokens column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'context_threads' AND column_name = 'max_context_tokens'
    ) THEN
        ALTER TABLE context_threads ADD COLUMN max_context_tokens INTEGER NOT NULL DEFAULT 8000;
        RAISE NOTICE 'Added context_threads.max_context_tokens column';
    END IF;
END $$;

-- Add auto_compact column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'context_threads' AND column_name = 'auto_compact'
    ) THEN
        ALTER TABLE context_threads ADD COLUMN auto_compact BOOLEAN NOT NULL DEFAULT TRUE;
        RAISE NOTICE 'Added context_threads.auto_compact column';
    END IF;
END $$;

-- Add last_activity_at column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'context_threads' AND column_name = 'last_activity_at'
    ) THEN
        ALTER TABLE context_threads ADD COLUMN last_activity_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW();
        -- Update existing rows to use created_at as last_activity_at
        UPDATE context_threads SET last_activity_at = created_at WHERE last_activity_at IS NULL OR last_activity_at = NOW();
        RAISE NOTICE 'Added context_threads.last_activity_at column';
    END IF;
END $$;

-- ==============================================================================
-- PART 3: Create indexes for new columns
-- ==============================================================================

-- Index on discussion_id
CREATE INDEX IF NOT EXISTS idx_context_threads_discussion_id
ON context_threads (discussion_id);

-- Compound index on discussion_id + user_id
CREATE INDEX IF NOT EXISTS idx_context_threads_discussion_user
ON context_threads (discussion_id, user_id);

-- Index on last_activity_at (for sorting)
CREATE INDEX IF NOT EXISTS idx_context_threads_last_activity_at
ON context_threads (last_activity_at DESC);

-- Index on source
CREATE INDEX IF NOT EXISTS idx_context_threads_source
ON context_threads (source);

-- ==============================================================================
-- VERIFICATION
-- ==============================================================================

DO $$
DECLARE
    col_count INTEGER;
BEGIN
    -- Count columns in context_threads
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns
    WHERE table_name = 'context_threads';

    RAISE NOTICE 'context_threads now has % columns', col_count;

    -- Verify processing_time_ms exists
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'query_history' AND column_name = 'processing_time_ms'
    ) THEN
        RAISE NOTICE 'query_history.processing_time_ms: OK';
    ELSE
        RAISE WARNING 'query_history.processing_time_ms: MISSING';
    END IF;

    -- Verify discussion_id exists
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'context_threads' AND column_name = 'discussion_id'
    ) THEN
        RAISE NOTICE 'context_threads.discussion_id: OK';
    ELSE
        RAISE WARNING 'context_threads.discussion_id: MISSING';
    END IF;
END $$;

-- Show final schema
\echo 'Migration 002 complete. Verifying schemas...'
\d query_history
\d context_threads
