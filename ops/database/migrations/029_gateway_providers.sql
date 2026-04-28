-- Migration: 029_gateway_providers
-- Description: Create providers table for Inference Gateway
-- Dependencies: users table
-- Date: 2025-11-03
-- Part of: P1-T2 Inference Gateway Database Schema

-- Create enum for provider types
CREATE TYPE provider_type AS ENUM ('openai', 'mistral', 'anthropic', 'local', 'custom');

-- Create enum for provider status
CREATE TYPE provider_status AS ENUM ('active', 'disabled', 'error', 'testing');

-- Create gateway_providers table
CREATE TABLE IF NOT EXISTS gateway_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    provider_type provider_type NOT NULL,
    base_url TEXT NOT NULL,
    api_key_encrypted TEXT,                             -- Encrypted API key (if needed)
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    status provider_status NOT NULL DEFAULT 'testing',
    priority INTEGER NOT NULL DEFAULT 100,               -- Lower = higher priority for routing
    config_json JSONB DEFAULT '{}',                     -- Provider-specific configuration
    health_check_url TEXT,                              -- Optional health check endpoint
    last_health_check TIMESTAMPTZ,
    last_health_status BOOLEAN,
    error_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    circuit_state VARCHAR(20) DEFAULT 'CLOSED' CHECK (circuit_state IN ('CLOSED', 'OPEN', 'HALF_OPEN')),
    circuit_opened_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_gateway_providers_enabled ON gateway_providers(is_enabled) WHERE is_enabled = true;
CREATE INDEX IF NOT EXISTS idx_gateway_providers_status ON gateway_providers(status);
CREATE INDEX IF NOT EXISTS idx_gateway_providers_type ON gateway_providers(provider_type);
CREATE INDEX IF NOT EXISTS idx_gateway_providers_priority ON gateway_providers(priority) WHERE is_enabled = true;
CREATE INDEX IF NOT EXISTS idx_gateway_providers_circuit ON gateway_providers(circuit_state);

-- Add trigger for updated_at
CREATE OR REPLACE TRIGGER update_gateway_providers_updated_at
    BEFORE UPDATE ON gateway_providers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add column comments
COMMENT ON TABLE gateway_providers IS 'Inference Gateway provider registry - manages LLM and embedding provider configurations';
COMMENT ON COLUMN gateway_providers.name IS 'Human-readable provider name (e.g., "OpenAI Production", "Mistral Backup")';
COMMENT ON COLUMN gateway_providers.provider_type IS 'Provider type enum: openai, mistral, anthropic, local, custom';
COMMENT ON COLUMN gateway_providers.base_url IS 'Provider base URL (e.g., https://api.openai.com/v1)';
COMMENT ON COLUMN gateway_providers.api_key_encrypted IS 'Encrypted API key using pgcrypto (decrypt with shared secret)';
COMMENT ON COLUMN gateway_providers.is_enabled IS 'Enable/disable toggle - disabled providers are not used for routing';
COMMENT ON COLUMN gateway_providers.status IS 'Current provider status: active, disabled, error, testing';
COMMENT ON COLUMN gateway_providers.priority IS 'Routing priority (lower = higher priority) for provider selection';
COMMENT ON COLUMN gateway_providers.config_json IS 'Provider-specific configuration (timeout, retries, model mappings, etc.)';
COMMENT ON COLUMN gateway_providers.health_check_url IS 'Optional URL for automated health checks';
COMMENT ON COLUMN gateway_providers.error_count IS 'Cumulative error count for circuit breaker logic';
COMMENT ON COLUMN gateway_providers.success_count IS 'Cumulative success count for health tracking';
COMMENT ON COLUMN gateway_providers.circuit_state IS 'Circuit breaker state: CLOSED (healthy), OPEN (failing), HALF_OPEN (testing)';
COMMENT ON COLUMN gateway_providers.circuit_opened_at IS 'Timestamp when circuit breaker opened (for timeout tracking)';
