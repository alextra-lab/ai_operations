# ADR-048: Secure Logging with Configurable Redaction

**Status:** ✅ ACCEPTED
**Date:** 2025-10-25
**Deciders:** Security Team, Architecture Team
**Severity:** **CRITICAL SECURITY FIX**

---

## Context

The backend logging system was logging **sensitive data in plaintext**, including:
- User queries (incident details, IOCs, investigation notes)
- LLM responses (analysis, recommendations, sensitive findings)
- Session IDs (linkable to users/sessions)
- Full request/response bodies

**Security Issue:** For a SOC system handling classified/sensitive incident data, this constitutes a **data breach** through log aggregation systems.

**Compliance Risk:**
- Violates "no logging of sensitive data" policies
- Creates audit trail of classified information
- Log aggregation systems (Splunk, ELK) contain sensitive operational data
- Potential regulatory violations (GDPR, HIPAA, classification requirements)

---

## Decision

Implement **configurable log redaction** with environment-based control:

### **v1: Simple Configuration Flags**

```bash
# Environment Variables
REDACT_LOGS=true|false           # Enable/disable redaction
LOG_REDACTION_LEVEL=none|partial|full  # Granularity
```

### **Redaction Levels:**

| Level | Description | Use Case | Example |
|-------|-------------|----------|---------|
| **none** | No redaction (full logging) | Dev/Test | `"query": "What is a SOC?"` |
| **partial** | Redact content, keep metadata | Production (recommended) | `"query": "[REDACTED:15chars:hash=a3b4c5d6]"` |
| **full** | Redact everything except IDs | High security | `"query": "[REDACTED]"` |

### **Default Settings:**

```python
# Development/Test (env.test.template)
REDACT_LOGS=false
LOG_REDACTION_LEVEL=none

# Production (env.template)
REDACT_LOGS=true  # ← CRITICAL: Must be enabled
LOG_REDACTION_LEVEL=partial
```

---

## Implementation

### **1. Secure Logging Utility** (`src/orchestrator/app/utils/secure_logging.py`)

```python
# Functions provided:
redact_query(query: str) → str
redact_response(response: str) → str
redact_session_id(session_id: str) → str
redact_request_body(body: dict) → dict
get_redaction_status() → dict
```

### **2. Middleware Integration** (`src/orchestrator/app/middleware/sanitization.py`)

**Before (Security Breach):**
```python
logger.info(
    "Request sanitization",
    extra={
        "original": "{\"query\":\"Investigate alert #12345 for...\",  # ← BREACH!
        "sanitized": "..."
    }
)
```

**After (Secure):**
```python
# With REDACT_LOGS=true, LOG_REDACTION_LEVEL=partial:
logger.info(
    "Request sanitization",
    extra={
        "original": "{\"query\":\"[REDACTED:45chars:hash=a3b4c5d6]\",  # ← SAFE
        "sanitized": "...",
        "redaction_enabled": true,
        "redaction_level": "partial"
    }
)
```

### **3. Configuration Files Updated**

- ✅ `config/env/env.template` - Production defaults
- ✅ `config/env/env.test.template` - Test defaults
- ✅ `deploy/docker-compose.test.yml` - Test environment vars

---

## What Gets Redacted

### **Sensitive Fields (Always Redacted When REDACT_LOGS=true):**

- `query` - User queries/prompts
- `response` - LLM responses
- `content` - Message content
- `message` - Error/status messages with sensitive data
- `context` - Optional context data
- `session_id` - (Partial: shows prefix + hash)

### **Metadata (Never Redacted):**

- `request_id` - For tracing
- `user_id` - For audit
- `timestamp` - For timelines
- `status_code` - For monitoring
- `latency_ms` - For performance
- `path` - For routing
- `risk_score` - For security metrics

---

## Examples

### **Redaction Level: none** (Test/Dev)

```json
{
  "message": "Request sanitization",
  "original": "{\"query\":\"What IOCs are associated with alert #12345?\"}",
  "risk_score": 0.0,
  "redaction_enabled": false
}
```

### **Redaction Level: partial** (Production - Recommended)

```json
{
  "message": "Request sanitization",
  "original": "{\"query\":\"[REDACTED:48chars:hash=7f3a9b21]\"}",
  "risk_score": 0.0,
  "redaction_enabled": true,
  "redaction_level": "partial"
}
```

### **Redaction Level: full** (High Security)

```json
{
  "message": "Request sanitization",
  "original": "{\"query\":\"[REDACTED]\"}",
  "risk_score": 0.0,
  "redaction_enabled": true,
  "redaction_level": "full"
}
```

---

## Consequences

### Positive

✅ **Security:** Prevents sensitive data leakage through logs
✅ **Compliance:** Meets "no logging of sensitive data" requirements
✅ **Auditability:** Still provides hash-based correlation
✅ **Flexibility:** Can disable for debugging in dev/test
✅ **Performance:** Minimal overhead (~1-2% CPU for hashing)

### Negative

⚠️ **Debugging:** Harder to troubleshoot issues in production
⚠️ **Correlation:** Can't directly see query content in logs

### Mitigation

- **Hash-based correlation:** Use hash values to link related logs
- **Request IDs:** Full tracing without seeing content
- **Metrics:** Monitor risk_score, latency, error rates
- **Test environment:** Can disable redaction for debugging

---

## Operational Guidelines

### **Production Deployment Checklist:**

```bash
# Before deploying to production, verify:
✅ REDACT_LOGS=true in .env
✅ LOG_REDACTION_LEVEL=partial or full
✅ No .env committed to git
✅ Log aggregation system configured
✅ Verify redaction with: curl /health/logging
```

### **Troubleshooting in Production:**

```bash
# If you need to debug production issues:

# Option 1: Use request_id for tracing (no sensitive data needed)
grep "request_id=abc123" logs.json

# Option 2: Temporarily enable detailed logging (with approval)
# Set REDACT_LOGS=false, restart container, test, immediately revert

# Option 3: Use hash correlation
# Query hash: 7f3a9b21 appears in multiple log entries
```

### **Monitoring Redaction Status:**

```bash
# Check current redaction config
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8006/health/logging

Response:
{
  "redaction_enabled": true,
  "redaction_level": "partial",
  "status": "secure"
}
```

---

## Future Enhancements (v1.2)

### **Granular Field Control**

```yaml
# config/logging_policy.yaml
redaction:
  enabled: true
  level: partial

  always_redact:
    - query
    - response
    - password
    - api_key

  conditionally_redact:
    - session_id:
        condition: length > 20
        method: hash_prefix

  never_redact:
    - request_id
    - timestamp
    - user_id
```

### **Classification-Based Redaction**

```python
# Redact based on data classification
if classification >= "CONFIDENTIAL":
    redact_level = "full"
elif classification == "INTERNAL":
    redact_level = "partial"
else:
    redact_level = "none"
```

### **Audit Log Separation**

```python
# Separate audit trail (no sensitive content)
audit_logger.info({
    "request_id": "...",
    "user_id": "...",
    "action": "query_executed",
    "query_hash": "7f3a9b21",  # Hash only
    "timestamp": "..."
})

# Operational logs (with redaction)
app_logger.info({
    "request_id": "...",
    "query": "[REDACTED:...]"
})
```

---

## Security Properties

### **What's Protected:**

✅ **Log files** - No plaintext queries/responses
✅ **Log aggregation systems** - Redacted data
✅ **Centralized logging** - Hash-based correlation only
✅ **Compliance audits** - Meets "no sensitive logging" requirement

### **What's NOT Protected (By Design):**

⚠️ **In-memory processing** - LLM must see plaintext
⚠️ **HTTPS traffic** - TLS protects in transit
⚠️ **Database** - Run manifests are PII-free (ADR-030)
⚠️ **Ephemeral cache** - Encrypted (ADR-035)

---

## References

### Related ADRs
- **[ADR-030: Stateless Architecture](ADR-030-No-Transcripts-Run-Manifests.md)** - No server-side PII storage
- **[ADR-047: Ephemeral Cache Observability](ADR-047-Ephemeral-Cache-Observability.md)** - Cache metrics and monitoring
- **[ADR-049: Unified Authentication and Security Implementation](ADR-049-Unified-Authentication-Security-Implementation.md)** - Comprehensive audit logging implementation

### External Resources
- **OWASP Logging Cheat Sheet:** https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- **NIST SP 800-92:** Guide to Computer Security Log Management

---

## Validation

### **Test Redaction Working:**

```bash
# Set redaction enabled
export REDACT_LOGS=true
export LOG_REDACTION_LEVEL=partial

# Restart container
docker-compose restart orchestrator-api

# Send test query
curl -X POST /api/v1/process \
  -d '{"query": "Sensitive incident data"}'

# Check logs - should see:
"original": "{\"query\":\"[REDACTED:25chars:hash=...]\""  # ← Redacted ✅

# NOT:
"original": "{\"query\":\"Sensitive incident data\"}"  # ← BREACH ❌
```

---

**Decision:** All production deployments MUST have `REDACT_LOGS=true`. This is a **critical security requirement**, not optional.

**Rollout:** Immediate. This is a security fix, not a feature.
