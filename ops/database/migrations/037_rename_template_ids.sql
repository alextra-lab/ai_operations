-- Migration: 037_rename_template_ids.sql
-- Date: 2026-02-05
-- Purpose: Rename visualization template IDs from domain-specific
--          to structural names (ADR-066).
--
-- Mapping:
--   threat-triage-dashboard  ->  score-table-timeline
--   ioc-extraction-table     ->  filterable-table
--   incident-summary         ->  score-timeline
--   simple-table             ->  auto-table
--   metrics-dashboard        ->  bar-chart

-- ==============================================================================
-- Update use_cases config_json where template_id references old names
-- ==============================================================================

UPDATE use_cases SET config_json = jsonb_set(
  config_json,
  '{output_contract,template_id}',
  CASE config_json->'output_contract'->>'template_id'
    WHEN 'threat-triage-dashboard' THEN '"score-table-timeline"'
    WHEN 'ioc-extraction-table'    THEN '"filterable-table"'
    WHEN 'incident-summary'        THEN '"score-timeline"'
    WHEN 'simple-table'            THEN '"auto-table"'
    WHEN 'metrics-dashboard'       THEN '"bar-chart"'
    ELSE config_json->'output_contract'->'template_id'
  END
)
WHERE config_json->'output_contract'->>'template_id' IN (
  'threat-triage-dashboard',
  'ioc-extraction-table',
  'incident-summary',
  'simple-table',
  'metrics-dashboard'
);

-- ==============================================================================
-- Verification
-- ==============================================================================

DO $$
DECLARE
  old_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO old_count
  FROM use_cases
  WHERE config_json->'output_contract'->>'template_id' IN (
    'threat-triage-dashboard',
    'ioc-extraction-table',
    'incident-summary',
    'simple-table',
    'metrics-dashboard'
  );

  IF old_count > 0 THEN
    RAISE WARNING
      'Migration 037: % use cases still reference old template IDs',
      old_count;
  ELSE
    RAISE NOTICE
      'Migration 037: All template IDs renamed successfully (ADR-066)';
  END IF;
END $$;
