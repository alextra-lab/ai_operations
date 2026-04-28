# LMStudio Setup for Load Testing

Guide for configuring LMStudio as the local inference provider for Gateway load testing.

---

## System Requirements

- **Hardware:** MacBook Pro M4 (128GB RAM recommended)
- **OS:** macOS 14+ (Sonoma or later)
- **LMStudio:** Version 0.2.0+
- **Models:** 3B-13B parameter models (fits in RAM)

---

## Installation

### 1. Install LMStudio

```bash
# Download from: https://lmstudio.ai/
# Or via Homebrew
brew install --cask lmstudio
```

### 2. Download Models

Recommended models for load testing:

| Model | Size | Speed | Quality | RAM |
|-------|------|-------|---------|-----|
| **Llama 3.2 3B** | 3.2B | Very Fast | Good | 8GB |
| **Mistral 7B** | 7B | Fast | Excellent | 16GB |
| **Llama 3.1 8B** | 8B | Fast | Excellent | 16GB |
| **Qwen 2.5 7B** | 7B | Fast | Excellent | 16GB |

**Download via LMStudio UI:**
1. Open LMStudio
2. Go to "Discover" tab
3. Search for model (e.g., "llama-3.2-3b")
4. Download GGUF format (Q4_K_M quantization recommended)

---

## Configuration

### 1. Start LMStudio Server

1. Open LMStudio
2. Click "Local Server" tab
3. Load model: Select downloaded model
4. Configure server:
   - **Port:** 1234 (default)
   - **CORS:** Enable (allow localhost)
   - **Context Length:** 4096
   - **Temperature:** 0.7

5. Click "Start Server"

### 2. Verify Server Running

```bash
# Test health endpoint
curl http://localhost:1234/v1/models

# Expected response:
# {
#   "object": "list",
#   "data": [
#     {
#       "id": "llama-3.2-3b",
#       "object": "model",
#       "owned_by": "lmstudio"
#     }
#   ]
# }
```

### 3. Test Chat Completions

```bash
curl http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.2-3b",
    "messages": [{"role": "user", "content": "Hello!"}],
    "temperature": 0.7,
    "max_tokens": 100
  }'
```

---

## Gateway Configuration

### 1. Add LMStudio Provider

```sql
-- Connect to test database
docker exec -it postgres-test psql -U testuser -d aio-test

-- Insert LMStudio provider
INSERT INTO gateway_providers (
    id,
    provider_type,
    provider_name,
    base_url,
    api_key_encrypted,
    is_enabled,
    config_json
) VALUES (
    gen_random_uuid(),
    'openai',  -- LMStudio uses OpenAI-compatible API
    'lmstudio-local',
    'http://host.docker.internal:1234',  -- Access host from Docker
    'not-required',  -- LMStudio doesn't require API key
    true,
    '{"supports_streaming": true, "max_retries": 2}'
);
```

### 2. Add Model Configuration

```sql
-- Add LMStudio model to models table
INSERT INTO models (
    id,
    model_id,
    model_name,
    model_type,
    provider,
    context_window,
    input_cost_per_million,
    output_cost_per_million,
    supports_streaming,
    is_default
) VALUES (
    gen_random_uuid(),
    'llama-3.2-3b',
    'Llama 3.2 3B (LMStudio)',
    'llm',
    'lmstudio-local',
    4096,
    0.0,  -- Local model = no cost
    0.0,
    true,
    false
);
```

### 3. Verify Gateway Routes to LMStudio

```bash
# Get auth token
TOKEN=$(curl -s -X POST "http://localhost:8006/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" \
  -d "password=adminpassword" \
  | jq -r '.access_token')

# Test via Gateway
curl http://localhost:8007/v1/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.2-3b",
    "messages": [{"role": "user", "content": "Test message"}]
  }'
```

---

## Performance Expectations

### Local LMStudio (MacBook Pro M4, 128GB)

| Model | Tokens/sec | Latency (p50) | Latency (p95) | Memory |
|-------|------------|---------------|---------------|---------|
| **Llama 3.2 3B** | 80-120 | 300ms | 800ms | 6GB |
| **Mistral 7B** | 50-80 | 500ms | 1200ms | 12GB |
| **Llama 3.1 8B** | 40-70 | 600ms | 1500ms | 14GB |

**Load Test Expectations:**
- **RPS:** 2-5 (limited by model inference speed)
- **Concurrent:** 10-20 requests
- **p95 Latency:** 500-2000ms (model-dependent)
- **Success Rate:** >99% (if under RPS limit)

**Note:** Latency includes full model inference time, not just Gateway overhead.

---

## Troubleshooting

### LMStudio Not Responding

```bash
# Check if server is running
lsof -i :1234
# Expected: LMStudio process listening on port 1234

# Check LMStudio logs
# UI: Bottom panel "Server Logs"
```

**Solution:** Restart LMStudio server, verify port 1234 not in use.

### Gateway Can't Reach LMStudio

```bash
# From Gateway container
docker exec inference-gateway-test curl http://host.docker.internal:1234/v1/models
```

**Issue:** `host.docker.internal` not resolving
**Solution:** Use `docker.for.mac.host.internal` or host IP address

### Slow Inference Speed

**Causes:**
- Model too large for available RAM
- Other applications consuming resources
- Temperature too high (increases randomness → slower)

**Solutions:**
1. Use smaller model (3B instead of 7B)
2. Close other applications
3. Lower temperature to 0.3
4. Reduce `max_tokens` to 100

### Out of Memory

```
Error: Failed to allocate tensor
```

**Solution:**
- Use smaller model or lower quantization (Q4_K_M → Q3_K_M)
- Close other applications
- Increase macOS memory swap

---

## Load Testing with LMStudio

### Conservative Test (Recommended)

```bash
# 2 RPS for 30 seconds (60 requests total)
python tests/load/load_test.py \
  --model llama-3.2-3b \
  --rps 2 \
  --duration 30 \
  --verbose
```

### Stress Test

```bash
# 5 RPS for 60 seconds (300 requests total)
python tests/load/load_test.py \
  --model llama-3.2-3b \
  --rps 5 \
  --duration 60 \
  --max-concurrent 20 \
  --output results/lmstudio_stress.json
```

### Baseline Comparison

```bash
# Test 1: Direct LMStudio (bypass Gateway)
curl http://localhost:1234/v1/chat/completions [...]
# Measure latency

# Test 2: Via Gateway
python tests/load/load_test.py --rps 1 --duration 10
# Compare Gateway latency vs direct latency
# Expected overhead: <10ms
```

---

## Migrating to Remote Provider

When switching from LMStudio to remote provider:

### 1. Update Provider Configuration

```sql
-- Disable LMStudio provider
UPDATE gateway_providers
SET is_enabled = false
WHERE provider_name = 'lmstudio-local';

-- Enable remote provider (OpenAI/Mistral)
UPDATE gateway_providers
SET is_enabled = true
WHERE provider_name = 'openai-production';
```

### 2. Update Load Test Expectations

```bash
# Remote provider: Higher RPS, lower latency per request
python tests/load/load_test.py \
  --model gpt-4o-mini \
  --rps 8.33 \          # 500 req/min (vs 2-5 for local)
  --duration 60 \
  --max-concurrent 100   # Higher concurrency (network I/O bound)
```

### 3. Compare Performance

| Metric | LMStudio (Local) | Remote Provider |
|--------|------------------|-----------------|
| **Latency (p95)** | 500-2000ms | 200-800ms |
| **Max RPS** | 2-5 | 50-100 |
| **Bottleneck** | CPU/GPU inference | Network/rate limits |
| **Cost** | $0 | $0.15-$0.60 per 1M tokens |

---

## References

- [LMStudio Documentation](https://lmstudio.ai/docs)
- [OpenAI-Compatible API Spec](https://platform.openai.com/docs/api-reference)
- [Gateway Provider Configuration](../../docs/api/admin/provider-management.md)

---

**Status:** Ready for local LMStudio testing
**Last Updated:** November 6, 2025
