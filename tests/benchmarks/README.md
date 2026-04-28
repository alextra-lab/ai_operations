# Performance Benchmarks (P5-A21)

Performance benchmarks for validating async database migration (ADR-022).

## Overview

These benchmarks validate that the async database migration (P5-A17 through P5-A20) did not introduce performance regressions and that the async patterns are performing as expected.

## What Gets Benchmarked

### Direct Database Operations

- **Simple Query**: Basic SELECT with LIMIT
- **Count Query**: COUNT aggregation
- **Filtered Query**: SELECT with WHERE clause
- **Join Query**: SELECT with JOIN
- **Transaction**: Read + Write transaction

### API Endpoints (End-to-End)

- **GET /api/v1/use-cases/available**: Use case listing with RBAC
- **GET /api/v1/tools/available**: Tool listing with permissions
- **GET /api/v1/query-history**: Query history with filters

## Usage

### Basic Run

```bash
# Run all benchmarks with default settings (50 iterations, 10 concurrent)
python tests/benchmarks/benchmark_async_db.py
```

### Custom Configuration

```bash
# Run with more iterations and higher concurrency
python tests/benchmarks/benchmark_async_db.py \
  --iterations 100 \
  --concurrency 20

# Skip API benchmarks (database only)
python tests/benchmarks/benchmark_async_db.py --skip-api

# Skip database benchmarks (API only)
python tests/benchmarks/benchmark_async_db.py --skip-db

# Custom output file
python tests/benchmarks/benchmark_async_db.py \
  --output results/my_benchmark.json
```

### Environment Setup

```bash
# Load test environment
source <(grep -Ev '^(#|$)' config/env/env.test | sed 's/^/export /')

# Verify database connection (from host, use localhost:5433)
# The script uses database config from environment variables
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5433

# Set credentials (if different from defaults)
export TEST_USERNAME=admin
export TEST_PASSWORD=adminpassword

# Run benchmarks
python tests/benchmarks/benchmark_async_db.py
```

**Note:** When running from the host machine (not inside Docker), ensure:

- Database host is `localhost` (not `postgres-test`)
- Database port is `5433` (mapped from container's 5432)
- All services are running: `docker-compose -f deploy/docker-compose.test.yml ps`

## Output

### Console Output

The script prints detailed statistics for each benchmark:

```
============================================================
Benchmark: simple_query
============================================================
Total Operations:     50
Successful:           50
Failed:               0
Success Rate:         100.00%

Latency Statistics (ms):
  Min:                2.45
  Max:                15.32
  Mean:               5.67
  Median:             5.12
  Std Dev:            2.34

Percentiles (ms):
  p50:                5.12
  p95:                12.45
  p99:                14.89

Throughput:
  Operations/sec:     8.82
  Total Duration:     5.67s
============================================================
```

### JSON Output

Results are saved to `tests/benchmarks/results/benchmark_YYYYMMDD_HHMMSS.json`:

```json
{
  "timestamp": "2025-12-01 14:30:00",
  "config": {
    "iterations": 50,
    "concurrency": 10,
    "orchestrator_url": "http://localhost:8006"
  },
  "results": {
    "database": {
      "simple_query": {
        "operation_name": "simple_query",
        "total_operations": 50,
        "successful_operations": 50,
        "success_rate": 100.0,
        "latency_ms": {
          "p50": 5.12,
          "p95": 12.45,
          "p99": 14.89
        },
        "throughput": {
          "operations_per_second": 8.82
        }
      }
    },
    "api": {
      "get_use_cases": {
        ...
      }
    }
  }
}
```

## Performance Targets

Based on ADR-022 and database index strategy:

| Operation | Target p95 Latency | Notes |
|-----------|-------------------|-------|
| Simple Query | < 10ms | Primary key lookup |
| Count Query | < 50ms | Aggregation |
| Filtered Query | < 20ms | Indexed WHERE clause |
| Join Query | < 30ms | Foreign key indexes |
| Transaction | < 50ms | Read + Write |
| API: Use Cases | < 200ms | Includes RBAC checks |
| API: Tools | < 200ms | Includes permission checks |
| API: Query History | < 300ms | Includes filters |

## Interpreting Results

### Success Criteria

- ✅ **Success Rate**: Should be 100% (no failures)
- ✅ **p95 Latency**: Should meet or exceed targets above
- ✅ **Throughput**: Should scale with concurrency
- ✅ **No Regressions**: Compare to baseline (if available)

### Red Flags

- ❌ **High Failure Rate**: Check database connectivity, connection pool
- ❌ **High p95 Latency**: Check for missing indexes, connection pool exhaustion
- ❌ **Low Throughput**: Check concurrency limits, connection pool size
- ❌ **High Std Dev**: Check for connection pool contention

## Baseline Establishment

This is the **initial baseline** after async migration (P5-A20 complete).

Future benchmarks should:

1. Compare against this baseline
2. Track performance trends over time
3. Alert on regressions (>20% latency increase)

## Connection Pool Monitoring

The benchmarks test connection pool utilization under load. Monitor:

- **Pool Size**: Default 10 (configurable via `DB_POOL_SIZE`)
- **Max Overflow**: Default 20 (configurable via `DB_MAX_OVERFLOW`)
- **Pool Exhaustion**: Should not occur with default settings

## Troubleshooting

### Database Connection Errors

```bash
# Check database is running
docker exec postgres-test psql -U testuser -d aio-test -c "SELECT 1;"

# Check connection pool settings
grep DB_POOL config/env/env.test
```

### API Authentication Errors

```bash
# Test token generation
curl -X POST "http://localhost:8006/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" -d "password=adminpassword"
```

### High Latency

1. Check database indexes: `ops/database/INDEXES.md`
2. Check connection pool size
3. Check for database locks: `SELECT * FROM pg_locks;`
4. Check query plans: `EXPLAIN ANALYZE ...`

## Related Documentation

- [ADR-022: Backend Async Database Migration](../docs/development/adrs/ADR-022-Backend-Async-Database-Migration.md)
- [Database Index Strategy](../../docs/architecture/database/INDEXES.md)
- [Phase 5 Infrastructure Overhaul](../../docs/development/plans/active/PHASE_05_INFRASTRUCTURE_OVERHAUL.md)

## Task Status

**P5-A21**: Performance Benchmarks

- ✅ Benchmark infrastructure created
- ✅ Direct database benchmarks implemented
- ✅ API endpoint benchmarks implemented
- ✅ Results formatting and JSON output
- 📋 Baseline results collection (run after setup)
