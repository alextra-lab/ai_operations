-- Migration: 027_add_is_hidden_to_models
-- Description: Add is_hidden column to models table for admin visibility control
-- Dependencies: 010_create_models_table
-- Date: 2025-10-26

-- Add is_hidden column to models table
ALTER TABLE models
ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN DEFAULT FALSE NOT NULL;

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_models_is_hidden ON models(is_hidden);

-- Comment
COMMENT ON COLUMN models.is_hidden IS 'Admin flag to hide models from default view. Hidden models can be shown via "Show Hidden" filter.';

-- Update existing models (all visible by default)
UPDATE models SET is_hidden = FALSE WHERE is_hidden IS NULL;
