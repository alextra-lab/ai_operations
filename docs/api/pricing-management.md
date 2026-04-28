# Pricing Management & Token Analytics API

**Version:** 1.0
**Last Updated:** October 13, 2025
**Status:** Production Ready

## Overview

The Pricing Management & Token Analytics API provides comprehensive LLMaaS pricing tier management and token rate limit monitoring capabilities. This system enables administrators to manage pricing configurations and analysts to monitor token usage in real-time.

## Base URLs

- **Test Environment:** `http://localhost:8006`
- **Production:** `TBD`

## Authentication

All endpoints require JWT authentication via Bearer token.

```bash
# Get access token
TOKEN=$(curl -s -X POST "http://localhost:8006/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" \
  -d "password=adminpassword" | jq -r '.access_token')

# Use token in requests
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8006/api/v1/admin/pricing/tiers"
```

## Pricing Management Endpoints

### Admin Pricing Tiers

**Base Path:** `/api/v1/admin/pricing/`
**Required Role:** `admin`

#### List Pricing Tiers

```http
GET /api/v1/admin/pricing/tiers
```

**Query Parameters:**
- `active_only` (boolean): Filter to active tiers only (default: false)
- `skip` (integer): Number of records to skip (default: 0)
- `limit` (integer): Number of records to return (default: 100, max: 1000)

**Response:**
```json
{
  "tiers": [
    {
      "id": "uuid",
      "tier_key": "L|Large",
      "tier_name": "Large - Mistral Large",
      "plan_size": "L",
      "model_class": "Large",
      "input_rate_per_1m": 17.9,
      "output_rate_per_1m": 4.5,
      "rate_limit_tpm": 33000,
      "description": "Large plan with Mistral Large model",
      "is_active": true,
      "is_default": false,
      "created_at": "2025-10-13T17:38:39.399787Z",
      "updated_at": "2025-10-13T17:38:39.399787Z",
      "created_by": null,
      "updated_by": null
    }
  ],
  "total_count": 15,
  "active_count": 15
}
```

#### Get Specific Tier

```http
GET /api/v1/admin/pricing/tiers/{tier_id}
```

#### Create Pricing Tier

```http
POST /api/v1/admin/pricing/tiers
```

**Request Body:**
```json
{
  "tier_key": "XL|Large",
  "tier_name": "Extra Large - Mistral Large",
  "plan_size": "XL",
  "model_class": "Large",
  "input_rate_per_1m": 44.8,
  "output_rate_per_1m": 11.2,
  "rate_limit_tpm": 83000,
  "description": "Extra Large plan with Mistral Large model",
  "is_active": true,
  "is_default": false
}
```

#### Update Pricing Tier

```http
PUT /api/v1/admin/pricing/tiers/{tier_id}
```

#### Delete Pricing Tier (Soft Delete)

```http
DELETE /api/v1/admin/pricing/tiers/{tier_id}
```

#### Get Tier Audit Trail

```http
GET /api/v1/admin/pricing/tiers/{tier_id}/audit
```

**Query Parameters:**
- `skip` (integer): Offset for pagination (default: 0)
- `limit` (integer): Number of records (default: 50, max: 200)

### Model Configurations

**Base Path:** `/api/v1/admin/pricing/`
**Required Role:** `admin`

#### List Model Configurations

```http
GET /api/v1/admin/pricing/models
```

**Query Parameters:**
- `active_only` (boolean): Filter to active models (default: false)
- `skip` (integer): Offset (default: 0)
- `limit` (integer): Limit (default: 100, max: 1000)

**Response:**
```json
{
  "models": [
    {
      "id": "uuid",
      "model_id": "mistral-large",
      "model_name": "Mistral Large",
      "description": "Mistral Large model",
      "default_pricing_tier_id": "uuid",
      "supports_streaming": true,
      "max_context_tokens": 8192,
      "is_active": true,
      "created_at": "2025-10-13T17:38:39.399787Z",
      "updated_at": "2025-10-13T17:38:39.399787Z"
    }
  ],
  "total_count": 6,
  "active_count": 6
}
```

#### Get Model Configuration

```http
GET /api/v1/admin/pricing/models/{model_id}
```

#### Create Model Configuration

```http
POST /api/v1/admin/pricing/models
```

#### Update Model Configuration

```http
PUT /api/v1/admin/pricing/models/{model_id}
```

## Token Analytics Endpoints

**Base Path:** `/api/v1/analytics/tokens/`
**Required Role:** `analyst` or `admin`

### Current Rate Limits

Get real-time token rate metrics for rate limit monitoring.

```http
GET /api/v1/analytics/tokens/rate-limits/current
```

**Query Parameters:**
- `window_minutes` (integer): Time window for rate calculation (default: 1, range: 1-60)
- `model_id` (string, optional): Filter by specific model ID

**Response:**
```json
{
  "metrics": [
    {
      "model_id": "mistral-large",
      "tokens_in_per_minute": 1250.5,
      "tokens_out_per_minute": 3450.2,
      "total_tokens_per_minute": 4700.7,
      "rate_limit_tpm": 33000,
      "utilization_percentage": 14.2,
      "tier_name": "L|Large",
      "recommended_action": "OK"
    }
  ],
  "window_minutes": 1,
  "calculated_at": "2025-10-13T17:40:00Z"
}
```

**Recommended Actions:**
- `OK` - Usage below 80% of rate limit
- `THROTTLE` - Usage between 80-90% of rate limit
- `UPGRADE` - Usage above 90% of rate limit

### Token Usage Summary

Get token usage summaries aggregated by model.

```http
GET /api/v1/analytics/tokens/usage/summary
```

**Query Parameters:**
- `hours` (integer): Time window in hours (default: 24, range: 1-168)
- `model_id` (string, optional): Filter by specific model ID

**Response:**
```json
{
  "summary": [
    {
      "model_id": "mistral-large",
      "total_tokens_in": 125000,
      "total_tokens_out": 345000,
      "total_tokens": 470000,
      "total_requests": 1500,
      "avg_duration_ms": 1250.5,
      "avg_tokens_per_minute": 326.4,
      "time_window_hours": 24
    }
  ],
  "time_window_hours": 24,
  "calculated_at": "2025-10-13T17:40:00Z",
  "total_models": 1
}
```

### Pricing Tier Status

Get pricing tier utilization status across all tiers.

```http
GET /api/v1/analytics/tokens/tiers/status
```

**Response:**
```json
{
  "tier_status": [
    {
      "tier_key": "L|Large",
      "tier_name": "Large - Mistral Large",
      "plan_size": "L",
      "model_class": "Large",
      "rate_limit_tpm": 33000,
      "input_rate_per_1m": 17.9,
      "output_rate_per_1m": 4.5,
      "models_using": 3,
      "total_usage_tpm": 4700.7,
      "utilization_percentage": 14.2,
      "status": "healthy",
      "recommended_action": "OK"
    }
  ],
  "calculated_at": "2025-10-13T17:40:00Z",
  "total_tiers": 15,
  "critical_tiers": 0,
  "warning_tiers": 1
}
```

**Tier Status Values:**
- `healthy` - Utilization < 80%
- `warning` - Utilization 80-90%
- `critical` - Utilization > 90%
- `unused` - No models using this tier

## LLMaaS Pricing Tiers

### Tier Structure

All tiers follow the pattern: `{PLAN_SIZE}|{MODEL_CLASS}`

**Plan Sizes:** XS, S, M, L, XL
**Model Classes:** Large (Mistral Large), Small (Mistral Small), Codestral/Llama

### Complete Tier List

| Tier Key | Plan | Model | Input $/1M | Output $/1M | TPM Limit |
|----------|------|-------|------------|-------------|-----------|
| XS\|Large | XS | Mistral Large | 1.2 | 0.3 | 2,000 |
| XS\|Small | XS | Mistral Small | 1.6 | 0.4 | 3,000 |
| XS\|Codestral/Llama | XS | Codestral/Llama | 3.6 | 0.9 | 6,900 |
| S\|Large | S | Mistral Large | 2.4 | 0.6 | 4,000 |
| S\|Small | S | Mistral Small | 3.2 | 0.8 | 6,000 |
| S\|Codestral/Llama | S | Codestral/Llama | 7.2 | 1.8 | 13,800 |
| M\|Large | M | Mistral Large | 8.8 | 2.2 | 16,500 |
| M\|Small | M | Mistral Small | 12.8 | 3.2 | 23,600 |
| M\|Codestral/Llama | M | Codestral/Llama | 29.6 | 7.4 | 55,140 |
| L\|Large | L | Mistral Large | 17.9 | 4.5 | 33,000 |
| L\|Small | L | Mistral Small | 25.5 | 6.4 | 47,200 |
| L\|Codestral/Llama | L | Codestral/Llama | 59.6 | 14.8 | 110,280 |
| XL\|Large | XL | Mistral Large | 44.8 | 11.2 | 83,000 |
| XL\|Small | XL | Mistral Small | 64.0 | 16.0 | 118,000 |
| XL\|Codestral/Llama | XL | Codestral/Llama | 148.8 | 37.2 | 275,700 |

## Model Configurations

### Supported Models

| Model ID | Default Tier | Description | Max Context |
|----------|--------------|-------------|-------------|
| foundation-sec | M\|Large | Foundation security model | 8,192 |
| phi-4-mini | M\|Large | Microsoft Phi-4 Mini | 4,096 |
| mistral-large | M\|Large | Mistral Large | 8,192 |
| mistral-small | M\|Small | Mistral Small | 8,192 |
| gpt-oss | M\|Large | Open source GPT variant | 4,096 |
| llama-3.3 | M\|Codestral/Llama | Meta Llama 3.3 | 8,192 |

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Missing or invalid Authorization header"
}
```

### 403 Forbidden
```json
{
  "detail": "Insufficient permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Pricing tier not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Rate Limiting

Rate limits are enforced per pricing tier based on the TPM (Tokens Per Minute) limits defined in the tier configuration.

## Related Documentation

- [ADR-019: Offline Tokenizer Strategy](../development/adrs/ADR-019-Offline-Tokenizer-Strategy.md)
- [Pricing Management Admin Guide](../admin/PRICING_MANAGEMENT.md)
- [Air-Gapped Deployment Guide](../operations/AIR_GAPPED_DEPLOYMENT.md)
- [Session Log: Implementation Details](../development/sessions/2025-10-13-pricing-management-implementation.md)

## Support

For issues or questions, refer to the troubleshooting section in the admin guide or contact the development team.
