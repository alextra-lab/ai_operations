# ADR-055: Observability, Metering, and Cost Accounting

**Status:** Approved
**Date:** 2025-11-02
**Deciders:** Operations Team, Backend Team, Security Team
**Tags:** observability, metrics, cost, monitoring, logging

---

## Context

The Inference Gateway centralizes all LLM and embedding requests for the platform. This creates a unique opportunity for **unified telemetry** across providers, models, users, and use cases. The platform operates at **department scale** (10-100 users) with air-gapped deployment requirements.

### Business Requirements

**Cost Accountability:**
- Track spend by provider (OpenAI, Mistral, local)
- Attribute costs to use cases and users
- Forecast monthly LLMaaS expenses
- Identify cost optimization opportunities

**Performance Monitoring:**
- Measure latency (Gateway overhead + provider latency)
- Track success/error rates by provider
- Detect degraded performance early
- Capacity planning (approaching limits?)

**Security & Compliance:**
- Audit trail for all AI interactions
- Detect unusual usage patterns (potential abuse)
- Compliance reporting (SOC 2, GDPR)
- PII protection in logs (ADR-045)

### Existing Infrastructure (Leverage)

**Shared Logging (`src/shared/logging_utils/fastapi`):**
- ✅ Structured JSON logs
- ✅ Configurable redaction (REDACT_LOGS env var)
- ✅ Request ID propagation
- ✅ Service/user context

**Run Manifests (`run_manifests` table):**
- ✅ Per-request telemetry (tokens, cost, latency)
- ✅ Linked to use cases
- ✅ User attribution
- ✅ Already in production (extend for Gateway)

**Models Table:**
- ✅ Model metadata (provider, capabilities)
- ✅ Pricing history (`model_pricing_history` table)
- ✅ Context windows, max tokens

**Audit Logs (`audit_logs` table):**
- ✅ User actions tracked
- ✅ Before/after state
- ✅ Timestamp and actor attribution

---

## Decision

Implement **three-layer observability**: Structured Logs + Usage Database + Integration with Run Manifests.

### Layer 1: Structured Logging (Immediate, Low Overhead)

**Use Existing `shared.logging_utils.fastapi`:**
```python
# src/inference-gateway/app/middleware/logging_middleware.py
from shared.logging_utils.fastapi import configure_logging

logger = configure_logging(service_name="inference_gateway")

class RequestLoggingMiddleware:
    """Log all Gateway requests with full context."""

    async def __call__(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.time()

        # Extract user context from JWT
        token = await get_token_from_request(request)

        try:
            response = await call_next(request)
            latency_ms = int((time.time() - start_time) * 1000)

            # Structured JSON log (existing pattern)
            logger.info(
                "Gateway request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                    "user_id": token.user_id if token else None,
                    "role": token.role if token else None,
                    "service_id": token.sub if token and token.role == "service" else None,
                    # Provider details added by endpoint handler
                    "provider": getattr(response, "provider", None),
                    "model": getattr(response, "model", None),
                    "tokens_in": getattr(response, "tokens_in", None),
                    "tokens_out": getattr(response, "tokens_out", None),
                    "cost_eur": getattr(response, "cost_eur", None),
                }
            )

            return response

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)

            logger.error(
                f"Gateway request failed: {type(e).__name__}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "latency_ms": latency_ms,
                    "user_id": token.user_id if token else None,
                },
                exc_info=True
            )
            raise
```

**Log Redaction (ADR-045 Compliance):**
```python
# Prompts/responses NOT logged by default
# Only metadata (tokens, cost, latency) logged

# Optional sampling for debugging (RBAC-gated)
if ENABLE_PROMPT_SAMPLING and random.random() < SAMPLE_RATE:
    # Only for admin users, audit trail required
    logger.debug(
        "Sampled request",
        extra={
            "request_id": request_id,
            "prompt_sample": messages[0]["content"][:100],  # First 100 chars only
            "sampled_by": token.sub,
            "audit_reason": "debugging"
        }
    )
```

### Layer 2: Usage Database (Historical Analysis)

**Extend `gateway_usage_log` Table (from ADR-053):**
```sql
-- Usage logging table (already defined in ADR-053)
CREATE TABLE gateway_usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    request_id TEXT NOT NULL,

    -- Caller identity
    user_id UUID REFERENCES users(id),
    service_id TEXT,
    role TEXT,

    -- Provider & model
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    endpoint TEXT NOT NULL,

    -- Usage metrics
    tokens_in INTEGER,
    tokens_out INTEGER,
    total_tokens INTEGER,
    cost_eur NUMERIC(10, 6),

    -- Performance metrics
    latency_ms INTEGER,
    gateway_latency_ms INTEGER,
    provider_latency_ms INTEGER,

    -- Status
    status_code INTEGER,
    error_type TEXT,

    -- Indexes
    INDEX idx_gateway_usage_timestamp (timestamp),
    INDEX idx_gateway_usage_user (user_id, timestamp),
    INDEX idx_gateway_usage_service (service_id, timestamp),
    INDEX idx_gateway_usage_provider (provider, timestamp)
);
```

**Async Batch Insertion (Performance Optimization):**
```python
# src/inference-gateway/app/services/usage_logger.py
import asyncio
from collections import deque

class BatchUsageLogger:
    """Batch insert usage records to reduce DB overhead."""

    def __init__(self, batch_size: int = 10, flush_interval: float = 5.0):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.queue: deque = deque()
        self._flush_task = None

    async def start(self):
        """Start background flush task."""
        self._flush_task = asyncio.create_task(self._periodic_flush())

    async def log_usage(self, usage_data: dict):
        """Queue usage record for batch insertion."""
        self.queue.append(usage_data)

        # Flush immediately if batch full
        if len(self.queue) >= self.batch_size:
            await self._flush()

    async def _periodic_flush(self):
        """Flush queue periodically."""
        while True:
            await asyncio.sleep(self.flush_interval)
            if self.queue:
                await self._flush()

    async def _flush(self):
        """Batch insert all queued records."""
        if not self.queue:
            return

        records = []
        while self.queue:
            records.append(self.queue.popleft())

        async with get_db() as db:
            db.bulk_insert_mappings(GatewayUsageLog, records)
            await db.commit()

        logger.debug(f"Flushed {len(records)} usage records to database")
```

### Layer 3: Run Manifest Integration (Use Case Attribution)

**Extend `run_manifests` Table:**
```python
# src/orchestrator/app/db/models.py (existing table, add fields)
class RunManifest(Base):
    """Execution telemetry (existing table)."""

    __tablename__ = "run_manifests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    request_id: Mapped[str] = mapped_column(String, unique=True, index=True)

    # Existing fields
    use_case_id: Mapped[uuid.UUID | None]
    user_id: Mapped[uuid.UUID]
    query: Mapped[str]
    intent_type: Mapped[str]

    # NEW: Gateway metrics (extend JSON field)
    gateway_metrics: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {
    #     "provider": "openai",
    #     "model": "gpt-4o-mini",
    #     "gateway_latency_ms": 5,
    #     "provider_latency_ms": 240,
    #     "tokens_in": 120,
    #     "tokens_out": 80,
    #     "cost_eur": 0.00015
    # }

    # Existing fields
    response_text: Mapped[str]
    metadata: Mapped[dict]  # Existing metrics (orchestrator-level)
    created_at: Mapped[datetime]
```

**Orchestrator Updates Gateway Metrics:**
```python
# src/orchestrator/app/orchestrator/steps/execute_llm.py
async def run(self, ctx: RequestContext) -> RequestContext:
    """Execute LLM via Gateway and capture metrics."""

    # Call Gateway
    response = await self.gateway_client.chat_completion(
        model=ctx.selected_model,
        messages=ctx.llm_request.messages,
        headers={"X-Request-ID": ctx.req_id}
    )

    # Extract Gateway metrics from response headers
    gateway_metrics = {
        "provider": response.headers.get("X-Gateway-Provider"),
        "model": response.headers.get("X-Gateway-Model"),
        "gateway_latency_ms": int(response.headers.get("X-Gateway-Latency-Ms", 0)),
        "provider_latency_ms": int(response.headers.get("X-Provider-Latency-Ms", 0)),
        "tokens_in": response.usage.prompt_tokens,
        "tokens_out": response.usage.completion_tokens,
        "cost_eur": float(response.headers.get("X-Gateway-Cost-Eur", 0))
    }

    # Add to context for run manifest
    ctx.gateway_metrics = gateway_metrics

    return ctx

# Run manifest persisted at end of pipeline
run_manifest = RunManifest(
    request_id=ctx.req_id,
    use_case_id=ctx.use_case_id,
    user_id=ctx.user_id,
    query=ctx.query,
    gateway_metrics=ctx.gateway_metrics,  # NEW
    metadata=ctx.llm_metrics  # Existing orchestrator metrics
)
db.add(run_manifest)
```

### Cost Calculation (Centralized in Gateway)

**Gateway Calculates Cost from Pricing Table:**
```python
# src/inference-gateway/app/services/cost_calculator.py
from src.backend.app.services.pricing_history_service import PricingHistoryService

class CostCalculator:
    """Calculate cost using existing pricing infrastructure."""

    def __init__(self, db: Session):
        self.pricing_service = PricingHistoryService(db)

    async def calculate_cost(
        self,
        model_id: str,
        tokens_in: int,
        tokens_out: int,
        timestamp: datetime | None = None
    ) -> dict:
        """
        Calculate cost using pricing history.

        Returns:
            {
                "input_cost_eur": 0.00003,
                "output_cost_eur": 0.00012,
                "total_cost_eur": 0.00015,
                "pricing_source": "pricing_history",
                "effective_date": "2025-11-02"
            }
        """
        # Use existing pricing service (ADR-046)
        pricing = await self.pricing_service.get_active_pricing(
            model_id=model_id,
            at_timestamp=timestamp or datetime.now(UTC)
        )

        if pricing:
            # Per 1M tokens
            input_cost = (tokens_in / 1_000_000) * pricing.input_price_per_million
            output_cost = (tokens_out / 1_000_000) * pricing.output_price_per_million

            return {
                "input_cost_eur": round(input_cost, 6),
                "output_cost_eur": round(output_cost, 6),
                "total_cost_eur": round(input_cost + output_cost, 6),
                "pricing_source": "pricing_history",
                "effective_date": pricing.effective_from.isoformat()
            }
        else:
            # Fallback to model registry defaults
            model = await db.query(Model).filter_by(model_id=model_id).first()
            if model:
                input_cost = (tokens_in / 1_000_000) * (model.input_price_per_million or 0)
                output_cost = (tokens_out / 1_000_000) * (model.output_price_per_million or 0)

                return {
                    "input_cost_eur": round(input_cost, 6),
                    "output_cost_eur": round(output_cost, 6),
                    "total_cost_eur": round(input_cost + output_cost, 6),
                    "pricing_source": "model_registry",
                    "effective_date": datetime.now(UTC).isoformat()
                }

        # No pricing data
        logger.warning(f"No pricing data for model {model_id}")
        return {
            "input_cost_eur": 0.0,
            "output_cost_eur": 0.0,
            "total_cost_eur": 0.0,
            "pricing_source": "unknown",
            "effective_date": datetime.now(UTC).isoformat()
        }
```

**Gateway Returns Cost in Headers:**
```http
HTTP/1.1 200 OK
Content-Type: application/json
X-Request-ID: abc-123-def-456
X-Gateway-Provider: openai
X-Gateway-Model: gpt-4o-mini
X-Gateway-Cost-Eur: 0.00015
X-Gateway-Cost-Input-Eur: 0.00003
X-Gateway-Cost-Output-Eur: 0.00012
X-Gateway-Latency-Ms: 5
X-Provider-Latency-Ms: 240
```

### Metrics Queries (Analytics)

**Daily Cost Trend:**
```sql
SELECT
    DATE(timestamp) as date,
    provider,
    SUM(cost_eur) as daily_cost_eur,
    SUM(total_tokens) as daily_tokens
FROM gateway_usage_log
WHERE timestamp > now() - interval '30 days'
GROUP BY DATE(timestamp), provider
ORDER BY date DESC;
```

**Use Case Cost Attribution:**
```sql
-- Link usage log to run manifests
SELECT
    uc.name as use_case_name,
    COUNT(DISTINCT rm.id) as executions,
    SUM((rm.gateway_metrics->>'tokens_in')::int) as total_tokens_in,
    SUM((rm.gateway_metrics->>'tokens_out')::int) as total_tokens_out,
    SUM((rm.gateway_metrics->>'cost_eur')::numeric) as total_cost_eur,
    AVG((rm.gateway_metrics->>'provider_latency_ms')::int) as avg_provider_latency_ms
FROM run_manifests rm
JOIN use_cases uc ON rm.use_case_id = uc.id
WHERE rm.created_at > now() - interval '7 days'
GROUP BY uc.name
ORDER BY total_cost_eur DESC;
```

**Top Users by Cost:**
```sql
SELECT
    u.username,
    COUNT(*) as requests,
    SUM(g.total_tokens) as total_tokens,
    SUM(g.cost_eur) as total_cost_eur
FROM gateway_usage_log g
JOIN users u ON g.user_id = u.id
WHERE g.timestamp > now() - interval '24 hours'
GROUP BY u.username
ORDER BY total_cost_eur DESC
LIMIT 10;
```

**Provider Performance:**
```sql
SELECT
    provider,
    COUNT(*) as total_requests,
    COUNT(CASE WHEN status_code = 200 THEN 1 END) as successful_requests,
    ROUND(AVG(provider_latency_ms)) as avg_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY provider_latency_ms) as p95_latency_ms,
    COUNT(CASE WHEN status_code >= 400 THEN 1 END) as errors
FROM gateway_usage_log
WHERE timestamp > now() - interval '1 hour'
GROUP BY provider
ORDER BY total_requests DESC;
```

---

## Monitoring Dashboards

### Admin UI Widgets (Phase 1)

**1. Real-Time Usage (Last Hour):**
```
┌─────────────────────────────────────┐
│ Gateway Activity (Last Hour)        │
├─────────────────────────────────────┤
│ Requests:     1,234                 │
│ Tokens:       456K in / 230K out    │
│ Cost:         €2.45                 │
│ Avg Latency:  245ms                 │
│ Error Rate:   0.3%                  │
└─────────────────────────────────────┘
```

**2. Provider Distribution:**
```
┌─────────────────────────────────────┐
│ Provider Usage (Last 24h)           │
├─────────────────────────────────────┤
│ OpenAI      ██████████░░ 65% │ €8.50│
│ Mistral     ████░░░░░░░░ 25% │ €2.30│
│ LMStudio    ██░░░░░░░░░░ 10% │ €0.00│
└─────────────────────────────────────┘
```

**3. Cost Trend (Last 7 Days):**
```
┌─────────────────────────────────────┐
│ Daily Cost (EUR)                    │
├─────────────────────────────────────┤
│ €15 │                        ▄      │
│ €10 │              ▄    ▄▄▄▄█▄▄     │
│  €5 │      ▄▄   ▄▄█▄▄▄██       ▄    │
│  €0 ├──────────────────────────────┤
│     │Mon Tue Wed Thu Fri Sat Sun   │
└─────────────────────────────────────┘
```

**4. Top Consumers:**
```
┌─────────────────────────────────────┐
│ Top 5 Users (Last 24h)              │
├─────────────────────────────────────┤
│ SOAR-Cortex   234 req  €3.45        │
│ analyst_john  123 req  €1.89        │
│ analyst_sarah  89 req  €1.20        │
│ embedding_svc  78 req  €0.45        │
│ analyst_mike   56 req  €0.78        │
└─────────────────────────────────────┘
```

### Prometheus Metrics (Phase 2 - Optional)

**If Prometheus integration needed:**
```python
# src/inference-gateway/app/metrics/prometheus.py
from prometheus_client import Counter, Histogram, Gauge

# Request counters
gateway_requests_total = Counter(
    "gateway_requests_total",
    "Total Gateway requests",
    ["provider", "model", "status"]
)

# Token counters
gateway_tokens_total = Counter(
    "gateway_tokens_total",
    "Total tokens processed",
    ["provider", "model", "direction"]  # direction = input/output
)

# Cost counter
gateway_cost_eur_total = Counter(
    "gateway_cost_eur_total",
    "Total cost in EUR",
    ["provider", "model"]
)

# Latency histogram
gateway_latency_seconds = Histogram(
    "gateway_latency_seconds",
    "Gateway request latency",
    ["provider", "model"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Active requests gauge
gateway_active_requests = Gauge(
    "gateway_active_requests",
    "Currently active requests",
    ["provider"]
)

# Record metrics
def record_request(
    provider: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    cost_eur: float,
    latency_seconds: float,
    status: int
):
    gateway_requests_total.labels(
        provider=provider,
        model=model,
        status=str(status)
    ).inc()

    gateway_tokens_total.labels(
        provider=provider,
        model=model,
        direction="input"
    ).inc(tokens_in)

    gateway_tokens_total.labels(
        provider=provider,
        model=model,
        direction="output"
    ).inc(tokens_out)

    gateway_cost_eur_total.labels(
        provider=provider,
        model=model
    ).inc(cost_eur)

    gateway_latency_seconds.labels(
        provider=provider,
        model=model
    ).observe(latency_seconds)
```

---

## Rationale

### Why Three Layers?

**Different Use Cases:**

| Layer | Purpose | Query Speed | Retention | Best For |
|-------|---------|-------------|-----------|----------|
| **Logs** | Debugging, tracing | Real-time | 7-30 days | Incident investigation |
| **Usage DB** | Analytics, trending | Seconds | 6-12 months | Cost analysis, capacity planning |
| **Run Manifests** | Use case attribution | Seconds | 12+ months | Product analytics, use case ROI |

**Example Workflows:**

1. **"Why is my request failing?"**
   - Search logs by `request_id` → Full trace with errors

2. **"Which use cases are expensive?"**
   - Query run manifests → Use case cost ranking

3. **"Is provider degraded?"**
   - Query usage DB (last hour) → Provider latency percentiles

### Why Extend Run Manifests (Not New Table)?

**Existing Pattern:**
- Run manifests already track orchestrator metrics
- Adding `gateway_metrics` JSONB field = minimal change
- Single table for complete request trace (orchestrator + Gateway)

**Unified Analytics:**
```sql
-- Complete request metrics (orchestrator + Gateway)
SELECT
    request_id,
    use_case_id,
    query,
    -- Orchestrator metrics (existing)
    (metadata->>'intent_type')::text as intent,
    (metadata->>'total_tokens')::int as orchestrator_tokens,
    -- Gateway metrics (new)
    (gateway_metrics->>'provider')::text as provider,
    (gateway_metrics->>'model')::text as model,
    (gateway_metrics->>'cost_eur')::numeric as gateway_cost,
    (gateway_metrics->>'provider_latency_ms')::int as provider_latency
FROM run_manifests
WHERE created_at > now() - interval '7 days';
```

### Why Batch Insert (Not Real-Time)?

**Performance Trade-Off:**
```
Real-Time Insert (bad):
  Every request → DB write → 10-20ms overhead
  500 req/min = 500 DB writes/min = CPU strain

Batch Insert (good):
  Every 10 requests OR 5 seconds → 1 DB write
  500 req/min = 50 DB writes/min = 80% reduction
  Max delay: 5 seconds (acceptable for analytics)
```

**Async Queue:**
- Requests don't wait for DB write (zero latency impact)
- Queue in-memory (fast)
- Periodic flush (efficient)

---

## Consequences

### Positive

✅ **Unified Visibility:** Single source of truth for all inference metrics
✅ **Cost Attribution:** Link costs to use cases, users, providers
✅ **Performance Monitoring:** Track latency, errors, capacity
✅ **Compliance:** Audit trail for all AI interactions (ADR-045 compliant)
✅ **Data-Driven Decisions:** Optimize based on actual usage, not guesses

### Negative

❌ **Storage Growth:** ~100KB/day/user = 300MB/month/100 users (manageable)
❌ **Query Complexity:** Join across 3 tables for complete metrics
❌ **Batch Delay:** Usage log has up to 5-second delay (analytics only)

### Mitigation

**Storage Growth:**
- Partition tables by month (automatic cleanup)
- Archive old data to S3/blob storage (PostgreSQL foreign tables)
- Retention policy: Logs 30 days, usage 12 months, run manifests 24+ months

**Query Complexity:**
- Create materialized views for common queries
- Pre-aggregate daily summaries (separate table)
- Admin UI widgets use optimized queries

**Batch Delay:**
- Not an issue (analytics, not real-time alerting)
- For real-time alerts, use structured logs (immediate)

---

## Acceptance Criteria

✅ **Logging:**
- All requests logged with full context (user, provider, model, tokens, cost)
- Prompts/responses redacted by default (ADR-045 compliance)
- Request ID propagated from orchestrator → Gateway → logs

✅ **Usage Database:**
- All requests persisted within 10 seconds (batch flush)
- Queries return results in <1 second (properly indexed)
- Storage growth <5MB/month/100 users

✅ **Run Manifest Integration:**
- `gateway_metrics` JSONB field populated for all use case executions
- Cost calculation matches pricing table within 1% accuracy
- Orchestrator can query Gateway cost per use case execution

✅ **Cost Calculation:**
- Uses existing `PricingHistoryService` (no duplicate logic)
- Pricing source attributed (pricing_history vs model_registry vs fallback)
- Cost returned in response headers (X-Gateway-Cost-Eur)

✅ **Analytics:**
- Admin UI shows real-time usage (last hour)
- Daily cost trend visible (last 30 days)
- Top consumers query returns results in <2 seconds

---

## References

### Related ADRs

- **ADR-030:** No Transcripts; Run Manifests Only (telemetry pattern)
- **ADR-045:** Secure Logging with Redaction (PII protection)
- **ADR-046:** Per-Model Pricing with History (cost calculation)
- **ADR-050:** Inference Gateway and Responsibility Split
- **ADR-053:** Rate Limiting and Usage Tracking (usage log table)

### Existing Code

- `src/shared/logging_utils/fastapi.py` - Structured logging
- `src/orchestrator/app/db/models.py` - `run_manifests` table
- `src/orchestrator/app/services/pricing_history_service.py` - Cost calculation
- `src/orchestrator/app/utils/cost_estimator.py` - Pricing lookups

### External References

- Prometheus Best Practices: https://prometheus.io/docs/practices/naming/
- PostgreSQL Partitioning: https://www.postgresql.org/docs/current/ddl-partitioning.html
- OpenTelemetry: https://opentelemetry.io/docs/

---

**Document Owner:** Operations Team
**Last Updated:** 2025-11-02
**Status:** Approved for Implementation
