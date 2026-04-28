-- Migration: 039_add_temperature_to_intent_model_defaults.sql
-- Date: 2026-02-08
-- Purpose: Add per-intent temperature configuration to intent_model_defaults (ADR-069 extension).
-- When set, overrides ModelType metadata default at runtime.

ALTER TABLE intent_model_defaults
    ADD COLUMN IF NOT EXISTS temperature DECIMAL(3, 2);

COMMENT ON COLUMN intent_model_defaults.temperature IS
    'Optional temperature override for this intent (0.0-1.0). NULL = use ModelType default.';

-- Constraint: valid range when not null
ALTER TABLE intent_model_defaults
    ADD CONSTRAINT chk_intent_model_defaults_temperature
    CHECK (temperature IS NULL OR (temperature >= 0 AND temperature <= 1));
