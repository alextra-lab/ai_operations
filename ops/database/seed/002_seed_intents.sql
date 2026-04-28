-- ============================================================================
-- Seed Data: Intent System
-- ============================================================================
-- Description: Populates intent categories and system intents
-- Prerequisites: 000_complete_init.sql, 001_seed_users.sql
--
-- Intent Categories:
--   - GENERAL, SECURITY, LEGAL, HR, FINANCE, COMPLIANCE
--
-- System Intents:
--   - QUERY, RULE_GENERATION, SUMMARIZATION, ENRICHMENT
--
-- Usage:
--   PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
--     -h $POSTGRES_HOST -p $POSTGRES_PORT \
--     -U $POSTGRES_USER -d $POSTGRES_DB \
--     -f scripts/database/seed/002_seed_intents.sql
-- ============================================================================

BEGIN;

-- ============================================================================
-- Intent Categories
-- ============================================================================

INSERT INTO intent_categories (category_code, display_name, description, icon, color, sort_order)
VALUES
    (
        'GENERAL',
        'General Purpose',
        'General-purpose AI assistant capabilities',
        'chat',
        '#607D8B',
        1
    ),
    (
        'SECURITY',
        'Security Operations',
        'Cybersecurity and SOC workflows',
        'security',
        '#f44336',
        2
    ),
    (
        'LEGAL',
        'Legal Affairs',
        'Legal document analysis and compliance',
        'gavel',
        '#9C27B0',
        3
    ),
    (
        'HR',
        'Human Resources',
        'HR policies, recruitment, and employee management',
        'people',
        '#4CAF50',
        4
    ),
    (
        'FINANCE',
        'Finance & Accounting',
        'Financial analysis and reporting',
        'attach_money',
        '#FF9800',
        5
    ),
    (
        'COMPLIANCE',
        'Compliance & Risk',
        'Regulatory compliance and risk management',
        'policy',
        '#3F51B5',
        6
    )
ON CONFLICT (category_code) DO NOTHING;

-- ============================================================================
-- System Intent Types (ADR-067: domain-neutral)
-- ============================================================================

-- These system intents are marked as is_system=TRUE and cannot be deleted.
-- They serve as configuration presets for the wizard (ADR-041).
-- Migration 036 adds capability profile columns for auto-presets.

INSERT INTO intent_types (
    intent_code,
    display_name,
    description,
    category_id,
    recommended_model,
    default_temperature_min,
    default_temperature_max,
    icon,
    color,
    is_system,
    sort_order
)
VALUES
    -- QUERY: General information retrieval
    (
        'QUERY',
        'General Query',
        'General question answering',
        (SELECT id FROM intent_categories WHERE category_code = 'GENERAL'),
        'mistral-small',
        0.5,
        0.9,
        'question_answer',
        '#2196F3',
        TRUE,
        1
    ),

    -- RULE_GENERATION: Structured rule/artifact generation
    (
        'RULE_GENERATION',
        'Rule / Artifact Generation',
        'Generate structured rules or artifacts from specifications',
        (SELECT id FROM intent_categories WHERE category_code = 'GENERAL'),
        'mistral-large',
        0.1,
        0.3,
        'policy',
        '#FF5722',
        TRUE,
        2
    ),

    -- SUMMARIZATION: Content summarization
    (
        'SUMMARIZATION',
        'Content Summarization',
        'Content summarization',
        (SELECT id FROM intent_categories WHERE category_code = 'GENERAL'),
        'mistral-small',
        0.3,
        0.7,
        'summarize',
        '#4CAF50',
        TRUE,
        3
    ),

    -- ENRICHMENT: Data enrichment
    (
        'ENRICHMENT',
        'Data Enrichment',
        'Data enrichment and augmentation',
        (SELECT id FROM intent_categories WHERE category_code = 'GENERAL'),
        'mistral-large',
        0.2,
        0.5,
        'psychology',
        '#9C27B0',
        TRUE,
        4
    )
ON CONFLICT (intent_code) DO NOTHING;

-- ============================================================================
-- NOTE: Role-Based Permissions Moved to Use Cases (ADR-041)
-- ============================================================================
-- Previously, this script created role_intent_permissions assignments.
--
-- Per ADR-041, Intent Types are configuration presets only, NOT permission boundaries.
-- Permissions are now managed at the Use Case level via role_use_case_assignments.
--
-- See: scripts/database/seed/003_seed_use_cases.sql for role-use case assignments.
-- ============================================================================

COMMIT;

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
DECLARE
    category_count INTEGER;
    intent_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO category_count FROM intent_categories;
    SELECT COUNT(*) INTO intent_count FROM intent_types WHERE is_system = TRUE;

    RAISE NOTICE '✅ Intent system seeded successfully!';
    RAISE NOTICE '   - Categories: %', category_count;
    RAISE NOTICE '   - System intents: %', intent_count;
    RAISE NOTICE '';
    RAISE NOTICE '📋 Intent Categories:';
    RAISE NOTICE '   - GENERAL, SECURITY, LEGAL, HR, FINANCE, COMPLIANCE';
    RAISE NOTICE '';
    RAISE NOTICE '🎯 System Intents (Configuration Presets):';
    RAISE NOTICE '   - QUERY: General question answering';
    RAISE NOTICE '   - RULE_GENERATION: Rule / artifact generation';
    RAISE NOTICE '   - SUMMARIZATION: Content summarization';
    RAISE NOTICE '   - ENRICHMENT: Data enrichment';
    RAISE NOTICE '';
    RAISE NOTICE 'ℹ️  Intent Types are configuration presets only (ADR-041)';
    RAISE NOTICE '   Permissions managed at Use Case level - see 003_seed_use_cases.sql';
END $$;

-- Display seeded data
SELECT
    ic.category_code,
    ic.display_name as category,
    COUNT(it.id) as intent_count
FROM intent_categories ic
LEFT JOIN intent_types it ON ic.id = it.category_id
GROUP BY ic.category_code, ic.display_name, ic.sort_order
ORDER BY ic.sort_order;
