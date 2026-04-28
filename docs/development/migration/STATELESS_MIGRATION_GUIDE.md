# Stateless Architecture Migration Guide

**Date:** October 25, 2025
**Status:** ✅ IMPLEMENTED
**ADRs:** ADR-030, ADR-031, ADR-033, ADR-043, ADR-044, ADR-045

---

## Executive Summary

AI Operations Platform has migrated to a **stateless architecture** where conversations are stored **client-side only** with TTL-based expiration. This eliminates 80% of security scope by removing server-side conversation storage, encryption requirements, and compliance burden.

### What Changed

| Aspect | Before (Stateful) | After (Stateless) |
|--------|------------------|-------------------|
| **Conversation Storage** | PostgreSQL server-side | IndexedDB client-side |
| **Retention** | Persistent until deleted | TTL-based (24hr default) |
| **Security Scope** | Encryption, key mgmt, audit trails | Minimal (run manifests only) |
| **Export** | Server-managed | Client-generated on-demand |
| **Summary** | Server-stored | Generated from client data |
| **Privacy** | PII stored server-side | Zero server-side PII |

---

## Architecture Overview

### Stateless Flow with Ephemeral Cache (v1.1+)

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT EDGE                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  IndexedDB (Browser Storage)                          │  │
│  │  • Full conversation history (TTL: 24 hours)          │  │
│  │  • Messages with metadata                             │  │
│  │  • Session context (for UI display)                   │  │
│  └───────────────────────────────────────────────────────┘  │
│                          ↕                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Angular Frontend                                     │  │
│  │  • SessionStorageService (manage history)             │  │
│  │  • Sends: query + session_id (not full history)       │  │
│  │  • Receives: response + cache_stats                   │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          ↕
            {query: "...", session_id: "session_abc123"}
                          ↕
┌─────────────────────────────────────────────────────────────┐
│                BACKEND (Stateless + Ephemeral Cache)         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  ConversationCache (In-Memory, Encrypted)             │  │
│  │  • AES-GCM-256 encrypted conversations                │  │
│  │  • Process-ephemeral master key                       │  │
│  │  • TTL: 24hr absolute + 15min idle                    │  │
│  │  • Model-aware token limits (from context_window)     │  │
│  │  • Lost on restart (by design)                        │  │
│  └───────────────────────────────────────────────────────┘  │
│                          ↕                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  FastAPI Backend                                      │  │
│  │  • Orchestrator: Loads history from cache             │  │
│  │  • LLM gets full context (multi-turn aware)           │  │
│  │  • Updates cache after response                       │  │
│  │  • Returns: response + cache_stats                    │  │
│  └───────────────────────────────────────────────────────┘  │
│                          ↕                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  PostgreSQL                                           │  │
│  │  • run_manifests (PII-free telemetry only)            │  │
│  │  • use_cases, users, collections (metadata)           │  │
│  │  • NO persistent conversation storage                 │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Key Difference from Pure Stateless:**

- **Client:** Still owns full history (IndexedDB)
- **Backend:** Ephemeral cache for LLM context (performance optimization)
- **Security:** Cache encrypted, lost on restart, no persistent storage

---

## Database Schema Changes

### Tables REMOVED from Active Use

These tables still exist but are **DEPRECATED** and will be removed in v2:

```sql
-- DEPRECATED: Server-side conversation storage
context_threads (
    ❌ Stores conversation metadata server-side
)

thread_messages (
    ❌ Stores message content server-side
)

query_history (
    ❌ Stores query/response text server-side
)
```

### Tables ADDED for Stateless

```sql
-- NEW: PII-free telemetry only
run_manifests (
    run_id UUID PRIMARY KEY,
    ts_utc TIMESTAMPTZ,
    use_case_id TEXT,
    model_name TEXT,
    conformance NUMERIC(4,3),
    latency_total_ms INTEGER,
    tokens_in INTEGER,
    tokens_out INTEGER,
    result_kind TEXT,
    -- ✅ NO user queries, responses, or conversation content
)
```

---

## API Changes

### NEW Stateless Endpoints

#### 1. Export Conversation (POST `/api/v1/stateless/export`)

```typescript
// Request (client provides conversation data)
{
  conversation_id: string;
  export_timestamp: string;
  use_case: { id: string, name: string };
  messages: Array<{ role, content, timestamp }>;
  session_metadata: Record<string, any>;
  format: "json" | "markdown";
}

// Response (generated on-demand, NOT stored)
{
  export_id: string;
  format: string;
  content: string;  // Full export content
}
```

#### 2. Generate Summary (POST `/api/v1/stateless/summary`)

```typescript
// Request (client provides messages)
{
  messages: Array<{ role, content }>;
  use_case_context: Record<string, any>;
  summary_type: "executive" | "technical" | "brief";
}

// Response (generated on-demand, NOT stored)
{
  summary: string;
  key_points: string[];
  recommendations: string[];
}
```

### DISABLED Endpoints (Core Edition)

**As of P5-SEC-01 (November 2025):** Write endpoints are **disabled** (return `501 Not Implemented`) in Core Edition to enforce ADR-030.

**Disabled Write Endpoints:**

| Endpoint | Method | Status |
|----------|--------|--------|
| `/api/v1/query-history` | POST | ⛔ 501 Not Implemented |
| `/api/v1/query-history/{id}` | PATCH | ⛔ 501 Not Implemented |
| `/api/v1/query-history/{id}` | DELETE | ⛔ 501 Not Implemented |
| `/api/v1/query-history/fork` | POST | ⛔ 501 Not Implemented |
| `/api/v1/query-history/threads` | POST | ⛔ 501 Not Implemented |
| `/api/v1/query-history/threads/{id}` | PATCH | ⛔ 501 Not Implemented |
| `/api/v1/query-history/threads/{id}` | DELETE | ⛔ 501 Not Implemented |

**Still Available (Read-Only):**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/query-history` | GET | Admin analytics |
| `/api/v1/query-history/{id}` | GET | Admin lookup |
| `/api/v1/query-history/threads` | GET | Admin thread listing |
| `/api/v1/query-history/threads/{id}` | GET | Admin thread lookup |

**To enable (Plus Edition):** Set `ENABLE_TRANSCRIPT_STORAGE=true` in environment.

**Migration Path:** Use client-side `SessionStorageService` for conversation history.

---

## Ephemeral Conversation Cache (v1.1+)

### Overview

For **performance**, the backend maintains an **encrypted, ephemeral cache** of conversation context. This enables multi-turn conversations without re-sending full history on each request.

**Key Properties:**

- ✅ **Encrypted:** AES-GCM-256 with process-ephemeral keys
- ✅ **Ephemeral:** Lost on container restart (by design)
- ✅ **Model-Aware:** Cache size = Model's `context_window` - `max_output_tokens` - overhead
- ✅ **Client-Owned:** Client generates and provides `session_id`
- ✅ **TTL-Based:** 24hr absolute + 15min idle timeout

### Using the Cache

**Send session_id with each request:**

```typescript
// Frontend sends session_id
POST /api/v1/process
{
  "query": "What are its main functions?",
  "session_id": "session_1234567890_abc",  // Client-owned ID
  "stream": true
}
```

**Backend automatically:**

1. Looks up session in cache
2. Loads conversation history (encrypted)
3. Passes full context to LLM
4. Updates cache with new turn
5. Returns response + cache utilization stats

**Response includes cache stats:**

```json
{
  "response": "...",
  "cache_stats": {
    "tokens_used": 1234,
    "max_tokens": 123404,
    "token_percentage": 1,
    "turn_count": 4,
    "will_compress": false,
    "ttl_remaining_seconds": 86100
  }
}
```

### Cache Capacity Calculation

**Formula:**

```
Cache Capacity = Model Context Window - Max Output Tokens - System Overhead
```

**Example (foundation-sec-8b-instruct-mlx):**

```
Context Window:   128,000 tokens (from model metadata)
Max Output:         4,096 tokens (user config)
System Overhead:      500 tokens
─────────────────────────────────
Cache Capacity:   123,404 tokens (~247 conversational turns)
```

### Monitoring Cache Usage

**Health endpoint:**

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8006/health/cache

Response:
{
  "status": "healthy",
  "stats": {
    "total_sessions": 234,
    "total_tokens": 1234567,
    "encryption": "AES-GCM-256",
    "token_estimation": "heuristic_v1"
  },
  "health_indicators": {
    "capacity_utilization_pct": 23.4
  }
}
```

**See:** [ADR-044: Ephemeral Cache Observability](../adrs/ADR-044-Ephemeral-Cache-Observability.md)

---

## Frontend Migration

### 1. Install idb Package

```bash
npm install idb
```

### 2. Initialize Session Storage

```typescript
import { SessionStorageService } from './services/session-storage.service';

constructor(private sessionStorage: SessionStorageService) {}

async ngOnInit() {
  // Create new conversation session
  const session = await this.sessionStorage.createSession(
    'Threat Analysis',
    'threat-triage-uuid',
    'Threat Triage',
    24 // TTL in hours
  );

  console.log('Session created:', session.id);
}
```

### 3. Add Messages to Session

```typescript
// Add user message
await this.sessionStorage.addMessage(
  sessionId,
  'user',
  'Analyze this IOC: 192.0.2.1'
);

// Add assistant response
await this.sessionStorage.addMessage(
  sessionId,
  'assistant',
  'This IP address appears to be...',
  { model: 'gpt-4', tokens: 150, latency_ms: 1200 }
);
```

### 4. Export Conversations

```typescript
import { ExportService } from './services/export.service';

constructor(private exportService: ExportService) {}

// Export as JSON
this.exportService.exportAsJson(sessionId).subscribe(response => {
  const filename = this.exportService.generateFilename(session.title, 'json');
  this.exportService.downloadExport(response.content, filename, 'json');
});

// Export as Markdown
this.exportService.exportAsMarkdown(sessionId).subscribe(response => {
  const filename = this.exportService.generateFilename(session.title, 'markdown');
  this.exportService.downloadExport(response.content, filename, 'markdown');
});
```

### 5. Generate Summaries

```typescript
this.exportService.generateSummary(sessionId, 'executive').subscribe(summary => {
  console.log('Summary:', summary.summary);
  console.log('Key points:', summary.key_points);
});
```

### 6. Add Expiry Warning Component

```typescript
// In your app component template
<app-session-expiry-warning></app-session-expiry-warning>
```

This component automatically:

- Checks for expiring sessions every 5 minutes
- Displays warning when sessions expire within 1 hour
- Provides quick export button

---

## Backend Provider Architecture

### Provider Interfaces (ADR-033)

```python
from app.providers import (
    HistoryProvider,      # Protocol for history persistence
    EvidenceSink,         # Protocol for evidence storage
    CryptoProvider,       # Protocol for crypto operations
    EdgeOnlyHistory,      # v1: No-op implementation
    NoneEvidence,         # v1: No-op implementation
    NoCrypto,             # v1: No-op implementation
)

# In orchestrator initialization
history = EdgeOnlyHistory()  # Client-side only
evidence = NoneEvidence()    # Disabled for v1
crypto = NoCrypto()          # No encryption needed
```

### Telemetry Capture

```python
from app.services.telemetry_service import TelemetryService

telemetry = TelemetryService(db)

# Capture PII-free metrics
await telemetry.capture_run_manifest(
    run_id=run_id,
    use_case_id="threat-triage",
    model_name="gpt-4",
    conformance=0.95,
    tokens_in=100,
    tokens_out=150,
    result_kind="success",
    # ❌ NO query text, response text, or conversation content
)
```

---

## Data Migration

### Exporting Existing Conversations

If you have existing server-side conversations, export them before migration:

```sql
-- Export existing conversations to JSON
COPY (
  SELECT
    ct.thread_id,
    ct.title,
    ct.use_case_name,
    json_agg(
      json_build_object(
        'role', tm.role,
        'content', tm.content,
        'timestamp', tm.created_at
      ) ORDER BY tm.sequence_number
    ) as messages
  FROM context_threads ct
  JOIN thread_messages tm ON ct.id = tm.thread_id
  WHERE ct.is_active = true
  GROUP BY ct.thread_id, ct.title, ct.use_case_name
) TO '/tmp/conversations_export.json';
```

### Clean Up Old Data

After migration and export, optionally clean up deprecated tables:

```sql
-- Optional: Truncate deprecated tables (keeps schema)
TRUNCATE TABLE thread_messages CASCADE;
TRUNCATE TABLE context_threads CASCADE;
TRUNCATE TABLE query_history CASCADE;

-- Or drop tables entirely (removes schema)
-- DROP TABLE thread_messages CASCADE;
-- DROP TABLE context_threads CASCADE;
-- DROP TABLE query_history CASCADE;
```

---

## Security Benefits

### Eliminated Security Scope

✅ **No Server-Side Conversation Storage** → No attack surface for data exfiltration
✅ **No Encryption Required** → Eliminates P4-F1 (Field-Level Encryption)
✅ **No Key Management** → Eliminates P4-F4 (Key Management)
✅ **No Audit Trails for Conversations** → Reduced compliance burden
✅ **No Data Retention Policies** → Simplified operations
✅ **Air-Gapped Ready** → No PII leaves the edge

### Security Checklist

- [x] Run manifests contain zero PII
- [x] Client-side storage uses IndexedDB (same-origin policy)
- [x] TTL enforces automatic expiration
- [x] Export/summary endpoints are stateless
- [x] RLS policies still enforce use case access control

---

## Testing

### Backend Tests

```bash
# Test telemetry capture
pytest src/orchestrator/tests/unit/test_telemetry_service.py -v

# Test export generation
pytest src/orchestrator/tests/unit/test_export_service.py -v

# Test summary generation
pytest src/orchestrator/tests/unit/test_summary_service.py -v
```

### Frontend Tests

```bash
# Test session storage
ng test --include='**/session-storage.service.spec.ts'

# Test export service
ng test --include='**/export.service.spec.ts'

# Test expiry warnings
ng test --include='**/session-expiry-warning.component.spec.ts'
```

---

## Troubleshooting

### Issue: Sessions not persisting

**Cause:** IndexedDB may be disabled or storage quota exceeded
**Solution:** Check browser settings, clear old data

```typescript
// Check IndexedDB support
if ('indexedDB' in window) {
  console.log('IndexedDB supported');
} else {
  console.error('IndexedDB not supported');
}
```

### Issue: Sessions expiring too quickly

**Cause:** Default TTL is 24 hours
**Solution:** Adjust TTL when creating sessions

```typescript
const session = await this.sessionStorage.createSession(
  'Long Investigation',
  useCaseId,
  useCaseName,
  72 // 72 hours TTL
);
```

### Issue: Export fails with large conversations

**Cause:** Memory limits in browser
**Solution:** Implement chunked export for large conversations

---

## Rollback Plan

If you need to rollback to stateful architecture:

1. **Re-enable server-side endpoints:**

   ```python
   # In main.py, uncomment:
   # fastapi_app.include_router(query_history_router)
   ```

2. **Restore database tables:**

   ```sql
   -- Tables are still present, just deprecated
   -- Simply start using them again
   ```

3. **Update frontend:**

   ```typescript
   // Revert to using context.service.ts instead of session-storage.service.ts
   ```

---

## Future Stateful Add-On (v2+)

For enterprises requiring server-side storage, future v2+ will offer:

- **GovernedHistory** provider (encrypted server storage)
- **WormEvidence** provider (immutable evidence archives)
- **KmsCrypto** provider (HSM/KMS integration)
- Configurable via environment variables (no code changes)

```python
# v2+ configuration
HISTORY_PROVIDER=governed  # Enable server-side storage
EVIDENCE_SINK=worm         # Enable evidence collection
CRYPTO_PROVIDER=kms        # Enable encryption
```

---

## Secure Logging Configuration

### Production Security (CRITICAL)

**Set these environment variables in production:**

```bash
REDACT_LOGS=true              # MUST be enabled for production
LOG_REDACTION_LEVEL=partial   # Recommended: partial (none|partial|full)
```

**Redaction Levels:**

- `none` - Full logging (dev/test only)
- `partial` - Redact content, show length+hash (recommended)
- `full` - Redact everything except metadata

**Example (partial redaction):**

```json
// Logged:
"query": "[REDACTED:45chars:hash=7f3a9b21]"  ← Safe

// NOT logged:
"query": "Investigate alert #12345 with IOCs..."  ← Security breach!
```

**See:** [ADR-045: Secure Logging with Redaction](../adrs/ADR-045-Secure-Logging-Redaction.md)

---

## References

- [ADR-030: No Transcripts; Run Manifests Only](../adrs/ADR-030-No-Transcripts-Run-Manifests.md)
- [ADR-031: Client-Owned Exports & Summary Generation](../adrs/ADR-031-Client-Owned-Exports.md)
- [ADR-033: Provider Interfaces for History/Evidence/Crypto](../adrs/ADR-033-Provider-Interfaces.md)
- [ADR-043: Conversations as QUERY Pattern](../adrs/ADR-043-Conversations-As-QUERY-Pattern.md)
- [ADR-044: Ephemeral Cache Observability](../adrs/ADR-044-Ephemeral-Cache-Observability.md)
- [ADR-045: Secure Logging with Redaction](../adrs/ADR-045-Secure-Logging-Redaction.md)
- [Stateless Core v1 Implementation Plan](../plans/STATELESS_CORE_V1_IMPLEMENTATION_PLAN.md)

---

## Support

For questions or issues:

- Check troubleshooting section above
- Review ADRs for architectural decisions
- File issue in project repository

**Migration completed:** October 25, 2025
**Backward compatibility:** Deprecated endpoints remain functional until v2
