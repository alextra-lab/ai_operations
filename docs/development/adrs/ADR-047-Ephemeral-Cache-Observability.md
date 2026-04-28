# ADR-047: Ephemeral Conversation Cache with Observability

**Status:** ✅ ACCEPTED
**Date:** 2025-10-25
**Deciders:** Architecture Team, Operations Team
**Related:** ADR-030 (Stateless), ADR-034 (Conversations as QUERY Pattern)

---

## Context

We've implemented an **ephemeral, encrypted, model-aware conversation cache** to maintain context between turns in stateless conversations. This cache is critical for:

- **User Experience:** Multi-turn conversations require context
- **Performance:** Avoid re-sending full history each request
- **Security:** AES-GCM encryption protects sensitive SOC data
- **Efficiency:** Model-aware limits based on `context_window`

**Problem:** Without proper monitoring, we can't:
- Detect performance degradation
- Identify security issues (encryption failures)
- Optimize resource allocation
- Debug user-reported issues
- Plan capacity scaling

---

## Decision

Implement **comprehensive observability** for the ephemeral conversation cache with:

1. **Metrics Collection** (what to measure)
2. **Exposure Endpoints** (how to access)
3. **Logging Standards** (what to log)
4. **Alerting Thresholds** (when to alert)
5. **Performance SLIs/SLOs** (service levels)

---

## Metrics Taxonomy

### **Performance Metrics** (SLI/SLO Critical)

| Metric | Type | Description | Target SLO |
|--------|------|-------------|------------|
| `cache.get.latency_ms` | Histogram | Time to decrypt and return | p95 < 10ms |
| `cache.set.latency_ms` | Histogram | Time to encrypt and store | p95 < 15ms |
| `cache.append.latency_ms` | Histogram | Time to decrypt, append, re-encrypt | p95 < 20ms |
| `cache.hit_rate` | Gauge | % of gets that find valid entry | > 80% |
| `cache.miss_rate` | Gauge | % of gets that miss | < 20% |
| `cache.eviction_rate` | Counter | Entries evicted per minute | Baseline < 10/min |

### **Capacity Metrics** (Resource Planning)

| Metric | Type | Description | Alert Threshold |
|--------|------|-------------|-----------------|
| `cache.total_sessions` | Gauge | Current active sessions | > 8000 (80% of max) |
| `cache.total_tokens` | Gauge | Total tokens across all sessions | N/A (informational) |
| `cache.total_bytes` | Gauge | Total encrypted data size | > 100MB |
| `cache.avg_tokens_per_session` | Gauge | Average token utilization | N/A (trend) |
| `cache.avg_turns_per_session` | Gauge | Average conversation length | N/A (trend) |
| `cache.max_session_tokens` | Gauge | Largest session token count | Alert if > limit |

### **Expiration Metrics** (Lifecycle Health)

| Metric | Type | Description | Meaning |
|--------|------|-------------|---------|
| `cache.expired_absolute_ttl` | Counter | Sessions expired by absolute TTL | Expected (24h) |
| `cache.expired_idle_timeout` | Counter | Sessions expired by idle | User abandoned |
| `cache.evicted_lru` | Counter | Sessions evicted by LRU (max entries) | Capacity pressure |
| `cache.gc_cycle_duration_ms` | Histogram | Time to run garbage collection | p95 < 50ms |
| `cache.gc_entries_removed` | Counter | Entries removed per GC cycle | Baseline |

### **Security Metrics** (Encryption Health)

| Metric | Type | Description | Alert Threshold |
|--------|------|-------------|-----------------|
| `cache.encrypt_success` | Counter | Successful encryptions | N/A |
| `cache.encrypt_failure` | Counter | Encryption failures | > 0 (critical) |
| `cache.decrypt_success` | Counter | Successful decryptions | N/A |
| `cache.decrypt_failure` | Counter | Decryption failures | > 10/hour |
| `cache.key_derivation_time_ms` | Histogram | HKDF key derivation latency | p95 < 1ms |
| `cache.master_key_age_seconds` | Gauge | Time since master key generated | Process uptime |

### **Usage Metrics** (Business Intelligence)

| Metric | Type | Description | Use |
|--------|------|-------------|-----|
| `cache.sessions_created` | Counter | Total sessions created | Growth tracking |
| `cache.messages_total` | Counter | Total messages processed | Volume tracking |
| `cache.user_messages` | Counter | User messages | Engagement |
| `cache.assistant_messages` | Counter | Assistant responses | Cost tracking |
| `cache.avg_session_duration_seconds` | Histogram | Time from create to expire/delete | Session patterns |
| `cache.token_limit_exceeded_errors` | Counter | Sessions hitting token limit | Compression trigger |
| `cache.turn_limit_exceeded_errors` | Counter | Sessions hitting turn limit | Long conversations |

---

## Implementation Architecture

### **1. Metrics Collection (Prometheus Format)**

```python
# src/orchestrator/app/services/conversation_cache.py

from prometheus_client import Counter, Histogram, Gauge

class ConversationCache:
    def __init__(self, ...):
        # Performance metrics
        self._get_latency = Histogram(
            'cache_get_latency_seconds',
            'Time to retrieve and decrypt conversation'
        )
        self._set_latency = Histogram(
            'cache_set_latency_seconds',
            'Time to encrypt and store conversation'
        )
        self._hit_total = Counter('cache_hits_total', 'Cache hit count')
        self._miss_total = Counter('cache_misses_total', 'Cache miss count')

        # Capacity metrics
        self._sessions_gauge = Gauge('cache_sessions_total', 'Active sessions')
        self._tokens_gauge = Gauge('cache_tokens_total', 'Total cached tokens')

        # Security metrics
        self._encrypt_success = Counter('cache_encrypt_success_total', 'Encryption successes')
        self._encrypt_failure = Counter('cache_encrypt_failure_total', 'Encryption failures')
        self._decrypt_failure = Counter('cache_decrypt_failure_total', 'Decryption failures')

        # Usage metrics
        self._token_limit_exceeded = Counter('cache_token_limit_exceeded_total', 'Token limits hit')
        ...

    def get(self, session_id: str):
        with self._get_latency.time():
            entry = self._cache.get(session_id)
            if entry:
                self._hit_total.inc()
            else:
                self._miss_total.inc()
            ...
```

### **2. Structured Logging (JSON)**

```python
# Every cache operation logs with context

logger.info(
    "Cache operation completed",
    extra={
        "operation": "get",
        "session_id": session_id,
        "hit": True,
        "token_count": entry.token_count,
        "turn_count": entry.turn_count,
        "utilization_pct": token_percentage,
        "latency_ms": latency,
        "encryption_ok": True,
    }
)
```

### **3. Health Endpoint** (`/health/cache`)

```python
@router.get("/health/cache")
async def cache_health():
    """
    Cache health and statistics endpoint.

    Returns real-time metrics for monitoring dashboards.
    """
    cache = get_conversation_cache()
    stats = cache.get_stats()

    # Calculate health indicators
    utilization = (stats["total_sessions"] / stats["max_entries"]) * 100
    health_status = "healthy" if utilization < 80 else "warning" if utilization < 95 else "critical"

    return {
        "status": health_status,
        "stats": stats,
        "health_indicators": {
            "capacity_utilization_pct": utilization,
            "expired_sessions": stats["expired_sessions"],
            "encryption": "enabled" if stats.get("encryption") else "disabled",
        },
        "timestamp": datetime.utcnow().isoformat()
    }
```

### **4. Session Stats in Response** (Client Visibility)

```python
# In orchestrator.py after LLM call

if session_id:
    cache_stats = cache.get_session_stats(session_id)
    formatted_response.cache_stats = cache_stats

# Client receives:
{
    "response": "...",
    "cache_stats": {
        "tokens_used": 1234,
        "max_tokens": 6000,
        "token_percentage": 21,
        "turn_count": 5,
        "will_compress": false,
        "ttl_remaining_seconds": 86100
    }
}
```

---

## Monitoring Dashboards

### **Dashboard 1: Cache Performance**

```
┌─────────────────────────────────────────────┐
│ Cache Performance                           │
├─────────────────────────────────────────────┤
│ Get Latency (p50/p95/p99):  2ms / 8ms / 15ms│
│ Set Latency (p50/p95/p99):  5ms / 12ms / 25ms│
│ Hit Rate:                   87%             │
│ Miss Rate:                  13%             │
│                                             │
│ [Graph: Latency over time]                  │
│ [Graph: Hit rate over time]                 │
└─────────────────────────────────────────────┘
```

### **Dashboard 2: Capacity & Resources**

```
┌─────────────────────────────────────────────┐
│ Cache Capacity                              │
├─────────────────────────────────────────────┤
│ Active Sessions:       6,234 / 10,000 (62%) │
│ Total Tokens Cached:   4.2M                 │
│ Total Bytes (encrypted): 68MB               │
│ Avg Tokens/Session:    674                  │
│ Avg Turns/Session:     8.3                  │
│                                             │
│ Expiration Breakdown (last hour):           │
│ - Absolute TTL:        12 sessions          │
│ - Idle Timeout:        156 sessions         │
│ - LRU Eviction:        0 sessions           │
│                                             │
│ [Graph: Session count over time]            │
│ [Graph: Token distribution histogram]       │
└─────────────────────────────────────────────┘
```

### **Dashboard 3: Security & Encryption**

```
┌─────────────────────────────────────────────┐
│ Encryption Health                           │
├─────────────────────────────────────────────┤
│ Status:                 ✅ Healthy           │
│ Master Key Age:         4h 23m              │
│ Encryption Successes:   12,456              │
│ Encryption Failures:    0                   │
│ Decryption Failures:    2 (0.02%)           │
│                                             │
│ Key Derivation (HKDF):                      │
│ - p95 Latency:          0.8ms               │
│ - Total Derivations:    12,458              │
│                                             │
│ [Graph: Decrypt failures over time]         │
│ [Alert: Encryption failure > 0]             │
└─────────────────────────────────────────────┘
```

### **Dashboard 4: User Experience**

```
┌─────────────────────────────────────────────┐
│ Conversation Metrics                        │
├─────────────────────────────────────────────┤
│ Sessions Approaching Limit (>80%):  23      │
│ Longest Session:                    42 turns│
│ Highest Token Usage:                7,234   │
│                                             │
│ Compression Triggers (if implemented):      │
│ - Token-based:          0                   │
│ - Turn-based:           0                   │
│                                             │
│ [Graph: Session length distribution]        │
│ [Graph: Token utilization distribution]     │
└─────────────────────────────────────────────┘
```

---

## Alerting Rules

### **Critical Alerts** (Page Immediately)

```yaml
- alert: CacheEncryptionFailures
  expr: rate(cache_encrypt_failure_total[5m]) > 0
  severity: critical
  summary: "Cache encryption failing - data security at risk"

- alert: CacheDecryptionFailureSpike
  expr: rate(cache_decrypt_failure_total[5m]) > 10
  severity: critical
  summary: "High decryption failure rate - possible key corruption"

- alert: CacheCapacityFull
  expr: (cache_sessions_total / cache_max_entries) > 0.95
  severity: critical
  summary: "Cache at 95% capacity - imminent LRU evictions"
```

### **Warning Alerts** (Investigate Soon)

```yaml
- alert: CacheHighUtilization
  expr: (cache_sessions_total / cache_max_entries) > 0.80
  severity: warning
  summary: "Cache at 80% capacity - plan for scaling"

- alert: CacheHighLatency
  expr: histogram_quantile(0.95, cache_get_latency_seconds) > 0.020
  severity: warning
  summary: "p95 cache get latency > 20ms"

- alert: CacheLowHitRate
  expr: rate(cache_hits_total[10m]) / rate(cache_total_requests[10m]) < 0.70
  severity: warning
  summary: "Cache hit rate below 70% - check TTL settings"

- alert: CacheHighEvictionRate
  expr: rate(cache_evicted_lru_total[10m]) > 10
  severity: warning
  summary: "High LRU eviction rate - increase max_entries"
```

### **Info Alerts** (Awareness)

```yaml
- alert: CacheMasterKeyOld
  expr: cache_master_key_age_seconds > 604800  # 7 days
  severity: info
  summary: "Cache master key is 7+ days old - consider process restart"

- alert: CacheSessionsApproachingLimit
  expr: cache_sessions_approaching_limit_total > 50
  severity: info
  summary: "50+ sessions approaching token limit - compression needed"
```

---

## Logging Standards

### **Structured JSON Logs**

Every cache operation logs:

```json
{
  "timestamp": "2025-10-25T15:30:45.123Z",
  "level": "INFO",
  "service": "conversation_cache",
  "operation": "append",
  "session_id": "session_abc123",
  "role": "assistant",
  "metrics": {
    "new_message_tokens": 234,
    "total_tokens": 1456,
    "token_percentage": 24,
    "turn_count": 6,
    "turn_percentage": 12,
    "will_compress": false,
    "latency_ms": 12.3,
    "encryption_ok": true
  },
  "request_id": "req_xyz789"
}
```

### **Log Levels**

| Level | Use Case | Example |
|-------|----------|---------|
| **DEBUG** | Cache hits/misses, key derivation | "Cache hit for session_123" |
| **INFO** | Successful operations, GC cycles | "Cache entry stored: 5 turns, 1234 tokens" |
| **WARNING** | Approaching limits, slow operations | "Session at 85% token capacity" |
| **ERROR** | Encryption/decryption failures | "Failed to decrypt entry: InvalidTag" |
| **CRITICAL** | System failures | "Master key corrupted" |

### **Never Log** (Security)

- ❌ Plaintext message content
- ❌ Ciphertext blobs (except first 16 bytes for debugging)
- ❌ Master key or DEKs
- ❌ Nonces (can be informational, but not with ciphertext)
- ❌ Session IDs with PII (hash if needed)

---

## Exposure Endpoints

### **Health Endpoint** (Public)

```http
GET /health/cache
Authorization: Bearer <token>

Response:
{
  "status": "healthy",  // healthy | warning | critical
  "stats": {
    "total_sessions": 6234,
    "total_tokens": 4200000,
    "capacity_utilization_pct": 62,
    "expired_sessions": 23,
    "encryption": "AES-GCM-256",
    "token_estimation": "heuristic_v1"
  },
  "health_indicators": {
    "capacity_ok": true,
    "latency_ok": true,
    "encryption_ok": true,
    "hit_rate_ok": true
  },
  "timestamp": "2025-10-25T15:30:45.123Z"
}
```

### **Metrics Endpoint** (Prometheus)

```http
GET /metrics
Authorization: Bearer <admin-token>

Response (Prometheus format):
# HELP cache_get_latency_seconds Cache get operation latency
# TYPE cache_get_latency_seconds histogram
cache_get_latency_seconds_bucket{le="0.005"} 8234
cache_get_latency_seconds_bucket{le="0.010"} 12456
cache_get_latency_seconds_bucket{le="0.020"} 12500
cache_get_latency_seconds_sum 125.3
cache_get_latency_seconds_count 12500

# HELP cache_sessions_total Active cache sessions
# TYPE cache_sessions_total gauge
cache_sessions_total 6234

# HELP cache_hits_total Cache hit count
# TYPE cache_hits_total counter
cache_hits_total 98765
...
```

### **Admin Endpoint** (Detailed Diagnostics)

```http
GET /admin/cache/diagnostics
Authorization: Bearer <admin-token>

Response:
{
  "global_stats": {...},
  "top_sessions": [
    {
      "session_id": "session_abc",
      "token_count": 7234,
      "turn_count": 42,
      "utilization_pct": 90,
      "age_seconds": 3600
    },
    ...
  ],
  "recent_evictions": [...],
  "recent_errors": [...],
  "compression_candidates": [...]  // Sessions > 80% utilization
}
```

---

## Performance SLIs/SLOs

### **Service Level Indicators (SLIs)**

| SLI | Measurement | Calculation |
|-----|-------------|-------------|
| **Availability** | % of requests that succeed | `(success / total) * 100` |
| **Latency** | p95 response time | `histogram_quantile(0.95, latency)` |
| **Throughput** | Operations per second | `rate(operations_total[1m])` |
| **Hit Rate** | % of gets that hit | `(hits / (hits + misses)) * 100` |

### **Service Level Objectives (SLOs)**

| Metric | Target | Measurement Window | Impact if Missed |
|--------|--------|-------------------|------------------|
| **Availability** | 99.9% | 30 days | User conversations fail |
| **p95 Get Latency** | < 10ms | 24 hours | Slow response times |
| **p95 Set Latency** | < 20ms | 24 hours | Delayed cache updates |
| **Hit Rate** | > 80% | 1 hour | Increased backend load |
| **Capacity Headroom** | < 80% | Real-time | Risk of evictions |

### **Error Budget**

- **Allowed Downtime:** 43 minutes per month (99.9% SLO)
- **Allowed Errors:** 0.1% of requests
- **Budget Tracking:** Daily aggregation
- **Burn Rate Alert:** If consuming > 5% budget per day

---

## Operational Runbooks

### **High Decryption Failure Rate**

```
Symptom: cache_decrypt_failure_total increasing
Possible Causes:
  1. Process restarted (master key regenerated)
  2. Memory corruption
  3. Concurrent modification race

Investigation:
  1. Check process uptime: cache_master_key_age_seconds
  2. Check for recent restarts in logs
  3. Check error logs for InvalidTag exceptions

Resolution:
  - If process restarted: Expected, failures will clear as cache rebuilds
  - If memory corruption: Restart process to regenerate master key
  - If race condition: Check thread-safety of cache operations
```

### **Cache Capacity Near Limit**

```
Symptom: cache_sessions_total > 8000 (80% of 10,000)
Impact: Imminent LRU evictions, active sessions will be dropped

Investigation:
  1. Check avg session duration
  2. Check idle timeout effectiveness
  3. Check GC cycle frequency

Actions:
  1. Reduce idle_timeout (15min → 10min) to expire faster
  2. Increase max_entries (10k → 20k) if memory available
  3. Trigger manual GC: POST /admin/cache/gc
  4. Plan for Redis migration if sustained high usage
```

### **High Latency**

```
Symptom: p95 cache latency > 20ms
Impact: Slow conversation response times

Investigation:
  1. Check cache size: total_bytes metric
  2. Check average session size
  3. Check CPU usage (encryption is CPU-intensive)
  4. Check for memory pressure (swap activity)

Actions:
  1. Enable hardware AES-NI (should be default on modern CPUs)
  2. Consider reducing max_bytes if sessions are huge
  3. Profile encryption/decryption with cProfile
  4. Consider migrating to Redis with pipelining
```

---

## Implementation Checklist

### **Phase 1: Basic Metrics** (v1.0)
- [x] Add global stats method
- [x] Add session stats method
- [ ] Add `cache_stats` to FormattedResponse
- [ ] Return stats in `/v1/process` response
- [ ] Log all cache operations with metrics
- [ ] Create `/health/cache` endpoint

### **Phase 2: Prometheus Integration** (v1.1)
- [ ] Add `prometheus_client` dependency
- [ ] Instrument all cache operations
- [ ] Create `/metrics` endpoint
- [ ] Configure Prometheus scraping
- [ ] Build Grafana dashboards

### **Phase 3: Advanced Monitoring** (v1.2)
- [ ] Add distributed tracing (OpenTelemetry)
- [ ] Add anomaly detection (sudden latency spikes)
- [ ] Add predictive alerts (capacity trending)
- [ ] Add cost tracking (token usage → $ estimation)

---

## Consequences

### Positive

✅ **Visibility:** Real-time insight into cache behavior
✅ **Debugging:** Faster root cause analysis
✅ **Capacity Planning:** Data-driven scaling decisions
✅ **Security Assurance:** Detect encryption issues immediately
✅ **Performance Optimization:** Identify bottlenecks
✅ **User Transparency:** Show cache utilization in UI

### Negative

⚠️ **Overhead:** Metrics collection adds ~2-5% CPU
⚠️ **Complexity:** More code to maintain
⚠️ **Storage:** Prometheus metrics require disk space

### Mitigation

- **Sampling:** Sample high-volume metrics (1 in 10)
- **Aggregation:** Pre-aggregate before export
- **Retention:** 30-day metric retention policy
- **Optional:** Feature flag to disable detailed metrics

---

## Future Enhancements

### **v1.2: Cost Tracking**
```python
cache_stats = {
    "tokens_used": 1234,
    "estimated_cost_usd": 0.0025,  # Based on model pricing
    "cost_trend": "increasing"
}
```

### **v2.0: Distributed Metrics**
- Redis-based cache → centralized metrics
- Multi-instance aggregation
- Cross-pod session tracking

### **v2.1: ML-Based Anomaly Detection**
- Detect unusual session patterns
- Identify potential attacks (context stuffing)
- Predict capacity needs

---

## References

- **ADR-030:** Stateless Architecture (Ephemeral by Design)
- **ADR-034:** Conversations as QUERY Pattern
- `src/orchestrator/app/services/conversation_cache.py` - Implementation
- `src/orchestrator/app/schemas/response.py` - Response schema with cache_stats
- Prometheus Client Library: https://github.com/prometheus/client_python
- OpenTelemetry Python: https://opentelemetry.io/docs/languages/python/

---

## Decision Rationale

**"If you can't measure it, you can't manage it."**

The ephemeral cache is:
- **Performance-critical:** Affects response latency
- **Security-sensitive:** Handles encrypted SOC data
- **Resource-constrained:** In-memory with hard limits
- **User-facing:** Impacts conversation UX

Comprehensive observability is **non-negotiable** for production operation.

---

**Status:** Metrics infrastructure defined. Implementation in progress.
