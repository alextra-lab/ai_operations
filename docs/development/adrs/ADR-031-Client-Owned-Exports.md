# ADR-031: Client-Owned Exports & Summary Generation

**Status:** Accepted
**Date:** 2025-10-22
**Deciders:** Architecture Team
**Tags:** stateless, exports, client-side, user-control

---

## Context

**What is the issue we're addressing?**

With the stateless architecture (ADR-030), conversation history lives on the client edge, but users need:

- **Export Capabilities:** Save important conversations for records, sharing, or compliance
- **Summary Generation:** Create executive summaries from conversation threads
- **Data Portability:** Move conversations between systems or users
- **Compliance Support:** Generate reports for audit or regulatory requirements

**Current limitations:**
- No server-side conversation storage means no centralized export capabilities
- Users lose conversation history if client data is cleared
- No way to generate summaries across conversation threads
- Limited data portability between sessions or users

**Forces at play:**
- Stateless architecture eliminates server-side conversation storage
- User need for conversation persistence and portability
- Compliance requirements for conversation records
- Executive reporting needs for SOC management

---

## Decision

**What did we decide?**

**Implement client-owned export and summary generation:**

- **Export Formats:** Markdown (.md) and JSON (.json) with full conversation content
- **Client-Side Generation:** Export functionality runs entirely on client edge
- **Summary Service:** Server-side summary generation from exported conversation data
- **User Control:** Users decide what to export and when
- **No Server Storage:** Exports are generated on-demand, not stored server-side

**Key Implementation Details:**
- Export includes: conversation messages, timestamps, use case context, model parameters
- Markdown format: Human-readable with proper formatting for sharing
- JSON format: Machine-readable with full metadata for integration
- Summary endpoint: Accepts exported conversation data, returns executive summary
- TTL warnings: Clear notifications about conversation expiration

---

## Alternatives Considered

### Option 1: Server-Side Export Storage
**Description:** Store exports on server for centralized access
**Pros:**
- Centralized export management
- Cross-user export sharing
- Server-side summary generation

**Cons:**
- Violates stateless architecture principles
- Creates new security surface (export storage)
- Requires export encryption and access controls
- Adds server storage complexity

**Why Rejected:** Conflicts with stateless architecture and adds security scope

### Option 2: No Export Capability
**Description:** Pure stateless with no export functionality
**Pros:**
- Simplest implementation
- Maximum security

**Cons:**
- Poor user experience (lost conversations)
- No compliance support
- Limited adoption potential
- No executive reporting

**Why Rejected:** Essential for user adoption and compliance requirements

### Option 3: Hybrid Client-Server Exports
**Description:** Client generates, server stores exports temporarily
**Pros:**
- Server-side summary generation
- Temporary export storage

**Cons:**
- Still requires server storage
- Complex TTL management
- Security concerns for export data

**Why Rejected:** Adds complexity without clear benefits over pure client-side approach

---

## Consequences

### Positive Consequences

**Benefits of this decision:**
- **User Control:** Complete control over conversation data and exports
- **Privacy Preserved:** No server-side conversation storage
- **Compliance Ready:** Export capabilities support audit requirements
- **Data Portability:** Easy to move conversations between systems
- **Executive Reporting:** Summary generation supports management reporting
- **Stateless Compliant:** Aligns with no server-side conversation storage

### Negative Consequences

**Tradeoffs and costs:**
- **Client Dependency:** Exports lost if client data cleared before export
- **No Cross-User Sharing:** Cannot share exports between users easily
- **Manual Process:** Users must remember to export important conversations
- **Limited Analytics:** No server-side conversation analytics across users

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Lost exports | Medium | Clear TTL warnings, auto-export prompts, backup guidance |
| User confusion | Low | Clear UI for export functionality, help documentation |
| Summary quality | Low | Test summary generation with various conversation types |

---

## Implementation Notes

**Key implementation details:**

**Export Data Structure:**
```json
{
  "conversation_id": "uuid",
  "export_timestamp": "2025-10-22T10:30:00Z",
  "use_case": {
    "id": "threat-triage",
    "name": "Threat Triage Analysis",
    "version": "1.2.0"
  },
  "messages": [
    {
      "role": "user",
      "content": "Analyze this threat...",
      "timestamp": "2025-10-22T10:25:00Z"
    },
    {
      "role": "assistant",
      "content": "Based on the indicators...",
      "timestamp": "2025-10-22T10:26:00Z",
      "metadata": {
        "model": "gpt-4",
        "tokens": 150,
        "latency_ms": 1200
      }
    }
  ],
  "session_metadata": {
    "duration_minutes": 15,
    "total_tokens": 500,
    "model_parameters": {...}
  }
}
```

**Files affected:**
- `src/frontend-angular/src/app/services/export.service.ts`
- `src/frontend-angular/src/app/components/export-dialog/`
- `src/orchestrator/app/schemas/export.py`
- `src/orchestrator/app/services/summary.service.py`
- `src/orchestrator/app/routers/summary.py`

**Export Formats:**
- **Markdown:** Human-readable with headers, code blocks, timestamps
- **JSON:** Machine-readable with full metadata and structure
- **Summary:** Executive summary with key findings and recommendations

**Summary Generation:**
- Accepts exported conversation data
- Generates executive summary using LLM
- Returns structured summary with key points
- No server-side storage of summary content

---

## References

- [ADR-030: No Transcripts; Run Manifests Only](ADR-030-No-Transcripts-Run-Manifests.md)
- [Stateless Core v1 Implementation Plan](../plans/STATELESS_CORE_V1_IMPLEMENTATION_PLAN.md)

---

## Status Updates

### 2025-10-22 - Accepted
**Changed By:** Architecture Team
**Reason:** Essential for user adoption and compliance with stateless architecture

---

**Template Version:** 1.0
**Based On:** [Michael Nygard's ADR pattern](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
