-- ============================================================================
-- Seed Data: Set "documents" Collection as Default
-- ============================================================================
-- Description: Data operation consolidated from migration
--              034_set_documents_as_default_collection.sql (AIO-65).
--              If a "documents" collection (BGE-M3) exists, promote it to the
--              default for uploads. Idempotent and a no-op when the "documents"
--              collection is absent (e.g. on a fresh init that only seeds the
--              "default" collection).
-- Prerequisites: 000_complete_init.sql
-- ============================================================================

BEGIN;

-- Only re-point the default flag when a "documents" collection actually exists,
-- so the seeded "default" collection remains the default otherwise.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM collections WHERE name = 'documents') THEN
    UPDATE collections SET is_default = FALSE WHERE is_default = TRUE;
    UPDATE collections SET is_default = TRUE WHERE name = 'documents';
  END IF;
END $$;

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

  RAISE NOTICE 'Default collection: % (model: %)',
    default_collection_name, default_collection_model;
END $$;
