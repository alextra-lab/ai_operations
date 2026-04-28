# ADR-053: Rate Limiting and Usage Tracking

**Status:** Approved
**Date:** 2025-11-02
**Deciders:** Security Team, Backend Team, Operations Team
**Tags:** security, performance, rate-limiting, monitoring, cost

---

## Context

The Inference Gateway consolidates access to external inference providers for a **department-scale deployment** (10-100 concurrent users). The platform must protect infrastructure, enforce upstream provider limits, and track usage for cost analysis and capacity planning.

### Problem Statement

**Infrastructure Protection:**
- Runaway scripts or misconfigured SOAR integrations can overwhelm system
- No protection against accidental denial-of-service (DOS) from internal sources
- Gateway could exhaust CPU/memory handling too many concurrent requests

**Upstream Provider Limits:**
- OpenAI API Tier 1: 500 requests/minute, 200K tokens/minute
- Mistral API Free Tier: 200 requests/minute, 100K tokens/minute
- Exceeding limits = provider blocks us for 5-60 minutes (cascading failures)
- No mechanism to stay under provider caps

**Usage Analysis (Security Audit HIGH PRIORITY):**
- Can't identify noisy neighbors (users consuming disproportionate resources)
- No visibility into cost attribution (which use cases are expensive?)
- Can't detect abuse patterns (unusual spike in requests)
- Can't forecast LLMaaS costs (no usage trending)

### Current State

**No Rate Limiting:**
- Orchestrator calls providers with no throttling
- Embedding service calls providers with no throttling
- If provider is slow/down, requests queue indefinitely
- No protection against runaway loops

**Scattered Metrics:**
- Orchestrator logs some usage (run manifests)
- Embedding service logs separately
- No unified view across all LLM/embedding calls
- Cost calculation happens per-call (not aggregated)

### Department Scale Context

**Deployment Profile:**
- 10-100 SOC analysts + automated integrations (SOAR, ServiceNow)
- Peak load: 100-500 requests/minute
- Average load: 50-200 requests/minute
- Use cases: Ad-hoc queries, scheduled reports, SOAR automation

**Resource Constraints:**
- Self-hosted on on-premises servers or powerful laptops
- Limited budget for external LLMaaS (Mistral, OpenAI)
- Air-gapped environments prefer minimal dependencies

---

## Decision

Implement **two-phase approach**: Usage Tracking (v1 immediate) + Rate Limiting (v2 as needed).

### Phase 1 (v1): Usage Tracking & Monitoring (IMMEDIATE)

**What:**
- Log every request with full context (user, provider, model, tokens, cost)
- Store in PostgreSQL for analysis and trending
- NO enforcement (no request rejection)
- Dashboard for usage analytics

**Why:**
- Identify noisy neighbors before implementing limits
- Measure actual usage patterns (not guesses)
- Build data-driven capacity plan
- Detect cost outliers and optimization opportunities

**When to Use:**
- Day 1 of Gateway deployment
- Runs alongside existing metrics (run manifests)
- Zero user impact (transparent logging)

### Phase 2 (v2): Rate Limiting Enforcement (AS NEEDED)

**What:**
- Enforce limits when usage data shows need
- Global limits (protect infrastructure)
- Per-provider limits (stay under upstream caps)
- Per-integration limits (prevent SOAR accidents)

**Why:**
- Only implement if Phase 1 reveals problems
- Data-driven thresholds (not arbitrary)
- Focused on protection, not punishment

**When to Use:**
- After 1 month of Phase 1 usage data
- If reject rate would be <5% (minimal user impact)
- If specific integration causes issues (SOAR runaway)
- If approaching provider limits (OpenAI 450/500 rpm)

---

## Phase 1: Usage Tracking (Immediate)

### Database Schema

**Usage Log Table:**
```sql
CREATE TABLE gateway_usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Request metadata
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    request_id TEXT NOT NULL,  -- Propagated from X-Request-ID

    -- Caller identity
    user_id UUID REFERENCES users(id),  -- NULL for service accounts
    service_id TEXT,                     -- "orchestrator-api", "cortex-prod"
    role TEXT,                           -- From JWT token

    -- Provider & model
    provider TEXT NOT NULL,    -- "openai", "mistral", "lmstudio"
    model TEXT NOT NULL,       -- "gpt-4o-mini", "mistral-large-latest"
    endpoint TEXT NOT NULL,    -- "/v1/chat/completions", "/v1/embeddings"

    -- Usage metrics
    tokens_in INTEGER,
    tokens_out INTEGER,
    total_tokens INTEGER,
    cost_eur NUMERIC(10, 6),   -- Calculated from pricing table

    -- Performance metrics
    latency_ms INTEGER,        -- Total request time
    gateway_latency_ms INTEGER,  -- Added Gateway overhead
    provider_latency_ms INTEGER, -- Provider response time

    -- Status
    status_code INTEGER,       -- 200, 429, 500, etc.
    error_type TEXT,           -- "timeout", "rate_limit", "provider_error"

    -- Indexes for common queries
    INDEX idx_gateway_usage_timestamp (timestamp),
    INDEX idx_gateway_usage_user (user_id, timestamp),
    INDEX idx_gateway_usage_service (service_id, timestamp),
    INDEX idx_gateway_usage_provider (provider, timestamp),
    INDEX idx_gateway_usage_model (model, timestamp)
);

-- Partition by month for performance (optional)
CREATE TABLE gateway_usage_log_2025_11
    PARTITION OF gateway_usage_log
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
```

### Logging Implementation

**Gateway Request Handler:**
```python
# src/inference-gateway/app/middleware/usage_tracker.py
from shared.logging_utils.fastapi import configure_logging
from shared.database import get_db

logger = configure_logging(service_name="gateway_usage")

class UsageTracker:
    """Track all Gateway requests for analysis."""

    async def log_request(
        self,
        request_id: str,
        token: TokenPayload,
        provider: str,
        model: str,
        endpoint: str,
        tokens_in: int,
        tokens_out: int,
        cost_eur: float,
        latency_ms: int,
        gateway_latency_ms: int,
        status_code: int,
        error_type: str | None = None
    ):
        """Log request to database and structured logs."""

        # Structured JSON log (existing pattern from shared.logging_utils)
        logger.info(
            "Gateway request completed",
            extra={
                "request_id": request_id,
                "user_id": token.user_id if token.role != "service" else None,
                "service_id": token.sub if token.role == "service" else None,
                "role": token.role,
                "provider": provider,
                "model": model,
                "endpoint": endpoint,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "total_tokens": tokens_in + tokens_out,
                "cost_eur": cost_eur,
                "latency_ms": latency_ms,
                "gateway_latency_ms": gateway_latency_ms,
                "provider_latency_ms": latency_ms - gateway_latency_ms,
                "status_code": status_code,
                "error_type": error_type
            }
        )

        # Database log (for aggregation queries)
        async with get_db() as db:
            usage_record = GatewayUsageLog(
                request_id=request_id,
                user_id=token.user_id if token.role != "service" else None,
                service_id=token.sub if token.role == "service" else None,
                role=token.role,
                provider=provider,
                model=model,
                endpoint=endpoint,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                total_tokens=tokens_in + tokens_out,
                cost_eur=cost_eur,
                latency_ms=latency_ms,
                gateway_latency_ms=gateway_latency_ms,
                provider_latency_ms=latency_ms - gateway_latency_ms,
                status_code=status_code,
                error_type=error_type
            )
            db.add(usage_record)
            await db.commit()
```

### Analytics Queries

**Noisy Neighbor Detection:**
```sql
-- Top 10 users by request count (last 24 hours)
SELECT
    COALESCE(u.username, g.service_id) as caller,
    COUNT(*) as request_count,
    SUM(g.total_tokens) as total_tokens,
    SUM(g.cost_eur) as total_cost_eur,
    ROUND(AVG(g.latency_ms)) as avg_latency_ms
FROM gateway_usage_log g
LEFT JOIN users u ON g.user_id = u.id
WHERE g.timestamp > now() - interval '24 hours'
GROUP BY u.username, g.service_id
ORDER BY request_count DESC
LIMIT 10;
```

**Provider Usage Distribution:**
```sql
-- Requests per provider (last 7 days)
SELECT
    provider,
    COUNT(*) as requests,
    SUM(total_tokens) as tokens,
    SUM(cost_eur) as cost_eur,
    ROUND(AVG(latency_ms)) as avg_latency_ms,
    COUNT(CASE WHEN status_code >= 400 THEN 1 END) as errors
FROM gateway_usage_log
WHERE timestamp > now() - interval '7 days'
GROUP BY provider
ORDER BY requests DESC;
```

**Cost Trending:**
```sql
-- Daily cost trend (last 30 days)
SELECT
    DATE(timestamp) as date,
    provider,
    COUNT(*) as requests,
    SUM(cost_eur) as daily_cost_eur
FROM gateway_usage_log
WHERE timestamp > now() - interval '30 days'
GROUP BY DATE(timestamp), provider
ORDER BY date DESC, daily_cost_eur DESC;
```

**Expensive Use Cases:**
```sql
-- Link to run_manifests for use case attribution
SELECT
    rm.use_case_id,
    uc.name as use_case_name,
    COUNT(*) as executions,
    SUM(g.cost_eur) as total_cost_eur,
    AVG(g.cost_eur) as avg_cost_per_execution
FROM gateway_usage_log g
JOIN run_manifests rm ON g.request_id = rm.request_id
JOIN use_cases uc ON rm.use_case_id = uc.id
WHERE g.timestamp > now() - interval '7 days'
GROUP BY rm.use_case_id, uc.name
ORDER BY total_cost_eur DESC
LIMIT 20;
```

---

## Phase 2: Rate Limiting (As Needed)

### When to Implement

**Criteria for Enabling:**
1. ✅ Usage data shows reject rate would be <5% (minimal impact)
2. ✅ Specific integration causes issues (SOAR runaway detected)
3. ✅ Approaching provider limits (>400 req/min to OpenAI's 500 limit)
4. ✅ Infrastructure strain detected (CPU >80%, queue depth >100)

**Criteria for Staying in Phase 1:**
1. ❌ All usage within comfortable margins
2. ❌ No runaway patterns detected
3. ❌ No user complaints about slow responses
4. ❌ Provider limits not approached

### Limit Hierarchy (If Implemented)

| Limit Type | Purpose | Typical Value |
|------------|---------|---------------|
| **Global** | Protect Gateway infrastructure | 500 req/min (system capacity) |
| **Per-Provider** | Stay under upstream limits | 450 req/min (OpenAI: 500), 180 req/min (Mistral: 200) |
| **Per-Integration** | Prevent SOAR accidents | 100 req/min per service account |
| **Per-Use-Case** | Cost control (optional) | 50-500 exec/day depending on cost |

### Implementation: Token Bucket Algorithm

**Redis-Backed (Recommended):**
```python
# src/inference-gateway/app/rate_limiting/limiter.py
import redis.asyncio as redis
import time

class TokenBucketLimiter:
    """Token bucket rate limiter with Redis backend."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def check(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> tuple[bool, int]:
        """
        Check if request is allowed.

        Args:
            key: Limit key (e.g., "global", "provider:openai", "service:cortex")
            limit: Max requests in window
            window_seconds: Window duration (60 for 1 minute)

        Returns:
            (allowed: bool, retry_after_seconds: int)
        """
        now = time.time()
        window_start = now - window_seconds

        # Use Redis sorted set for sliding window
        pipe = self.redis.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)

        # Count current entries
        pipe.zcard(key)

        # Add this request (optimistic)
        pipe.zadd(key, {str(now): now})

        # Set expiry
        pipe.expire(key, window_seconds)

        results = await pipe.execute()
        current_count = results[1]  # Count before adding

        if current_count >= limit:
            # Rate limited - remove the optimistic add
            await self.redis.zrem(key, str(now))

            # Calculate retry_after
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                oldest_timestamp = oldest[0][1]
                retry_after = int(window_seconds - (now - oldest_timestamp)) + 1
            else:
                retry_after = window_seconds

            return (False, retry_after)

        # Allowed
        return (True, 0)
```

**Usage in Gateway:**
```python
@router.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    token: TokenPayload = Depends(requires_scope("inference:chat")),
    limiter: TokenBucketLimiter = Depends(get_limiter)
):
    # Check global limit
    allowed, retry_after = await limiter.check("global", limit=500, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="System busy, too many requests",
            headers={"Retry-After": str(retry_after)}
        )

    # Check provider limit
    provider = get_provider_for_model(request.model)
    allowed, retry_after = await limiter.check(
        f"provider:{provider.name}",
        limit=provider.rate_limit_rpm,  # 450 for OpenAI
        window_seconds=60
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Provider {provider.name} rate limit exceeded",
            headers={"Retry-After": str(retry_after)}
        )

    # Check integration limit (if service account)
    if token.role == "service":
        allowed, retry_after = await limiter.check(
            f"service:{token.sub}",
            limit=100,  # SOAR/automation limit
            window_seconds=60
        )
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Service {token.sub} rate limit exceeded",
                headers={"Retry-After": str(retry_after)}
            )

    # Proceed with request
    response = await provider.chat_completion(request)
    return response
```

### PostgreSQL Fallback (No Redis)

**For Air-Gapped or Simple Deployments:**
```python
# Slower but works without Redis
class PostgresRateLimiter:
    """Token bucket using PostgreSQL."""

    async def check(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> tuple[bool, int]:
        """PostgreSQL-based rate limiting."""

        now = datetime.now(UTC)
        window_start = now - timedelta(seconds=window_seconds)

        # Count recent requests
        count = await db.execute(
            """
            SELECT COUNT(*)
            FROM gateway_rate_limit_tokens
            WHERE key = :key AND timestamp > :window_start
            """,
            {"key": key, "window_start": window_start}
        )

        if count >= limit:
            # Calculate retry_after
            oldest = await db.execute(
                """
                SELECT timestamp
                FROM gateway_rate_limit_tokens
                WHERE key = :key
                ORDER BY timestamp
                LIMIT 1
                """,
                {"key": key}
            )
            retry_after = int((window_start - oldest).total_seconds()) + 1
            return (False, retry_after)

        # Add token
        await db.execute(
            """
            INSERT INTO gateway_rate_limit_tokens (key, timestamp)
            VALUES (:key, :timestamp)
            """,
            {"key": key, "timestamp": now}
        )

        # Cleanup old tokens (periodic)
        await db.execute(
            """
            DELETE FROM gateway_rate_limit_tokens
            WHERE timestamp < :window_start
            """,
            {"window_start": window_start}
        )

        return (True, 0)
```

**Trade-offs:**
- Redis: <1ms latency, 10,000+ req/sec
- PostgreSQL: 10-20ms latency, 500-1,000 req/sec
- For department scale (100-500 req/min), PostgreSQL is sufficient

### Configuration Management

**Environment Variables (v1):**
```bash
# .env
RATE_LIMIT_ENABLED=false  # v1: disabled, just tracking

# When enabled (v2)
RATE_LIMIT_ENABLED=true
RATE_LIMIT_GLOBAL_RPM=500
RATE_LIMIT_OPENAI_RPM=450
RATE_LIMIT_MISTRAL_RPM=180
RATE_LIMIT_SERVICE_ACCOUNT_RPM=100
```

**Database Configuration (v2+):**
```sql
CREATE TABLE gateway_rate_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    limit_type TEXT NOT NULL,  -- 'global', 'provider', 'integration', 'use_case'
    identifier TEXT,           -- NULL for global, 'openai' for provider, etc.
    requests_per_minute INTEGER NOT NULL,
    tokens_per_minute BIGINT,
    burst_size INTEGER DEFAULT 10,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Default limits
INSERT INTO gateway_rate_limits VALUES
    (gen_random_uuid(), 'global', NULL, 500, NULL, 50, true),
    (gen_random_uuid(), 'provider', 'openai', 450, 150000, 20, true),
    (gen_random_uuid(), 'provider', 'mistral', 180, 90000, 10, true),
    (gen_random_uuid(), 'integration', 'service:cortex-prod', 100, NULL, 10, true);
```

---

## User Experience

### When NOT Rate Limited (Phase 1)

**User Flow:**
1. Analyst executes use case
2. Request flows through Gateway
3. Usage logged transparently
4. Response returned normally
5. **Zero user impact**

### When Rate Limited (Phase 2 - If Enabled)

**Analyst UI:**
```
Analyst clicks "Execute Use Case"
→ Gateway returns 429 Too Many Requests

Frontend displays:
┌──────────────────────────────────────┐
│ ⚠️ System Busy                       │
│                                      │
│ Too many requests right now.         │
│ Retrying automatically in 15s...     │
│                                      │
│ Requests: 523/500 (limit reached)    │
│                                      │
│ [Retry Now] [Cancel]                 │
└──────────────────────────────────────┘

After 15s: Auto-retry succeeds ✅
```

**SOAR Integration:**
```python
# SOAR script with retry logic
response = requests.post("/v1/chat/completions", ...)

if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", 30))
    logger.warning(f"Rate limited, retrying in {retry_after}s")
    time.sleep(retry_after)
    response = requests.post(...)  # Retry
```

**Error Response:**
```json
{
    "error": {
        "type": "rate_limit_error",
        "message": "Provider OpenAI rate limit exceeded",
        "code": "rate_limit_exceeded",
        "retry_after": 30,
        "limit_type": "provider:openai",
        "current_usage": 451,
        "limit": 450,
        "suggestion": "Retry in 30 seconds or use local model"
    }
}
```

---

## Monitoring & Alerting

### Metrics Dashboard

**Grafana/Admin UI Widgets:**

1. **Request Rate (Last Hour)**
   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Requests/min:  234 / 500
   Utilization:   46.8%
   Status:        ✅ Healthy
   ```

2. **Provider Usage (Last 24h)**
   ```
   Provider    Requests  Limit  Utilization
   ─────────────────────────────────────────
   OpenAI      12,450    450/m  ██████░░░░ 60%
   Mistral     3,200     180/m  ███░░░░░░░ 30%
   LMStudio    8,900     1000/m ████░░░░░░ 40%
   ```

3. **Cost Trending (Last 7 Days)**
   ```
   €15.23 total

   Mon ██████░░░░ €2.10
   Tue ███████░░░ €2.45
   Wed ████████░░ €2.80
   Thu ██████████ €3.45
   Fri ████████░░ €2.60
   Sat ███░░░░░░░ €1.20
   Sun ███░░░░░░░ €0.63
   ```

4. **Top Consumers (Last 24h)**
   ```
   User/Service         Requests  Cost
   ─────────────────────────────────────
   SOAR (Cortex)        3,450     €4.20
   analyst_john         890       €1.10
   service:embedding    780       €0.95
   analyst_sarah        670       €0.82
   ```

### Alert Rules

**Critical Alerts (PagerDuty/Email):**
```yaml
alerts:
  provider_limit_approaching:
    condition: |
      (requests_last_minute / provider_limit) > 0.9
    severity: critical
    action: email_on_call
    message: "Provider {{ provider }} at 90% of rate limit"

  provider_blocked:
    condition: |
      provider_429_errors > 10 in 5 minutes
    severity: critical
    action: page_on_call
    message: "Provider {{ provider }} blocking requests (429 errors)"
```

**Warning Alerts (Slack/Email):**
```yaml
  high_cost_user:
    condition: |
      daily_cost_per_user > 10 EUR
    severity: warning
    action: slack_notification
    message: "User {{ user }} cost €{{ cost }} today (investigate use case)"

  unusual_spike:
    condition: |
      requests_last_hour > 2x average_last_week
    severity: warning
    action: slack_notification
    message: "Unusual traffic spike: {{ requests }}/hr (avg: {{ average }})"
```

---

## Rationale

### Why Phase 1 First?

**Data-Driven Approach:**
- Don't implement limits based on guesses
- Measure actual usage patterns for 30 days
- Identify real thresholds (not arbitrary 100 req/min)
- Understand user behavior before constraining it

**Example Scenario:**
```
Week 1: Track usage
  - 99% of requests between 50-200 req/min
  - Peak: 280 req/min (SOAR batch job, Wednesdays 2pm)
  - Noisy neighbor: cortex-prod (40% of traffic)

Week 2: Analysis
  - If we set limit to 500 req/min → 0% reject rate (no impact)
  - If we set limit to 300 req/min → 1.2% reject rate (Wednesday spikes)
  - Conclusion: 500 rpm is safe, 300 rpm impacts users

Week 3: Decision
  - Set global limit to 500 rpm (handles peak)
  - Set cortex limit to 150 rpm (prevents runaway)
  - Enable limits with 7-day monitoring

Week 4: Validation
  - 0.08% reject rate (4 requests out of 5,000)
  - All rejections from cortex during misconfiguration
  - No analyst impact
  - Success ✅
```

### Why Redis for Phase 2?

**Performance:**
```
Redis:      <1ms per rate limit check
PostgreSQL: 10-20ms per rate limit check

At 500 req/min:
  Redis overhead:      8 req/sec × 1ms = 8ms/sec = negligible
  PostgreSQL overhead: 8 req/sec × 15ms = 120ms/sec = 12% CPU

Verdict: Redis is 10-20x faster, worth the extra container
```

**State Sharing:**
```
Single Gateway instance:
  PostgreSQL: Works fine
  Redis: Works fine

Multiple Gateway instances (future):
  PostgreSQL: Works but slower (row locking contention)
  Redis: Works perfectly (atomic operations, no locking)

Verdict: Redis enables horizontal scaling (future-proof)
```

**Memory:**
```
Redis container: 50MB actual usage for rate limit state
PostgreSQL: ~100MB for rate limit table + indexes

Verdict: Similar memory, Redis is faster
```

### Why Not Per-User Limits?

**All Users Same Team:**
- Everyone in SOC has same access (same RBAC role)
- No billing tiers (not SaaS)
- Trust model: users are colleagues, not customers

**Better Approach:**
- Track per-user usage (Phase 1)
- If specific user is outlier, **talk to them** (not block them)
- Understand root cause (inefficient use case? automation gone wrong?)
- Fix the problem (optimize use case, fix script) vs symptom (rate limit)

**Exception:**
- SOAR/automation = service accounts (not humans)
- OK to limit service accounts (prevent runaway scripts)
- Per-integration limits (cortex: 100 rpm) make sense

---

## Consequences

### Positive

✅ **Phase 1 Benefits (Immediate):**
- Full visibility into usage patterns
- Identify cost optimization opportunities
- Detect noisy neighbors and abuse
- Data-driven capacity planning
- No user impact (transparent logging)

✅ **Phase 2 Benefits (If Enabled):**
- Prevent infrastructure overload
- Stay under provider limits (no blocking)
- Protect against runaway scripts
- Fair resource allocation

### Negative

❌ **Phase 1 Overhead:**
- Database writes per request (~10ms)
- Storage growth (~100KB/day/user = 3MB/month/100 users)

❌ **Phase 2 Complexity (If Enabled):**
- Redis dependency (new container)
- Rate limit config management
- User education (why am I blocked?)
- False positives (legitimate spike blocked)

### Mitigation

**Phase 1 Overhead:**
- Batch insert usage records (10 requests → 1 DB write)
- Partition table by month (automatic cleanup)
- Async logging (don't block response)

**Phase 2 Complexity:**
- Feature flag (enable/disable instantly)
- Generous limits (99% of requests pass)
- Clear error messages (Retry-After header)
- Admin override capability (bypass limits for debugging)

---

## Acceptance Criteria

### Phase 1 (Usage Tracking)

✅ Every request logged with complete metadata
✅ Database queries return usage within 1 second
✅ Metrics dashboard shows real-time and historical data
✅ Noisy neighbor detection query identifies top 10 users
✅ Cost trending shows daily/weekly/monthly patterns
✅ Storage growth <5MB/month for 100 users

### Phase 2 (Rate Limiting - If Implemented)

✅ Limits enforced accurately (<5% error at p99)
✅ Retry-After header present on 429 responses
✅ Redis operations <1ms (p95)
✅ PostgreSQL fallback works (10-20ms slower but functional)
✅ Admin UI shows current utilization vs limits
✅ Feature flag enables/disables limits without restart
✅ Limit updates (via Admin UI) apply within 60 seconds

---

## References

### Related ADRs

- **ADR-050:** Inference Gateway and Responsibility Split
- **ADR-051:** Provider Secrets and S2S Auth
- **ADR-030:** No Transcripts; Run Manifests Only (extend for Gateway metrics)
- **ADR-055:** Observability, Metering, and Cost Accounting

### Existing Code

- `src/orchestrator/app/db/models.py` - `run_manifests` table (similar pattern)
- `src/orchestrator/app/utils/cost_estimator.py` - Cost calculation logic
- `src/orchestrator/app/services/pricing_history_service.py` - Pricing lookups
- `src/shared/logging_utils/fastapi.py` - Structured logging

### External References

- Token Bucket Algorithm: https://en.wikipedia.org/wiki/Token_bucket
- Redis Rate Limiting: https://redis.io/docs/manual/patterns/rate-limiter/
- OpenAI Rate Limits: https://platform.openai.com/docs/guides/rate-limits
- Mistral Rate Limits: https://docs.mistral.ai/api/

---

**Document Owner:** Operations Team
**Last Updated:** 2025-11-02
**Status:** Approved for Phase 1 Implementation
