-- Seed: 011_seed_gateway_rate_limits_defaults
-- Description: Default rate limit configurations for Inference Gateway
-- Dependencies: 032_gateway_rate_limits.sql (table must exist)
-- Date: 2025-11-03
-- Part of: P2-T5 Rate Limiting Implementation

-- Clear existing rate limits (for idempotency)
DELETE FROM gateway_rate_limits;

-- Global rate limit: Protect Gateway infrastructure
-- 500 req/min system capacity, 50 burst allowance
INSERT INTO gateway_rate_limits (
    limit_type,
    identifier,
    requests_per_minute,
    tokens_per_minute,
    burst_size,
    enabled,
    description
) VALUES (
    'global',
    NULL,
    500,
    NULL,
    50,
    true,
    'System-wide request limit to protect Gateway infrastructure (500 RPM + 50 burst)'
);

-- OpenAI provider limit: Stay under upstream limit
-- OpenAI Tier 1: 500 RPM, we use 450 (10% buffer)
-- OpenAI Tier 1: 200K TPM, we use 180K (10% buffer)
INSERT INTO gateway_rate_limits (
    limit_type,
    identifier,
    requests_per_minute,
    tokens_per_minute,
    burst_size,
    enabled,
    description
) VALUES (
    'provider',
    'openai',
    450,
    180000,
    20,
    true,
    'OpenAI provider limit with 10% buffer to avoid upstream blocking (450/500 RPM, 180K/200K TPM)'
);

-- Mistral provider limit: Stay under upstream limit
-- Mistral Free Tier: 200 RPM, we use 180 (10% buffer)
-- Mistral Free Tier: 100K TPM, we use 90K (10% buffer)
INSERT INTO gateway_rate_limits (
    limit_type,
    identifier,
    requests_per_minute,
    tokens_per_minute,
    burst_size,
    enabled,
    description
) VALUES (
    'provider',
    'mistral',
    180,
    90000,
    10,
    true,
    'Mistral provider limit with 10% buffer to avoid upstream blocking (180/200 RPM, 90K/100K TPM)'
);

-- Anthropic provider limit: Conservative limit
-- Anthropic Tier 1: 1000 RPM, 100K TPM
-- We use conservative limits: 900 RPM, 90K TPM (10% buffer)
INSERT INTO gateway_rate_limits (
    limit_type,
    identifier,
    requests_per_minute,
    tokens_per_minute,
    burst_size,
    enabled,
    description
) VALUES (
    'provider',
    'anthropic',
    900,
    90000,
    50,
    true,
    'Anthropic provider limit with 10% buffer (900/1000 RPM, 90K/100K TPM)'
);

-- Example integration limit (disabled by default)
-- SOAR integrations should have per-service limits to prevent runaway scripts
INSERT INTO gateway_rate_limits (
    limit_type,
    identifier,
    requests_per_minute,
    tokens_per_minute,
    burst_size,
    enabled,
    description
) VALUES (
    'integration',
    'service:cortex-prod',
    100,
    NULL,
    10,
    false,
    'Rate limit for Cortex SOAR production integration (100 RPM, disabled until Cortex deployed)'
);

-- Example use case limit (disabled by default)
-- Use case limits for cost control (Phase 2 feature)
-- Note: use_case limits not fully implemented in v1, structure only
INSERT INTO gateway_rate_limits (
    limit_type,
    identifier,
    requests_per_minute,
    tokens_per_minute,
    burst_size,
    enabled,
    description
) VALUES (
    'use_case',
    '00000000-0000-0000-0000-000000000000',
    50,
    NULL,
    5,
    false,
    'Example: Per-use-case rate limit for cost control (not implemented in v1)'
);

-- Log seed completion
DO $$
BEGIN
    RAISE NOTICE 'Gateway rate limits seeded: % configurations', (SELECT COUNT(*) FROM gateway_rate_limits);
END$$;
