-- ============================================================================
-- Seed Data: Model Registry
-- ============================================================================
-- Description: Populates model registry with default LLM and embedding models
-- Prerequisites: 000_complete_init.sql, 001_seed_users.sql, 004_seed_pricing.sql
--
-- Default Models:
--   LLMs: gpt-4o-mini, gpt-4o, gpt-4-turbo, claude-3-sonnet, claude-3-opus
--   Model Configs: foundation-sec, phi-4-mini, mistral-large, mistral-small, gpt-oss, llama-3.3
--
-- Usage:
--   PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
--     -h $POSTGRES_HOST -p $POSTGRES_PORT \
--     -U $POSTGRES_USER -d $POSTGRES_DB \
--     -f scripts/database/seed/005_seed_models.sql
-- ============================================================================

BEGIN;

-- ============================================================================
-- Model Registry (from models table)
-- ============================================================================

-- Insert default LLM models
INSERT INTO models (
    model_id, name, provider, model_type,
    context_window, max_output_tokens,
    default_temperature, description, specialization,
    recommended_use_cases, created_by
) VALUES
(
    'gpt-4o-mini',
    'GPT-4O Mini',
    'openai',
    'llm',
    128000,
    16384,
    0.7,
    'Fast and cost-effective model for general queries',
    'general',
    ARRAY['query', 'analysis', 'general'],
    (SELECT id FROM users WHERE username = 'admin' LIMIT 1)
),
(
    'gpt-4o',
    'GPT-4O',
    'openai',
    'llm',
    128000,
    16384,
    0.7,
    'Advanced model with vision and tool capabilities',
    'multimodal',
    ARRAY['query', 'analysis', 'complex_reasoning'],
    (SELECT id FROM users WHERE username = 'admin' LIMIT 1)
),
(
    'gpt-4-turbo',
    'GPT-4 Turbo',
    'openai',
    'llm',
    128000,
    4096,
    0.2,
    'High-capability model for complex tasks',
    'advanced_analysis',
    ARRAY['rule_generation', 'complex_reasoning', 'code_generation'],
    (SELECT id FROM users WHERE username = 'admin' LIMIT 1)
),
(
    'claude-3-sonnet',
    'Claude 3 Sonnet',
    'anthropic',
    'llm',
    200000,
    4096,
    0.7,
    'Balanced model for various tasks',
    'general',
    ARRAY['query', 'analysis', 'summarization'],
    (SELECT id FROM users WHERE username = 'admin' LIMIT 1)
),
(
    'claude-3-opus',
    'Claude 3 Opus',
    'anthropic',
    'llm',
    200000,
    4096,
    0.7,
    'Most capable Claude model for complex tasks',
    'advanced_analysis',
    ARRAY['complex_reasoning', 'analysis', 'rule_generation'],
    (SELECT id FROM users WHERE username = 'admin' LIMIT 1)
)
ON CONFLICT (model_id) DO NOTHING;

-- ============================================================================
-- Model Configs (with tokenizer and pricing tier associations)
-- ============================================================================

INSERT INTO model_configs (
    model_id, model_name, model_provider,
    tokenizer_type, encoding_name,
    default_pricing_tier_id,
    supports_streaming, max_context_tokens,
    is_active, description,
    created_by
)
VALUES
    (
        'foundation-sec',
        'Foundation Security Model',
        'foundation',
        'tiktoken',
        'foundation-sec',
        (SELECT id FROM pricing_tiers WHERE tier_key = 'M|Large'),
        TRUE,
        8192,
        TRUE,
        'Foundation security-focused model',
        (SELECT id FROM users WHERE username = 'admin' LIMIT 1)
    ),
    (
        'phi-4-mini',
        'Phi-4 Mini',
        'microsoft',
        'tiktoken',
        'phi-4-mini',
        (SELECT id FROM pricing_tiers WHERE tier_key = 'S|Small'),
        TRUE,
        4096,
        TRUE,
        'Microsoft Phi-4 Mini model',
        (SELECT id FROM users WHERE username = 'admin' LIMIT 1)
    ),
    (
        'mistral-large',
        'Mistral Large',
        'mistral',
        'tiktoken',
        'mistral-large',
        (SELECT id FROM pricing_tiers WHERE tier_key = 'M|Large'),
        TRUE,
        8192,
        TRUE,
        'Mistral Large model',
        (SELECT id FROM users WHERE username = 'admin' LIMIT 1)
    ),
    (
        'mistral-small',
        'Mistral Small',
        'mistral',
        'tiktoken',
        'mistral-small',
        (SELECT id FROM pricing_tiers WHERE tier_key = 'M|Small'),
        TRUE,
        8192,
        TRUE,
        'Mistral Small model',
        (SELECT id FROM users WHERE username = 'admin' LIMIT 1)
    ),
    (
        'gpt-oss',
        'GPT Open Source',
        'openai',
        'tiktoken',
        'cl100k_base',
        (SELECT id FROM pricing_tiers WHERE tier_key = 'L|Large'),
        TRUE,
        4096,
        TRUE,
        'Open source GPT variant',
        (SELECT id FROM users WHERE username = 'admin' LIMIT 1)
    ),
    (
        'llama-3.3',
        'Llama 3.3',
        'meta',
        'tiktoken',
        'llama-3.3',
        (SELECT id FROM pricing_tiers WHERE tier_key = 'L|Codestral/Llama'),
        TRUE,
        8192,
        TRUE,
        'Meta Llama 3.3 model',
        (SELECT id FROM users WHERE username = 'admin' LIMIT 1)
    )
ON CONFLICT (model_id) DO NOTHING;

COMMIT;

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
DECLARE
    model_count INTEGER;
    config_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO model_count FROM models;
    SELECT COUNT(*) INTO config_count FROM model_configs;

    RAISE NOTICE '✅ Model registry seeded successfully!';
    RAISE NOTICE '   - Models registered: %', model_count;
    RAISE NOTICE '   - Model configs: %', config_count;
    RAISE NOTICE '';
    RAISE NOTICE '🤖 Available LLM Models:';
    RAISE NOTICE '   OpenAI: gpt-4o-mini, gpt-4o, gpt-4-turbo, gpt-oss';
    RAISE NOTICE '   Anthropic: claude-3-sonnet, claude-3-opus';
    RAISE NOTICE '   Mistral: mistral-large, mistral-small';
    RAISE NOTICE '   Microsoft: phi-4-mini';
    RAISE NOTICE '   Meta: llama-3.3';
    RAISE NOTICE '   Foundation: foundation-sec';
    RAISE NOTICE '';
    RAISE NOTICE '💡 Context Windows:';
    RAISE NOTICE '   - GPT-4O/Turbo: 128K tokens';
    RAISE NOTICE '   - Claude 3: 200K tokens';
    RAISE NOTICE '   - Others: 4K-8K tokens';
END $$;

-- Display registered models
SELECT
    m.model_id,
    m.name,
    m.provider::text as provider,
    m.model_type::text as type,
    m.context_window,
    m.specialization
FROM models m
ORDER BY m.provider, m.model_id;

-- Display model configs with pricing
SELECT
    mc.model_id,
    mc.model_name,
    mc.model_provider,
    pt.tier_key as pricing_tier,
    mc.max_context_tokens,
    mc.is_active
FROM model_configs mc
LEFT JOIN pricing_tiers pt ON mc.default_pricing_tier_id = pt.id
ORDER BY mc.model_provider, mc.model_id;
