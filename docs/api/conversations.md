# Conversation Threads API Documentation

**Version:** 1.1
**Date:** November 28, 2025
**Status:** ⚠️ Write endpoints disabled in Core Edition (ADR-030)

---

## ⚠️ Important: Core Edition Restrictions

**As of P5-SEC-01 (November 2025):** Write endpoints are **disabled** in Core Edition to enforce ADR-030 (stateless architecture).

### Disabled Write Endpoints (return 501 Not Implemented)

| Endpoint | Method | Status |
|----------|--------|--------|
| `/api/v1/query-history/threads` | POST | ⛔ Disabled |
| `/api/v1/query-history/threads/{id}` | PATCH | ⛔ Disabled |
| `/api/v1/query-history/threads/{id}` | DELETE | ⛔ Disabled |

### Available Read Endpoints

| Endpoint | Method | Status |
|----------|--------|--------|
| `/api/v1/query-history/threads` | GET | ✅ Available |
| `/api/v1/query-history/threads/{id}` | GET | ✅ Available |
| `/api/v1/query-history/threads/{id}/messages` | GET | ✅ Available |

### Enabling Write Endpoints (Plus Edition)

To enable write functionality, set the environment variable:
```bash
ENABLE_TRANSCRIPT_STORAGE=true
```

### Alternative: Client-Side Storage (Recommended)

For Core Edition, use the client-side `SessionStorageService` which stores conversations in browser IndexedDB with TTL-based expiration. See [Stateless Migration Guide](../development/migration/STATELESS_MIGRATION_GUIDE.md).

---

## Overview

The Conversation Threads API provides multi-turn conversation management with context preservation, enabling ChatGPT-style interactions. Supports DiscussionID namespacing for correlating conversations across UI and API sources (e.g., Cortex SOAR integration).

**Key Features:**
- Multi-turn conversations with full context preservation
- DiscussionID for incident/ticket correlation
- Token usage tracking and compaction warnings
- Cross-source visibility (UI + API/SOAR)
- Automatic context loading for LLM requests

## Architecture

```
DiscussionID: "INC-2024-001" (optional namespace)
├── Thread 1: "IOC Analysis" (use_case: ioc_analysis, source: ui)
│   ├── Message 1: User query (7 tokens)
│   ├── Message 2: Assistant response (28 tokens)
│   └── Message 3: Follow-up query → LLM sees full history
├── Thread 2: "Follow-up Investigation" (use_case: ioc_analysis, source: ui)
│   └── Multiple threads can share same DiscussionID
└── Thread 3: "SOAR Enrichment" (use_case: enrichment, source: api)
    └── API calls can join same DiscussionID namespace
```

## Base URL

```
/api/v1/query-history/threads
```

## Authentication

All endpoints require JWT Bearer token authentication.

```bash
Authorization: Bearer <access_token>
```

---

## Endpoints

### 1. Create Thread

Create a new conversation thread.

**Endpoint:** `POST /threads`

**Request Body:**

```json
{
  "title": "IOC Investigation",
  "description": "Investigating suspicious IP 192.0.2.1",
  "discussion_id": "INC-2024-001",
  "use_case_id": "550e8400-e29b-41d4-a716-446655440000",
  "use_case_name": "IOC Analysis",
  "source": "ui",
  "metadata": {
    "priority": "high",
    "assigned_to": "analyst@example.com"
  }
}
```

**Response:**

```json
{
  "id": "ba0c6e49-2813-4887-8970-e0c1753234f7",
  "thread_id": "eba0915c-ce6a-4e9e-8022-c6e831629efd",
  "title": "IOC Investigation",
  "description": "Investigating suspicious IP 192.0.2.1",
  "user_id": "4bf13246-184e-462d-9085-f3dc3a0642d0",
  "discussion_id": "INC-2024-001",
  "use_case_id": "550e8400-e29b-41d4-a716-446655440000",
  "use_case_name": "IOC Analysis",
  "source": "ui",
  "is_active": true,
  "message_count": 0,
  "context_size_tokens": 0,
  "max_context_tokens": 8000,
  "created_at": "2025-10-10T13:35:02.895681Z",
  "updated_at": "2025-10-10T13:35:02.895682Z",
  "last_activity_at": "2025-10-10T13:35:02.895680Z",
  "metadata_json": {"priority": "high"}
}
```

---

### 2. List Threads

List all threads for the current user with optional filtering.

**Endpoint:** `GET /threads`

**Query Parameters:**
- `limit` (integer, default: 50, max: 100) - Number of threads to return
- `offset` (integer, default: 0) - Number of threads to skip
- `discussion_id` (string, optional) - Filter by DiscussionID
- `use_case_id` (UUID, optional) - Filter by use case
- `is_active` (boolean, default: true) - Filter by active status

**Example:**

```bash
GET /threads?discussion_id=INC-2024-001&limit=10
```

**Response:**

```json
{
  "items": [
    {
      "id": "ba0c6e49-2813-4887-8970-e0c1753234f7",
      "thread_id": "eba0915c-ce6a-4e9e-8022-c6e831629efd",
      "title": "IOC Investigation",
      "discussion_id": "INC-2024-001",
      "message_count": 12,
      "context_size_tokens": 1547,
      "max_context_tokens": 8000,
      "last_activity_at": "2025-10-10T14:22:15.123456Z"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0,
  "has_more": false
}
```

---

### 3. Get Thread

Retrieve a specific thread by ID.

**Endpoint:** `GET /threads/{thread_id}`

**Path Parameters:**
- `thread_id` (UUID) - The thread UUID

**Response:**

```json
{
  "id": "ba0c6e49-2813-4887-8970-e0c1753234f7",
  "thread_id": "eba0915c-ce6a-4e9e-8022-c6e831629efd",
  "title": "IOC Investigation",
  "discussion_id": "INC-2024-001",
  "message_count": 12,
  "context_size_tokens": 1547,
  "max_context_tokens": 8000
}
```

---

### 4. Get Thread Messages

Retrieve all messages in a thread (conversation history).

**Endpoint:** `GET /threads/{thread_id}/messages`

**Path Parameters:**
- `thread_id` (UUID) - The thread UUID

**Response:**

```json
[
  {
    "id": "msg-uuid-1",
    "thread_id": "thread-internal-id",
    "sequence_number": 1,
    "role": "user",
    "content": "What is this IP address?",
    "token_count": 7,
    "created_at": "2025-10-10T13:35:03Z"
  },
  {
    "id": "msg-uuid-2",
    "thread_id": "thread-internal-id",
    "sequence_number": 2,
    "role": "assistant",
    "content": "This IP address belongs to...",
    "token_count": 45,
    "model_used": "gpt-4",
    "created_at": "2025-10-10T13:35:08Z"
  },
  {
    "id": "msg-uuid-3",
    "thread_id": "thread-internal-id",
    "sequence_number": 3,
    "role": "system",
    "content": "[Summary of 15 earlier messages]: Previous discussion covered...",
    "token_count": 120,
    "is_summary": true,
    "original_message_count": 15,
    "created_at": "2025-10-10T13:40:00Z"
  }
]
```

---

### 5. Update Thread

Update thread metadata.

**Endpoint:** `PATCH /threads/{thread_id}`

**Request Body:**

```json
{
  "title": "Updated Title",
  "description": "Updated description",
  "discussion_id": "INC-2024-002",
  "is_active": true
}
```

**Response:** Updated `ThreadResponse` object

---

### 6. Delete/Archive Thread

Archive or permanently delete a thread.

**Endpoint:** `DELETE /threads/{thread_id}`

**Query Parameters:**
- `archive` (boolean, default: true) - If true, archive; if false, permanently delete

**Example:**

```bash
DELETE /threads/{thread_id}?archive=true
```

**Response:**

```json
{
  "status": "archived"
}
```

---

## Multi-Turn Conversation Flow

### Sending Query with Thread Context

When sending a query to `/api/v1/process` with `thread_id`, the orchestrator:

1. **Loads conversation history** from the thread
2. **Builds messages array** with full context
3. **Sends to LLM** with conversation history
4. **Saves user query** and assistant response to thread
5. **Updates token counts** and activity timestamps

**Example:**

```bash
POST /api/v1/process
{
  "query": "What is the population of that city?",
  "thread_id": "eba0915c-ce6a-4e9e-8022-c6e831629efd"
}
```

The LLM receives:
```json
{
  "messages": [
    {"role": "user", "content": "What is the capital of France?"},
    {"role": "assistant", "content": "The capital of France is Paris."},
    {"role": "system", "content": "[assembled prompt]"},
    {"role": "user", "content": "What is the population of that city?"}
  ]
}
```

---

## DiscussionID Use Cases

### 1. UI Workflow

```bash
# User creates thread with incident ID
POST /threads
{
  "title": "Investigating Phishing Email",
  "discussion_id": "INC-2024-1234",
  "source": "ui"
}

# User sends multiple queries in conversation
POST /api/v1/process
{
  "query": "Analyze this email header...",
  "thread_id": "<thread_id>"
}

# Later, user creates another thread for same incident
POST /threads
{
  "title": "IP Reputation Check",
  "discussion_id": "INC-2024-1234",  # Same incident
  "source": "ui"
}

# Both threads visible when filtering by INC-2024-1234
GET /threads?discussion_id=INC-2024-1234
```

### 2. SOAR Integration

```python
# SOAR playbook sends enrichment request
response = requests.post(
    "http://aio:8000/api/v1/process",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "query": "Enrich IOC: 192.0.2.1",
        "discussion_id": "INC-2024-1234",  # From SOAR ticket
        "use_case_id": "enrichment-use-case-id"
    }
)

# Backend auto-creates/finds thread with discussion_id
# Subsequent API calls with same discussion_id + use_case_id
# will continue the same conversation
```

### 3. Cross-Source Visibility

```bash
# Analyst can see all threads for an incident
GET /threads?discussion_id=INC-2024-1234

# Response includes:
# - UI threads created by analysts
# - API threads created by SOAR playbooks
# - All grouped under same incident ID
```

---

## Token Management

### Context Size Tracking

- Every message saved includes `token_count` (calculated with tiktoken)
- Thread's `context_size_tokens` tracks total context size
- Default `max_context_tokens`: 8000
- Compaction warning at 70% utilization (5600 tokens)

### Context Compaction (Future)

When thread approaches token limit:
1. System logs warning
2. UI displays warning indicator
3. Admin can trigger manual compaction
4. Automatic compaction summarizes older messages

**Compaction Strategy:**
- Keep last 10 messages unchanged
- Summarize older messages into single system message
- Preserve important context for continued conversation

---

## Error Handling

### Common Errors

**Thread Not Found (404):**
```json
{
  "detail": "Thread not found or not accessible"
}
```

**Invalid UUID (422):**
```json
{
  "detail": [
    {
      "type": "uuid_parsing",
      "loc": ["path", "thread_id"],
      "msg": "Input should be a valid UUID"
    }
  ]
}
```

**Authentication Required (401):**
```json
{
  "detail": "Not authenticated"
}
```

---

## Integration Examples

### Example 1: Multi-Turn Investigation

```bash
# 1. Create thread
THREAD_ID=$(curl -X POST "/api/v1/query-history/threads" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title": "Malware Analysis", "discussion_id": "INC-2024-5678"}' \
  | jq -r '.thread_id')

# 2. Initial query
curl -X POST "/api/v1/process" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"query\": \"Analyze this hash: abc123...\", \"thread_id\": \"$THREAD_ID\"}"

# 3. Follow-up (LLM sees first query + response)
curl -X POST "/api/v1/process" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"query\": \"What are the associated domains?\", \"thread_id\": \"$THREAD_ID\"}"

# 4. View conversation history
curl -X GET "/api/v1/query-history/threads/$THREAD_ID/messages" \
  -H "Authorization: Bearer $TOKEN"
```

### Example 2: SOAR Integration

```python
import requests

class AIOpsSOARConnector:
    """SOAR connector for AI Operations Platform."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}

    def enrich_ioc(self, ioc: str, incident_id: str):
        """
        Enrich an IOC with conversation context.
        Multiple calls with same incident_id continue the conversation.
        """
        response = requests.post(
            f"{self.base_url}/api/v1/process",
            headers=self.headers,
            json={
                "query": f"Enrich IOC: {ioc}",
                "discussion_id": incident_id,
                "use_case_id": "enrichment-uuid"
            }
        )
        return response.json()

    def get_incident_threads(self, incident_id: str):
        """Get all conversation threads for an incident."""
        response = requests.get(
            f"{self.base_url}/api/v1/query-history/threads",
            headers=self.headers,
            params={"discussion_id": incident_id}
        )
        return response.json()
```

### Example 3: Context Monitoring

```bash
# Monitor context usage
THREAD_ID="eba0915c-ce6a-4e9e-8022-c6e831629efd"
curl -X GET "/api/v1/query-history/threads/$THREAD_ID" \
  -H "Authorization: Bearer $TOKEN" \
  | jq '{
      title,
      tokens: .context_size_tokens,
      max: .max_context_tokens,
      utilization_percent: ((.context_size_tokens / .max_context_tokens) * 100 | floor)
    }'

# Response:
# {
#   "title": "Multi-Turn Investigation",
#   "tokens": 2154,
#   "max": 8000,
#   "utilization_percent": 26
# }
```

---

## Best Practices

### 1. DiscussionID Naming

```
Recommended formats:
- INC-YYYY-NNNN (Incident)
- TICKET-NNNN (Help Desk)
- CASE-YYYY-NNNN (Investigation)
- ALERT-NNNN (Security Alert)

Accept any string format (max 255 characters).
```

### 2. Thread Lifecycle

```
1. Create thread with DiscussionID
2. Send queries with thread_id for context
3. Monitor token usage
4. Archive when investigation complete
5. Search by DiscussionID for related threads
```

### 3. Multiple Threads per Incident

```bash
# Good practice: Separate threads for different aspects
INC-2024-001 (Phishing Investigation)
├── Thread A: "Email Header Analysis" (use_case: email_analysis)
├── Thread B: "Sender IP Reputation" (use_case: ioc_analysis)
└── Thread C: "Link URL Analysis" (use_case: url_analysis)

# Each thread has focused conversation
# All linked by discussion_id for correlation
```

### 4. Context Management

- **Monitor token usage**: Check `context_size_tokens` regularly
- **Start new thread**: When approaching 70% utilization
- **Link threads**: Use same `discussion_id` for related investigations
- **Archive completed**: Set `is_active=false` when done

---

## Technical Details

### Token Counting

- Uses `tiktoken` library with `gpt-4` encoding
- Token count calculated on message save
- Air-gapped compatible (encoding bundled in package)
- Fallback: ~4 characters per token if tiktoken unavailable

### Message Sequence

- Messages numbered sequentially within thread
- Unique constraint on `(thread_id, sequence_number)`
- Ordered retrieval ensures correct conversation flow

### RLS (Row-Level Security)

- Threads automatically filtered by `user_id`
- Users only see their own threads
- Admin can see all threads (future enhancement)

---

## Migration Information

**Migration:** `012_add_thread_conversation_support.sql`

**Schema Changes:**
- Added 8 columns to `context_threads`
- Added 4 columns to `thread_messages`
- Created 2 new indexes for `discussion_id` queries
- Made `query_id` nullable in `thread_messages`

---

## Testing

### Unit Tests

Run thread conversation tests:

```bash
pytest src/orchestrator/tests/integration/test_thread_conversations.py -v
```

### API Integration Tests

```bash
# Create thread
TOKEN=$(curl -s -X POST "http://localhost:8006/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" -d "password=adminpassword" | jq -r '.access_token')

# Test thread creation
curl -X POST "http://localhost:8006/api/v1/query-history/threads" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Thread", "discussion_id": "TEST-001"}'

# Test multi-turn conversation
THREAD_ID="<from-above>"
curl -X POST "http://localhost:8006/api/v1/process" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"query\": \"First query\", \"thread_id\": \"$THREAD_ID\"}"

curl -X POST "http://localhost:8006/api/v1/process" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"query\": \"Follow-up question\", \"thread_id\": \"$THREAD_ID\"}"

# Verify messages saved
curl -X GET "http://localhost:8006/api/v1/query-history/threads/$THREAD_ID/messages" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Limitations & Future Enhancements

### Current Limitations

- Automatic compaction not yet implemented (warning only)
- No admin view of all threads across users
- No thread sharing/collaboration features
- Context compaction requires manual trigger

### Planned Enhancements

- Automatic context compaction when >70% utilization
- Thread sharing between users
- Export conversation to PDF/markdown
- Smart context summarization with LLM
- Thread templates for common investigation types
- Analytics dashboard for thread usage patterns

---

## Related Documentation

- [Authentication API](./authentication.md) - JWT token management
- [Query Processing](./query.md) - Use case execution
- [UI Development Plan](../development/plans/UI_DEVELOPMENT_PLAN.md) - P2-F4 implementation

---

## Changelog

### Version 1.0 (October 10, 2025)

- Initial implementation
- Multi-turn conversation support
- DiscussionID namespacing
- Token tracking with tiktoken
- SOAR integration support
- Cross-source visibility
