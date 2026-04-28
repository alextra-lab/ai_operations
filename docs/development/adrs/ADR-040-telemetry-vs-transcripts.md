# ADR-004: Telemetry Without Transcripts (Run Manifests)

**Status:** Accepted
**Date:** 2025-10-24
**Related:** ADR-030 in docs/development/adrs/
**Deciders:** Privacy Team, Database Team, Product Team

## Context

AI Operations Platform needs to track:
- **Performance metrics** - Latency, token usage, conformance scores
- **Quality metrics** - Schema validity, idempotence, tool chain usage
- **Cost tracking** - LLM API costs, resource consumption
- **Debugging** - Execution traces for troubleshooting

**Privacy Constraints:**
- GDPR/CCPA compliance requires PII protection
- Air-gapped deployments cannot send data externally
- Customers may prohibit storing conversation content
- Security-sensitive queries must not leak

## Decision

We will implement **stateless telemetry** using the `run_manifests` table, which stores **performance metrics WITHOUT conversation content (no transcripts)**.

**What is stored:**
- ✅ Performance metrics (latency, tokens)
- ✅ Quality scores (conformance, schema validity)
- ✅ Execution metadata (model, template, tools used)
- ✅ Result classification (success/error/policy_block)

**What is NOT stored:**
- ❌ User queries (no PII)
- ❌ LLM responses (no generated content)
- ❌ Retrieved chunks (no document content)
- ❌ User identifiers (no user_id)

## Rationale

### Why Separate Query History from Telemetry

**Query History (`query_history` table):**
- Purpose: User features (search history, conversation threading)
- Contains: Full query text, responses, sources
- Privacy: User-specific, RLS-protected
- Retention: User-controlled, can be deleted

**Telemetry (`run_manifests` table):**
- Purpose: System monitoring, quality metrics
- Contains: Performance data, no content
- Privacy: PII-free, aggregatable
- Retention: Long-term, analytics-safe

### Advantages

1. **Privacy Compliance**
   - No PII in telemetry (GDPR-safe)
   - Can aggregate without anonymization
   - Safe to export for analysis
   - Customers comfortable with performance data

2. **Air-Gapped Friendly**
   - Telemetry doesn't leak secrets
   - Can be exported for external analysis
   - No content to sanitize

3. **Long-Term Analytics**
   - Query history can be deleted (user request)
   - Telemetry can be retained indefinitely
   - Performance trends over time
   - A/B testing without privacy concerns

4. **Cost Optimization**
   - Smaller table size (no large text columns)
   - Faster aggregations
   - Efficient time-series queries

5. **Security**
   - Analyst queries don't leak in telemetry
   - Security investigations invisible in metrics
   - Compliance with zero-trust architecture

### Trade-Offs

1. **Debugging Limitations**
   - Can't see what query caused an issue
   - Must correlate run_id with query_history
   - **Mitigation:** run_id links to query_history for debugging

2. **No Conversation Replay**
   - Can't reconstruct full conversation from telemetry
   - **Mitigation:** query_history stores conversations separately

3. **Limited Contextual Understanding**
   - Metrics don't explain WHY execution failed
   - **Mitigation:** result_kind and tool_chain provide hints

## Schema Design

```sql
CREATE TABLE run_manifests (
    run_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ts_utc          TIMESTAMPTZ NOT NULL DEFAULT now(),
    use_case_id     TEXT NOT NULL,
    template_ver    TEXT NOT NULL,
    model_name      TEXT NOT NULL,
    model_version   TEXT NOT NULL,
    params_hash     TEXT NOT NULL,           -- Hash of generation params
    schema_valid    BOOLEAN NOT NULL,
    conformance     NUMERIC(4,3) NOT NULL,   -- 0.0 to 1.0
    tool_chain      TEXT[] NOT NULL,
    idempotence_ok  BOOLEAN NOT NULL,
    latency_total_ms INTEGER NOT NULL,
    latency_llm_ms    INTEGER NOT NULL,
    latency_tools_ms  INTEGER NOT NULL,
    tokens_in       INTEGER NOT NULL,
    tokens_out      INTEGER NOT NULL,
    result_kind     TEXT NOT NULL,           -- success/contract_violation/policy_block/error
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),

    CHECK (conformance >= 0 AND conformance <= 1),
    CHECK (result_kind IN ('success','contract_violation','policy_block','error'))
);

-- Indexes for time-series analytics
CREATE INDEX idx_run_manifests_use_case ON run_manifests (use_case_id, ts_utc DESC);
CREATE INDEX idx_run_manifests_result ON run_manifests (result_kind, ts_utc DESC);
CREATE INDEX idx_run_manifests_conformance ON run_manifests (conformance DESC);
```

## Correlation Strategy

When debugging is needed, correlate via `run_id`:

```sql
-- Get performance metrics
SELECT * FROM run_manifests WHERE run_id = 'xxx';

-- Correlate with query details (if user has access)
SELECT * FROM query_history WHERE run_id = 'xxx';

-- User has RLS access to query_history
-- But run_manifests contains no PII regardless
```

## Alternatives Considered

### 1. Combined Table (Rejected)

**Example:**
```sql
CREATE TABLE query_executions (
    id UUID PRIMARY KEY,
    user_id UUID,              -- PII
    query_text TEXT,           -- PII
    response_text TEXT,        -- PII
    latency_ms INTEGER,        -- Telemetry
    tokens_used INTEGER,       -- Telemetry
    conformance FLOAT          -- Telemetry
);
```

**Rejected because:**
- Mixes PII with non-PII (GDPR complication)
- Can't export metrics without sanitization
- Retention policies complex (delete content, keep metrics?)
- RLS required for all queries (performance impact)

### 2. Anonymized Queries (Rejected)

**Example:**
```sql
CREATE TABLE telemetry (
    id UUID PRIMARY KEY,
    query_hash VARCHAR,         -- SHA-256 of query
    response_hash VARCHAR,      -- SHA-256 of response
    metrics JSONB               -- Performance data
);
```

**Rejected because:**
- Hashes can be reversed (rainbow tables)
- Still contains user behavior patterns
- Doesn't address PII in query text
- Complex to implement correctly

### 3. Sampling (Considered, Deferred)

**Keep only 1% of queries for debugging:**
- **Pros:** Reduces storage, limits PII exposure
- **Cons:** Miss rare events, incomplete metrics
- **Decision:** Implement telemetry for 100%, sample query_history if needed

## Implementation Guidelines

### 1. Always Write Both (When Needed)

```python
# Write telemetry (PII-free)
await db.execute("""
    INSERT INTO run_manifests (
        run_id, use_case_id, template_ver, model_name, model_version,
        params_hash, schema_valid, conformance, tool_chain,
        idempotence_ok, latency_total_ms, latency_llm_ms, latency_tools_ms,
        tokens_in, tokens_out, result_kind
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
""", run_id, ...)

# Write query history (user-facing, contains PII)
await db.execute("""
    INSERT INTO query_history (
        run_id, user_id, use_case_id, query_text, response_text,
        metrics, execution_time_ms
    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
""", run_id, user_id, ...)
```

### 2. Analytics Use Telemetry

```sql
-- Performance trends (PII-free)
SELECT
    date_trunc('day', ts_utc) AS day,
    use_case_id,
    AVG(latency_total_ms) AS avg_latency,
    AVG(conformance) AS avg_conformance,
    COUNT(*) AS executions
FROM run_manifests
WHERE ts_utc >= NOW() - INTERVAL '30 days'
GROUP BY day, use_case_id
ORDER BY day DESC;
```

### 3. Debugging Uses Correlation

```sql
-- Find failing runs
SELECT run_id, use_case_id, result_kind, latency_total_ms
FROM run_manifests
WHERE result_kind = 'error'
  AND ts_utc >= NOW() - INTERVAL '1 hour'
ORDER BY ts_utc DESC;

-- Investigate specific run (if you have access)
SELECT * FROM query_history WHERE run_id = 'failing-run-uuid';
```

## Data Retention

**run_manifests:**
- Retention: 1 year (or indefinite for aggregates)
- Deletion: Never (contains no PII)
- Aggregation: Monthly rollups for long-term trends

**query_history:**
- Retention: 90 days (configurable per deployment)
- Deletion: User can request deletion (GDPR right to be forgotten)
- Archival: Can be exported/deleted independently

## Privacy Guarantees

**What run_manifests CANNOT reveal:**
1. ❌ Who asked the question (no user_id)
2. ❌ What was asked (no query_text)
3. ❌ What was answered (no response_text)
4. ❌ What documents were retrieved (no chunk_ids)
5. ❌ Session context (no thread_id)

**What run_manifests CAN reveal:**
1. ✅ System is performing well
2. ✅ Model A is faster than Model B
3. ✅ Use case X has high conformance
4. ✅ Certain tools are frequently used
5. ✅ API costs are within budget

## Monitoring and Alerts

**Metrics from run_manifests:**
- P50/P95/P99 latency per use case
- Conformance score trends
- Error rate by result_kind
- Token consumption rate
- Tool chain usage patterns

**Alerts:**
- Latency spike: AVG(latency_total_ms) > 5000
- Low conformance: AVG(conformance) < 0.8
- High error rate: COUNT(result_kind='error') / COUNT(*) > 0.05
- Token budget: SUM(tokens_in + tokens_out) > threshold

## References

- GDPR Article 4 (Definition of Personal Data)
- CCPA Definition of Personal Information
- [PostgreSQL Time-Series Best Practices](https://www.timescale.com/blog/time-series-data-postgresql/)
- Internal: ADR-030 (No Transcripts; Run Manifests Only)

## Revision History

- 2025-10-24: Initial decision (PII-free telemetry in run_manifests)
