-- Migration: Add Security Classification Columns (ADR-057)
-- Date: 2025-11-27
-- Description: Adds security classification columns to tools table
--              to replace deprecated tool_purpose/service_location model

-- Check if migration is needed (idempotent)
DO $$
BEGIN
    -- Add data_source_type column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tools' AND column_name = 'data_source_type'
    ) THEN
        ALTER TABLE tools
        ADD COLUMN data_source_type VARCHAR(20) NOT NULL DEFAULT 'internal';

        RAISE NOTICE 'Added column: data_source_type';
    END IF;

    -- Add data_flow_direction column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tools' AND column_name = 'data_flow_direction'
    ) THEN
        ALTER TABLE tools
        ADD COLUMN data_flow_direction VARCHAR(20) NOT NULL DEFAULT 'ingress';

        RAISE NOTICE 'Added column: data_flow_direction';
    END IF;

    -- Add network_access_level column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tools' AND column_name = 'network_access_level'
    ) THEN
        ALTER TABLE tools
        ADD COLUMN network_access_level VARCHAR(20) NOT NULL DEFAULT 'internal';

        RAISE NOTICE 'Added column: network_access_level';
    END IF;

    -- Add max_data_sensitivity column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tools' AND column_name = 'max_data_sensitivity'
    ) THEN
        ALTER TABLE tools
        ADD COLUMN max_data_sensitivity VARCHAR(20) NOT NULL DEFAULT 'internal';

        RAISE NOTICE 'Added column: max_data_sensitivity';
    END IF;
END $$;

-- Add CHECK constraints (drop first if exists for idempotency)
DO $$
BEGIN
    -- data_source_type constraint
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'valid_data_source_type'
    ) THEN
        ALTER TABLE tools ADD CONSTRAINT valid_data_source_type
        CHECK (data_source_type IN ('internal', 'external', 'none', 'mixed'));

        RAISE NOTICE 'Added constraint: valid_data_source_type';
    END IF;

    -- data_flow_direction constraint
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'valid_data_flow_direction'
    ) THEN
        ALTER TABLE tools ADD CONSTRAINT valid_data_flow_direction
        CHECK (data_flow_direction IN ('ingress', 'egress', 'bidirectional', 'none'));

        RAISE NOTICE 'Added constraint: valid_data_flow_direction';
    END IF;

    -- network_access_level constraint
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'valid_network_access_level'
    ) THEN
        ALTER TABLE tools ADD CONSTRAINT valid_network_access_level
        CHECK (network_access_level IN ('isolated', 'internal', 'external'));

        RAISE NOTICE 'Added constraint: valid_network_access_level';
    END IF;

    -- max_data_sensitivity constraint
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'valid_max_data_sensitivity'
    ) THEN
        ALTER TABLE tools ADD CONSTRAINT valid_max_data_sensitivity
        CHECK (max_data_sensitivity IN ('public', 'internal', 'confidential', 'restricted'));

        RAISE NOTICE 'Added constraint: valid_max_data_sensitivity';
    END IF;
END $$;

-- Add indexes for security queries
CREATE INDEX IF NOT EXISTS idx_tools_data_source_type
    ON tools(data_source_type);

CREATE INDEX IF NOT EXISTS idx_tools_security
    ON tools(data_source_type, max_data_sensitivity);

-- Migrate existing tools based on legacy classification
-- This sets sensible defaults based on the old tool_purpose field
UPDATE tools SET
    data_source_type = CASE
        WHEN tool_purpose = 'retrieval' THEN 'internal'
        WHEN category IN ('reasoning', 'documentation') THEN 'none'
        ELSE 'external'
    END,
    data_flow_direction = CASE
        WHEN tool_purpose = 'retrieval' THEN 'ingress'
        WHEN category = 'reasoning' THEN 'none'
        ELSE 'ingress'
    END,
    network_access_level = CASE
        WHEN tool_purpose = 'retrieval' THEN 'internal'
        WHEN category = 'reasoning' THEN 'isolated'
        ELSE 'external'
    END,
    max_data_sensitivity = 'internal'  -- Conservative default
WHERE data_source_type = 'internal'  -- Only update rows with default value
  AND created_at < NOW() - INTERVAL '1 minute';  -- Only existing rows

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Migration 001_add_security_classification_columns completed successfully';
END $$;
