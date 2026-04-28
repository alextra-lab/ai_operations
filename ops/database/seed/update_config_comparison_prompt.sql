-- Update Configuration Comparison (Demo) developer_prompt so the model
-- outputs full left/right content without truncation.
-- Run after 003_seed_use_cases.sql if that script was already applied
-- (ON CONFLICT DO NOTHING skips updates to existing rows).

UPDATE use_cases
SET metadata = jsonb_set(
  metadata,
  '{prompts,developer_prompt}',
  to_jsonb(
    'Compare the configurations and return ONLY valid JSON with left and right objects. '
    'Each must have: title (e.g., Current Configuration or Proposed Configuration) '
    'and content (full formatted text as a single string). Output the complete content '
    'for BOTH left and right; do not truncate, abbreviate, or use placeholders. '
    'Format each side with clear settings listed, one per line. Use newline characters '
    'in content strings to separate lines. Both panels must contain the full '
    'configuration text from the user input.'::text
  )
)
WHERE use_case_id = 'aiop-config-comparison-demo';
