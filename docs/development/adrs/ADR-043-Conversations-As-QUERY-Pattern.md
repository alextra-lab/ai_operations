# ADR-034: Conversations Panel as QUERY Intent Pattern

**Status:** ✅ ACCEPTED
**Date:** 2025-10-25
**Deciders:** Architecture Team
**Related:** ADR-030 (Stateless), ADR-036 (Pipeline Architecture)

---

## Context

We are implementing a **Conversations** feature in the UI that provides:
- Multi-turn dialogue capability
- Ephemeral context management
- Client-side history (IndexedDB)
- Backend cache for LLM context
- Session-based continuity

Simultaneously, we have **Use Cases** with `RequestType.QUERY` intent that represent semantic search and Q&A functionality.

**Question:** What is the relationship between Conversations and QUERY-type Use Cases?

---

## Decision

**The Conversations panel IS the reference implementation for how QUERY-type Use Cases should function.**

### Principles

1. **Conversations = Generic QUERY Use Case**
   - Conversations panel = QUERY intent without a specific use case configured
   - Registered QUERY use cases = Same behavior with custom prompts/RAG/tools

2. **Shared Architecture**
   - Both use: `/api/v1/process` endpoint
   - Both use: Ephemeral conversation cache
   - Both use: Same pipeline (GuardValidate → RetrieveContext → AssemblePrompt → ExecuteLLM → FormatResponse)
   - Both support: Streaming and non-streaming responses

3. **Use Case Differentiation**
   ```python
   # Generic Conversation (no use_case_id)
   POST /api/v1/process
   {
     "query": "What is threat intelligence?",
     "session_id": "session_123",
     "stream": true
   }
   # → Uses default config, generic prompts

   # QUERY Use Case (with use_case_id)
   POST /api/v1/process
   {
     "query": "What is threat intelligence?",
     "session_id": "session_123",
     "use_case_id": "uuid-of-incident-analysis",
     "stream": true
   }
   # → Uses custom config, specialized prompts, specific RAG collections
   ```

4. **Context Management**
   - **Client-side (Both):** Full conversation in IndexedDB for UI display
   - **Server-side (Both):** Ephemeral cache maintains LLM context window
   - **Model-aware (Both):** Cache size = model's `context_window` attribute

---

## Implementation Mapping

| Feature | Conversations Panel | QUERY Use Cases |
|---------|---------------------|-----------------|
| **Intent Type** | `RequestType.QUERY` | `RequestType.QUERY` |
| **Endpoint** | `/api/v1/process` | `/api/v1/process` |
| **Session Management** | Client `session_id` | Client `session_id` |
| **Context Cache** | Ephemeral backend cache | Ephemeral backend cache |
| **UI Storage** | IndexedDB | IndexedDB |
| **RAG Retrieval** | Default collection | Use case-specific collections |
| **Prompts** | Generic templates | Custom prompts from use case config |
| **Tools** | None by default | Use case-defined tools |
| **Model Selection** | Default model | Use case-configured model |

---

## Architectural Flow

```
┌─────────────────────────────────────────────────────────┐
│ UI Layer                                                │
│ ┌───────────────────┐  ┌──────────────────────────┐   │
│ │ Conversations     │  │ Use Case Execution       │   │
│ │ Panel             │  │ (QUERY Intent)           │   │
│ │                   │  │                          │   │
│ │ No use_case_id    │  │ Has use_case_id          │   │
│ └───────────────────┘  └──────────────────────────┘   │
│          │                        │                     │
│          └────────────┬───────────┘                     │
└───────────────────────┼─────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────┐
│ POST /api/v1/process                                    │
│ {query, session_id, use_case_id?, stream}              │
└─────────────────────────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Pipeline Steps (ADR-036)                                │
│                                                         │
│ if use_case_id:                                         │
│   config = load_use_case_config(use_case_id)           │
│   prompts = load_use_case_prompts(use_case_id)         │
│ else:                                                   │
│   config = get_default_config()                        │
│   prompts = None  # Use generic templates              │
│                                                         │
│ 1. GuardValidate (same)                                │
│ 2. RetrieveContext (collection varies)                 │
│ 3. AssemblePrompt (prompt varies)                      │
│ 4. ExecuteLLM (model varies)                           │
│ 5. FormatResponse (same)                               │
└─────────────────────────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Ephemeral Cache (ADR-030)                               │
│ - Encrypted conversation history                       │
│ - Model-aware token limits                             │
│ - TTL + idle timeout                                   │
│ - Same for both conversation types                     │
└─────────────────────────────────────────────────────────┘
```

---

## Use Case Registration for Conversations

When creating a QUERY-type use case, admins configure:

```yaml
# Use Case: Incident Triage Assistant
name: "Incident Triage Assistant"
intent_type: QUERY
description: "Helps SOC analysts triage security incidents"

# Behavior matches Conversations panel, but customized:
model: "gpt-4-turbo"
context_window: 128000  # Longer conversations
temperature: 0.3  # More deterministic
prompts:
  system: "You are a SOC incident triage assistant..."

rag:
  collections: ["incident-playbooks", "ioc-database"]
  top_k: 5

tools:
  - fetch_alert_details
  - query_siem
  - enrich_ioc
```

**Result:** Same conversation UX, specialized behavior.

---

## Consequences

### Positive

✅ **Consistency:** Users get familiar conversation UX everywhere
✅ **Reusability:** Conversations panel code = reference for use cases
✅ **Simplicity:** One architecture, one cache, one endpoint
✅ **Extensibility:** Easy to add specialized QUERY use cases
✅ **Testing:** Test conversations = test QUERY use cases

### Negative

⚠️ **Coupling:** Changes to conversations affect all QUERY use cases
⚠️ **Expectations:** Users expect conversation-like behavior from QUERY use cases

### Mitigation

- **Versioning:** API versioned (`/api/v1/process`) for breaking changes
- **Feature Flags:** Can disable conversation features per use case if needed
- **Documentation:** Clear docs that QUERY = conversational by default

---

## Validation Criteria

A QUERY use case implementation is valid if:

1. ✅ Supports multi-turn conversations via `session_id`
2. ✅ Maintains context in ephemeral cache
3. ✅ Respects model's `context_window` limits
4. ✅ Supports streaming responses
5. ✅ Uses same `/api/v1/process` endpoint
6. ✅ Client can store history in IndexedDB
7. ✅ Cache stats returned to UI for utilization display

---

## Future Considerations

### v1.1: Conversation Templates
- Pre-configured conversation starters
- Suggested follow-up questions
- Context-aware prompting

### v1.2: Context Compression
- Auto-summarization at 80% limit
- Smart truncation strategies
- User-controlled compression

### v2.0: Multi-Model Conversations
- Switch models mid-conversation
- Different models for different turn types
- Model routing based on query complexity

---

## References

- **ADR-030:** No Transcripts, Run Manifests Only (Stateless Core v1)
- **ADR-031:** Client-Owned Exports
- **ADR-033:** Provider Interfaces
- **ADR-036:** Pipeline + Steps Architecture
- `src/orchestrator/app/routers/orchestrator.py` - Process endpoint implementation
- `src/frontend-angular/src/app/pages/conversations/` - Reference UI

---

**Decision:** The Conversations panel establishes the pattern for all QUERY-type use cases. This creates consistency, reusability, and a clear mental model: **"QUERY = Conversational"**.
