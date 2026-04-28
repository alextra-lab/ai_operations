-- ============================================================================
-- Migration 033: Fix Embedding Model Provider Type and Provider
-- ============================================================================
-- Description: Update existing embedding models to have proper provider_type and provider
-- Issue: Seed file was missing provider_type column
-- Fix: Set provider_type and provider based on ADR-050 architecture
--
-- ADR-050 Provider Types:
--   - 'local' = Python in-process models (SentenceTransformer), no HTTP API
--   - 'openai' = OpenAI-compatible API (LMStudio, Ollama, vLLM, actual OpenAI)
--
-- Date: 2025-12-11
-- Reference: docs/development/adrs/ADR-050-Inference-Gateway-and-Responsibility-Split.md
-- ============================================================================

BEGIN;

-- First, ensure LMStudio gateway provider exists
INSERT INTO gateway_providers (
    name,
    provider_type,
    base_url,
    is_enabled,
    status,
    priority,
    created_by
) VALUES (
    'LMStudio',
    'openai',
    'http://host.docker.internal:1234/v1',
    TRUE,
    'active',
    100,
    (SELECT id FROM users WHERE username = 'admin' LIMIT 1)
)
ON CONFLICT (name) DO NOTHING;

-- Update LMStudio-served models (OpenAI-compatible API)
UPDATE models
SET
    provider_type = 'openai'::model_provider_enum,
    provider = 'LMStudio'
WHERE model_type = 'embedding'
AND model_id IN (
    'text-embedding-nomic-embed-text-v1.5@f16',
    'text-embedding-nomic-embed-text-v1.5@q4_k_m',
    'text-embedding-bge-m3',
    'e5-mistral-7b-instruct-embedding',
    'text-embedding-gguf-multi-qa-minilm-l6-cos-v1'
);

-- Update built-in local models (Python in-process, SentenceTransformer)
UPDATE models
SET
    provider_type = 'local'::model_provider_enum,
    provider = NULL
WHERE model_type = 'embedding'
AND model_id = 'all-MiniLM-L6-v2';

-- Verify the update
DO $$
DECLARE
    lmstudio_count INTEGER;
    local_count INTEGER;
    total_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO lmstudio_count
    FROM models
    WHERE model_type = 'embedding'
    AND provider_type = 'openai'
    AND provider = 'LMStudio';

    SELECT COUNT(*) INTO local_count
    FROM models
    WHERE model_type = 'embedding'
    AND provider_type = 'local'
    AND provider IS NULL;

    SELECT COUNT(*) INTO total_count
    FROM models
    WHERE model_type = 'embedding';

    RAISE NOTICE '✅ Migration 033 completed successfully!';
    RAISE NOTICE '   - LMStudio models (provider_type=openai, provider=LMStudio): %', lmstudio_count;
    RAISE NOTICE '   - Local in-process models (provider_type=local, provider=NULL): %', local_count;
    RAISE NOTICE '   - Total embedding models: %', total_count;
    RAISE NOTICE '';
    RAISE NOTICE '💡 ADR-050: Provider Architecture';
    RAISE NOTICE '   - provider_type=local: Python in-process (SentenceTransformer)';
    RAISE NOTICE '   - provider_type=openai: OpenAI-compatible (LMStudio, Ollama, vLLM)';
END $$;

COMMIT;
