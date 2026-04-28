-- Migration: 036_add_intent_capability_profiles.sql
-- Date: 2026-02-05
-- Purpose: Add capability profile columns to intent_types for auto-preset
--          behavior in the wizard (ADR-067).
-- New columns:
--   - default_sampling_preset: strict | balanced | creative
--   - default_output_format: text | json | yaml | structured
--   - recommended_capabilities: text[] (informational tags for future model filtering)
-- Also adds new categories and expanded intent types per ADR-067.

-- ==============================================================================
-- PART 1: Add new columns to intent_types
-- ==============================================================================

ALTER TABLE intent_types
  ADD COLUMN IF NOT EXISTS default_sampling_preset VARCHAR(20)
    NOT NULL DEFAULT 'balanced',
  ADD COLUMN IF NOT EXISTS default_output_format VARCHAR(20)
    NOT NULL DEFAULT 'text',
  ADD COLUMN IF NOT EXISTS recommended_capabilities TEXT[]
    NOT NULL DEFAULT '{}';

-- Add CHECK constraints
ALTER TABLE intent_types
  ADD CONSTRAINT chk_sampling_preset
    CHECK (default_sampling_preset IN ('strict', 'balanced', 'creative'));

ALTER TABLE intent_types
  ADD CONSTRAINT chk_output_format
    CHECK (default_output_format IN ('text', 'json', 'yaml', 'structured'));

-- ==============================================================================
-- PART 2: Update existing system intents with capability profiles
-- ==============================================================================

-- QUERY: balanced sampling, text output
UPDATE intent_types SET
  default_sampling_preset = 'balanced',
  default_output_format = 'text',
  recommended_capabilities = ARRAY['general'],
  category_id = (SELECT id FROM intent_categories WHERE category_code = 'GENERAL'),
  description = 'General question answering'
WHERE intent_code = 'QUERY';

-- RULE_GENERATION: strict sampling, json output, reasoning model
UPDATE intent_types SET
  default_sampling_preset = 'strict',
  default_output_format = 'json',
  recommended_capabilities = ARRAY['reasoning', 'json_mode']
WHERE intent_code = 'RULE_GENERATION';

-- SUMMARIZATION: balanced sampling, text output, large context
UPDATE intent_types SET
  default_sampling_preset = 'balanced',
  default_output_format = 'text',
  recommended_capabilities = ARRAY['large_context'],
  category_id = (SELECT id FROM intent_categories WHERE category_code = 'GENERAL'),
  description = 'Content summarization'
WHERE intent_code = 'SUMMARIZATION';

-- ENRICHMENT: balanced sampling, structured output, json mode
UPDATE intent_types SET
  default_sampling_preset = 'balanced',
  default_output_format = 'structured',
  recommended_capabilities = ARRAY['json_mode'],
  category_id = (SELECT id FROM intent_categories WHERE category_code = 'GENERAL'),
  description = 'Data enrichment and augmentation'
WHERE intent_code = 'ENRICHMENT';

-- ==============================================================================
-- PART 3: Add new categories
-- ==============================================================================

INSERT INTO intent_categories (category_code, display_name, description, icon, color, sort_order)
VALUES
  ('IT_OPERATIONS', 'IT Operations', 'Infrastructure, monitoring, and operations management', 'dns', '#00BCD4', 7),
  ('DATA_ANALYSIS', 'Data Analysis', 'Data processing, analytics, and insights', 'analytics', '#795548', 8),
  ('CONTENT', 'Content', 'Content creation, editing, and management', 'edit_note', '#E91E63', 9),
  ('CUSTOM', 'Custom', 'User-defined custom category', 'tune', '#9E9E9E', 10)
ON CONFLICT (category_code) DO NOTHING;

-- ==============================================================================
-- PART 4: Add new intent types (ADR-067 expanded set)
-- ==============================================================================

INSERT INTO intent_types (
  intent_code, display_name, description, category_id,
  recommended_model, default_temperature_min, default_temperature_max,
  icon, color, is_system, sort_order,
  default_sampling_preset, default_output_format, recommended_capabilities
)
VALUES
  (
    'CLASSIFICATION',
    'Classification',
    'Categorization and labeling',
    (SELECT id FROM intent_categories WHERE category_code = 'GENERAL'),
    NULL, 0.1, 0.3,
    'label', '#CDDC39', TRUE, 5,
    'strict', 'json', ARRAY['json_mode']
  ),
  (
    'EXTRACTION',
    'Data Extraction',
    'Structured data extraction from unstructured content',
    (SELECT id FROM intent_categories WHERE category_code = 'GENERAL'),
    NULL, 0.1, 0.3,
    'find_in_page', '#009688', TRUE, 6,
    'strict', 'json', ARRAY['json_mode']
  ),
  (
    'GENERATION',
    'Content Generation',
    'Content or artifact generation',
    (SELECT id FROM intent_categories WHERE category_code = 'GENERAL'),
    NULL, 0.7, 1.0,
    'auto_awesome', '#FF9800', TRUE, 7,
    'creative', 'text', ARRAY['general']
  ),
  (
    'ANALYSIS',
    'Deep Analysis',
    'Deep analysis and assessment',
    (SELECT id FROM intent_categories WHERE category_code = 'GENERAL'),
    NULL, 0.4, 0.8,
    'insights', '#673AB7', TRUE, 8,
    'balanced', 'structured', ARRAY['reasoning']
  ),
  (
    'THREAT_TRIAGE',
    'Threat Triage',
    'Threat assessment and prioritization',
    (SELECT id FROM intent_categories WHERE category_code = 'SECURITY'),
    NULL, 0.1, 0.4,
    'shield', '#f44336', TRUE, 9,
    'strict', 'structured', ARRAY['reasoning']
  ),
  (
    'CONTRACT_REVIEW',
    'Contract Review',
    'Contract analysis and key terms extraction',
    (SELECT id FROM intent_categories WHERE category_code = 'LEGAL'),
    NULL, 0.3, 0.7,
    'description', '#9C27B0', TRUE, 10,
    'balanced', 'structured', ARRAY['vision', 'large_context']
  ),
  (
    'COMPLIANCE_CHECK',
    'Compliance Check',
    'Regulatory compliance verification',
    (SELECT id FROM intent_categories WHERE category_code = 'COMPLIANCE'),
    NULL, 0.1, 0.3,
    'verified', '#3F51B5', TRUE, 11,
    'strict', 'json', ARRAY['json_mode']
  )
ON CONFLICT (intent_code) DO NOTHING;

-- ==============================================================================
-- Verification
-- ==============================================================================

DO $$
DECLARE
  category_count INTEGER;
  intent_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO category_count FROM intent_categories;
  SELECT COUNT(*) INTO intent_count FROM intent_types;

  RAISE NOTICE 'Migration 036 complete: Intent capability profiles added';
  RAISE NOTICE '  Categories: %', category_count;
  RAISE NOTICE '  Intent types: %', intent_count;
END $$;
