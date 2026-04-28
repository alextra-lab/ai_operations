# Hybrid Model Metadata Management Workflow

**Feature:** P2-FIX-10 Model Registry Service
**Version:** 1.0
**Date:** 2025-10-09

## Overview

The hybrid metadata system provides three ways to manage model metadata:

1. **YAML Configuration** (Git version-controlled, restart required)
2. **Admin API Updates** (Runtime updates, immediate effect)
3. **Auto-Discovery** (From inference server, with fallback)

## Metadata Priority Chain

```
┌─────────────────────────────────────────────────────────┐
│          Metadata Resolution Priority                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. Database Admin Overrides (highest priority)         │
│     └─ Set via: PATCH /api/v1/models/{id}/metadata     │
│     └─ Use for: Runtime corrections, custom configs     │
│                                                          │
│  2. YAML Configuration File                             │
│     └─ File: config/models/model_metadata.yaml          │
│     └─ Use for: Baseline metadata for all models        │
│                                                          │
│  3. Extended Metadata from Inference Server             │
│     └─ Endpoint: GET /v1/models/{model_id}              │
│     └─ Use for: Server-provided metadata (if available) │
│                                                          │
│  4. Pattern-Based Inference                             │
│     └─ Hardcoded patterns in ModelMetadataInferencer    │
│     └─ Use for: Fallback when nothing else available    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Workflow 1: Initial Setup (DevOps)

### Step 1: Create YAML Configuration

```bash
# Copy template
cd $PROJECT_ROOT
cp config/models/model_metadata.template.yaml config/models/model_metadata.yaml

# Edit with your models
nano config/models/model_metadata.yaml
```

### Step 2: Add Your Models

```yaml
models:
  your-llm-model:
    context_window: 8192
    max_output_tokens: 4096
    provider: local
    model_type: llm
    specialization: security_analysis
    description: "Your model description"
    supports_tools: true
    recommended_use_cases:
      - query
      - analysis

  your-embedding-model:
    context_window: 8192
    embedding_dimensions: 768
    provider: local
    model_type: embedding
    description: "Your embedding model"
```

### Step 3: Deploy and Sync

```bash
# Restart orchestrator to load YAML
docker-compose -f deploy/docker-compose.test.yml restart orchestrator-api

# Trigger model sync (discovers + applies YAML metadata)
TOKEN=$(curl -s -X POST "http://localhost:8006/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" -d "password=adminpassword" | jq -r '.access_token')

curl -X POST "http://localhost:8006/api/v1/models/sync" \
  -H "Authorization: Bearer $TOKEN"

# Response shows models created with YAML metadata
{
  "summary": {
    "total_discovered": 17,
    "newly_created": 17
  },
  "created_models": [...]
}
```

## Workflow 2: Runtime Updates (Admin)

### Update Model Metadata via API

```bash
# Get admin token
TOKEN=$(curl -s -X POST "http://localhost:8006/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" -d "password=adminpassword" | jq -r '.access_token')

# Update model metadata (immediate effect, no restart)
curl -X PATCH "http://localhost:8006/api/v1/models/foundation-sec-8b-mlx/metadata" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "context_window": 16384,
    "max_output_tokens": 8192,
    "description": "Updated via admin API",
    "specialization": "security_custom"
  }'

# Verify update
curl -X GET "http://localhost:8006/api/v1/models/foundation-sec-8b-mlx" \
  -H "Authorization: Bearer $TOKEN" | jq '{model_id, context_window, max_output_tokens}'
```

### Update Embedding Dimensions

```bash
# For embedding models, update vector dimensions
curl -X PATCH "http://localhost:8006/api/v1/models/text-embedding-bge-m3/metadata" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "embedding_dimensions": 1024,
    "context_window": 8192,
    "description": "BGE-M3 multilingual embedding model"
  }'
```

### Update Pricing (Per-Model Override)

```bash
# Override default pricing for specific model
curl -X PATCH "http://localhost:8006/api/v1/models/gpt-4o/metadata" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "input_price_per_million": 2.50,
    "output_price_per_million": 10.00
  }'

# Now gpt-4o uses custom pricing, others use environment default
```

## Workflow 3: Periodic Sync (Admin)

### Check Model Availability

```bash
# Run sync to check which models are still available
TOKEN=$(curl -s -X POST "http://localhost:8006/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" -d "password=adminpassword" | jq -r '.access_token')

curl -X POST "http://localhost:8006/api/v1/models/sync" \
  -H "Authorization: Bearer $TOKEN" | jq '{summary, unavailable_models}'

# Response shows:
{
  "summary": {
    "total_discovered": 15,      # 2 models removed
    "marked_unavailable": 2
  },
  "unavailable_models": [
    {"model_id": "old-model", "last_seen": "2025-10-08T..."}
  ]
}
```

## Workflow 4: Developer Usage

### List Available Models in UI

```typescript
// Developer tools query current registry
async loadModels() {
  const response = await this.modelRegistryService.listModels(
    undefined,     // all providers
    'llm',        // or 'embedding'
    true,         // available only
    false         // exclude deprecated
  );

  this.models = response.models;
  // All models have YAML metadata + admin overrides applied
}
```

### Get Model with Embedding Dimensions

```typescript
// For embedding model selection
const model = await this.modelRegistryService.getModel(
  'text-embedding-bge-m3'
);

console.log(model.embedding_dimensions);  // 1024 (from YAML)
console.log(model.context_window);        // 8192 (from YAML)
```

## Field Definitions Reference

### Required Fields (Must provide in YAML or will be inferred)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `provider` | enum | Model provider | `local`, `openai`, `anthropic`, `other` |
| `model_type` | enum | Model type | `llm`, `embedding`, `vision`, `audio` |

### Recommended Fields (Highly recommended to provide)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `context_window` | integer | Max input tokens | `8192`, `128000` |
| `max_output_tokens` | integer | Max output tokens | `4096`, `16384` |
| `description` | string | Model description | "Foundation security model..." |

### LLM-Specific Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `supports_tools` | boolean | Function calling support | `true`, `false` |
| `supports_vision` | boolean | Image input support | `true`, `false` |
| `supports_audio` | boolean | Audio input support | `true`, `false` |
| `is_reasoning_model` | boolean | Reasoning capability | `true`, `false` |
| `specialization` | string | Model specialization | `coding`, `security_analysis` |
| `recommended_use_cases` | array | Use case types | `["query", "analysis"]` |

### Embedding-Specific Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `embedding_dimensions` | integer | Vector dimensions | `384`, `768`, `1024`, `1536` |

### Optional Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `max_input_tokens` | integer | Explicit input limit | `128000` |

## Configuration Examples

### Example 1: Security-Focused LLM

```yaml
foundation-sec-8b-instruct-mlx:
  context_window: 8192
  max_output_tokens: 4096
  provider: local
  model_type: llm
  specialization: security_analysis
  description: "Foundation security model optimized for SOC analysis"
  supports_tools: false
  recommended_use_cases:
    - query
    - analysis
    - threat_intel
```

### Example 2: High-Capacity Embedding Model

```yaml
e5-mistral-7b-instruct-embedding:
  context_window: 4096
  embedding_dimensions: 4096
  provider: local
  model_type: embedding
  description: "E5 Mistral 7B instruction-tuned embedding model"
```

### Example 3: Coding-Specialized Model

```yaml
qwen/qwen3-coder-30b:
  context_window: 32768
  max_output_tokens: 8192
  provider: local
  model_type: llm
  specialization: coding
  supports_tools: true
  description: "Qwen 3 Coder 30B specialized for coding tasks"
  recommended_use_cases:
    - code_generation
    - code_analysis
```

## Troubleshooting

### Models Not Getting YAML Metadata

**Problem:** Models created before YAML exists don't have metadata

**Solution:** Delete and re-sync
```bash
# Delete auto-discovered models
docker exec -i postgres-test psql -U testuser -d aio-test \
  -c "DELETE FROM models WHERE metadata_json->>'auto_discovered' = 'true';"

# Re-sync to apply YAML metadata
curl -X POST "http://localhost:8006/api/v1/models/sync" \
  -H "Authorization: Bearer $TOKEN"
```

### YAML Changes Not Applied

**Problem:** Updated YAML but models still have old metadata

**Solution:** Restart orchestrator
```bash
docker-compose -f deploy/docker-compose.test.yml restart orchestrator-api
```

### Admin API Updates Not Persisting

**Problem:** PATCH returns 500 error

**Solution:** Check logs
```bash
docker logs orchestrator-api-test 2>&1 | grep "Error updating"
```

## Best Practices

### 1. Use YAML for Baseline Configuration
- Define all your models in YAML
- Commit to version control
- Provides documented baseline

### 2. Use Admin API for Quick Fixes
- Runtime corrections (typos, wrong values)
- Testing different configurations
- Emergency updates without restart

### 3. Re-Sync After YAML Changes
- Always run `/sync` after updating YAML
- Deletes old models to apply new metadata
- Verifies changes applied correctly

### 4. Document Admin Overrides
- When using admin API, document why
- Consider updating YAML for next deployment
- Track overrides in admin notes

## Integration with Cost Estimation

**Pricing Fallback:**
```
1. Model database field (admin API override)
   └─ input_price_per_million, output_price_per_million

2. Environment variables (default for all)
   └─ PRICING_DEFAULT_INPUT_PER_MILLION=0.0
   └─ PRICING_DEFAULT_OUTPUT_PER_MILLION=0.0

3. Hardcoded pricing (legacy fallback)
   └─ MODEL_PRICING dict in cost_estimator.py

4. Generic default ($1.00/$2.00)
```

## Production Deployment Checklist

- [ ] Create `config/models/model_metadata.yaml` from template
- [ ] Populate with your LLMaaS/LM Studio models
- [ ] Mount config directory in docker-compose.yml
- [ ] Set pricing environment variables
- [ ] Run initial sync: `POST /api/v1/models/sync`
- [ ] Verify all models have metadata: `GET /api/v1/models`
- [ ] Document any admin API overrides in runbook
- [ ] Train admins on sync and update workflows

## Summary

✅ **YAML Configuration:** 17 models defined for LM Studio
✅ **Admin API:** Runtime updates without restart
✅ **Auto-Discovery:** 17 models discovered and created
✅ **Embedding Dimensions:** Tracked for all embedding models
✅ **Pricing:** Environment-based with per-model override
✅ **Frontend:** TypeScript models 100% aligned

**The hybrid metadata system provides maximum flexibility with operational control!**
