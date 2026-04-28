-- Migration: 038_output_templates.sql
-- Date: 2026-02-06
-- Purpose: Create output_templates table for custom visualization templates.
--          Built-in templates remain hardcoded in the frontend TemplateRegistryService.
--          Custom templates are persisted here and merged at runtime.
--
-- ADR-066: Domain-Neutral Visualization Template Architecture

-- ==============================================================================
-- Create output_templates table
-- ==============================================================================

CREATE TABLE IF NOT EXISTS output_templates (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id   VARCHAR(100) NOT NULL,
  name          VARCHAR(255) NOT NULL,
  description   TEXT DEFAULT '',
  is_builtin    BOOLEAN NOT NULL DEFAULT FALSE,
  data_schema   JSONB NOT NULL DEFAULT '{}',
  layout        JSONB NOT NULL DEFAULT '{}',
  export_formats TEXT[] NOT NULL DEFAULT '{}',
  created_by    UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT uq_output_templates_template_id
    UNIQUE (template_id)
);

-- Index for fast lookup by template_id
CREATE INDEX IF NOT EXISTS idx_output_templates_template_id
  ON output_templates (template_id);

-- Index for listing (created_at desc)
CREATE INDEX IF NOT EXISTS idx_output_templates_created_at
  ON output_templates (created_at DESC);

-- ==============================================================================
-- Verification
-- ==============================================================================

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_name = 'output_templates'
  ) THEN
    RAISE NOTICE
      'Migration 038: output_templates table created successfully';
  ELSE
    RAISE WARNING
      'Migration 038: output_templates table was NOT created';
  END IF;
END $$;
