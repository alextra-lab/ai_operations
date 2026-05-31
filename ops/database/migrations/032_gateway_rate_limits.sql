-- Migration: 032_gateway_rate_limits
-- Description: Create rate limits configuration table for Inference Gateway
-- Dependencies: None (standalone configuration table)
-- Date: 2025-11-03
-- Part of: P1-T2 Inference Gateway Database Schema
-- Note: Structure only - table will not be used until P2-T5 (Rate Limiting Implementation)

-- Create enum for rate limit types
DO $$ BEGIN
    CREATE TYPE rate_limit_type AS ENUM ('global', 'provider', 'integration', 'use_case');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Create gateway_rate_limits table
CREATE TABLE IF NOT EXISTS gateway_rate_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    limit_type rate_limit_type NOT NULL,
    identifier TEXT,                              -- NULL for global, 'openai' for provider, 'service:cortex-prod' for integration
    requests_per_minute INTEGER NOT NULL CHECK (requests_per_minute > 0),
    tokens_per_minute BIGINT CHECK (tokens_per_minute IS NULL OR tokens_per_minute > 0),
    burst_size INTEGER NOT NULL DEFAULT 10 CHECK (burst_size >= 0),
    enabled BOOLEAN NOT NULL DEFAULT true,
    description TEXT,                             -- Human-readable description of this limit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create unique constraint: only one limit per type+identifier combination
CREATE UNIQUE INDEX IF NOT EXISTS idx_gateway_rate_limits_unique
    ON gateway_rate_limits(limit_type, COALESCE(identifier, ''));

-- Create indexes for query performance
CREATE INDEX IF NOT EXISTS idx_gateway_rate_limits_type ON gateway_rate_limits(limit_type, enabled) WHERE enabled = true;
CREATE INDEX IF NOT EXISTS idx_gateway_rate_limits_identifier ON gateway_rate_limits(identifier) WHERE identifier IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_gateway_rate_limits_enabled ON gateway_rate_limits(enabled) WHERE enabled = true;

-- Add trigger for updated_at
CREATE OR REPLACE TRIGGER update_gateway_rate_limits_updated_at
    BEFORE UPDATE ON gateway_rate_limits
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add column comments
COMMENT ON TABLE gateway_rate_limits IS 'Inference Gateway rate limit configuration - defines request/token limits for global, provider, and integration levels';
COMMENT ON COLUMN gateway_rate_limits.limit_type IS 'Rate limit scope: global (system-wide), provider (per provider), integration (per service account), use_case (per use case)';
COMMENT ON COLUMN gateway_rate_limits.identifier IS 'Identifier for the limit scope: NULL for global, provider name (e.g., "openai"), integration ID (e.g., "service:cortex-prod"), or use_case_id';
COMMENT ON COLUMN gateway_rate_limits.requests_per_minute IS 'Maximum number of requests allowed per minute for this limit scope';
COMMENT ON COLUMN gateway_rate_limits.tokens_per_minute IS 'Maximum number of tokens (input + output) allowed per minute. NULL means no token limit (only request limit applies)';
COMMENT ON COLUMN gateway_rate_limits.burst_size IS 'Number of requests allowed to burst beyond the RPM limit (allows short spikes without rejection)';
COMMENT ON COLUMN gateway_rate_limits.enabled IS 'Enable/disable toggle - disabled limits are not enforced';
COMMENT ON COLUMN gateway_rate_limits.description IS 'Human-readable description of what this limit protects or controls';

-- Note: Table structure only - no seed data until P2-T5
-- Example future seed data (when implemented):
-- INSERT INTO gateway_rate_limits (limit_type, identifier, requests_per_minute, tokens_per_minute, burst_size, enabled, description) VALUES
--   ('global', NULL, 500, NULL, 50, true, 'System-wide request limit to protect Gateway infrastructure'),
--   ('provider', 'openai', 450, 150000, 20, true, 'OpenAI provider limit with 10% buffer to avoid upstream blocking'),
--   ('provider', 'mistral', 180, 90000, 10, true, 'Mistral provider limit with 10% buffer'),
--   ('integration', 'service:cortex-prod', 100, NULL, 10, true, 'Rate limit for Cortex SOAR production integration');
