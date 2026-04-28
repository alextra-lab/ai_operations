-- ============================================================================
-- Migration: 034_set_documents_as_default_collection.sql
-- Description: Set "documents" collection (BGE-M3) as the default for uploads
-- Created: 2025-01-11
-- ============================================================================

BEGIN;

-- Remove default flag from all collections
UPDATE collections
SET is_default = FALSE
WHERE is_default = TRUE;

-- Set "documents" collection as the default
UPDATE collections
SET is_default = TRUE
WHERE name = 'documents';

COMMIT;

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
DECLARE
    default_collection_name VARCHAR(255);
    default_collection_model VARCHAR(255);
BEGIN
    SELECT name, embedding_model
    INTO default_collection_name, default_collection_model
    FROM collections
    WHERE is_default = TRUE
    LIMIT 1;

    RAISE NOTICE '';
    RAISE NOTICE '✅ Default collection updated successfully!';
    RAISE NOTICE '   - Default collection: %', default_collection_name;
    RAISE NOTICE '   - Embedding model: %', default_collection_model;
    RAISE NOTICE '';
END $$;

-- Show all collections
SELECT
    name,
    embedding_model,
    is_default,
    is_active,
    document_count
FROM collections
ORDER BY is_default DESC, name;
