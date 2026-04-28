# Pipeline Parity Testing Guide

**Purpose:** Verify UseCaseRunner pipeline produces identical outputs to legacy Orchestrator
**Date:** October 24, 2025
**Status:** Ready for manual testing

---

## Prerequisites

✅ Container rebuilt and running: `docker ps | grep orchestrator-api-test`
✅ Backend API healthy: `curl http://localhost:8006/health`
✅ Database accessible: `psql-17 -h localhost -p 5433 -U testuser -d aio-test`

---

## Test Procedure

### **Phase 1: Test Legacy Mode (Flag OFF)**

**1. Verify flag is OFF (default):**
```bash
docker exec orchestrator-api-test env | grep USECASE_RUNNER_ENABLED
# Should return: USECASE_RUNNER_ENABLED=false (or not set)
```

**2. Check run_manifests table (baseline):**
```sql
psql-17 -h localhost -p 5433 -U testuser -d aio-test -c \
  "SELECT COUNT(*) as baseline_count FROM run_manifests;"
```

**3. Make test request (via OpenAPI docs):**
- Open: http://localhost:8006/docs
- Find: `/api/v1/process` endpoint
- Click: "Try it out"
- Input:
  ```json
  {
    "query": "What is a CVE?",
    "request_type": "QUERY",
    "stream": false
  }
  ```
- Click: "Execute"
- Save response to `temp_ops/legacy_response.json`

**4. Check logs:**
```bash
docker logs orchestrator-api-test --tail 20 | grep "pipeline_mode"
# Should show: "pipeline_mode": "legacy"
```

**5. Verify NO run_manifests created (legacy doesn't use telemetry):**
```sql
psql-17 -h localhost -p 5433 -U testuser -d aio-test -c \
  "SELECT COUNT(*) as after_legacy FROM run_manifests;"
# Count should be same as baseline (legacy doesn't create manifests)
```

---

### **Phase 2: Test Pipeline Mode (Flag ON)**

**1. Enable the flag:**
```bash
# Edit config/env/env.test
# Change: USECASE_RUNNER_ENABLED=false
# To:     USECASE_RUNNER_ENABLED=true
```

**2. Restart container:**
```bash
cd $PROJECT_ROOT
export $(grep -v '^#' config/env/env.test | xargs)
docker-compose -f deploy/docker-compose.test.yml restart orchestrator-api-test
sleep 10  # Wait for startup
```

**3. Verify flag is ON:**
```bash
docker exec orchestrator-api-test env | grep USECASE_RUNNER_ENABLED
# Should return: USECASE_RUNNER_ENABLED=true
```

**4. Make same test request:**
- Open: http://localhost:8006/docs
- Find: `/api/v1/process` endpoint
- Use SAME inputs as Phase 1:
  ```json
  {
    "query": "What is a CVE?",
    "request_type": "QUERY",
    "stream": false
  }
  ```
- Click: "Execute"
- Save response to `temp_ops/pipeline_response.json`

**5. Check logs for pipeline mode:**
```bash
docker logs orchestrator-api-test --tail 30 | grep -E "pipeline_mode|UseCaseRunner|step.*complete"
# Should show:
# - "pipeline_mode": "runner"
# - "Starting pipeline execution"
# - "Executing step 1/6: GuardValidate"
# - "Step GuardValidate complete"
# - ... (all 6 steps)
# - "Pipeline execution complete"
```

**6. Verify run_manifests created (pipeline uses telemetry):**
```sql
psql-17 -h localhost -p 5433 -U testuser -d aio-test -c \
  "SELECT request_id, result_kind, created_at, manifest_data->>'use_case_id' as use_case
   FROM run_manifests
   ORDER BY created_at DESC
   LIMIT 3;"
# Should show new manifest entry with result_kind='SUCCESS'
```

---

### **Phase 3: Compare Outputs**

**1. Compare response structure:**
```bash
cd temp_scripts
# Extract just the response fields
jq '.response' legacy_response.json > legacy_text.txt
jq '.response' pipeline_response.json > pipeline_text.txt

# Compare
diff legacy_text.txt pipeline_text.txt
# Should be identical (or minimal differences)
```

**2. Compare metadata:**
```bash
jq '{confidence, sources: .sources | length, citations: .citations | length}' legacy_response.json
jq '{confidence, sources: .sources | length, citations: .citations | length}' pipeline_response.json
# Should match
```

**3. Latency comparison:**
```bash
# Extract from API response headers or logs
# Acceptable if pipeline is within 20% of legacy
```

---

## Expected Results

### ✅ **Success Criteria:**

| Metric | Legacy | Pipeline | Pass? |
|--------|--------|----------|-------|
| Response text | "CVE stands for..." | "CVE stands for..." | ✅ Identical |
| Confidence | 0.85 | 0.85 | ✅ ±0.01 |
| Sources count | 0 | 0 | ✅ Match |
| Citations count | 0 | 0 | ✅ Match |
| HTTP status | 200 | 200 | ✅ Match |
| Run manifests | 0 created | 1 created | ✅ Expected |
| Logs | "legacy mode" | "runner mode" | ✅ Expected |

### ⚠️ **Acceptable Differences:**

- Request IDs (different UUIDs)
- Timestamps (different execution times)
- Latency (within 20%)
- Log formatting (different log messages OK)

### ❌ **Failure Conditions:**

- Response text differs
- Confidence differs by >0.05
- Sources/citations counts differ
- HTTP error in pipeline mode
- Pipeline crashes or times out
- No run_manifest created in pipeline mode

---

## Troubleshooting

### **Pipeline Mode Not Activating:**

Check logs:
```bash
docker logs orchestrator-api-test --tail 50 | grep -i "pipeline\|runner\|usecase_runner"
```

Verify env var loaded:
```bash
docker exec orchestrator-api-test python -c "import os; print('USECASE_RUNNER_ENABLED=', os.getenv('USECASE_RUNNER_ENABLED'))"
```

### **Import Errors:**

Verify imports:
```bash
docker exec orchestrator-api-test python -c "from app.orchestrator.runner import UseCaseRunner; print('✅ Imports OK')"
```

### **No Run Manifests Created:**

Check telemetry:
```bash
docker logs orchestrator-api-test | grep -i "telemetry\|manifest"
```

Check database:
```sql
SELECT table_name FROM information_schema.tables WHERE table_name = 'run_manifests';
```

---

## Golden Traces (After Validation)

Once parity is confirmed, create golden trace files:

```bash
# Save validated outputs as regression baselines
cp temp_ops/legacy_response.json tests/fixtures/golden_traces/query_simple_legacy.json
cp temp_ops/pipeline_response.json tests/fixtures/golden_traces/query_simple_pipeline.json
```

These serve as regression tests for future changes.

---

## Quick Reference

**Toggle flag OFF:**
```bash
# config/env/env.test
USECASE_RUNNER_ENABLED=false
docker-compose -f deploy/docker-compose.test.yml restart orchestrator-api-test
```

**Toggle flag ON:**
```bash
# config/env/env.test
USECASE_RUNNER_ENABLED=true
docker-compose -f deploy/docker-compose.test.yml restart orchestrator-api-test
```

**Check which mode is active:**
```bash
curl -s http://localhost:8006/api/v1/process -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}' 2>&1 | head -20

# Then check logs:
docker logs orchestrator-api-test --tail 10 | grep pipeline_mode
```

---

**Status:** Ready for manual testing
**Next:** Execute Phase 1, then Phase 2, then Phase 3
