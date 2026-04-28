# Summaries API

**Version:** 1.0
**Last Updated:** November 1, 2025
**ADR Reference:** ADR-031 Client-Owned Exports & Summary Generation

## Overview

The Summaries API generates PII-free, concise summaries from client-provided conversation data without server-side storage. This API implements ADR-031 (Client-Owned Exports) for the Stateless Core v1 architecture.

**Key Principles:**
- **No server-side storage** - Conversations remain client-owned
- **On-demand generation** - Summaries created in real-time
- **PII redaction** - Automatic removal of sensitive information
- **Multiple formats** - Markdown, JSON, and plain text support

## Endpoints

### Generate Summary

Generate a summary from conversation messages.

**Endpoint:** `POST /api/v1/summaries`
**Authentication:** Required (JWT)
**Rate Limit:** 50 requests/minute

#### Request

```http
POST /api/v1/summaries HTTP/1.1
Host: api.aio.local
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "use_case_id": "threat-triage-v1",
  "messages": [
    {
      "role": "user",
      "content": "What are the security implications of this alert?",
      "timestamp": "2025-11-01T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "The alert indicates a potential data exfiltration attempt...",
      "timestamp": "2025-11-01T10:00:15Z"
    }
  ],
  "export_format": "markdown",
  "redaction": {
    "redact_pii": true,
    "redact_secrets": true,
    "replacement_strategy": "mask",
    "pii_patterns": ["email", "ip", "ssn"],
    "secret_patterns": ["api_key", "password", "token"]
  }
}
```

#### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `use_case_id` | string | Yes | Use case identifier for context |
| `messages` | array | Yes | Conversation messages to summarize |
| `export_format` | string | No | Output format (`markdown`, `json`, `text`) (default: `markdown`) |
| `redaction` | object | No | Redaction configuration |

#### Message Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `role` | string | Yes | Message role (`user`, `assistant`, `system`) |
| `content` | string | Yes | Message content |
| `timestamp` | string | Yes | ISO 8601 timestamp |

#### Redaction Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `redact_pii` | boolean | false | Redact personally identifiable information |
| `redact_secrets` | boolean | false | Redact API keys, passwords, tokens |
| `replacement_strategy` | string | `mask` | Strategy (`mask`, `remove`, `placeholder`) |
| `pii_patterns` | array | `[]` | PII patterns to redact |
| `secret_patterns` | array | `[]` | Secret patterns to redact |

#### Response

**Status:** 200 OK

```json
{
  "summary": "## Conversation Summary\n\n**Use Case:** Threat Triage\n**Date:** 2025-11-01\n**Messages:** 2\n\n### Key Points\n\n- User inquired about security implications\n- Analysis identified potential data exfiltration\n- Recommended immediate isolation and investigation\n\n### Actions Recommended\n\n1. Isolate affected account\n2. Block suspicious connections\n3. Review access logs\n4. Escalate to IR team\n\n---\n*Generated: 2025-11-01T10:05:30Z*",
  "redacted_fields": ["email", "ip_address"],
  "token_count": 156,
  "message_count": 2,
  "format": "markdown",
  "generated_at": "2025-11-01T10:05:30Z",
  "model_used": "extraction-based-v1"
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `summary` | string | Generated summary text |
| `redacted_fields` | array | List of redacted field types |
| `token_count` | integer | Estimated token count |
| `message_count` | integer | Number of messages processed |
| `format` | string | Output format used |
| `generated_at` | string | Generation timestamp (ISO 8601) |
| `model_used` | string | Summary generation model/method |

#### Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Invalid request (malformed messages) |
| 401 | Unauthorized (invalid/missing JWT) |
| 413 | Payload too large (>10MB messages) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

### Batch Summary Generation

Generate multiple summaries in a single request.

**Endpoint:** `POST /api/v1/summaries/batch`
**Authentication:** Required (JWT)
**Rate Limit:** 10 requests/minute
**Max Batch Size:** 25 summaries

#### Request

```http
POST /api/v1/summaries/batch HTTP/1.1
Host: api.aio.local
Authorization: Bearer <jwt_token>
Content-Type: application/json

[
  {
    "use_case_id": "threat-triage-v1",
    "messages": [...],
    "export_format": "markdown"
  },
  {
    "use_case_id": "incident-response-v1",
    "messages": [...],
    "export_format": "json"
  }
]
```

#### Response

**Status:** 200 OK

```json
[
  {
    "summary": "...",
    "redacted_fields": [],
    "token_count": 156,
    "message_count": 2,
    "format": "markdown",
    "generated_at": "2025-11-01T10:05:30Z",
    "model_used": "extraction-based-v1"
  },
  {
    "summary": "...",
    "redacted_fields": ["api_key"],
    "token_count": 203,
    "message_count": 5,
    "format": "json",
    "generated_at": "2025-11-01T10:05:31Z",
    "model_used": "extraction-based-v1"
  }
]
```

## Output Formats

### Markdown Format

```markdown
## Conversation Summary

**Use Case:** Threat Triage
**Date:** 2025-11-01
**Messages:** 4

### Key Points

- Suspicious PowerShell execution detected
- User attempted external data upload
- Multiple IOCs correlated

### Actions Recommended

1. Isolate user account
2. Block outbound connections
3. Review access logs
4. Escalate to incident response team

---
*Generated: 2025-11-01T10:05:30Z*
```

### JSON Format

```json
{
  "use_case": "Threat Triage",
  "date": "2025-11-01",
  "message_count": 4,
  "key_points": [
    "Suspicious PowerShell execution detected",
    "User attempted external data upload",
    "Multiple IOCs correlated"
  ],
  "actions": [
    "Isolate user account",
    "Block outbound connections",
    "Review access logs",
    "Escalate to incident response team"
  ],
  "generated_at": "2025-11-01T10:05:30Z"
}
```

### Plain Text Format

```
CONVERSATION SUMMARY

Use Case: Threat Triage
Date: 2025-11-01
Messages: 4

KEY POINTS
- Suspicious PowerShell execution detected
- User attempted external data upload
- Multiple IOCs correlated

ACTIONS RECOMMENDED
1. Isolate user account
2. Block outbound connections
3. Review access logs
4. Escalate to incident response team

Generated: 2025-11-01T10:05:30Z
```

## Redaction Strategies

### Mask Strategy

Replaces sensitive data with masking characters.

**Example:**
```
Before: "User email is admin@example.com"
After:  "User email is ***@***.***"
```

### Remove Strategy

Completely removes sensitive data.

**Example:**
```
Before: "API key: sk-1234567890abcdef"
After:  "API key:"
```

### Placeholder Strategy

Replaces sensitive data with descriptive placeholders.

**Example:**
```
Before: "Connect to 192.0.2.1"
After:  "Connect to [REDACTED_IP]"
```

## Usage Examples

### TypeScript/Angular

```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface SummaryRequest {
  use_case_id: string;
  messages: ConversationMessage[];
  export_format?: 'markdown' | 'json' | 'text';
  redaction?: RedactionConfig;
}

export interface SummaryResponse {
  summary: string;
  redacted_fields: string[];
  token_count: number;
  message_count: number;
  format: string;
  generated_at: string;
  model_used: string;
}

@Injectable({ providedIn: 'root' })
export class SummaryService {
  private apiUrl = '/api/v1/summaries';

  constructor(private http: HttpClient) {}

  generateSummary(request: SummaryRequest): Observable<SummaryResponse> {
    return this.http.post<SummaryResponse>(this.apiUrl, request);
  }

  downloadSummary(response: SummaryResponse, filename: string): void {
    const blob = new Blob([response.summary], {
      type: this.getMimeType(response.format)
    });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  private getMimeType(format: string): string {
    switch (format) {
      case 'json': return 'application/json';
      case 'markdown': return 'text/markdown';
      case 'text': return 'text/plain';
      default: return 'text/plain';
    }
  }
}
```

### Python

```python
import httpx
from typing import List, Dict, Optional
from datetime import datetime

class SummaryClient:
    """Client for Summaries API."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}

    async def generate_summary(
        self,
        use_case_id: str,
        messages: List[Dict],
        export_format: str = "markdown",
        redaction: Optional[Dict] = None
    ) -> Dict:
        """Generate a conversation summary."""
        payload = {
            "use_case_id": use_case_id,
            "messages": messages,
            "export_format": export_format,
        }
        if redaction:
            payload["redaction"] = redaction

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/summaries",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def generate_with_pii_redaction(
        self,
        use_case_id: str,
        messages: List[Dict]
    ) -> Dict:
        """Generate summary with PII redaction enabled."""
        redaction = {
            "redact_pii": True,
            "redact_secrets": True,
            "replacement_strategy": "mask",
            "pii_patterns": ["email", "ip", "ssn", "phone"],
            "secret_patterns": ["api_key", "password", "token"]
        }

        return await self.generate_summary(
            use_case_id=use_case_id,
            messages=messages,
            redaction=redaction
        )

# Usage
client = SummaryClient("http://localhost:8006", "jwt_token_here")

messages = [
    {
        "role": "user",
        "content": "What should I do about this alert?",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    },
    {
        "role": "assistant",
        "content": "Isolate the affected system immediately.",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
]

summary = await client.generate_with_pii_redaction(
    use_case_id="threat-triage-v1",
    messages=messages
)

print(f"Summary: {summary['summary']}")
print(f"Redacted fields: {summary['redacted_fields']}")
```

### cURL

```bash
# Generate summary with PII redaction
curl -X POST http://localhost:8006/api/v1/summaries \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "use_case_id": "threat-triage-v1",
    "messages": [
      {
        "role": "user",
        "content": "What are the security implications?",
        "timestamp": "2025-11-01T10:00:00Z"
      },
      {
        "role": "assistant",
        "content": "This indicates a potential breach...",
        "timestamp": "2025-11-01T10:00:15Z"
      }
    ],
    "export_format": "markdown",
    "redaction": {
      "redact_pii": true,
      "redact_secrets": true,
      "replacement_strategy": "mask",
      "pii_patterns": ["email", "ip"],
      "secret_patterns": ["api_key", "password"]
    }
  }'
```

## Best Practices

### 1. Always Redact PII in Shared Summaries

```typescript
// Good: Redact PII before sharing
const summary = await summaryService.generateSummary({
  use_case_id: 'threat-analysis',
  messages: conversation,
  redaction: {
    redact_pii: true,
    redact_secrets: true,
    replacement_strategy: 'mask'
  }
});

// Bad: No redaction when sharing
const summary = await summaryService.generateSummary({
  use_case_id: 'threat-analysis',
  messages: conversation
});
```

### 2. Handle Large Conversations

```typescript
// Split large conversations into chunks
const CHUNK_SIZE = 100; // messages

async function summarizeLargeConversation(messages: Message[]) {
  const summaries = [];

  for (let i = 0; i < messages.length; i += CHUNK_SIZE) {
    const chunk = messages.slice(i, i + CHUNK_SIZE);
    const summary = await summaryService.generateSummary({
      use_case_id: 'conversation',
      messages: chunk
    });
    summaries.push(summary);
  }

  return mergeSummaries(summaries);
}
```

### 3. Cache Summaries Client-Side

```typescript
const CACHE_KEY_PREFIX = 'summary_cache_';

async function getCachedOrGenerateSummary(
  conversationId: string,
  request: SummaryRequest
): Promise<SummaryResponse> {
  const cacheKey = `${CACHE_KEY_PREFIX}${conversationId}`;
  const cached = localStorage.getItem(cacheKey);

  if (cached) {
    return JSON.parse(cached);
  }

  const summary = await summaryService.generateSummary(request);
  localStorage.setItem(cacheKey, JSON.stringify(summary));

  return summary;
}
```

## Error Handling

```typescript
try {
  const summary = await summaryService.generateSummary(request);
  displaySummary(summary);
} catch (error) {
  if (error.status === 400) {
    showError('Invalid conversation format');
  } else if (error.status === 413) {
    showError('Conversation too large - please split into smaller chunks');
  } else if (error.status === 429) {
    showError('Rate limit exceeded - please wait before retrying');
  } else {
    showError('Failed to generate summary');
    logError(error);
  }
}
```

## Limitations

| Limitation | Value | Notes |
|------------|-------|-------|
| Max messages per request | 1,000 | For larger conversations, use batch API |
| Max message size | 100 KB | Per individual message |
| Max total payload | 10 MB | Sum of all messages |
| Rate limit | 50/minute | Per user |
| Batch rate limit | 10/minute | Per user |
| Max batch size | 25 summaries | Per batch request |

## Related Documentation

- [ADR-031: Client-Owned Exports](../development/adrs/ADR-031-Client-Owned-Exports.md)
- [ADR-030: No Transcripts; Run Manifests Only](../development/adrs/ADR-030-No-Transcripts-Run-Manifests.md)
- [Capabilities API](capabilities.md)
- [Export API](exports.md)

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-01 | Initial release for Stateless Core v1 |
