-- Migration 028: Add Preflight Configuration to Collections
-- Date: 2025-11-03
-- Purpose: Add auto-chunking detection configuration fields to collections table
-- Part of: P4-DOC-07 Auto Chunking Detection

-- Add preflight configuration columns to collections table
ALTER TABLE collections
ADD COLUMN IF NOT EXISTS preflight_sample_tokens INTEGER NOT NULL DEFAULT 10000
    CHECK (preflight_sample_tokens BETWEEN 1000 AND 100000),
ADD COLUMN IF NOT EXISTS preflight_strategies TEXT[] NOT NULL DEFAULT
    ARRAY['sentence_paragraph', 'fixed_token', 'sliding_token', 'heading_aware', 'table_aware'],
ADD COLUMN IF NOT EXISTS auto_chunk_enabled BOOLEAN NOT NULL DEFAULT true;

-- Add index for performance (optional but useful for filtering)
CREATE INDEX IF NOT EXISTS idx_collections_auto_enabled
ON collections(auto_chunk_enabled)
WHERE auto_chunk_enabled = true;

-- Update existing collections with sensible defaults based on collection purpose
UPDATE collections
SET preflight_sample_tokens = CASE
    WHEN name = 'default' THEN 10000
    WHEN name ILIKE '%security%' THEN 25000
    WHEN name ILIKE '%news%' THEN 5000
    WHEN name ILIKE '%legal%' THEN 15000
    WHEN name ILIKE '%technical%' THEN 20000
    ELSE 10000
END
WHERE preflight_sample_tokens = 10000;  -- Only update if still at default

-- Add column comments for documentation
COMMENT ON COLUMN collections.preflight_sample_tokens IS
    'Sample size in tokens for preflight analysis during auto-detection. Range: 1000-100000';

COMMENT ON COLUMN collections.preflight_strategies IS
    'List of chunking strategies to test during auto-detection. Core strategies: sentence_paragraph, fixed_token, sliding_token, heading_aware, table_aware';

COMMENT ON COLUMN collections.auto_chunk_enabled IS
    'Whether auto-chunking detection is enabled for this collection. If false, users must manually select chunking strategy';
