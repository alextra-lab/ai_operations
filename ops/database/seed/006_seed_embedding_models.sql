-- ============================================================================
-- Seed Data: Embedding Models Registry
-- ============================================================================
-- Description: Populates model registry with embedding models for vector search
-- Prerequisites: 000_complete_init.sql, 001_seed_users.sql
-- Source: config/models/model_metadata.yaml (local embedding models)
--
-- Default Embedding Models:
--   - Nomic Embed v1.5 (q4_k_m, f16) - 768 dimensions
--   - BGE-M3 - 1024 dimensions
--   - E5 Mistral 7B - 4096 dimensions
--   - Multi-QA MiniLM L6 - 384 dimensions
--
-- Note: System currently enforces single embedding model via env vars.
--       Multi-model support planned for Phase 5 (P5-F8).
--
-- Usage:
--   PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
--     -h $POSTGRES_HOST -p $POSTGRES_PORT \
--     -U $POSTGRES_USER -d $POSTGRES_DB \
--     -f ops/database/seed/006_seed_embedding_models.sql
-- ============================================================================

BEGIN;

-- ============================================================================
-- Embedding Models (from config/models/model_metadata.yaml)
-- ============================================================================

INSERT INTO models (
    model_id,
    name,
    provider_type,
    provider,
    model_type,
    context_window,
    embedding_dimensions,
    description,
    specialization,
    is_available,
    health_status,
    created_by
) VALUES
-- Nomic Embed v1.5 (FP16)
(
    'text-embedding-nomic-embed-text-v1.5@f16',
    'Nomic Embed Text v1.5 (FP16)',
    'openai',
    'LMStudio',
    'embedding',
    8192,
    768,
    'Nomic Embed Text v1.5 (FP16)',
    'general',
    TRUE,
    'unknown',
    (SELECT id FROM users WHERE username = 'admin' LIMIT 1)
),
-- BGE-M3 Multilingual
(
    'text-embedding-bge-m3',
    'BGE-M3',
    'openai',
    'LMStudio',
    'embedding',
    8192,
    1024,
    'BGE-M3 multilingual embedding model',
    'general',
    TRUE,
    'unknown',
    (SELECT id FROM users WHERE username = 'admin' LIMIT 1)
),
-- E5 Mistral 7B
(
    'e5-mistral-7b-instruct-embedding',
    'E5 Mistral 7B',
    'openai',
    'LMStudio',
    'embedding',
    4096,
    4096,
    'E5 Mistral 7B instruction-tuned embedding model',
    'general',
    TRUE,
    'unknown',
    (SELECT id FROM users WHERE username = 'admin' LIMIT 1)
),
-- Multi-QA MiniLM L6
(
    'text-embedding-gguf-multi-qa-minilm-l6-cos-v1',
    'Multi-QA MiniLM L6',
    'openai',
    'LMStudio',
    'embedding',
    512,
    384,
    'Multi-QA MiniLM L6 cosine similarity model',
    'general',
    TRUE,
    'unknown',
    (SELECT id FROM users WHERE username = 'admin' LIMIT 1)
),
-- all-MiniLM-L6-v2 (Built-in)
(
    'all-MiniLM-L6-v2',
    'all-MiniLM-L6-v2',
    'local',
    NULL,
    'embedding',
    256,
    384,
    'Built-in local embedding model from sentence-transformers. Fast, no API costs, always available. 384-dimensional sentence embeddings.',
    'sentence-embeddings',
    TRUE,
    'healthy',
    (SELECT id FROM users WHERE username = 'admin' LIMIT 1)
)
ON CONFLICT (model_id) DO NOTHING;

COMMIT;

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
DECLARE
    embedding_count INTEGER;
    total_models INTEGER;
BEGIN
    SELECT COUNT(*) INTO embedding_count FROM models WHERE model_type = 'embedding';
    SELECT COUNT(*) INTO total_models FROM models;

    RAISE NOTICE '✅ Embedding models seeded successfully!';
    RAISE NOTICE '   - Embedding models: %', embedding_count;
    RAISE NOTICE '   - Total models: %', total_models;
    RAISE NOTICE '';
    RAISE NOTICE '🔢 Embedding Dimensions:';
    RAISE NOTICE '   - 384D: all-MiniLM-L6-v2 (built-in, always available), Multi-QA MiniLM L6';
    RAISE NOTICE '   - 768D: Nomic Embed v1.5 (f16)';
    RAISE NOTICE '   - 1024D: BGE-M3';
    RAISE NOTICE '   - 4096D: E5 Mistral 7B';
    RAISE NOTICE '';
    RAISE NOTICE '💡 ADR-021 Addendum 3: Per-Collection Embedding Model Selection';
    RAISE NOTICE '   - Collections can now choose their embedding model at creation';
    RAISE NOTICE '   - Use Cases enforce same-model multi-collection searches';
    RAISE NOTICE '   - all-MiniLM-L6-v2 is built-in and always available';
END $$;

-- Display all embedding models
SELECT
    m.model_id,
    m.name,
    m.provider::text as provider,
    m.embedding_dimensions as dims,
    m.context_window as ctx_window,
    m.is_available
FROM models m
WHERE m.model_type = 'embedding'
ORDER BY m.embedding_dimensions, m.model_id;
