-- Update all demo AIOps with user-facing prompt templates containing {{variable}} placeholders
-- Run this to add helpful input guidance to existing demo AIOps

BEGIN;

-- 1. Threat Intelligence Triage (Demo)
UPDATE use_cases
SET metadata = jsonb_set(
  jsonb_set(
    metadata,
    '{prompts,prompt_template}',
    to_jsonb('Analyze the following threat data and provide a comprehensive security assessment:

{{threat_data}}

Identify all threat indicators (commands, IPs, domains, hashes), assess the overall severity level, and create a chronological timeline of key events.'::text)
  ),
  '{prompts,variables}',
  '["threat_data"]'::jsonb
)
WHERE use_case_id = 'aiop-threat-triage-demo';

-- 2. IOC Extraction (Demo)
UPDATE use_cases
SET metadata = jsonb_set(
  jsonb_set(
    metadata,
    '{prompts,prompt_template}',
    to_jsonb('Extract all indicators of compromise (IOCs) from the following security data:

{{security_data}}

Identify and extract: IP addresses, domain names, file hashes (MD5/SHA1/SHA256), URLs, email addresses, and any other security indicators. Assess confidence for each IOC based on context.'::text)
  ),
  '{prompts,variables}',
  '["security_data"]'::jsonb
)
WHERE use_case_id = 'aiop-ioc-extraction-demo';

-- 3. Incident Summarization (Demo)
UPDATE use_cases
SET metadata = jsonb_set(
  jsonb_set(
    metadata,
    '{prompts,prompt_template}',
    to_jsonb('Summarize the following security incident with a severity assessment and chronological timeline:

{{incident_data}}

Extract the timeline of events, assess the overall severity (0-10 scale), count affected systems, determine if data loss occurred, and identify the current incident status (detected/investigating/contained/resolved).'::text)
  ),
  '{prompts,variables}',
  '["incident_data"]'::jsonb
)
WHERE use_case_id = 'aiop-incident-summary-demo';

-- 4. Security Log Parser (Demo)
UPDATE use_cases
SET metadata = jsonb_set(
  jsonb_set(
    metadata,
    '{prompts,prompt_template}',
    to_jsonb('Parse and structure the following raw security log entries:

{{log_data}}

Extract structured information from each log entry. Use consistent field names across all entries (timestamp, event_type, source, severity, message, details). Parse all relevant information from the log format.'::text)
  ),
  '{prompts,variables}',
  '["log_data"]'::jsonb
)
WHERE use_case_id = 'aiop-log-parser-demo';

-- 5. Security Metrics Visualization (Demo)
UPDATE use_cases
SET metadata = jsonb_set(
  jsonb_set(
    metadata,
    '{prompts,prompt_template}',
    to_jsonb('Extract and structure security metrics from the following data:

{{metrics_query}}

Identify all quantitative security metrics. Create a metrics array with clear labels and numeric values. Order by significance or magnitude.'::text)
  ),
  '{prompts,variables}',
  '["metrics_query"]'::jsonb
)
WHERE use_case_id = 'aiop-metrics-viz-demo';

-- 6. Policy Compliance Summary (Demo)
UPDATE use_cases
SET metadata = jsonb_set(
  jsonb_set(
    metadata,
    '{prompts,prompt_template}',
    to_jsonb('Summarize the following policy or compliance assessment as key-value pairs:

{{policy_data}}

Extract key information including: Policy Name, Compliance Status, Review Date, Next Review, Key Findings, and Recommendations. Use clear, descriptive keys and concise values.'::text)
  ),
  '{prompts,variables}',
  '["policy_data"]'::jsonb
)
WHERE use_case_id = 'aiop-policy-summary-demo';

-- 7. Multi-Source Alert Correlation (Demo)
UPDATE use_cases
SET metadata = jsonb_set(
  jsonb_set(
    metadata,
    '{prompts,prompt_template}',
    to_jsonb('Analyze and correlate the following security alerts from multiple sources:

{{alert_data}}

Group related alerts into logical categories (e.g., Network Alerts, Endpoint Alerts, Authentication Alerts). Use consistent field names within each category. Include relevant details for each alert.'::text)
  ),
  '{prompts,variables}',
  '["alert_data"]'::jsonb
)
WHERE use_case_id = 'aiop-alert-correlation-demo';

-- 8. Configuration Comparison (Demo)
UPDATE use_cases
SET metadata = jsonb_set(
  jsonb_set(
    metadata,
    '{prompts,prompt_template}',
    to_jsonb('Compare the configurations and present the differences side-by-side:

{{comparison_request}}

Create a left panel showing the current/before configuration and a right panel showing the proposed/after configuration. Format each side clearly with one setting per line for easy comparison.'::text)
  ),
  '{prompts,variables}',
  '["comparison_request"]'::jsonb
)
WHERE use_case_id = 'aiop-config-comparison-demo';

COMMIT;

-- ============================================================================
-- Verification
-- ============================================================================
SELECT
    use_case_id,
    name,
    metadata->'prompts'->>'prompt_template' IS NOT NULL as has_prompt_template,
    jsonb_array_length(metadata->'prompts'->'variables') as variable_count,
    length(metadata->'prompts'->>'prompt_template') as template_length,
    metadata->'prompts'->>'variables' as variables
FROM use_cases
WHERE metadata->>'seed_script' = '003_seed_use_cases'
  AND metadata->>'demo' = 'true'
ORDER BY use_case_id;
