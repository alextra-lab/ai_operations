# ADR-030: No Transcripts; Run Manifests Only

**Status:** Accepted
**Date:** 2025-10-22
**Deciders:** Architecture Team
**Tags:** stateless, security, telemetry, architecture

---

## Context

**What is the issue we're addressing?**

The current system stores conversation transcripts server-side, creating security and compliance concerns:

- **Security Risk:** Server-side conversation storage creates attack surface for data exfiltration
- **Compliance Burden:** Stored conversations require encryption, audit trails, and data retention policies
- **Privacy Concerns:** PII in conversations stored on server violates air-gapped deployment principles
- **Operational Complexity:** Conversation history management adds significant backend complexity

**Forces at play:**
- Enterprise security requirements for air-gapped SOC environments
- Need for telemetry and quality metrics without storing sensitive conversation data
- Requirement for repeatability and debugging capabilities
- Stateless architecture pivot to reduce security scope

---

## Decision

**What did we decide?**

**For Stateless Core v1, eliminate server-side conversation storage and replace with run manifests:**

- **No Transcripts:** Server never stores conversation history or user messages
- **Run Manifests Only:** Store PII-free telemetry data for quality metrics and debugging
- **Client-Owned History:** Conversation history lives on client edge with TTL-based expiration
- **Export Capability:** Users can export conversations as Markdown/JSON for their own records

**Key Implementation Details:**
- Run manifests contain: use_case_id, model_params, latency, token counts, conformance scores, result_kind
- No user messages, responses, or conversation content stored server-side
- Client manages session history with configurable TTL (default: 24 hours)
- Export functionality generates Markdown/JSON from client-side session data

---

## Alternatives Considered

### Option 1: Encrypted Server-Side Storage
**Description:** Store conversations encrypted with enterprise key management
**Pros:**
- Centralized conversation history
- Advanced search across conversations
- Audit trail capabilities

**Cons:**
- High security complexity (encryption, key management, HSM integration)
- Compliance burden (data retention, audit trails, access controls)
- Attack surface for data exfiltration
- Violates air-gapped deployment principles

**Why Rejected:** Security and compliance overhead too high for v1 delivery

### Option 2: Hybrid Approach
**Description:** Store metadata server-side, content client-side
**Pros:**
- Reduced server storage
- Some centralized capabilities

**Cons:**
- Still requires encryption for metadata
- Complex data synchronization
- Partial security benefits

**Why Rejected:** Adds complexity without eliminating core security concerns

### Option 3: No Telemetry (Current)
**Description:** No server-side storage of any conversation data
**Pros:**
- Maximum security
- Simplest implementation

**Cons:**
- No quality metrics or debugging capabilities
- No repeatability for use case validation
- Difficult to optimize system performance

**Why Rejected:** Need telemetry for system improvement and use case validation

---

## Consequences

### Positive Consequences

**Benefits of this decision:**
- **Eliminated Security Scope:** No conversation storage = no encryption/audit requirements
- **Air-Gapped Ready:** No server-side PII storage aligns with SOC requirements
- **Reduced Complexity:** 80% reduction in security feature scope
- **Quality Metrics:** Run manifests provide repeatability and performance data
- **User Control:** Client-owned history with export capabilities
- **Future-Proof:** Clean architecture for optional stateful add-on (v2+)

### Negative Consequences

**Tradeoffs and costs:**
- **No Server-Side Search:** Cannot search across user conversations
- **Limited Analytics:** No cross-user conversation analytics
- **Client Dependency:** History lost if client data cleared
- **Export Overhead:** Users must manually export important conversations

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Lost conversation history | Medium | Clear TTL warnings, export reminders, backup guidance |
| Limited debugging | Low | Run manifests provide sufficient telemetry for debugging |
| User adoption resistance | Low | Export functionality maintains user control |

---

## Implementation Notes

**Key implementation details:**

**Database Schema:**
```sql
CREATE TABLE run_manifests (
  run_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ts_utc          TIMESTAMPTZ NOT NULL DEFAULT now(),
  use_case_id     TEXT NOT NULL,
  template_ver    TEXT NOT NULL,
  model_name      TEXT NOT NULL,
  model_version   TEXT NOT NULL,
  params_hash     TEXT NOT NULL,
  schema_valid    BOOLEAN NOT NULL,
  conformance     NUMERIC(4,3) NOT NULL,
  tool_chain      TEXT[] NOT NULL,
  idempotence_ok  BOOLEAN NOT NULL,
  latency_total_ms INTEGER NOT NULL,
  latency_llm_ms    INTEGER NOT NULL,
  latency_tools_ms  INTEGER NOT NULL,
  tokens_in       INTEGER NOT NULL,
  tokens_out      INTEGER NOT NULL,
  result_kind     TEXT NOT NULL CHECK (result_kind IN ('success','contract_violation','policy_block','error'))
);
```

**Files affected:**
- `ops/migrations/sql/010_run_manifests.sql`
- `src/orchestrator/app/schemas/run_manifest.py`
- `src/orchestrator/app/services/run_manifest_service.py`
- Frontend session management components

**Migration steps:**
1. Create run_manifests table
2. Implement run manifest writer service
3. Update orchestrator to capture telemetry
4. Remove conversation storage endpoints
5. Add client-side session management

**Testing strategy:**
- Unit tests for run manifest creation
- Integration tests for telemetry capture
- E2E tests for client session management
- Performance tests for manifest writing overhead

---

## References

- [Stateless Core v1 Implementation Plan](../plans/STATELESS_CORE_V1_IMPLEMENTATION_PLAN.md)
- [ADR-031: Client-Owned Exports & Summary Generation](ADR-031-Client-Owned-Exports.md)
- [ADR-033: Provider Interfaces for History/Evidence/Crypto](ADR-033-Provider-Interfaces.md)

---

## Enforcement Mechanism (Added November 2025)

### Background

During P5-A13 analysis (November 28, 2025), it was discovered that frontend code was **directly calling** `/api/v1/query-history` endpoints to store PII (query_text, response_text), bypassing the stateless architecture. This violated the core principle of ADR-030.

### Enforcement Design

**Principle:** Defense in depth - the backend enforces the policy regardless of client behavior.

**Implementation:**

1. **Feature Flag:** `ENABLE_TRANSCRIPT_STORAGE` environment variable
   - Default: `false` (Core Edition - stateless)
   - Set to `true` for Plus Edition v2+ (future stateful deployments)

2. **API Guards:** All write endpoints for query history return `501 Not Implemented` when flag is `false`

3. **Audit Logging:** Blocked PII storage attempts are logged for security monitoring

### Protected Endpoints

| Endpoint | Method | Status (Core Edition) |
|----------|--------|----------------------|
| `/api/v1/query-history` | POST | 501 Not Implemented |
| `/api/v1/query-history/{id}` | PATCH | 501 Not Implemented |
| `/api/v1/query-history/{id}` | DELETE | 501 Not Implemented |
| `/api/v1/query-history/fork` | POST | 501 Not Implemented |
| `/api/v1/query-history/threads` | POST | 501 Not Implemented |
| `/api/v1/query-history/threads/{id}` | PATCH | 501 Not Implemented |
| `/api/v1/query-history/threads/{id}` | DELETE | 501 Not Implemented |

### Allowed Endpoints (Read-Only)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/query-history` | GET | Admin analytics (returns empty in Core) |
| `/api/v1/query-history/{id}` | GET | Admin lookup |

### Correct Architecture (Enforced)

```
Client → POST /api/v1/process
           ↓
     Orchestrator Pipeline
           ↓
     RecordHistory Step (NO-OP in Core Edition)
           ↓
     run_manifests table (PII-FREE telemetry only)
           ↓
     Response to Client

⛔ POST /api/v1/query-history → 501 Not Implemented
```

### Re-enabling Transcript Storage (Plus Edition)

To enable full history storage for Plus Edition deployments:

```bash
# In deployment environment
ENABLE_TRANSCRIPT_STORAGE=true
```

This enables:
- Write endpoints accept PII data
- RecordHistory pipeline step is activated
- Full conversation history stored server-side
- Requires encryption and audit compliance (ADR-033)

---

## Status Updates

### 2025-11-28 - Enforcement Added
**Changed By:** Architecture Team
**Reason:** Discovered frontend bypassing stateless architecture; added API-level enforcement

**Task Reference:** P5-SEC-01 Stateless PII Enforcement

### 2025-10-22 - Accepted
**Changed By:** Architecture Team
**Reason:** Strategic pivot to stateless architecture for accelerated v1 delivery

---

**Template Version:** 1.1
**Based On:** [Michael Nygard's ADR pattern](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
