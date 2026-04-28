# Quick Start: Load Testing with LMStudio

Your M4 MacBook Pro is ready with `llama-3.2-3b-instruct` loaded. Here's how to run the tests.

---

## Pre-Flight Check

Run this first to verify everything is ready:

```bash
cd /Users/Alex/Dev/ai_operations
bash tests/load/pre_test_checklist.sh
```

**Expected output:**

```
✅ PRE-FLIGHT CHECK PASSED
```

If it fails, follow the on-screen instructions.

---

## Recommended Test Sequence

### Test 1: Baseline (30 seconds)

Establishes your baseline performance:

```bash
python tests/load/load_test.py \
  --rps 1 \
  --duration 30 \
  --verbose
```

**Expected Results:**

- Total requests: ~30
- p50 latency: 200-400ms
- p95 latency: 300-600ms
- Success rate: 100%

**What this tells you:** Single-request latency (no queuing)

---

### Test 2: Default Load (60 seconds) **← RECOMMENDED**

This is the main test - sustainable load for your M4:

```bash
python tests/load/load_test.py
```

That's it! No arguments needed - defaults are set for your setup:

- Model: `llama-3.2-3b-instruct` ✓
- RPS: 2.0 (120 req/min)
- Duration: 60 seconds
- Max concurrent: 20

**Expected Results:**

- Total requests: ~120
- p50 latency: 250-500ms
- p95 latency: 400-800ms
- Success rate: >99%

**What this tells you:** Sustainable performance under realistic load

---

### Test 3: Stress Test (30 seconds)

Pushes the system to find the breaking point:

```bash
python tests/load/load_test.py \
  --rps 5 \
  --duration 30
```

**Expected Results:**

- Total requests: ~150
- p50 latency: 400-700ms
- p95 latency: 800-1500ms
- Success rate: 90-98% (some failures expected)

**What this tells you:** Maximum capacity before degradation

---

## Save Results for Analysis

Add `--output` to any test to save JSON results:

```bash
# Baseline
python tests/load/load_test.py \
  --rps 1 --duration 30 \
  --output tests/load/results/baseline.json

# Default load
python tests/load/load_test.py \
  --output tests/load/results/default.json

# Stress test
python tests/load/load_test.py \
  --rps 5 --duration 30 \
  --output tests/load/results/stress.json
```

Results include:

- Latency percentiles (p50, p95, p99)
- Success/failure counts
- Actual RPS achieved
- Error breakdown

---

## Understanding the Results

### Console Output Example

```
================================================================================
INFERENCE GATEWAY LOAD TEST
================================================================================
Mode:             DIRECT
Gateway URL:      http://localhost:8007
Target RPS:       2.00 (120 req/min)
Duration:         60 seconds
Model:            llama-3.2-3b-instruct
Max Concurrent:   20
Timeout:          30s
================================================================================

Starting load test at 2025-11-06 18:45:00...

================================================================================
RESULTS - DIRECT MODE
================================================================================
Duration:          60.1s
Target RPS:        2.00 (120 req/min)
Actual RPS:        2.00 (120 req/min)

Requests:
  Total:           120
  Successful:      119
  Failed:          1
  Rate Limited:    0
  Success Rate:    99.17%

Latency (ms):
  Min:             210
  Max:             650
  Mean:            320.5
  Median:          305
  p50:             305
  p95:             485
  p99:             610
  StdDev:          75.2

📊 ACCEPTANCE CRITERIA (Local LMStudio):
   Latency (p95): 485ms (threshold: <2000ms)
   ✓ Latency acceptable for local inference
   ✓ Success rate: 99.2%

✅ PASS: All acceptance criteria met
```

### What to Look For

**✅ Good Performance:**

- Success rate >99%
- p95 latency <800ms
- Actual RPS matches target RPS
- No timeouts

**⚠️ Degradation Warning:**

- Success rate 95-99%
- p95 latency 800-1500ms
- Some failed requests
- Consider lowering RPS

**❌ System Overloaded:**

- Success rate <95%
- p95 latency >1500ms
- Many timeouts or errors
- Actual RPS < target RPS

---

## Comparing Direct vs Gateway

To measure Gateway overhead, compare direct LMStudio latency:

```bash
# 1. Test direct to LMStudio (no Gateway)
curl -w "\nTime: %{time_total}s\n" \
  http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.2-3b-instruct",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100
  }'

# Note the time (e.g., "Time: 0.345s" = 345ms)

# 2. Run Gateway load test
python tests/load/load_test.py --rps 1 --duration 10

# 3. Compare p50 latency from test vs direct time
# Gateway overhead = (Gateway p50) - (Direct time)
# Expected: <10ms overhead
```

---

## Troubleshooting

### "No successful requests"

**Cause:** Gateway can't authenticate or reach LMStudio

**Fix:**

```bash
# Check Gateway health
curl http://localhost:8007/health

# Check LMStudio
curl http://localhost:1234/v1/models

# Check Gateway → LMStudio connectivity
docker exec inference-gateway-test \
  curl http://host.docker.internal:1234/v1/models
```

### "p95 latency > 2000ms"

**Cause:** Model too slow or system overloaded

**Fix:**

1. Close other applications
2. Lower RPS: `--rps 1`
3. Check LMStudio isn't using swap memory
4. Verify model is still loaded (didn't unload due to memory)

### "Rate Limited: 0" (at high RPS)

**Cause:** Rate limiting not configured

**This is OK for local testing** - rate limits are for production remote APIs

---

## Next Steps

After successful tests:

1. **Document baseline:** Save your p50/p95 latencies
2. **Test different models:** Try mistral-7b if you have it
3. **Compare environments:** When you switch to remote provider, compare latencies
4. **Monitor trends:** Run daily to catch performance regressions

---

**Ready to test!** Just run: `python tests/load/load_test.py`
