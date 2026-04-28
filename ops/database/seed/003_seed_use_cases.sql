-- ============================================================================
-- Seed Data: Demonstration AIOps (AI Operations)
-- ============================================================================
-- Description: Creates 8 demonstration AIOps showcasing all visualization templates
-- Prerequisites: 000_complete_init.sql, 001_seed_users.sql, 002_seed_intents.sql
--
-- Demonstration AIOps (8 total):
--   1. Threat Analysis & Triage - score-table-timeline visualization
--   2. IOC Extraction & Analysis - filterable-table visualization
--   3. Incident Timeline Summary - score-timeline visualization
--   4. Security Log Parser - auto-table visualization
--   5. Security Metrics Dashboard - bar-chart visualization
--   6. Policy Compliance Summary - kv-summary visualization
--   7. Alert Correlation Analysis - multi-table visualization
--   8. Configuration Comparison - comparison-grid visualization
--
-- Each AIOp:
--   - Has default input values for immediate execution
--   - Disables RAG and tool usage
--   - Includes proper output schema and template_id
--   - Is marked as demo content in metadata
--
-- Usage:
--   PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
--     -h $POSTGRES_HOST -p $POSTGRES_PORT \
--     -U $POSTGRES_USER -d $POSTGRES_DB \
--     -f ops/database/seed/003_seed_use_cases.sql
-- ============================================================================
BEGIN;

-- ============================================================================
-- 1. Threat Analysis & Triage (Demo)
--    Visualization: score-table-timeline
-- ============================================================================
INSERT INTO use_cases (
        use_case_id,
        name,
        description,
        category,
        intent_type,
        lifecycle_state,
        is_active,
        config_json,
        metadata,
        created_by_user_id
    )
VALUES (
        'aiop-threat-triage-demo',
        'Threat Analysis & Triage (Demo)',
        'Demonstration: Analyze security threats with confidence scoring, findings table, and event timeline',
        'security_analysis',
        'QUERY',
        'published',
        true,
        '{
        "input_fields": [
            {
                "name": "threat_data",
                "type": "textarea",
                "label": "Threat Data",
                "description": "Security threat information to analyze",
                "required": true,
                "placeholder": "Paste threat indicators, alerts, or suspicious activity",
                "default_value": "Suspicious PowerShell execution detected:\\npowershell.exe -WindowStyle Hidden -EncodedCommand SGVsbG8gV29ybGQ=\\nSource IP: 192.0.2.42\\nTimestamp: 2026-02-09 10:15:23"
            }
        ],
        "visibility": {
            "roles": ["admin", "corpus_admin", "user"],
            "tags": ["demo", "threat_analysis", "visualization"]
        },
        "models": {
            "llm": "openai/gpt-oss-120b"
        },
        "generation_params": {
            "sampling_preset": "custom",
            "temperature": 0.3,
            "max_tokens": 2000,
            "top_p": 0.95,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        },
        "rag": {
            "enabled": false
        },
        "tools_allowlist": [],
        "tool_restrictions": null,
        "output_contract": {
            "format": "json",
            "template_id": "score-table-timeline",
            "output_schema": {
                "type": "object",
                "required": ["score", "confidence", "items", "events"],
                "properties": {
                    "score": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "Overall threat severity level"
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Confidence score for the assessment"
                    },
                    "items": {
                        "type": "array",
                        "description": "Threat indicators and findings",
                        "items": {
                            "type": "object",
                            "required": ["type", "value"],
                            "properties": {
                                "type": {"type": "string", "description": "Indicator type"},
                                "value": {"type": "string", "description": "Indicator value"},
                                "context": {"type": "string", "description": "Additional context"}
                            }
                        }
                    },
                    "events": {
                        "type": "array",
                        "description": "Timeline of threat events",
                        "items": {
                            "type": "object",
                            "required": ["timestamp", "description"],
                            "properties": {
                                "timestamp": {"type": "string", "format": "date-time"},
                                "description": {"type": "string"},
                                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]}
                            }
                        }
                    }
                },
                "additionalProperties": false
            },
            "validation_mode": "strict"
        },
        "telemetry": {
            "required_metrics": ["performance", "model"]
        },
        "policy": {
            "streaming_enabled": false,
            "streaming_default": false,
            "history_persistence": true,
            "pii_redaction": "anonymize"
        }
    }'::jsonb,
        '{
        "prompts": {
            "system_prompt": "You are a cybersecurity threat analyst. Analyze security threats and return structured JSON output with threat scoring, indicators, and timeline.",
            "developer_prompt": "Analyze the provided threat data and return ONLY valid JSON with these fields: score (low/medium/high/critical), confidence (0.0-1.0), items array with type/value/context, and events array with timestamp/description/severity. Identify all threat indicators, assess severity level, and create a chronological timeline. Use ISO 8601 format for timestamps.",
            "prompt_template": "Analyze the following threat data and provide a comprehensive security assessment:\n\n{{threat_data}}\n\nIdentify all threat indicators (commands, IPs, domains, hashes), assess the overall severity level, and create a chronological timeline of key events.",
            "fewshots": [],
            "variables": ["threat_data"]
        },
        "demo": true,
        "visualization_template": "score-table-timeline",
        "seed_script": "003_seed_use_cases"
    }'::jsonb,
        (
            SELECT id
            FROM users
            WHERE username = 'admin'
            LIMIT 1
        )
    ) ON CONFLICT (use_case_id) DO NOTHING;

-- ============================================================================
-- 2. IOC Extraction & Analysis (Demo)
--    Visualization: filterable-table
-- ============================================================================
INSERT INTO use_cases (
        use_case_id,
        name,
        description,
        category,
        intent_type,
        lifecycle_state,
        is_active,
        config_json,
        metadata,
        created_by_user_id
    )
VALUES (
        'aiop-ioc-extraction-demo',
        'IOC Extraction & Analysis (Demo)',
        'Demonstration: Extract and analyze indicators of compromise from security data with filterable table view',
        'threat_intelligence',
        'EXTRACTION',
        'published',
        true,
        '{
        "input_fields": [
            {
                "name": "security_data",
                "type": "textarea",
                "label": "Security Data",
                "description": "Security logs, alerts, or threat intelligence to extract IOCs from",
                "required": true,
                "placeholder": "Paste logs, alerts, or threat reports",
                "default_value": "Security Alert Log:\\n[2026-02-09 10:30:15] Failed SSH login from 203.0.113.45\\n[2026-02-09 10:31:02] Suspicious connection to malicious-domain.example\\n[2026-02-09 10:32:18] File hash detected: d41d8cd98f00b204e9800998ecf8427e\\n[2026-02-09 10:33:45] C2 callback to https://evil-site.example/beacon"
            }
        ],
        "visibility": {
            "roles": ["admin", "corpus_admin", "user"],
            "tags": ["demo", "ioc", "extraction", "visualization"]
        },
        "models": {
            "llm": "openai/gpt-oss-120b"
        },
        "generation_params": {
            "sampling_preset": "custom",
            "temperature": 0.2,
            "max_tokens": 2000,
            "top_p": 0.95,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        },
        "rag": {
            "enabled": false
        },
        "tools_allowlist": [],
        "tool_restrictions": null,
        "output_contract": {
            "format": "json",
            "template_id": "filterable-table",
            "output_schema": {
                "type": "object",
                "required": ["items"],
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "Extracted indicators of compromise",
                        "items": {
                            "type": "object",
                            "required": ["type", "value"],
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "description": "IOC type (e.g., IP, Domain, Hash, URL)"
                                },
                                "value": {
                                    "type": "string",
                                    "description": "IOC value"
                                },
                                "context": {
                                    "type": "string",
                                    "description": "Context where IOC was found"
                                },
                                "confidence": {
                                    "type": "number",
                                    "minimum": 0,
                                    "maximum": 1,
                                    "description": "Confidence in IOC validity"
                                }
                            }
                        }
                    }
                },
                "additionalProperties": false
            },
            "validation_mode": "strict"
        },
        "telemetry": {
            "required_metrics": ["performance", "model"]
        },
        "policy": {
            "streaming_enabled": false,
            "streaming_default": false,
            "history_persistence": true,
            "pii_redaction": "anonymize"
        }
    }'::jsonb,
        '{
        "prompts": {
            "system_prompt": "You are a threat intelligence analyst. Extract indicators of compromise (IOCs) from security data and return structured JSON.",
            "developer_prompt": "Extract all IOCs from the security data and return ONLY valid JSON with an items array. Each item must have: type (IP Address, Domain, Hash, URL, Email), value (the actual IOC), context (where found), and confidence (0.0-1.0). Identify all IP addresses, domains, file hashes, URLs, and email addresses. Assess confidence based on context validity.",
            "prompt_template": "Extract all indicators of compromise (IOCs) from the following security data:\n\n{{security_data}}\n\nIdentify and extract: IP addresses, domain names, file hashes (MD5/SHA1/SHA256), URLs, email addresses, and any other security indicators. Assess confidence for each IOC based on context.",
            "fewshots": [],
            "variables": ["security_data"]
        },
        "demo": true,
        "visualization_template": "filterable-table",
        "seed_script": "003_seed_use_cases"
    }'::jsonb,
        (
            SELECT id
            FROM users
            WHERE username = 'admin'
            LIMIT 1
        )
    ) ON CONFLICT (use_case_id) DO NOTHING;

-- ============================================================================
-- 3. Incident Timeline Summary (Demo)
--    Visualization: score-timeline
-- ============================================================================
INSERT INTO use_cases (
        use_case_id,
        name,
        description,
        category,
        intent_type,
        lifecycle_state,
        is_active,
        config_json,
        metadata,
        created_by_user_id
    )
VALUES (
        'aiop-incident-timeline-demo',
        'Incident Timeline Summary (Demo)',
        'Demonstration: Generate incident summary with severity gauge and event timeline',
        'incident_response',
        'SUMMARIZATION',
        'published',
        true,
        '{
        "input_fields": [
            {
                "name": "incident_data",
                "type": "textarea",
                "label": "Incident Data",
                "description": "Security incident information to summarize",
                "required": true,
                "placeholder": "Paste incident details, alerts, and timeline",
                "default_value": "Security Incident Report:\\n\\nIncident: Ransomware Detection\\nAffected Systems: 5 servers in production\\nFirst Detection: 2026-02-09 08:15:00\\nInitial Response: 2026-02-09 08:25:00 - Systems isolated\\nContainment: 2026-02-09 09:45:00 - Threat contained\\nCurrent Status: Investigation ongoing\\nData Loss: No evidence of data exfiltration detected"
            }
        ],
        "visibility": {
            "roles": ["admin", "corpus_admin", "user"],
            "tags": ["demo", "incident", "timeline", "visualization"]
        },
        "models": {
            "llm": "openai/gpt-oss-120b"
        },
        "generation_params": {
            "sampling_preset": "custom",
            "temperature": 0.3,
            "max_tokens": 2000,
            "top_p": 0.95,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        },
        "rag": {
            "enabled": false
        },
        "tools_allowlist": [],
        "tool_restrictions": null,
        "output_contract": {
            "format": "json",
            "template_id": "score-timeline",
            "output_schema": {
                "type": "object",
                "required": ["events", "metric", "status"],
                "properties": {
                    "events": {
                        "type": "array",
                        "description": "Chronological incident timeline",
                        "items": {
                            "type": "object",
                            "required": ["timestamp", "description"],
                            "properties": {
                                "timestamp": {"type": "string", "format": "date-time"},
                                "description": {"type": "string"},
                                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                                "details": {"type": "string"}
                            }
                        }
                    },
                    "metric": {
                        "type": "object",
                        "description": "Incident severity metrics",
                        "required": ["severity"],
                        "properties": {
                            "severity": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 10,
                                "description": "Severity score 0-10"
                            },
                            "affected_count": {
                                "type": "number",
                                "description": "Number of affected systems"
                            },
                            "data_loss": {
                                "type": "boolean",
                                "description": "Whether data loss occurred"
                            }
                        }
                    },
                    "status": {
                        "type": "string",
                        "enum": ["detected", "investigating", "contained", "resolved"],
                        "description": "Current incident status"
                    }
                },
                "additionalProperties": false
            },
            "validation_mode": "strict"
        },
        "telemetry": {
            "required_metrics": ["performance", "model"]
        },
        "policy": {
            "streaming_enabled": false,
            "streaming_default": false,
            "history_persistence": true,
            "pii_redaction": "anonymize"
        }
    }'::jsonb,
        '{
        "prompts": {
            "system_prompt": "You are a SOC incident analyst. Summarize security incidents with severity assessment and chronological timeline.",
            "developer_prompt": "Analyze the incident data and return ONLY valid JSON with: events array (timestamp, description, severity, details), metric object (severity 0-10, affected_count, data_loss boolean), and status (detected/investigating/contained/resolved). Extract timeline events in chronological order using ISO 8601 timestamps. Assess overall severity where 0=negligible and 10=critical. Count affected systems and determine current incident status.",
            "prompt_template": "Summarize the following security incident with a severity assessment and chronological timeline:\n\n{{incident_data}}\n\nExtract the timeline of events, assess the overall severity (0-10 scale), count affected systems, determine if data loss occurred, and identify the current incident status (detected/investigating/contained/resolved).",
            "fewshots": [],
            "variables": ["incident_data"]
        },
        "demo": true,
        "visualization_template": "score-timeline",
        "seed_script": "003_seed_use_cases"
    }'::jsonb,
        (
            SELECT id
            FROM users
            WHERE username = 'admin'
            LIMIT 1
        )
    ) ON CONFLICT (use_case_id) DO NOTHING;

-- ============================================================================
-- 4. Security Log Parser (Demo)
--    Visualization: auto-table
-- ============================================================================
INSERT INTO use_cases (
        use_case_id,
        name,
        description,
        category,
        intent_type,
        lifecycle_state,
        is_active,
        config_json,
        metadata,
        created_by_user_id
    )
VALUES (
        'aiop-log-parser-demo',
        'Security Log Parser (Demo)',
        'Demonstration: Parse and structure security logs with auto-detected columns',
        'security_analysis',
        'EXTRACTION',
        'published',
        true,
        '{
        "input_fields": [
            {
                "name": "log_data",
                "type": "textarea",
                "label": "Log Data",
                "description": "Raw security logs to parse",
                "required": true,
                "placeholder": "Paste raw log entries",
                "default_value": "[2026-02-09 10:15:23] FIREWALL DENY src=203.0.113.45 dst=10.0.1.5 proto=TCP port=22\\n[2026-02-09 10:16:45] IDS ALERT signature=SQL_Injection_Attempt src=198.51.100.23 severity=HIGH\\n[2026-02-09 10:18:12] AUTH FAILURE user=admin src=192.0.2.78 service=SSH\\n[2026-02-09 10:19:33] MALWARE DETECTED file=invoice.pdf hash=abc123def456 action=QUARANTINE"
            }
        ],
        "visibility": {
            "roles": ["admin", "corpus_admin", "user"],
            "tags": ["demo", "logs", "parsing", "visualization"]
        },
        "models": {
            "llm": "openai/gpt-oss-120b"
        },
        "generation_params": {
            "sampling_preset": "custom",
            "temperature": 0.2,
            "max_tokens": 2000,
            "top_p": 0.95,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        },
        "rag": {
            "enabled": false
        },
        "tools_allowlist": [],
        "tool_restrictions": null,
        "output_contract": {
            "format": "json",
            "template_id": "auto-table",
            "output_schema": {
                "type": "object",
                "required": ["data"],
                "properties": {
                    "data": {
                        "type": "array",
                        "description": "Parsed log entries",
                        "items": {
                            "type": "object",
                            "description": "Structured log entry with any fields"
                        }
                    }
                },
                "additionalProperties": false
            },
            "validation_mode": "strict"
        },
        "telemetry": {
            "required_metrics": ["performance", "model"]
        },
        "policy": {
            "streaming_enabled": false,
            "streaming_default": false,
            "history_persistence": true,
            "pii_redaction": "anonymize"
        }
    }'::jsonb,
        '{
        "prompts": {
            "system_prompt": "You are a log analysis expert. Parse security logs and extract structured data with consistent field names.",
            "developer_prompt": "Parse the log data and return ONLY valid JSON with a data array. Each log entry should be an object with consistent fields across all entries. Common fields include: timestamp, event_type, source, severity, message, and details. Extract all relevant information from each log line. Use clear, descriptive field names that are consistent across all entries.",
            "prompt_template": "Parse and structure the following raw security log entries:\n\n{{log_data}}\n\nExtract structured information from each log entry. Use consistent field names across all entries (timestamp, event_type, source, severity, message, details). Parse all relevant information from the log format.",
            "fewshots": [],
            "variables": ["log_data"]
        },
        "demo": true,
        "visualization_template": "auto-table",
        "seed_script": "003_seed_use_cases"
    }'::jsonb,
        (
            SELECT id
            FROM users
            WHERE username = 'admin'
            LIMIT 1
        )
    ) ON CONFLICT (use_case_id) DO NOTHING;

-- ============================================================================
-- 5. Security Metrics Dashboard (Demo)
--    Visualization: bar-chart
-- ============================================================================
INSERT INTO use_cases (
        use_case_id,
        name,
        description,
        category,
        intent_type,
        lifecycle_state,
        is_active,
        config_json,
        metadata,
        created_by_user_id
    )
VALUES (
        'aiop-metrics-dashboard-demo',
        'Security Metrics Dashboard (Demo)',
        'Demonstration: Analyze security metrics and present as bar chart visualization',
        'security_analysis',
        'QUERY',
        'published',
        true,
        '{
        "input_fields": [
            {
                "name": "metrics_query",
                "type": "textarea",
                "label": "Metrics Query",
                "description": "Security metrics to analyze and visualize",
                "required": true,
                "placeholder": "Describe metrics or paste security data to analyze",
                "default_value": "Security Operations Summary for Week of Feb 9, 2026:\\n\\nBlocked intrusion attempts: 1,247\\nMalware detections: 38\\nPhishing emails quarantined: 156\\nFailed authentication attempts: 892\\nVulnerability scans completed: 12\\nSecurity patches deployed: 45\\nIncidents investigated: 23\\nAlerts generated: 3,456"
            }
        ],
        "visibility": {
            "roles": ["admin", "corpus_admin", "user"],
            "tags": ["demo", "metrics", "dashboard", "visualization"]
        },
        "models": {
            "llm": "openai/gpt-oss-120b"
        },
        "generation_params": {
            "sampling_preset": "custom",
            "temperature": 0.3,
            "max_tokens": 1500,
            "top_p": 0.95,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        },
        "rag": {
            "enabled": false
        },
        "tools_allowlist": [],
        "tool_restrictions": null,
        "output_contract": {
            "format": "json",
            "template_id": "bar-chart",
            "output_schema": {
                "type": "object",
                "required": ["metrics"],
                "properties": {
                    "metrics": {
                        "type": "array",
                        "description": "Security metrics for visualization",
                        "items": {
                            "type": "object",
                            "required": ["label", "value"],
                            "properties": {
                                "label": {
                                    "type": "string",
                                    "description": "Metric name/label"
                                },
                                "value": {
                                    "type": "number",
                                    "description": "Metric value (numeric)"
                                }
                            }
                        }
                    }
                },
                "additionalProperties": false
            },
            "validation_mode": "strict"
        },
        "telemetry": {
            "required_metrics": ["performance", "model"]
        },
        "policy": {
            "streaming_enabled": false,
            "streaming_default": false,
            "history_persistence": true,
            "pii_redaction": "anonymize"
        }
    }'::jsonb,
        '{
        "prompts": {
            "system_prompt": "You are a security metrics analyst. Extract and structure security metrics for visualization.",
            "developer_prompt": "Extract security metrics and return ONLY valid JSON with a metrics array. Each metric must have: label (clear metric name as string) and value (numeric value only, not string). Extract key security metrics from the provided data. Use clear, concise labels. Ensure all values are numbers. Order metrics by significance or magnitude.",
            "prompt_template": "Extract and structure security metrics from the following data:\n\n{{metrics_query}}\n\nIdentify all quantitative security metrics. Create a metrics array with clear labels and numeric values. Order by significance or magnitude.",
            "fewshots": [],
            "variables": ["metrics_query"]
        },
        "demo": true,
        "visualization_template": "bar-chart",
        "seed_script": "003_seed_use_cases"
    }'::jsonb,
        (
            SELECT id
            FROM users
            WHERE username = 'admin'
            LIMIT 1
        )
    ) ON CONFLICT (use_case_id) DO NOTHING;

-- ============================================================================
-- 6. Policy Compliance Summary (Demo)
--    Visualization: kv-summary
-- ============================================================================
INSERT INTO use_cases (
        use_case_id,
        name,
        description,
        category,
        intent_type,
        lifecycle_state,
        is_active,
        config_json,
        metadata,
        created_by_user_id
    )
VALUES (
        'aiop-policy-summary-demo',
        'Policy Compliance Summary (Demo)',
        'Demonstration: Summarize policy compliance with key-value grid visualization',
        'compliance',
        'SUMMARIZATION',
        'published',
        true,
        '{
        "input_fields": [
            {
                "name": "policy_data",
                "type": "textarea",
                "label": "Policy Data",
                "description": "Security policy or compliance data to summarize",
                "required": true,
                "placeholder": "Paste policy document or compliance assessment",
                "default_value": "Password Policy Compliance Review\\n\\nPolicy: Corporate Password Security Standard v2.1\\nReview Date: February 9, 2026\\nReviewer: Security Team\\n\\nMinimum Length: 12 characters - COMPLIANT\\nComplexity Requirements: Upper, lower, number, special - COMPLIANT\\nExpiration: 90 days - COMPLIANT\\nHistory: 12 passwords - COMPLIANT\\nLockout Threshold: 5 attempts - COMPLIANT\\nMFA Requirement: Enabled for admin accounts - COMPLIANT\\n\\nOverall Status: COMPLIANT\\nNext Review: May 9, 2026\\nRecommendations: Consider reducing expiration to 60 days per NIST guidelines"
            }
        ],
        "visibility": {
            "roles": ["admin", "corpus_admin", "user"],
            "tags": ["demo", "compliance", "policy", "visualization"]
        },
        "models": {
            "llm": "openai/gpt-oss-120b"
        },
        "generation_params": {
            "sampling_preset": "custom",
            "temperature": 0.2,
            "max_tokens": 1500,
            "top_p": 0.95,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        },
        "rag": {
            "enabled": false
        },
        "tools_allowlist": [],
        "tool_restrictions": null,
        "output_contract": {
            "format": "json",
            "template_id": "kv-summary",
            "output_schema": {
                "type": "object",
                "required": ["summary"],
                "properties": {
                    "summary": {
                        "type": "object",
                        "description": "Policy summary as key-value pairs",
                        "additionalProperties": {
                            "type": "string"
                        }
                    }
                },
                "additionalProperties": false
            },
            "validation_mode": "strict"
        },
        "telemetry": {
            "required_metrics": ["performance", "model"]
        },
        "policy": {
            "streaming_enabled": false,
            "streaming_default": false,
            "history_persistence": true,
            "pii_redaction": "anonymize"
        }
    }'::jsonb,
        '{
        "prompts": {
            "system_prompt": "You are a compliance analyst. Summarize policy compliance status as key-value pairs.",
            "developer_prompt": "Summarize the policy data and return ONLY valid JSON with a summary object containing key-value pairs. Include fields like: Policy Name, Compliance Status, Review Date, Next Review, Key Findings, and Recommendations. Extract key information as clear key-value pairs. Use descriptive keys and keep values concise but informative. All values must be strings.",
            "prompt_template": "Summarize the following policy or compliance assessment as key-value pairs:\n\n{{policy_data}}\n\nExtract key information including: Policy Name, Compliance Status, Review Date, Next Review, Key Findings, and Recommendations. Use clear, descriptive keys and concise values.",
            "fewshots": [],
            "variables": ["policy_data"]
        },
        "demo": true,
        "visualization_template": "kv-summary",
        "seed_script": "003_seed_use_cases"
    }'::jsonb,
        (
            SELECT id
            FROM users
            WHERE username = 'admin'
            LIMIT 1
        )
    ) ON CONFLICT (use_case_id) DO NOTHING;

-- ============================================================================
-- 7. Alert Correlation Analysis (Demo)
--    Visualization: multi-table
-- ============================================================================
INSERT INTO use_cases (
        use_case_id,
        name,
        description,
        category,
        intent_type,
        lifecycle_state,
        is_active,
        config_json,
        metadata,
        created_by_user_id
    )
VALUES (
        'aiop-alert-correlation-demo',
        'Alert Correlation Analysis (Demo)',
        'Demonstration: Correlate security alerts across categories with multi-table view',
        'security_analysis',
        'QUERY',
        'published',
        true,
        '{
        "input_fields": [
            {
                "name": "alert_data",
                "type": "textarea",
                "label": "Alert Data",
                "description": "Security alerts to correlate and categorize",
                "required": true,
                "placeholder": "Paste security alerts from multiple sources",
                "default_value": "Security Alert Feed - Feb 9, 2026\\n\\nFirewall Alerts:\\n- 10:15 DENY 203.0.113.45 -> 10.0.1.5:22 (Repeated SSH attempts)\\n- 10:22 DENY 198.51.100.23 -> 10.0.2.8:3389 (RDP brute force)\\n\\nIDS Alerts:\\n- 10:18 SQL Injection attempt from 198.51.100.23\\n- 10:30 Port scan detected from 203.0.113.45\\n\\nEndpoint Alerts:\\n- 10:25 Malware quarantined on WS-042: Trojan.Generic\\n- 10:35 Suspicious PowerShell on WS-103\\n\\nAuthentication Alerts:\\n- 10:16 Failed login: admin from 192.0.2.78\\n- 10:28 Account lockout: dbadmin after 5 failed attempts"
            }
        ],
        "visibility": {
            "roles": ["admin", "corpus_admin", "user"],
            "tags": ["demo", "alerts", "correlation", "visualization"]
        },
        "models": {
            "llm": "openai/gpt-oss-120b"
        },
        "generation_params": {
            "sampling_preset": "custom",
            "temperature": 0.3,
            "max_tokens": 2000,
            "top_p": 0.95,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        },
        "rag": {
            "enabled": false
        },
        "tools_allowlist": [],
        "tool_restrictions": null,
        "output_contract": {
            "format": "json",
            "template_id": "multi-table",
            "output_schema": {
                "type": "object",
                "required": ["tables"],
                "properties": {
                    "tables": {
                        "type": "array",
                        "description": "Alert categories as separate tables",
                        "items": {
                            "type": "object",
                            "required": ["title", "rows"],
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "Category/table name"
                                },
                                "rows": {
                                    "type": "array",
                                    "description": "Alert entries in this category",
                                    "items": {
                                        "type": "object",
                                        "description": "Alert with consistent fields"
                                    }
                                }
                            }
                        }
                    }
                },
                "additionalProperties": false
            },
            "validation_mode": "strict"
        },
        "telemetry": {
            "required_metrics": ["performance", "model"]
        },
        "policy": {
            "streaming_enabled": false,
            "streaming_default": false,
            "history_persistence": true,
            "pii_redaction": "anonymize"
        }
    }'::jsonb,
        '{
        "prompts": {
            "system_prompt": "You are a security operations analyst. Correlate and categorize security alerts into logical groups.",
            "developer_prompt": "Analyze and categorize the alerts, return ONLY valid JSON with a tables array. Each table must have: title (category name like Network Alerts or Endpoint Alerts) and rows (array of alert objects). Use consistent field names within each table such as: timestamp, source, severity, description, and action. Group related alerts into logical categories and include relevant details for each alert.",
            "prompt_template": "Analyze and correlate the following security alerts from multiple sources:\n\n{{alert_data}}\n\nGroup related alerts into logical categories (e.g., Network Alerts, Endpoint Alerts, Authentication Alerts). Use consistent field names within each category. Include relevant details for each alert.",
            "fewshots": [],
            "variables": ["alert_data"]
        },
        "demo": true,
        "visualization_template": "multi-table",
        "seed_script": "003_seed_use_cases"
    }'::jsonb,
        (
            SELECT id
            FROM users
            WHERE username = 'admin'
            LIMIT 1
        )
    ) ON CONFLICT (use_case_id) DO NOTHING;

-- ============================================================================
-- 8. Configuration Comparison (Demo)
--    Visualization: comparison-grid
-- ============================================================================
INSERT INTO use_cases (
        use_case_id,
        name,
        description,
        category,
        intent_type,
        lifecycle_state,
        is_active,
        config_json,
        metadata,
        created_by_user_id
    )
VALUES (
        'aiop-config-comparison-demo',
        'Configuration Comparison (Demo)',
        'Demonstration: Compare security configurations side-by-side with comparison grid',
        'security_analysis',
        'QUERY',
        'published',
        true,
        '{
        "input_fields": [
            {
                "name": "comparison_request",
                "type": "textarea",
                "label": "Comparison Request",
                "description": "Configuration data or change request to compare",
                "required": true,
                "placeholder": "Describe configurations to compare or paste before/after settings",
                "default_value": "Firewall Configuration Change Request\\n\\nCurrent Production Config:\\n- SSH Access: Enabled (Port 22)\\n- Admin Access: Restricted to 10.0.0.0/8\\n- Logging: Standard (Local only)\\n- Session Timeout: 30 minutes\\n- Failed Login Lockout: 5 attempts\\n- IPS Mode: Detection\\n\\nProposed Hardened Config:\\n- SSH Access: Enabled (Port 2222, non-standard)\\n- Admin Access: Restricted to 10.0.0.0/8 + MFA required\\n- Logging: Enhanced (Local + SIEM forwarding)\\n- Session Timeout: 15 minutes\\n- Failed Login Lockout: 3 attempts\\n- IPS Mode: Prevention"
            }
        ],
        "visibility": {
            "roles": ["admin", "corpus_admin", "user"],
            "tags": ["demo", "configuration", "comparison", "visualization"]
        },
        "models": {
            "llm": "openai/gpt-oss-120b"
        },
        "generation_params": {
            "sampling_preset": "custom",
            "temperature": 0.2,
            "max_tokens": 1500,
            "top_p": 0.95,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        },
        "rag": {
            "enabled": false
        },
        "tools_allowlist": [],
        "tool_restrictions": null,
        "output_contract": {
            "format": "json",
            "template_id": "comparison-grid",
            "output_schema": {
                "type": "object",
                "required": ["left", "right"],
                "properties": {
                    "left": {
                        "type": "object",
                        "required": ["title", "content"],
                        "description": "Left side of comparison",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Title for left panel"
                            },
                            "content": {
                                "type": "string",
                                "description": "Content (text with newlines)"
                            }
                        }
                    },
                    "right": {
                        "type": "object",
                        "required": ["title", "content"],
                        "description": "Right side of comparison",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Title for right panel"
                            },
                            "content": {
                                "type": "string",
                                "description": "Content (text with newlines)"
                            }
                        }
                    }
                },
                "additionalProperties": false
            },
            "validation_mode": "strict"
        },
        "telemetry": {
            "required_metrics": ["performance", "model"]
        },
        "policy": {
            "streaming_enabled": false,
            "streaming_default": false,
            "history_persistence": true,
            "pii_redaction": "anonymize"
        }
    }'::jsonb,
        '{
        "prompts": {
            "system_prompt": "You are a security configuration analyst. Compare configurations and present differences clearly.",
            "developer_prompt": "Compare the configurations and return ONLY valid JSON with left and right objects. Each must have: title (e.g., Current Configuration or Proposed Configuration) and content (full formatted text as a single string). Output the complete content for BOTH left and right; do not truncate, abbreviate, or use placeholders. Format each side with clear settings listed, one per line. Use newline characters (backslash-n) in content strings to separate lines. Both panels must contain the full configuration text from the user input.",
            "prompt_template": "Compare the configurations and present the differences side-by-side:\\n\\n{{comparison_request}}\\n\\nCreate a left panel showing the current/before configuration and a right panel showing the proposed/after configuration. Format each side clearly with one setting per line for easy comparison.",
            "fewshots": [],
            "variables": ["comparison_request"]
        },
        "demo": true,
        "visualization_template": "comparison-grid",
        "seed_script": "003_seed_use_cases"
    }'::jsonb,
        (
            SELECT id
            FROM users
            WHERE username = 'admin'
            LIMIT 1
        )
    ) ON CONFLICT (use_case_id) DO NOTHING;

-- ============================================================================
-- Assign admin user to all seeded demo AIOps
-- ============================================================================
INSERT INTO user_use_case_assignments (
        user_id,
        use_case_id,
        assigned_role,
        assigned_by_user_id,
        metadata
    )
SELECT u.id,
    uc.id,
    'admin',
    u.id,
    jsonb_build_object(
        'seed_script',
        '003_seed_use_cases',
        'auto_assigned',
        TRUE,
        'demo',
        TRUE
    )
FROM users u
    JOIN use_cases uc ON uc.metadata->>'seed_script' = '003_seed_use_cases'
WHERE u.username = 'admin'
    AND NOT EXISTS (
        SELECT 1
        FROM user_use_case_assignments
        WHERE user_id = u.id
            AND use_case_id = uc.id
            AND assigned_role = 'admin'
    );

-- ============================================================================
-- Role-Based Assignments (ADR-041, ADR-060)
-- ============================================================================
-- Assign all published demo AIOps to 'analyst' grouping role
INSERT INTO role_use_case_assignments (role_name, use_case_id, granted_by)
SELECT 'analyst' AS role_name,
    id AS use_case_id,
    NULL AS granted_by -- System seeded
FROM use_cases
WHERE is_active = TRUE
    AND lifecycle_state = 'published'
    AND metadata->>'seed_script' = '003_seed_use_cases'
ON CONFLICT (role_name, use_case_id) DO NOTHING;

-- ============================================================================
-- Ensure global visibility for demo AIOps
-- ============================================================================
UPDATE use_cases
SET team_id = NULL
WHERE lifecycle_state = 'published'
  AND team_id IS NOT NULL
  AND metadata->>'seed_script' = '003_seed_use_cases';

COMMIT;

-- ============================================================================
-- Verification
-- ============================================================================
DO $$
DECLARE
    use_case_count INTEGER;
    user_assignment_count INTEGER;
    role_assignment_count INTEGER;
    team_scoped_published INTEGER;
    demo_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO use_case_count
    FROM use_cases
    WHERE metadata->>'seed_script' = '003_seed_use_cases';

    SELECT COUNT(*) INTO demo_count
    FROM use_cases
    WHERE metadata->>'seed_script' = '003_seed_use_cases'
      AND metadata->>'demo' = 'true';

    SELECT COUNT(*) INTO user_assignment_count
    FROM user_use_case_assignments
    WHERE metadata->>'seed_script' = '003_seed_use_cases';

    SELECT COUNT(*) INTO role_assignment_count
    FROM role_use_case_assignments ruca
    JOIN use_cases uc ON uc.id = ruca.use_case_id
    WHERE uc.metadata->>'seed_script' = '003_seed_use_cases';

    SELECT COUNT(*) INTO team_scoped_published
    FROM use_cases
    WHERE lifecycle_state = 'published'
      AND team_id IS NOT NULL
      AND metadata->>'seed_script' = '003_seed_use_cases';

    RAISE NOTICE '✅ Demonstration AIOps seeded successfully!';
    RAISE NOTICE '   - AIOps created: % (% marked as demos)', use_case_count, demo_count;
    RAISE NOTICE '   - User assignments: %', user_assignment_count;
    RAISE NOTICE '   - Role assignments: %', role_assignment_count;
    RAISE NOTICE '   - Published with team_id (should be 0): %', team_scoped_published;

    IF use_case_count != 8 THEN
        RAISE WARNING '⚠️  Expected 8 AIOps, found %', use_case_count;
    END IF;

    IF demo_count != 8 THEN
        RAISE WARNING '⚠️  Expected 8 demo AIOps, found %', demo_count;
    END IF;

    IF team_scoped_published > 0 THEN
        RAISE WARNING '⚠️  Some published AIOps have team_id set (should be NULL for global visibility)';
    END IF;

    RAISE NOTICE '';
    RAISE NOTICE '📋 Demonstration AIOps (Visualization Templates):';
    RAISE NOTICE '   1. Threat Analysis & Triage - score-table-timeline';
    RAISE NOTICE '   2. IOC Extraction & Analysis - filterable-table';
    RAISE NOTICE '   3. Incident Timeline Summary - score-timeline';
    RAISE NOTICE '   4. Security Log Parser - auto-table';
    RAISE NOTICE '   5. Security Metrics Dashboard - bar-chart';
    RAISE NOTICE '   6. Policy Compliance Summary - kv-summary';
    RAISE NOTICE '   7. Alert Correlation Analysis - multi-table';
    RAISE NOTICE '   8. Configuration Comparison - comparison-grid';
    RAISE NOTICE '';
    RAISE NOTICE '🎯 All AIOps are ready for immediate execution with default values!';
END $$;

-- Display created AIOps
SELECT use_case_id,
    name,
    intent_type,
    lifecycle_state,
    is_active,
    category,
    metadata->>'visualization_template' as template,
    metadata->>'demo' as is_demo
FROM use_cases
WHERE metadata->>'seed_script' = '003_seed_use_cases'
ORDER BY use_case_id;
