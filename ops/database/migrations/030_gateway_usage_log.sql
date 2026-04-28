-- Migration: 030_gateway_usage_log
-- Description: Create usage log table for Inference Gateway request/response tracking
-- Dependencies: users, gateway_providers tables
-- Date: 2025-11-03
-- Part of: P1-T2 Inference Gateway Database Schema

-- Create gateway_usage_log table
CREATE TABLE IF NOT EXISTS gateway_usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(255) NOT NULL,                   -- Correlation ID from X-Request-ID header
    ts_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Request metadata
    user_id UUID REFERENCES users(id),                  -- User making the request (nullable for service accounts)
    integration_id VARCHAR(255),                        -- Integration/service account identifier
    endpoint VARCHAR(100) NOT NULL,                     -- Gateway endpoint hit (e.g., /v1/chat/completions)

    -- Routing information
    provider_id UUID REFERENCES gateway_providers(id),  -- Provider used for this request
    provider_name VARCHAR(255),                         -- Denormalized provider name for fast queries
    model_requested VARCHAR(255) NOT NULL,              -- Model requested by client
    model_used VARCHAR(255),                            -- Actual model used (may differ if routing/mapping)

    -- Token usage
    tokens_in INTEGER NOT NULL DEFAULT 0 CHECK (tokens_in >= 0),
    tokens_out INTEGER NOT NULL DEFAULT 0 CHECK (tokens_out >= 0),
    tokens_total INTEGER GENERATED ALWAYS AS (tokens_in + tokens_out) STORED,

    -- Cost tracking
    cost_eur NUMERIC(10, 6) DEFAULT 0.00 CHECK (cost_eur >= 0),

    -- Latency metrics (milliseconds)
    latency_total_ms INTEGER NOT NULL CHECK (latency_total_ms >= 0),
    latency_gateway_ms INTEGER CHECK (latency_gateway_ms >= 0),    -- Gateway processing overhead
    latency_provider_ms INTEGER CHECK (latency_provider_ms >= 0),   -- Provider API call latency

    -- Request/response status
    http_status INTEGER NOT NULL,                       -- HTTP status code returned to client
    success BOOLEAN NOT NULL DEFAULT false,             -- Whether request succeeded
    error_type VARCHAR(100),                            -- Error type if failed (timeout, rate_limit, etc.)
    error_message TEXT,                                 -- Error details (sanitized, no secrets)

    -- Additional context
    stream_enabled BOOLEAN DEFAULT false,               -- Whether streaming was used
    cache_hit BOOLEAN DEFAULT false,                    -- Cache hit (future use)
    retry_count INTEGER DEFAULT 0,                      -- Number of retries attempted
    metadata_json JSONB DEFAULT '{}',                   -- Additional request metadata

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for query performance
CREATE INDEX IF NOT EXISTS idx_gateway_usage_log_ts_utc ON gateway_usage_log(ts_utc DESC);
CREATE INDEX IF NOT EXISTS idx_gateway_usage_log_user_id ON gateway_usage_log(user_id, ts_utc DESC);
CREATE INDEX IF NOT EXISTS idx_gateway_usage_log_provider_id ON gateway_usage_log(provider_id, ts_utc DESC);
CREATE INDEX IF NOT EXISTS idx_gateway_usage_log_request_id ON gateway_usage_log(request_id);
CREATE INDEX IF NOT EXISTS idx_gateway_usage_log_model ON gateway_usage_log(model_requested, ts_utc DESC);
CREATE INDEX IF NOT EXISTS idx_gateway_usage_log_success ON gateway_usage_log(success, ts_utc DESC);
CREATE INDEX IF NOT EXISTS idx_gateway_usage_log_error_type ON gateway_usage_log(error_type) WHERE error_type IS NOT NULL;

-- Composite index for analytics queries
CREATE INDEX IF NOT EXISTS idx_gateway_usage_log_analytics
    ON gateway_usage_log(provider_id, model_requested, ts_utc DESC)
    INCLUDE (tokens_total, cost_eur, latency_total_ms);

-- Add column comments
COMMENT ON TABLE gateway_usage_log IS 'Inference Gateway usage tracking - logs all requests for analytics, billing, and debugging';
COMMENT ON COLUMN gateway_usage_log.request_id IS 'Correlation ID from X-Request-ID header for distributed tracing';
COMMENT ON COLUMN gateway_usage_log.user_id IS 'User making the request (null for service account requests)';
COMMENT ON COLUMN gateway_usage_log.integration_id IS 'Service account or integration identifier (e.g., "orchestrator", "embedding-service")';
COMMENT ON COLUMN gateway_usage_log.endpoint IS 'Gateway endpoint accessed (e.g., /v1/chat/completions, /v1/embeddings)';
COMMENT ON COLUMN gateway_usage_log.provider_name IS 'Denormalized provider name for fast queries without join';
COMMENT ON COLUMN gateway_usage_log.model_requested IS 'Model requested by client in API call';
COMMENT ON COLUMN gateway_usage_log.model_used IS 'Actual model used after routing/mapping (may differ from requested)';
COMMENT ON COLUMN gateway_usage_log.cost_eur IS 'Total cost in EUR calculated from pricing history';
COMMENT ON COLUMN gateway_usage_log.latency_gateway_ms IS 'Gateway processing overhead (total - provider)';
COMMENT ON COLUMN gateway_usage_log.latency_provider_ms IS 'Provider API call latency (measured at Gateway)';
COMMENT ON COLUMN gateway_usage_log.error_type IS 'Error classification: timeout, rate_limit, auth_failed, provider_error, etc.';
COMMENT ON COLUMN gateway_usage_log.metadata_json IS 'Additional request context: headers, retry info, circuit breaker state, etc.';
