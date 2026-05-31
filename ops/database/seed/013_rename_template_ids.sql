-- ============================================================================
-- Seed Data: Rename Visualization Template IDs (ADR-066)
-- ============================================================================
-- Description: Data operation consolidated from migration
--              037_rename_template_ids.sql (AIO-65). Renames visualization
--              template IDs in use_cases.config_json from domain-specific to
--              structural names. Idempotent: only updates rows still using the
--              old names, so it is safe to re-run.
-- Prerequisites: 000_complete_init.sql, 003_seed_use_cases.sql,
--                009_seed_draft_use_cases.sql
--
-- Mapping:
--   threat-triage-dashboard  ->  score-table-timeline
--   ioc-extraction-table     ->  filterable-table
--   incident-summary         ->  score-timeline
--   simple-table             ->  auto-table
--   metrics-dashboard        ->  bar-chart
-- ============================================================================

BEGIN;

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

COMMIT;

-- ============================================================================
-- Verification
-- ============================================================================

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
      'Template ID rename: % use cases still reference old template IDs', old_count;
  ELSE
    RAISE NOTICE 'Template IDs renamed successfully (ADR-066)';
  END IF;
END $$;
