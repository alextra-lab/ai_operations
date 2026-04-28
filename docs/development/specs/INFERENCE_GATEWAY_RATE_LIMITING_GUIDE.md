# Inference Gateway Rate Limiting Guide

**Version:** 1.0
**Date:** 2025-11-02
**Status:** Reference Guide
**Related:** ADR-053 (Rate Limiting and Usage Tracking)

---

## Overview

This guide explains **who/what gets rate limited**, **how to configure limits**, and **how users experience rate limiting** in the Inference Gateway.

**Key Principle:** Rate limiting is for **protection, not punishment** at department scale (10-100 users).

---

## Who/What Gets Limited?

### 1. System-Wide (Global Limits)

**Purpose:** Protect Gateway infrastructure from overload

**What's Limited:** Total requests across ALL users and services

**Configuration:**
```bash
RATE_LIMIT_GLOBAL_RPM=500  # 500 requests/minute total capacity
```

**When It Triggers:**
```
Normal load:     50-200 requests/minute → No limiting
Peak load:       400 requests/minute → No limiting
Overload:        550 requests/minute → 50 requests rejected (429)
```

**User Experience:**
- First 500 requests/min: ✅ Pass through
- Request 501-550: ❌ HTTP 429 "System busy, retry in Ns"
- Frontend auto-retries after N seconds
- Impact: Temporary slowdown, not complete failure

---

### 2. Per-Provider Limits

**Purpose:** Stay under upstream provider limits (don't get blocked by OpenAI/Mistral)

**What's Limited:** Requests to specific provider (OpenAI, Mistral, etc.)

**Configuration:**
```bash
RATE_LIMIT_OPENAI_RPM=450    # OpenAI limit: 500/min, use 450 (10% buffer)
RATE_LIMIT_OPENAI_TPM=150000 # OpenAI limit: 200K tokens/min, use 150K (25% buffer)

RATE_LIMIT_MISTRAL_RPM=180   # Mistral limit: 200/min, use 180 (10% buffer)
RATE_LIMIT_MISTRAL_TPM=90000 # Mistral limit: 100K tokens/min, use 90K (10% buffer)
```

**Why Buffer:**
```
Without buffer (500/min limit):
  Gateway sends 500 requests/min
  Network delays → some arrive in next minute
  OpenAI sees 505 requests/min → blocks you for 5 minutes ❌

With buffer (450/min limit):
  Gateway sends 450 requests/min
  Network delays → OpenAI sees 455 requests/min
  Still under 500 limit → No blocking ✅
```

**When It Triggers:**
```
OpenAI usage:
  Minute 1: 200 requests → OK (under 450 limit)
  Minute 2: 500 requests → 50 rejected (over 450 limit)

Error response:
  HTTP 429 Too Many Requests
  Retry-After: 30
  Message: "Provider OpenAI rate limit exceeded, retry in 30s"
```

---

### 3. Per-Integration Limits (Service Accounts)

**Purpose:** Prevent runaway automation (SOAR scripts, ServiceNow integrations)

**What's Limited:** Requests from service accounts (not human users)

**Configuration:**
```bash
RATE_LIMIT_SERVICE_ACCOUNT_RPM=100  # Default for all service accounts
```

**Database Config (Optional):**
```sql
INSERT INTO gateway_rate_limits (limit_type, identifier, requests_per_minute)
VALUES
  ('integration', 'service:cortex-prod', 100),     -- SOAR
  ('integration', 'service:servicenow', 50),       -- ITSM
  ('integration', 'service:splunk-soar', 150);     -- High-volume SOAR
```

**How It's Identified:**
```python
# Service account JWT token
{
    "sub": "service:cortex-prod",  # Identifies service account
    "role": "service",
    "scopes": ["inference:chat"]
}

# Gateway checks:
limit_key = f"service:{token.sub}"
if requests_this_minute > 100:
    raise HTTP 429
```

**Example Scenario:**
```
SOAR Integration (Cortex):
  Normal: 20-40 requests/minute → No limiting
  Misconfiguration: 200 requests/minute → 100 rejected
  Impact: SOAR slowed, but human analysts unaffected ✅
```

---

### 4. NOT Limited (Important)

**Individual Users:**
- ❌ No per-user limits (everyone on same team)
- ✅ Usage tracked for analysis (identify noisy neighbors)
- ✅ Talk to user if outlier (don't block them)

**Example:**
```
analyst_john makes 100 requests/hour (normal: 20/hour)
Action: Check with John - "Are you testing something? Need help?"
NOT: Block John with rate limit
```

---

## Configuration Methods

### Phase 1: Environment Variables (Simple)

**File:** `.env` or docker-compose environment

```bash
# Enable/disable rate limiting
RATE_LIMIT_ENABLED=true  # false = tracking only, true = enforcement

# Global limits
RATE_LIMIT_GLOBAL_RPM=500
RATE_LIMIT_GLOBAL_BURST=50  # Allow short spikes

# Provider limits
RATE_LIMIT_OPENAI_RPM=450
RATE_LIMIT_OPENAI_TPM=150000

RATE_LIMIT_MISTRAL_RPM=180
RATE_LIMIT_MISTRAL_TPM=90000

# Service account limits
RATE_LIMIT_SERVICE_ACCOUNT_RPM=100
```

**Pros:** Simple, no UI needed
**Cons:** Restart required to change

---

### Phase 2: Database Configuration (Flexible)

**Table:** `gateway_rate_limits`

```sql
CREATE TABLE gateway_rate_limits (
    id UUID PRIMARY KEY,
    limit_type TEXT NOT NULL,  -- 'global', 'provider', 'integration'
    identifier TEXT,           -- NULL for global, 'openai' for provider
    requests_per_minute INTEGER NOT NULL,
    tokens_per_minute BIGINT,
    burst_size INTEGER DEFAULT 10,
    enabled BOOLEAN DEFAULT true,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Seed default limits
INSERT INTO gateway_rate_limits VALUES
  (gen_random_uuid(), 'global', NULL, 500, NULL, 50, true),
  (gen_random_uuid(), 'provider', 'openai', 450, 150000, 20, true),
  (gen_random_uuid(), 'provider', 'mistral', 180, 90000, 10, true),
  (gen_random_uuid(), 'integration', 'service:cortex-prod', 100, NULL, 10, true);
```

**Admin UI:**
```typescript
// Update limits via UI (no restart needed)
updateRateLimit({
  type: 'provider',
  identifier: 'openai',
  requestsPerMinute: 400  // Reduced during peak hours
})

// Gateway reloads config within 60 seconds
```

**Pros:** Dynamic updates, no restart
**Cons:** More complex

---

## User Experience

### When NOT Rate Limited (Normal Flow)

```
1. Analyst clicks "Execute Use Case"
2. Request flows through Gateway
3. Provider responds
4. Result displayed
5. Zero indication of rate limiting (transparent)
```

---

### When Rate Limited (Graceful Degradation)

**Frontend (Angular):**
```typescript
// Auto-retry with exponential backoff
async executeUseCase(useCaseId: string, inputs: any) {
  try {
    return await this.api.post('/v1/chat/completions', ...);
  } catch (error) {
    if (error.status === 429) {
      // Extract retry_after from headers
      const retryAfter = parseInt(error.headers.get('Retry-After') || '30');

      // Show user-friendly message
      this.showMessage(
        `System busy. Retrying in ${retryAfter} seconds...`,
        'warning'
      );

      // Wait and retry
      await this.delay(retryAfter * 1000);
      return await this.api.post('/v1/chat/completions', ...);
    }
    throw error;
  }
}
```

**UI Display:**
```
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
```

**SOAR Integration (API):**
```python
# SOAR script with retry logic
import time

def call_gateway(prompt):
    response = requests.post(
        "http://inference-gateway:8002/v1/chat/completions",
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}]},
        headers={"Authorization": f"Bearer {service_token}"}
    )

    if response.status_code == 429:
        # Get retry_after from header
        retry_after = int(response.headers.get("Retry-After", 30))

        logger.warning(f"Rate limited, retrying in {retry_after}s")
        time.sleep(retry_after)

        # Retry once
        response = requests.post(...)

    return response.json()
```

**Error Response:**
```json
{
    "error": {
        "type": "rate_limit_error",
        "message": "Provider OpenAI rate limit exceeded",
        "code": "provider_rate_limit",
        "provider": "openai",
        "retry_after": 30,
        "current_usage": 451,
        "limit": 450,
        "suggestion": "Retry in 30 seconds or use local model",
        "request_id": "abc-123-def-456"
    }
}
```

**HTTP Headers:**
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 30
X-RateLimit-Limit: 450
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1730559030
Content-Type: application/json
```

---

## Monitoring & Alerts

### Metrics Dashboard

**Admin UI Widgets:**

```
┌─────────────────────────────────────┐
│ Rate Limit Status (Real-Time)       │
├─────────────────────────────────────┤
│ Global:    234/500 requests/min     │
│            ████████░░░░░░ 46.8%     │
│                                     │
│ OpenAI:    312/450 requests/min     │
│            █████████████░ 69.3%     │
│                                     │
│ Mistral:   45/180 requests/min      │
│            ████░░░░░░░░░░ 25.0%     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Rate Limit Events (Last Hour)       │
├─────────────────────────────────────┤
│ Total Requests:      12,450         │
│ Rejected (429):      23 (0.18%)     │
│                                     │
│ By Limit Type:                      │
│   Global:            3              │
│   OpenAI Provider:   15             │
│   SOAR Integration:  5              │
└─────────────────────────────────────┘
```

### SQL Queries

**Rate Limit Events:**
```sql
-- Count rejections by limit type (last 24 hours)
SELECT
    CASE
        WHEN error_type = 'rate_limit_error' THEN 'Rate Limited'
        ELSE 'Success'
    END as status,
    COUNT(*) as count,
    ROUND(AVG(latency_ms)) as avg_latency_ms
FROM gateway_usage_log
WHERE timestamp > now() - interval '24 hours'
GROUP BY
    CASE
        WHEN error_type = 'rate_limit_error' THEN 'Rate Limited'
        ELSE 'Success'
    END;
```

**Rejection Rate by Provider:**
```sql
SELECT
    provider,
    COUNT(*) as total_requests,
    COUNT(CASE WHEN status_code = 429 THEN 1 END) as rejections,
    ROUND(
        COUNT(CASE WHEN status_code = 429 THEN 1 END)::numeric / COUNT(*)::numeric * 100,
        2
    ) as rejection_rate_percent
FROM gateway_usage_log
WHERE timestamp > now() - interval '1 hour'
GROUP BY provider
ORDER BY rejection_rate_percent DESC;
```

### Alerts

**Critical (PagerDuty/Email):**
```yaml
rate_limit_high_rejection:
  condition: rejection_rate > 5% for 5 minutes
  severity: critical
  action: page_on_call
  message: "Gateway rejecting >5% of requests, limits too low"
```

**Warning (Slack):**
```yaml
provider_limit_approaching:
  condition: (current_usage / limit) > 0.9
  severity: warning
  action: slack_notification
  message: "Provider {{provider}} at 90% of rate limit"
```

---

## Tuning Guide

### Step 1: Start Conservative (Week 1)

```bash
# Set limits high (minimal rejections)
RATE_LIMIT_GLOBAL_RPM=500   # Plenty of headroom
RATE_LIMIT_OPENAI_RPM=450   # Under provider limit
RATE_LIMIT_ENABLED=true     # Enable enforcement

# Monitor for 1 week
```

### Step 2: Measure Actual Usage (Week 2)

```sql
-- Query peak usage
SELECT
    DATE_TRUNC('hour', timestamp) as hour,
    provider,
    COUNT(*) as requests,
    MAX(COUNT(*)) OVER (PARTITION BY provider) as peak_requests
FROM gateway_usage_log
WHERE timestamp > now() - interval '7 days'
GROUP BY DATE_TRUNC('hour', timestamp), provider
ORDER BY requests DESC
LIMIT 20;

-- Example results:
-- hour               | provider | requests | peak_requests
-- 2025-11-01 14:00   | openai   | 380      | 380
-- 2025-11-01 10:00   | openai   | 310      | 380
```

### Step 3: Adjust Limits (Week 3)

**If rejection rate <0.1%:**
```bash
# Limits are good, no change needed
RATE_LIMIT_OPENAI_RPM=450  # Keep as is
```

**If rejection rate >5%:**
```bash
# Limits too low, increase
RATE_LIMIT_OPENAI_RPM=450  # Before
RATE_LIMIT_OPENAI_RPM=600  # After (increase 33%)

# Or upgrade provider tier (OpenAI Tier 2 = 5,000 RPM)
```

**If specific integration problematic:**
```sql
-- Add per-integration limit
INSERT INTO gateway_rate_limits VALUES
  (gen_random_uuid(), 'integration', 'service:cortex-prod', 50, NULL, 10, true);
  -- Reduced from 100 to 50 (SOAR causing issues)
```

---

## Troubleshooting

### Issue: Users Complaining of Slowness

**Symptom:** "System is slow" reports from analysts

**Check:**
```sql
-- Query rejection rate
SELECT
    COUNT(CASE WHEN status_code = 429 THEN 1 END) as rejections,
    COUNT(*) as total_requests,
    ROUND(COUNT(CASE WHEN status_code = 429 THEN 1 END)::numeric / COUNT(*)::numeric * 100, 2) as rejection_rate
FROM gateway_usage_log
WHERE timestamp > now() - interval '1 hour';
```

**If rejection_rate > 1%:**
- Limits too low, increase or optimize use cases
- Check for runaway automation (service accounts)

**If rejection_rate < 0.1%:**
- Not a rate limiting issue
- Check provider latency, network issues

---

### Issue: Provider Blocking Us

**Symptom:** OpenAI returns 429 even though Gateway limit not reached

**Root Cause:** Buffer too small, network delays causing spillover

**Fix:**
```bash
# Increase buffer
RATE_LIMIT_OPENAI_RPM=450  # Before (10% buffer)
RATE_LIMIT_OPENAI_RPM=400  # After (20% buffer)

# More conservative = safer
```

---

### Issue: SOAR Integration Failing

**Symptom:** SOAR automation reports failures

**Check:**
```sql
-- Query service account usage
SELECT
    service_id,
    COUNT(*) as requests,
    COUNT(CASE WHEN status_code = 429 THEN 1 END) as rejections
FROM gateway_usage_log
WHERE timestamp > now() - interval '1 hour'
  AND service_id IS NOT NULL
GROUP BY service_id
ORDER BY rejections DESC;
```

**If SOAR rejected:**
- Increase service account limit (100 → 150 RPM)
- Or optimize SOAR workflow (batch requests)

---

## Best Practices

### 1. Start with Tracking Only

```bash
# Phase 1: Measure before enforcing
RATE_LIMIT_ENABLED=false  # Track usage, don't reject
```

**Run for 30 days, then:**
- Analyze usage patterns
- Set limits based on data
- Enable enforcement

### 2. Use Generous Buffers

```
Provider limit: 500 RPM
Gateway limit:  400 RPM (20% buffer)  ✅ Safe
Gateway limit:  495 RPM (1% buffer)   ❌ Risky
```

### 3. Monitor Rejection Rate

```
Healthy:  <0.5% rejections
Warning:  0.5-2% rejections (tune limits)
Critical: >5% rejections (limits too low)
```

### 4. Separate Service Accounts

```sql
-- Don't let SOAR consume all capacity
INSERT INTO gateway_rate_limits VALUES
  ('integration', 'service:cortex-prod', 100, ...);  -- Cap SOAR
```

### 5. Communicate Changes

```
Before changing limits:
  1. Announce in team Slack channel
  2. Explain why (cost savings, stability, etc.)
  3. Set limits during low-traffic hours
  4. Monitor for 24 hours
  5. Rollback if issues
```

---

## Quick Reference

### Environment Variables

```bash
# Enable/disable
RATE_LIMIT_ENABLED=false  # or true

# Global
RATE_LIMIT_GLOBAL_RPM=500

# Providers
RATE_LIMIT_OPENAI_RPM=450
RATE_LIMIT_MISTRAL_RPM=180

# Service accounts
RATE_LIMIT_SERVICE_ACCOUNT_RPM=100
```

### SQL Queries

```sql
-- Current usage (last minute)
SELECT provider, COUNT(*)
FROM gateway_usage_log
WHERE timestamp > now() - interval '1 minute'
GROUP BY provider;

-- Rejection rate (last hour)
SELECT
    COUNT(CASE WHEN status_code = 429 THEN 1 END)::float / COUNT(*) * 100 as rejection_rate_percent
FROM gateway_usage_log
WHERE timestamp > now() - interval '1 hour';

-- Top service accounts
SELECT service_id, COUNT(*) as requests
FROM gateway_usage_log
WHERE timestamp > now() - interval '1 hour'
  AND service_id IS NOT NULL
GROUP BY service_id
ORDER BY requests DESC;
```

---

**Document Owner:** Operations Team
**Last Updated:** 2025-11-02
**Status:** Reference Guide
