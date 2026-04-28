-- Migration: 031_extend_run_manifests_gateway_metrics
-- Description: Add gateway_metrics JSONB column to run_manifests table
-- Dependencies: run_manifests table, gateway_providers table
-- Date: 2025-11-03
-- Part of: P1-T2 Inference Gateway Database Schema

-- Add gateway_metrics JSONB column to existing run_manifests table
ALTER TABLE run_manifests
ADD COLUMN IF NOT EXISTS gateway_metrics JSONB DEFAULT '{}'::jsonb;

-- Add GIN index for fast JSONB queries
CREATE INDEX IF NOT EXISTS idx_run_manifests_gateway_metrics
    ON run_manifests USING GIN (gateway_metrics);

-- Add column comment
COMMENT ON COLUMN run_manifests.gateway_metrics IS
'Gateway execution metrics captured during request processing. Example structure:
{
  "provider_id": "550e8400-e29b-41d4-a716-446655440000",
  "provider_name": "OpenAI Production",
  "provider_type": "openai",
  "model_requested": "gpt-4o-mini",
  "model_used": "gpt-4o-mini",
  "gateway_latency_ms": 5,
  "provider_latency_ms": 240,
  "tokens_in": 120,
  "tokens_out": 80,
  "cost_eur": 0.00015,
  "routing_decision": "primary",
  "retry_count": 0,
  "cache_hit": false,
  "circuit_state": "CLOSED"
}
This enables correlation between use case execution and provider performance without duplicating data.';

-- Update existing run_manifests with empty gateway_metrics if NULL
UPDATE run_manifests
SET gateway_metrics = '{}'::jsonb
WHERE gateway_metrics IS NULL;
