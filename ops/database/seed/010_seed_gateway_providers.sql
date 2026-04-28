-- ============================================================================
-- Seed Data: Gateway Providers
-- ============================================================================
-- Description: Populates gateway_providers table with initial provider configurations
-- Prerequisites: 000_complete_init.sql, 001_seed_users.sql, 029_gateway_providers.sql
-- Date: 2025-12-11
--
-- Default Providers:
--   - LMStudio: OpenAI-compatible local server for embedding and LLM models
--
-- Usage:
--   PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
--     -h $POSTGRES_HOST -p $POSTGRES_PORT \
--     -U $POSTGRES_USER -d $POSTGRES_DB \
--     -f ops/database/seed/010_seed_gateway_providers.sql
-- ============================================================================

BEGIN;

-- ============================================================================
-- Gateway Providers
-- ============================================================================

INSERT INTO gateway_providers (
    name,
    provider_type,
    base_url,
    is_enabled,
    status,
    priority,
    health_check_url,
    config_json,
    created_by
) VALUES
-- LMStudio (OpenAI-compatible local server)
(
    'LMStudio',
    'openai',
    'http://host.docker.internal:1234/v1',
    TRUE,
    'active',
    100,
    'http://host.docker.internal:1234/v1/models',
    '{
        "timeout_seconds": 60,
        "max_retries": 3,
        "description": "OpenAI-compatible local server for embedding and LLM models"
    }'::jsonb,
    (SELECT id FROM users WHERE username = 'admin' LIMIT 1)
)
ON CONFLICT (name) DO UPDATE SET
    provider_type = EXCLUDED.provider_type,
    base_url = EXCLUDED.base_url,
    is_enabled = EXCLUDED.is_enabled,
    status = EXCLUDED.status,
    priority = EXCLUDED.priority,
    health_check_url = EXCLUDED.health_check_url,
    config_json = EXCLUDED.config_json,
    updated_at = NOW();

COMMIT;

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
DECLARE
    provider_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO provider_count FROM gateway_providers;

    RAISE NOTICE '✅ Gateway providers seeded successfully!';
    RAISE NOTICE '   - Total providers: %', provider_count;
    RAISE NOTICE '';
    RAISE NOTICE '📡 Available Providers:';
    RAISE NOTICE '   - LMStudio: http://host.docker.internal:1234/v1';
    RAISE NOTICE '';
    RAISE NOTICE '💡 Note: Models can reference provider name in models.provider column';
    RAISE NOTICE '   Example: UPDATE models SET provider = ''LMStudio'' WHERE model_id = ''text-embedding-bge-m3'';';
END $$;

-- Display all gateway providers
SELECT
    gp.name,
    gp.provider_type::text,
    gp.base_url,
    gp.is_enabled,
    gp.status::text,
    gp.priority
FROM gateway_providers gp
ORDER BY gp.priority, gp.name;
