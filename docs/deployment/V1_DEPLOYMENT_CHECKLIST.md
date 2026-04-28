# AI Operations Platform v1.0 Deployment Checklist

**Version:** 1.0
**Date:** November 1, 2025
**Target Environment:** Development → Staging → Production
**Architecture:** Stateless Core v1

---

## Pre-Deployment Verification

### 1. Code Readiness

- [ ] All P4-F8 through P4-F12 tasks completed
- [ ] All integration tests passing
- [ ] Frontend builds cleanly (0 errors, 0 warnings)
- [ ] Backend linting clean (ruff, mypy)
- [ ] No TODO/FIXME comments in production code
- [ ] All ADRs (030-034, 036) reviewed and approved

### 2. Database Readiness

- [ ] Migrations 001-025 applied successfully
- [ ] Run manifests table exists (`run_manifests`)
- [ ] Test suites table exists (`test_suites`, `test_questions`)
- [ ] Collections support ephemeral mode (`is_ephemeral`, `ttl_days`, `expires_at`)
- [ ] RLS policies applied and tested
- [ ] Database backup created

**Verification Command:**
```bash
psql-17 -U postgres -d aio -c "\dt" | grep -E "run_manifests|test_suites|collections"
```

### 3. Environment Configuration

- [ ] `config/env/.env` file created from `config/env/env.template`
- [ ] All required environment variables set
- [ ] JWT_SECRET set to secure random value (≥32 chars)
- [ ] OpenAI API key configured (or local LLM endpoint)
- [ ] Database credentials configured
- [ ] Feature flags verified

**Critical Environment Variables:**
```bash
# Stateless Core v1 Configuration
STATEFUL_ENABLED=false
HISTORY_PROVIDER=none
EVIDENCE_SINK=none
CRYPTO_PROVIDER=none
EDITION=core

# Run Manifest Configuration
RUN_MANIFEST_ENABLED=true
RUN_MANIFEST_FAIL_OPEN=true

# Chunking Configuration
ENABLE_EXPERT_CHUNKING=false

# Database
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/aio
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=aio
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<secure_password>

# Security
JWT_SECRET=<generate_with: openssl rand -hex 32>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# LLM Configuration
OPENAI_API_KEY=<your_key_or_local_endpoint>
DEFAULT_MODEL=gpt-4

# Services
EMBEDDING_SERVICE_URL=http://embedding-service:8002
RETRIEVAL_SERVICE_URL=http://retrieval-service:8003
LLM_GUARD_URL=http://llm-guard:8004
```

### 4. Docker Images

- [ ] All images built successfully
- [ ] Image security scans passed
- [ ] No critical vulnerabilities
- [ ] Image tags properly versioned

**Build Commands:**
```bash
# PROJECT_ROOT = path to the repository root (e.g. where this repo is cloned)
cd $PROJECT_ROOT
docker-compose -f deploy/docker-compose.yml build --no-cache
```

---

## Deployment Steps

### Step 1: Database Setup (15 min)

```bash
# 1. Create database
psql-17 -U postgres -c "CREATE DATABASE aio;"

# 2. Init schema and apply migrations/seed (SQL in ops/database/)
# See ops/database/README.md for full steps; example:
export $(grep -v '^#' config/env/.env | xargs)
PGPASSWORD=$POSTGRES_PASSWORD psql-17 -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -f ops/database/init/000_complete_init.sql
for f in ops/database/seed/*.sql; do PGPASSWORD=$POSTGRES_PASSWORD psql-17 -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -f "$f"; done

# 3. Verify schema
psql-17 -U postgres -d aio -c "\dt"

# 4. Verify RLS policies
psql-17 -U postgres -d aio -c "SELECT tablename, policyname FROM pg_policies;"
```

**Expected Output:**
- 25+ tables created
- 15+ RLS policies active
- 6 system roles created (admin, corpus_admin, use_case_publisher, conversations_privileged, user, service)
- 5+ LLM models in models table
- 5+ embedding models in models table

### Step 2: Start Services (10 min)

```bash
# 1. Start infrastructure services
docker-compose -f deploy/docker-compose.yml up -d postgres qdrant

# 2. Wait for services to be ready
sleep 10

# 3. Start application services
docker-compose -f deploy/docker-compose.yml up -d

# 4. Verify all services running
docker-compose -f deploy/docker-compose.yml ps
```

**Expected Services:**
- postgres (port 5432)
- qdrant (port 6333)
- backend (port 8006)
- retrieval (port 8003)
- embedding (port 8002)
- llm-guard (port 8004)
- ui-webapp (port 4200)

### Step 3: Smoke Tests (10 min)

```bash
# 1. Check health endpoints
curl http://localhost:8006/health
curl http://localhost:8003/health
curl http://localhost:8002/health

# 2. Test authentication
TOKEN=$(curl -s -X POST "http://localhost:8006/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" \
  -d "password=adminpassword" | jq -r '.access_token')

echo "Token: $TOKEN"

# 3. Test capabilities endpoint
curl -s http://localhost:8006/api/system/capabilities \
  -H "Authorization: Bearer $TOKEN" | jq .

# 4. Verify stateless configuration
# Should show: stateless=true, history=edge_only, evidence=none

# 5. Test chunking strategies
curl -s http://localhost:8003/api/v1/corpus/chunking/strategies \
  -H "Authorization: Bearer $TOKEN" | jq .

# 6. Test frontend
curl -I http://localhost:4200
```

### Step 4: Functional Tests (20 min)

```bash
# Run integration test suite
python ops/testing/run_all_tests.py --component integration

# Expected: All integration tests pass
```

---

## Post-Deployment Verification

### 1. Verify Core Features

- [ ] **Authentication** - Admin login works
- [ ] **Use Case Execution** - Can execute a use case
- [ ] **Document Upload** - Can upload and process a document
- [ ] **Semantic Search** - Returns relevant results
- [ ] **RAG Q&A** - Generates answers with sources
- [ ] **Export** - Can export conversation as MD/JSON
- [ ] **Capabilities** - Returns correct stateless config

### 2. Verify Stateless Architecture (ADR-030)

- [ ] No conversation transcripts in database
  ```sql
  SELECT COUNT(*) FROM conversations;  -- Should be 0 or only metadata
  ```

- [ ] Run manifests being created
  ```sql
  SELECT COUNT(*) FROM run_manifests;  -- Should increase with each execution
  ```

- [ ] Session tracking uses IndexedDB (check browser DevTools)

### 3. Verify Run Manifest Telemetry

- [ ] Run manifests capture all required fields
  ```sql
  SELECT run_id, use_case_id, schema_valid, conformance, latency_total_ms, result_kind
  FROM run_manifests
  ORDER BY ts_utc DESC
  LIMIT 5;
  ```

- [ ] Schema Validity Rate ≥ 99.5%
- [ ] Average conformance ≥ 0.98
- [ ] p95 latency ≤ 2500ms

### 4. Verify Export Functionality

- [ ] Markdown export includes all messages
- [ ] JSON export is valid JSON
- [ ] Summary generation works
- [ ] PII redaction works (if enabled)
- [ ] No server-side storage of exports

### 5. Verify Provider Configuration

```bash
# Check capabilities
curl -s http://localhost:8006/api/system/capabilities \
  -H "Authorization: Bearer $TOKEN" | jq '.providers'

# Expected:
# {
#   "history": "edge_only",
#   "evidence": "none",
#   "crypto": "none"
# }
```

---

## Performance Baselines

### Expected Performance (Stateless Core v1)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Authentication | < 200ms | `curl -w "%{time_total}\n"` |
| Use case execution (no RAG) | < 2s | Check `latency_total_ms` in run manifest |
| Use case execution (with RAG) | < 5s | Check `latency_total_ms` in run manifest |
| Semantic search | < 1s | Check response time |
| Document upload | < 3s | For < 1MB files |
| Frontend initial load | < 2s | Lighthouse test |
| API p95 latency | < 2.5s | From run manifests aggregate |

### Collect Baseline Metrics

```bash
# Run 10 use case executions
for i in {1..10}; do
  curl -s -X POST http://localhost:8006/api/v1/orchestrator/execute \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "use_case_id": "threat-triage-v1",
      "prompt": "Test execution '$i'"
    }'
  sleep 2
done

# Query aggregate metrics
curl -s "http://localhost:8006/api/v1/run-manifests/metrics/aggregate?use_case_id=threat-triage-v1" \
  -H "Authorization: Bearer $TOKEN" | jq '.metrics'
```

---

## Rollback Procedures (Development Only)

### If Services Don't Start

```bash
# 1. Check logs
docker-compose -f deploy/docker-compose.yml logs backend
docker-compose -f deploy/docker-compose.yml logs retrieval

# 2. Rebuild images
docker-compose -f deploy/docker-compose.yml build --no-cache

# 3. Reset database if corrupted
docker-compose -f deploy/docker-compose.yml down -v
# Re-run Step 1: Database Setup
```

### If Tests Fail

```bash
# 1. Check test logs
python ops/testing/run_all_tests.py --verbose

# 2. Run specific failing test
pytest tests/integration/test_export_workflow.py -v

# 3. Check environment variables
python ops/testing/load_test_env.py

# 4. Reset test database
python ops/testing/manage_test_database.py reset
```

### If Frontend Doesn't Build

```bash
cd src/frontend-angular

# 1. Clean build
rm -rf dist node_modules
npm install
ng build

# 2. Check for errors
ng build --configuration production

# 3. Verify assets
ls -la dist/browser/
```

---

## Monitoring Setup

### 1. Health Checks

Add to your monitoring system:

```yaml
services:
  - name: backend
    url: http://localhost:8006/health
    interval: 30s
    timeout: 5s

  - name: retrieval
    url: http://localhost:8003/health
    interval: 30s
    timeout: 5s

  - name: frontend
    url: http://localhost:4200
    interval: 60s
    timeout: 10s
```

### 2. Run Manifest Alerts

```sql
-- Daily quality check (run as cron job)
SELECT
  DATE(ts_utc) as date,
  COUNT(*) as total_runs,
  AVG(CASE WHEN schema_valid THEN 1.0 ELSE 0.0 END) as svr,
  AVG(conformance) as avg_conformance,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_total_ms) as p95_latency
FROM run_manifests
WHERE ts_utc >= NOW() - INTERVAL '24 hours'
GROUP BY DATE(ts_utc);
```

Alert if:
- SVR < 0.995
- avg_conformance < 0.98
- p95_latency > 2500ms

### 3. Log Aggregation

```bash
# Export logs for analysis
docker-compose -f deploy/docker-compose.yml logs --since 24h > logs/deployment_$(date +%Y%m%d).log
```

---

## Success Criteria

### Deployment is successful if:

✅ **All services healthy** - Health endpoints return 200
✅ **Authentication works** - Can obtain JWT token
✅ **Stateless mode verified** - Capabilities show stateless=true
✅ **Use case execution works** - Can execute at least one use case
✅ **Run manifests created** - Telemetry captured
✅ **Export works** - Can export conversation as MD/JSON
✅ **No errors in logs** - Clean startup
✅ **Quality metrics met** - SVR ≥ 99.5%, conformance ≥ 0.98

---

## Common Issues & Solutions

### Issue: Database Connection Failed

**Symptoms:** Backend logs show "could not connect to server"

**Solution:**
```bash
# Check postgres is running
docker ps | grep postgres

# Check connection
psql-17 -U postgres -h localhost -p 5432 -c "SELECT 1;"

# Verify DATABASE_URL in .env matches postgres config
```

### Issue: Frontend 401 Unauthorized

**Symptoms:** UI shows "Unauthorized" on every request

**Solution:**
```bash
# Verify JWT_SECRET matches between backend and frontend proxy
grep JWT_SECRET config/env/.env

# Check token is being sent
# Open browser DevTools → Network → Check Authorization header
```

### Issue: Qdrant Connection Failed

**Symptoms:** Document upload fails, embedding errors

**Solution:**
```bash
# Check qdrant is running
curl http://localhost:6333/collections

# Verify collection exists
curl http://localhost:6333/collections/documents
```

### Issue: Run Manifests Not Being Created

**Symptoms:** `SELECT COUNT(*) FROM run_manifests;` returns 0 after executions

**Solution:**
```bash
# Check feature flag
grep RUN_MANIFEST_ENABLED config/env/.env

# Should be: RUN_MANIFEST_ENABLED=true

# Check backend logs for manifest write errors
docker-compose logs backend | grep "run_manifest"
```

---

## Air-Gapped Deployment Notes

### Pre-Stage Requirements

1. **Python Wheelhouse** (all dependencies pre-downloaded)
   ```bash
   python ops/bootstrap/build_wheelhouse.sh
   # Creates wheelhouse/ with all Python packages
   ```

2. **Embedding Models** (downloaded locally)
   ```bash
   python ops/bootstrap/download_embedding_models.py
   # Downloads models to data/models/
   ```

3. **LLM Guard Models** (downloaded locally)
   ```bash
   python ops/bootstrap/download_llm_guard_models.py
   # Downloads to data/llm-guard-models/
   ```

4. **Docker Images** (exported as .tar files)
   ```bash
   bash ops/ci/build_images.sh
   docker save aio/backend:latest > backend.tar
   docker save aio/frontend:latest > frontend.tar
   # ... repeat for all services
   ```

5. **Frontend node_modules** (bundled)
   ```bash
   cd src/frontend-angular
   npm ci --production
   tar czf ../../node_modules.tar.gz node_modules/
   ```

### Air-Gapped Deployment Process

```bash
# 1. Transfer files to air-gapped environment
# - Docker images (*.tar)
# - Wheelhouse directory
# - Model files
# - node_modules.tar.gz

# 2. Load Docker images
for img in *.tar; do docker load < $img; done

# 3. Install Python dependencies from wheelhouse
pip install --no-index --find-links=wheelhouse/ -r requirements-all.txt

# 4. Deploy normally
docker-compose -f deploy/docker-compose.yml up -d
```

---

## Post-Deployment Tasks

### 1. Create Admin User

Admin and other default users are created by `ops/database/seed/001_seed_users.sql`. Change default passwords in production (see seed file comments).

### 2. Upload Initial Corpus

```bash
# Example: Upload security frameworks
python ops/cli/bulk_upload_documents.py \
  --directory corpus_docs/ \
  --collection-name "Security Frameworks" \
  --embedding-model all-MiniLM-L6-v2
```

### 3. Publish Use Cases

```bash
# Publish draft use cases to make them available
# Via UI: Use Case Management → Select draft → Publish
# Or via API:
curl -X PATCH http://localhost:8006/api/v1/use-cases/{id} \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"lifecycle_state": "published"}'
```

### 4. Configure System Settings

Via Admin UI (`/admin/system-config`):
- Set max_output_tokens
- Configure session TTL
- Set rate limits
- Configure password policy

### 5. Baseline Metrics Collection

```bash
# Let system run for 24 hours, then collect baseline
psql-17 -U postgres -d aio -c "
SELECT
  'Baseline Metrics' as label,
  COUNT(*) as total_runs,
  AVG(CASE WHEN schema_valid THEN 1.0 ELSE 0.0 END) as svr,
  AVG(conformance) as avg_conformance,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_total_ms) as p95_latency
FROM run_manifests
WHERE ts_utc >= NOW() - INTERVAL '24 hours';
"
```

---

## Deployment Sign-Off

**Deployer:** ___________________
**Date:** ___________________
**Environment:** [ ] Dev [ ] Staging [ ] Production

**Checklist Completed:** [ ] Yes [ ] No
**All Tests Passed:** [ ] Yes [ ] No
**Baseline Metrics Collected:** [ ] Yes [ ] No
**Monitoring Configured:** [ ] Yes [ ] No

**Notes:**
```
_____________________________________________________________________________
_____________________________________________________________________________
_____________________________________________________________________________
```

---

## Related Documentation

- [Stateless Migration Guide](../development/migration/STATELESS_MIGRATION_GUIDE.md)
- [ADR-030: No Transcripts; Run Manifests Only](../development/adrs/ADR-030-No-Transcripts-Run-Manifests.md)
- [ADR-031: Client-Owned Exports](../development/adrs/ADR-031-Client-Owned-Exports.md)
- [ADR-036: Pipeline+Steps Architecture](../development/adrs/ADR-036-Orchestrator-Pipeline-Pattern.md)
- [Testing Guide](../testing/TESTING_GUIDE.md)
- [Operations Guide](../operations/OPERATIONS_GUIDE.md)

---

**Document Owner:** DevOps Team
**Last Updated:** November 1, 2025
**Version:** 1.0
