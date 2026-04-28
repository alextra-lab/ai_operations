-- ============================================================================
-- Seed Data: Draft Use Cases (RBAC V2 Team Isolation Demo)
-- ============================================================================
-- Description: Creates draft use cases assigned to teams for RBAC V2 isolation demo
-- Prerequisites: 000_complete_init.sql, 001_seed_users.sql, 008_seed_rbac_v2_assignments.sql
--
-- RBAC V2 Team Isolation (ADR-060):
--   - Draft use cases are isolated by team (team_id column)
--   - Only team members can see their team's draft use cases
--   - Admins and use_case_admin can see all draft use cases
--   - Published use cases (team_id = NULL) are visible to all users
--
-- Draft Use Cases:
--   - team_uc_csirt_001: CSIRT Threat Analysis (team:csirt_security)
--   - team_uc_csirt_002: Incident Response Playbook (team:csirt_security)
--   - team_uc_gov_001: Compliance Reporting (team:soc_governance)
--   - team_uc_dev_001: RAG Test Case (team:development)
--   - team_uc_dev_002: Model Evaluation (team:development)
--
-- Usage:
--   PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
--     -h $POSTGRES_HOST -p $POSTGRES_PORT \
--     -U $POSTGRES_USER -d $POSTGRES_DB \
--     -f ops/database/seed/009_seed_draft_use_cases.sql
-- ============================================================================

BEGIN;

-- ============================================================================
-- Draft Use Cases - Team: CSIRT Security (team:csirt_security)
-- ============================================================================

-- 1. CSIRT Threat Analysis
INSERT INTO use_cases (
    use_case_id,
    name,
    description,
    category,
    intent_type,
    lifecycle_state,
    is_active,
    team_id,
    config_json,
    metadata,
    created_by_user_id
)
VALUES (
    'team_uc_csirt_001',
    'CSIRT Threat Analysis',
    'Advanced threat analysis use case for CSIRT team (draft)',
    'security_analysis',
    'QUERY',
    'draft',
    false,
    'team:csirt_security',
    '{
        "input_fields": [
            {
                "name": "query",
                "type": "textarea",
                "label": "Threat Analysis Query",
                "description": "Describe the threat to analyze",
                "required": true,
                "placeholder": "Enter threat details...",
                "default_value": ""
            }
        ],
        "visibility": {
            "roles": ["admin", "use_case_admin", "developer"],
            "tags": ["threat_analysis", "csirt"]
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
            "enabled": true,
            "vector_collections": ["documents"],
            "top_k": 10,
            "similarity_threshold": 0.7,
            "hybrid_bm25": false,
            "metadata_filters": {},
            "tags": []
        },
        "tools_allowlist": [],
        "tool_restrictions": null,
        "output_contract": {
            "format": "text",
            "output_schema": null,
            "validation_mode": "best_effort"
        },
        "telemetry": {
            "required_metrics": ["retrieval", "guard", "performance", "model"]
        },
        "policy": {
            "streaming_enabled": true,
            "streaming_default": false,
            "history_persistence": true,
            "pii_redaction": "anonymize"
        }
    }'::jsonb,
    '{
        "prompts": {
            "system_prompt": "You are a CSIRT threat analyst. Analyze security threats and provide actionable insights.",
            "developer_prompt": "Provide detailed threat analysis with severity, impact, and mitigations.",
            "fewshots": [],
            "variables": []
        },
        "seed_script": "009_seed_draft_use_cases",
        "team": "team:csirt_security"
    }'::jsonb,
    (SELECT id FROM users WHERE username = 'developer2' LIMIT 1)
) ON CONFLICT (use_case_id) DO NOTHING;

-- 2. Incident Response Playbook
INSERT INTO use_cases (
    use_case_id,
    name,
    description,
    category,
    intent_type,
    lifecycle_state,
    is_active,
    team_id,
    config_json,
    metadata,
    created_by_user_id
)
VALUES (
    'team_uc_csirt_002',
    'Incident Response Playbook',
    'Incident response playbook generation for CSIRT team (draft)',
    'incident_response',
    'QUERY',
    'draft',
    false,
    'team:csirt_security',
    '{
        "input_fields": [
            {
                "name": "incident_type",
                "type": "text",
                "label": "Incident Type",
                "description": "Type of security incident",
                "required": true,
                "placeholder": "e.g., malware, data breach, DDoS",
                "default_value": ""
            }
        ],
        "visibility": {
            "roles": ["admin", "use_case_admin", "developer"],
            "tags": ["incident_response", "csirt"]
        },
        "models": {
            "llm": "openai/gpt-oss-120b"
        },
        "generation_params": {
            "sampling_preset": "custom",
            "temperature": 0.2,
            "max_tokens": 2500,
            "top_p": 0.95,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        },
        "rag": {
            "enabled": true,
            "vector_collections": ["documents"],
            "top_k": 15,
            "similarity_threshold": 0.6,
            "hybrid_bm25": false,
            "metadata_filters": {},
            "tags": []
        },
        "tools_allowlist": [],
        "tool_restrictions": null,
        "output_contract": {
            "format": "text",
            "output_schema": null,
            "validation_mode": "best_effort"
        },
        "telemetry": {
            "required_metrics": ["retrieval", "guard", "performance", "model"]
        },
        "policy": {
            "streaming_enabled": true,
            "streaming_default": false,
            "history_persistence": true,
            "pii_redaction": "anonymize"
        }
    }'::jsonb,
    '{
        "prompts": {
            "system_prompt": "You are a CSIRT incident responder. Generate incident response playbooks.",
            "developer_prompt": "Create detailed incident response playbooks with step-by-step procedures.",
            "fewshots": [],
            "variables": []
        },
        "seed_script": "009_seed_draft_use_cases",
        "team": "team:csirt_security"
    }'::jsonb,
    (SELECT id FROM users WHERE username = 'developer2' LIMIT 1)
) ON CONFLICT (use_case_id) DO NOTHING;

-- ============================================================================
-- Draft Use Cases - Team: SOC Governance (team:soc_governance)
-- ============================================================================

-- 3. Compliance Reporting
INSERT INTO use_cases (
    use_case_id,
    name,
    description,
    category,
    intent_type,
    lifecycle_state,
    is_active,
    team_id,
    config_json,
    metadata,
    created_by_user_id
)
VALUES (
    'team_uc_gov_001',
    'Compliance Reporting',
    'Automated compliance reporting for SOC governance team (draft)',
    'compliance',
    'QUERY',
    'draft',
    false,
    'team:soc_governance',
    '{
        "input_fields": [
            {
                "name": "compliance_framework",
                "type": "select",
                "label": "Compliance Framework",
                "description": "Select compliance framework",
                "required": true,
                "options": [
                    {"value": "nist", "label": "NIST"},
                    {"value": "iso27001", "label": "ISO 27001"},
                    {"value": "pci", "label": "PCI DSS"},
                    {"value": "gdpr", "label": "GDPR"}
                ],
                "default_value": "nist"
            }
        ],
        "visibility": {
            "roles": ["admin", "use_case_admin", "developer"],
            "tags": ["compliance", "governance"]
        },
        "models": {
            "llm": "openai/gpt-oss-120b"
        },
        "generation_params": {
            "sampling_preset": "custom",
            "temperature": 0.2,
            "max_tokens": 3000,
            "top_p": 0.95,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        },
        "rag": {
            "enabled": true,
            "vector_collections": ["documents"],
            "top_k": 12,
            "similarity_threshold": 0.65,
            "hybrid_bm25": false,
            "metadata_filters": {},
            "tags": []
        },
        "tools_allowlist": [],
        "tool_restrictions": null,
        "output_contract": {
            "format": "text",
            "output_schema": null,
            "validation_mode": "best_effort"
        },
        "telemetry": {
            "required_metrics": ["retrieval", "guard", "performance", "model"]
        },
        "policy": {
            "streaming_enabled": true,
            "streaming_default": false,
            "history_persistence": true,
            "pii_redaction": "anonymize"
        }
    }'::jsonb,
    '{
        "prompts": {
            "system_prompt": "You are a compliance analyst. Generate compliance reports for various frameworks.",
            "developer_prompt": "Create comprehensive compliance reports with gap analysis and recommendations.",
            "fewshots": [],
            "variables": []
        },
        "seed_script": "009_seed_draft_use_cases",
        "team": "team:soc_governance"
    }'::jsonb,
    (SELECT id FROM users WHERE username = 'uc_publisher' LIMIT 1)
) ON CONFLICT (use_case_id) DO NOTHING;

-- ============================================================================
-- Draft Use Cases - Team: Development (team:development)
-- ============================================================================

-- 4. RAG Test Case
INSERT INTO use_cases (
    use_case_id,
    name,
    description,
    category,
    intent_type,
    lifecycle_state,
    is_active,
    team_id,
    config_json,
    metadata,
    created_by_user_id
)
VALUES (
    'team_uc_dev_001',
    'RAG Test Case',
    'RAG functionality testing use case for development team (draft)',
    'testing',
    'QUERY',
    'draft',
    false,
    'team:development',
    '{
        "input_fields": [
            {
                "name": "test_query",
                "type": "textarea",
                "label": "Test Query",
                "description": "Enter test query for RAG evaluation",
                "required": true,
                "placeholder": "Enter test query...",
                "default_value": ""
            }
        ],
        "visibility": {
            "roles": ["admin", "use_case_admin", "developer"],
            "tags": ["testing", "rag", "development"]
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
            "enabled": true,
            "vector_collections": ["documents"],
            "top_k": 10,
            "similarity_threshold": 0.7,
            "hybrid_bm25": false,
            "metadata_filters": {},
            "tags": []
        },
        "tools_allowlist": [],
        "tool_restrictions": null,
        "output_contract": {
            "format": "text",
            "output_schema": null,
            "validation_mode": "best_effort"
        },
        "telemetry": {
            "required_metrics": ["retrieval", "guard", "performance", "model"]
        },
        "policy": {
            "streaming_enabled": true,
            "streaming_default": false,
            "history_persistence": true,
            "pii_redaction": "anonymize"
        }
    }'::jsonb,
    '{
        "prompts": {
            "system_prompt": "You are a test assistant. Help test RAG functionality.",
            "developer_prompt": "Provide test responses for RAG evaluation.",
            "fewshots": [],
            "variables": []
        },
        "seed_script": "009_seed_draft_use_cases",
        "team": "team:development"
    }'::jsonb,
    (SELECT id FROM users WHERE username = 'developer1' LIMIT 1)
) ON CONFLICT (use_case_id) DO NOTHING;

-- 5. Model Evaluation
INSERT INTO use_cases (
    use_case_id,
    name,
    description,
    category,
    intent_type,
    lifecycle_state,
    is_active,
    team_id,
    config_json,
    metadata,
    created_by_user_id
)
VALUES (
    'team_uc_dev_002',
    'Model Evaluation',
    'LLM model evaluation and benchmarking use case (draft)',
    'testing',
    'QUERY',
    'draft',
    false,
    'team:development',
    '{
        "input_fields": [
            {
                "name": "evaluation_prompt",
                "type": "textarea",
                "label": "Evaluation Prompt",
                "description": "Enter prompt for model evaluation",
                "required": true,
                "placeholder": "Enter evaluation prompt...",
                "default_value": ""
            }
        ],
        "visibility": {
            "roles": ["admin", "use_case_admin", "developer"],
            "tags": ["testing", "model_evaluation", "development"]
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
            "enabled": false,
            "vector_collections": [],
            "top_k": 0,
            "similarity_threshold": 0.0,
            "hybrid_bm25": false,
            "metadata_filters": {},
            "tags": []
        },
        "tools_allowlist": [],
        "tool_restrictions": null,
        "output_contract": {
            "format": "text",
            "output_schema": null,
            "validation_mode": "best_effort"
        },
        "telemetry": {
            "required_metrics": ["performance", "model"]
        },
        "policy": {
            "streaming_enabled": true,
            "streaming_default": false,
            "history_persistence": true,
            "pii_redaction": "anonymize"
        }
    }'::jsonb,
    '{
        "prompts": {
            "system_prompt": "You are a model evaluation assistant. Help evaluate LLM performance.",
            "developer_prompt": "Provide model evaluation responses for benchmarking.",
            "fewshots": [],
            "variables": []
        },
        "seed_script": "009_seed_draft_use_cases",
        "team": "team:development"
    }'::jsonb,
    (SELECT id FROM users WHERE username = 'developer1' LIMIT 1)
) ON CONFLICT (use_case_id) DO NOTHING;

COMMIT;

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
DECLARE
    draft_count INTEGER;
    csirt_drafts INTEGER;
    governance_drafts INTEGER;
    development_drafts INTEGER;
    drafts_with_team_id INTEGER;
    drafts_without_team_id INTEGER;
BEGIN
    -- Count total draft use cases
    SELECT COUNT(*) INTO draft_count
    FROM use_cases
    WHERE lifecycle_state = 'draft'
      AND metadata->>'seed_script' = '009_seed_draft_use_cases';

    -- Count by team
    SELECT COUNT(*) INTO csirt_drafts
    FROM use_cases
    WHERE lifecycle_state = 'draft'
      AND team_id = 'team:csirt_security'
      AND metadata->>'seed_script' = '009_seed_draft_use_cases';

    SELECT COUNT(*) INTO governance_drafts
    FROM use_cases
    WHERE lifecycle_state = 'draft'
      AND team_id = 'team:soc_governance'
      AND metadata->>'seed_script' = '009_seed_draft_use_cases';

    SELECT COUNT(*) INTO development_drafts
    FROM use_cases
    WHERE lifecycle_state = 'draft'
      AND team_id = 'team:development'
      AND metadata->>'seed_script' = '009_seed_draft_use_cases';

    -- Verify all drafts have team_id
    SELECT COUNT(*) INTO drafts_with_team_id
    FROM use_cases
    WHERE lifecycle_state = 'draft'
      AND team_id IS NOT NULL
      AND metadata->>'seed_script' = '009_seed_draft_use_cases';

    SELECT COUNT(*) INTO drafts_without_team_id
    FROM use_cases
    WHERE lifecycle_state = 'draft'
      AND team_id IS NULL
      AND metadata->>'seed_script' = '009_seed_draft_use_cases';

    RAISE NOTICE '✅ Draft use cases seeded successfully!';
    RAISE NOTICE '   - Total draft use cases: %', draft_count;
    RAISE NOTICE '';
    RAISE NOTICE '👥 Draft Use Cases by Team:';
    RAISE NOTICE '   - team:csirt_security: % drafts', csirt_drafts;
    RAISE NOTICE '   - team:soc_governance: % drafts', governance_drafts;
    RAISE NOTICE '   - team:development: % drafts', development_drafts;
    RAISE NOTICE '';
    RAISE NOTICE '🔒 Team Isolation Verification:';
    RAISE NOTICE '   - Drafts with team_id: %', drafts_with_team_id;
    RAISE NOTICE '   - Drafts without team_id: % (should be 0)', drafts_without_team_id;
    RAISE NOTICE '';
    RAISE NOTICE '📝 Note: Draft use cases are visible only to:';
    RAISE NOTICE '   - Team members (users with matching team role)';
    RAISE NOTICE '   - Admins (full access)';
    RAISE NOTICE '   - use_case_admin (all teams)';
END $$;

-- Display draft use cases
SELECT
    use_case_id,
    name,
    team_id,
    lifecycle_state,
    is_active,
    category,
    created_at
FROM use_cases
WHERE lifecycle_state = 'draft'
  AND metadata->>'seed_script' = '009_seed_draft_use_cases'
ORDER BY team_id, use_case_id;
