-- Migration: 037_create_intent_model_defaults.sql
-- Date: 2026-02-08
-- Purpose: Create intent_model_defaults table for database-driven intent-to-model
--          configuration (ADR-069).
-- Changes:
--   - Creates intent_model_defaults table
--   - Adds indexes for performance
--   - Adds audit columns for tracking changes
--   - Ensures only one active default per intent
-- Replaces: Environment variables INTENT_MODEL_QUERY, INTENT_MODEL_RULE_GENERATION, etc.

-- ==============================================================================
-- PART 1: Create intent_model_defaults table
-- ==============================================================================

CREATE TABLE IF NOT EXISTS intent_model_defaults (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Intent and model configuration
    intent_code VARCHAR(50) NOT NULL,
    model_id VARCHAR(255) NOT NULL,

    -- Configuration metadata
    priority INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    effective_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    notes TEXT,

    -- Audit columns
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_by UUID,

    -- Foreign key constraints
    CONSTRAINT fk_intent_model_defaults_intent_code
        FOREIGN KEY (intent_code)
        REFERENCES intent_types(intent_code)
        ON DELETE RESTRICT,

    CONSTRAINT fk_intent_model_defaults_model_id
        FOREIGN KEY (model_id)
        REFERENCES models(model_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_intent_model_defaults_created_by
        FOREIGN KEY (created_by)
        REFERENCES users(id)
        ON DELETE SET NULL,

    CONSTRAINT fk_intent_model_defaults_updated_by
        FOREIGN KEY (updated_by)
        REFERENCES users(id)
        ON DELETE SET NULL,

    -- Ensure priority is positive
    CONSTRAINT chk_intent_model_defaults_priority
        CHECK (priority > 0)
);

-- ==============================================================================
-- PART 2: Create indexes
-- ==============================================================================

-- Ensure only one active default per intent (partial unique index)
CREATE UNIQUE INDEX uq_intent_model_defaults_intent_active
    ON intent_model_defaults(intent_code)
    WHERE is_active = TRUE;

-- Index for active lookups (most common query pattern)
CREATE INDEX idx_intent_model_defaults_active
    ON intent_model_defaults(intent_code, is_active)
    WHERE is_active = TRUE;

-- Index for audit queries
CREATE INDEX idx_intent_model_defaults_created_at
    ON intent_model_defaults(created_at DESC);

-- Index for model_id lookups (to check which intents use a model)
CREATE INDEX idx_intent_model_defaults_model_id
    ON intent_model_defaults(model_id);

-- ==============================================================================
-- PART 3: Add comments for documentation
-- ==============================================================================

COMMENT ON TABLE intent_model_defaults IS
    'Stores system-wide default model assignments for each intent type. Replaces environment variables (ADR-069).';

COMMENT ON COLUMN intent_model_defaults.intent_code IS
    'Intent type code from intent_types table (e.g., QUERY, RULE_GENERATION)';

COMMENT ON COLUMN intent_model_defaults.model_id IS
    'Model identifier from models registry table';

COMMENT ON COLUMN intent_model_defaults.priority IS
    'Priority for selection if multiple defaults exist (lower = higher priority)';

COMMENT ON COLUMN intent_model_defaults.is_active IS
    'Whether this default is currently active (only one active default per intent)';

COMMENT ON COLUMN intent_model_defaults.effective_date IS
    'When this configuration becomes effective (for future-dated changes)';

COMMENT ON COLUMN intent_model_defaults.notes IS
    'Admin notes about why this model was chosen';

-- ==============================================================================
-- PART 4: Create function to auto-update updated_at
-- ==============================================================================

CREATE OR REPLACE FUNCTION update_intent_model_defaults_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_intent_model_defaults_updated_at
    BEFORE UPDATE ON intent_model_defaults
    FOR EACH ROW
    EXECUTE FUNCTION update_intent_model_defaults_timestamp();

-- ==============================================================================
-- PART 5: Grant permissions
-- ==============================================================================

-- Grant permissions only if the roles exist (they are created in production setups,
-- not in the base init SQL — skip gracefully on fresh local bootstraps).
DO $$ BEGIN
    GRANT SELECT, INSERT, UPDATE, DELETE ON intent_model_defaults TO admin_role;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;
DO $$ BEGIN
    GRANT SELECT ON intent_model_defaults TO developer_role;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;
DO $$ BEGIN
    GRANT SELECT ON intent_model_defaults TO analyst_role;
    GRANT SELECT ON intent_model_defaults TO readonly_role;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

-- ==============================================================================
-- Verification
-- ==============================================================================

DO $$
DECLARE
    table_exists BOOLEAN;
    index_count INTEGER;
BEGIN
    -- Check if table was created
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'intent_model_defaults'
    ) INTO table_exists;

    -- Count indexes
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE tablename = 'intent_model_defaults';

    RAISE NOTICE 'Migration 037 complete: Intent Model Defaults table created';
    RAISE NOTICE '  Table exists: %', table_exists;
    RAISE NOTICE '  Indexes created: %', index_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. Run seed script to populate defaults from env vars';
    RAISE NOTICE '  2. Configure additional intent defaults via Admin UI';
    RAISE NOTICE '  3. Remove INTENT_MODEL_* env vars after verification';
END $$;
