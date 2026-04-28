# Load Testing - Inference Gateway

Load tests for validating Inference Gateway performance at department scale (100-500 req/min).

## Overview

- **Target:** Inference Gateway service
- **Scale:** Department (10-100 users, 100-500 req/min)
- **Modes:** Direct Gateway access or via Orchestrator proxy
- **Test Environment:**
  - **Current:** MacBook Pro M4 (128GB) + LMStudio (local inference)
  - **Future:** Remote inference server (production-like latency)

## Quick Start

```bash
# Default test (local LMStudio: 2 RPS for 60 seconds)
python tests/load/load_test.py

# Baseline test (1 RPS for 30 seconds)
python tests/load/load_test.py --rps 1 --duration 30 --verbose

# Stress test (5 RPS for 30 seconds)
python tests/load/load_test.py --rps 5 --duration 30

# Save results to JSON
python tests/load/load_test.py --output tests/load/results/lmstudio_test.json

# Test both modes (direct + proxy) - requires orchestrator proxy
python tests/load/load_test.py --mode both --duration 30
```

## Test Modes

### Direct Mode (Default)

Tests the Gateway directly at `http://localhost:8007`.

```bash
python tests/load/load_test.py --mode direct
```

### Proxy Mode

Tests via Orchestrator API at `http://localhost:8006` (requires P3-T5 migration).

```bash
python tests/load/load_test.py --mode proxy
```

### Both Modes

Runs tests in both direct and proxy modes sequentially.

```bash
python tests/load/load_test.py --mode both
```

## Prerequisites

### 1. Services Running

```bash
# Start test environment
cd deploy
docker-compose -f docker-compose.test.yml up -d

# Verify services healthy
docker-compose -f docker-compose.test.yml ps
```

Required containers:

- `postgres-test` (healthy)
- `redis-test` (healthy)
- `inference-gateway-test` (healthy)
- `orchestrator-api-test` (healthy, for proxy mode)

### 2. Inference Provider

#### Option A: Local LMStudio (Current)

1. Start LMStudio on MacBook Pro M4
2. Load a model (e.g., Llama 3.2 3B, Mistral 7B)
3. Enable local server on `http://localhost:1234`
4. Configure Gateway provider to point to LMStudio

**LMStudio Configuration:**

- Model: `llama-3.2-3b` or `mistral-7b`
- Context: 4096 tokens
- Temperature: 0.7
- Port: 1234 (default)

#### Option B: Remote Provider (Future)

1. Configure Gateway with remote OpenAI/Mistral API
2. Set API keys in provider configuration
3. Verify provider health via Gateway admin

### 3. Environment Variables

The test uses JWT configuration from environment:

```bash
export JWT_SECRET="your_secret_key_minimum_32_chars_long"
export JWT_ALGORITHM="HS256"
export JWT_ISSUER="ai-operations-platform"
```

Or source from config:

```bash
source <(grep -Ev '^(#|$)' config/env/env.test | sed 's/^/export /')
```

### 4. Python Dependencies

```bash
# Install required packages
pip install httpx pytest pytest-asyncio
```

## Usage Examples

### Basic Load Test

```bash
# Test at 500 req/min (8.33 RPS) for 60 seconds
python tests/load/load_test.py --rps 8.33 --duration 60
```

### Under Rate Limit Test

```bash
# Test at 400 req/min (should have 100% success rate)
python tests/load/load_test.py --rps 6.67 --duration 60
```

### Over Rate Limit Test

```bash
# Test at 600 req/min (should trigger rate limiting)
python tests/load/load_test.py --rps 10 --duration 60
```

### Quick Smoke Test

```bash
# 10-second test with verbose output
python tests/load/load_test.py --rps 5 --duration 10 --verbose
```

### Custom Model Test

```bash
# Test with different model
python tests/load/load_test.py --model gpt-4o --rps 5 --duration 30

# Test with LMStudio local model
python tests/load/load_test.py --model llama-3.2-3b --rps 2 --duration 30
```

## Acceptance Criteria

The test validates against these criteria:

### Local LMStudio (Current)

1. **Latency:** p95 < 500ms (local inference overhead)
2. **Rate Limiting:** Triggers at 500 req/min threshold
3. **Reliability:** >99% success rate when under limit
4. **Stability:** Gateway + LMStudio remain healthy

### Remote Provider (Future)

1. **Latency:** p95 < 100ms added overhead (Gateway routing only)
2. **Rate Limiting:** Triggers at 500 req/min threshold
3. **Reliability:** >99% success rate when under limit
4. **Stability:** Gateway remains healthy (CPU <80%, memory stable)

**Note:** Latency expectations differ significantly:

- **Local LMStudio:** 100-2000ms (model inference time)
- **Remote OpenAI:** 200-1000ms (network + API latency)
- **Gateway Overhead:** <10ms (routing/logging only)

## Output

### Console Output

```
================================================================================
INFERENCE GATEWAY LOAD TEST
================================================================================
Mode:             DIRECT
Gateway URL:      http://localhost:8007
Target RPS:       8.33 (500 req/min)
Duration:         60 seconds
Model:            gpt-4o-mini
Max Concurrent:   100
Timeout:          30s
================================================================================

Starting load test at 2025-11-06 14:30:00...

================================================================================
RESULTS - DIRECT MODE
================================================================================
Duration:          60.1s
Target RPS:        8.33 (500 req/min)
Actual RPS:        8.31 (498 req/min)

Requests:
  Total:           499
  Successful:      495
  Failed:          0
  Rate Limited:    4
  Success Rate:    99.20%

Latency (ms):
  Min:             45
  Max:             210
  Mean:            67.3
  Median:          65
  p50:             65
  p95:             95
  p99:             145
  StdDev:          18.2

✅ PASS: All acceptance criteria met
```

### JSON Output

```bash
# Save to file
python tests/load/load_test.py --output tests/load/results/test1.json
```

JSON structure:

```json
{
  "timestamp": "2025-11-06T14:30:00.123456",
  "config": {
    "gateway_url": "http://localhost:8007",
    "rps": 8.33,
    "duration": 60,
    "model": "gpt-4o-mini"
  },
  "results": {
    "total_requests": 499,
    "successful_requests": 495,
    "success_rate": 99.2
  },
  "latency_ms": {
    "p50": 65,
    "p95": 95,
    "p99": 145
  }
}
```

## Troubleshooting

### Connection Refused

```
Error: Connection refused to http://localhost:8007
```

**Solution:** Ensure Gateway container is running:

```bash
docker ps | grep inference-gateway-test
curl http://localhost:8007/health
```

### Authentication Errors

```
Error: 401 Unauthorized
```

**Solution:** Check JWT configuration:

```bash
echo $JWT_SECRET
# Should be at least 32 characters
```

### Rate Limiting Not Triggering

```
⚠️  WARNING: No rate limiting detected at 500 req/min threshold
```

**Solution:** Verify rate limits configured in database:

```bash
docker exec postgres-test psql -U testuser -d aio-test \
  -c "SELECT * FROM gateway_rate_limits;"
```

### High Latency

```
❌ FAIL: p95 latency 350ms > 100ms threshold
```

**Solution:**

1. Check Gateway container resources
2. Verify Redis connection
3. Check for provider API delays
4. Review concurrent request settings

## Architecture

### Load Test Flow

```
Load Test Script
    ↓
[Direct Mode] → http://localhost:8007/v1/chat/completions → Gateway → Provider
    ↓
[Proxy Mode] → http://localhost:8006/... → Orchestrator → Gateway → Provider
```

### Components

- **load_test.py:** Main load testing script
- **utils.py:** Helper functions (tokens, stats, formatting)
- **results/:** JSON output directory

## Development

### Adding New Test Scenarios

1. Copy `load_test.py` to `scenario_name_test.py`
2. Modify request payload and assertions
3. Update README with new scenario

### Modifying Request Patterns

Edit the `send_request()` function in `load_test.py`:

```python
payload = {
    "model": model,
    "messages": [...],  # Customize prompt
    "max_tokens": 150,
    "temperature": 0.3,
}
```

## Related Documentation

- [Inference Gateway Implementation Plan](../../docs/development/plans/INFERENCE_GATEWAY_IMPLEMENTATION_PLAN.md)
- [ADR-053: Rate Limiting and Usage Tracking](../../docs/development/adrs/ADR-053-Rate-Limiting-and-Usage-Tracking.md)
- [Integration Tests](../README.md)

## Status

- ✅ P3-T4: Load Testing (this document)
- ⏸️ P3-T5: Migration Guide (pending)
- ⏸️ P3-T6: Deployment Validation (pending)
