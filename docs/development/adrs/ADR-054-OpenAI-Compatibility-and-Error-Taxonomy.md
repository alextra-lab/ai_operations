# ADR-054: OpenAI Compatibility and Error Taxonomy

**Status:** Approved
**Date:** 2025-11-02
**Deciders:** Backend Team, Integration Team
**Tags:** api, compatibility, error-handling, openai

---

## Context

The Inference Gateway must present an OpenAI-compatible API to minimize migration risk and maximize ecosystem compatibility. The existing `LLMClient` (`src/orchestrator/app/orchestrator/llm_client.py`) uses the OpenAI Python SDK, which expects specific request/response formats and error handling.

### Requirements

**API Compatibility:**
- Drop-in replacement for OpenAI endpoints (orchestrator code unchanged)
- Support existing OpenAI SDK clients (Python `openai` library)
- Compatible with third-party tools (LangChain, LlamaIndex, etc.)

**Streaming Compatibility:**
- Server-Sent Events (SSE) with proper chunking
- `text/event-stream` content type
- `data: ` prefix and `[DONE]` terminator
- Proper flush behavior for low latency

**Error Handling:**
- Consistent error format across providers
- Standard HTTP status codes
- Retry-friendly error messages
- Provider-agnostic error abstraction

### Existing OpenAI Usage

**Orchestrator LLMClient:**
```python
# src/orchestrator/app/orchestrator/llm_client.py
from openai import OpenAI

self.client = OpenAI(
    api_key=api_key,
    base_url=base_url,  # Will point to Gateway
    timeout=10.0
)

# Sync request
response = self.client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    temperature=0.7,
    max_tokens=1024
)

# Streaming request
stream = self.client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    stream=True
)
for chunk in stream:
    content = chunk.choices[0].delta.content
```

**Goal:** Gateway works with this code **without changes**.

---

## Decision

Implement OpenAI-compatible endpoints with faithful request/response formats and comprehensive error taxonomy.

### API Endpoints

#### 1. Chat Completions (Sync)

**Endpoint:** `POST /v1/chat/completions`

**Request:**
```json
{
    "model": "gpt-4o-mini",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is RAG?"}
    ],
    "temperature": 0.7,
    "max_tokens": 1024,
    "top_p": 1.0,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
    "stop": null,
    "stream": false,
    "user": "analyst_john"  // Optional user identifier
}
```

**Response:**
```json
{
    "id": "chatcmpl-abc123",
    "object": "chat.completion",
    "created": 1730559000,
    "model": "gpt-4o-mini",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "RAG (Retrieval-Augmented Generation) is..."
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 25,
        "completion_tokens": 150,
        "total_tokens": 175
    },
    "system_fingerprint": "fp_gateway_v1"  // Optional
}
```

**Headers:**
```http
HTTP/1.1 200 OK
Content-Type: application/json
X-Request-ID: abc-123-def-456
X-Gateway-Provider: openai
X-Gateway-Model: gpt-4o-mini
X-Gateway-Latency-Ms: 245
```

#### 2. Chat Completions (Streaming)

**Request:** Same as sync, with `"stream": true`

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Request-ID: abc-123-def-456

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1730559000,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1730559000,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{"content":"RAG"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1730559000,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{"content":" stands"},"finish_reason":null}]}

...

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1730559000,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":25,"completion_tokens":150,"total_tokens":175}}

data: [DONE]
```

**Key SSE Requirements:**
- `data: ` prefix for each chunk (NOT `event: message\ndata: `)
- Proper flush after each chunk (low latency)
- `[DONE]` terminator at end
- Final chunk includes `usage` if available
- Chunks sent as received (no buffering)

#### 3. Embeddings

**Endpoint:** `POST /v1/embeddings`

**Request:**
```json
{
    "model": "text-embedding-3-small",
    "input": [
        "Malware analysis techniques",
        "Threat intelligence sources"
    ],
    "encoding_format": "float"  // or "base64"
}
```

**Response:**
```json
{
    "object": "list",
    "data": [
        {
            "object": "embedding",
            "embedding": [0.123, -0.456, 0.789, ...],  // 1536 dimensions
            "index": 0
        },
        {
            "object": "embedding",
            "embedding": [0.321, -0.654, 0.987, ...],
            "index": 1
        }
    ],
    "model": "text-embedding-3-small",
    "usage": {
        "prompt_tokens": 12,
        "total_tokens": 12
    }
}
```

**Behavior:**
- Input order preserved in output (index field)
- Batching handled internally (transparent to caller)
- Dimensions from model metadata (not in response)

#### 4. Models List

**Endpoint:** `GET /v1/models`

**Response:**
```json
{
    "object": "list",
    "data": [
        {
            "id": "gpt-4o-mini",
            "object": "model",
            "owned_by": "openai",
            "created": 1730559000
        },
        {
            "id": "gpt-4o",
            "object": "model",
            "owned_by": "openai",
            "created": 1730559000
        },
        {
            "id": "local/llama-3.1-8b",
            "object": "model",
            "owned_by": "local",
            "created": 1730559000
        }
    ]
}
```

**Optional Extensions (Non-Standard):**
```json
{
    "id": "gpt-4o-mini",
    "object": "model",
    "owned_by": "openai",
    "created": 1730559000,
    // Gateway-specific metadata (optional)
    "context_window": 128000,
    "max_output_tokens": 4096,
    "supports_tools": true,
    "supports_vision": false,
    "input_price_per_million": 0.15,
    "output_price_per_million": 0.60
}
```

### Vision Support (Forward Compatible)

**Message Format:**
```json
{
    "model": "gpt-4o",
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Analyze this network diagram"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "data:image/png;base64,iVBORw0KGgoAAAANS..."
                    }
                }
            ]
        }
    ]
}
```

**Gateway Handling:**
- Proxy vision messages transparently (no special processing)
- Provider must support vision (check `supports_vision` flag)
- Return 400 if vision not supported for model
- Activated when document image upload feature ready

### Tool Calling Support (Pass-Through)

**Request with Tools:**
```json
{
    "model": "gpt-4o",
    "messages": [...],
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "search_threat_intel",
                "description": "Search threat intelligence database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ioc": {"type": "string", "description": "Indicator of compromise"}
                    },
                    "required": ["ioc"]
                }
            }
        }
    ],
    "tool_choice": "auto"
}
```

**Response with Tool Calls:**
```json
{
    "id": "chatcmpl-abc123",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": null,
                "tool_calls": [
                    {
                        "id": "call_abc123",
                        "type": "function",
                        "function": {
                            "name": "search_threat_intel",
                            "arguments": "{\"ioc\": \"192.0.2.1\"}"
                        }
                    }
                ]
            },
            "finish_reason": "tool_calls"
        }
    ]
}
```

**Gateway Responsibility:**
- Proxy `tools` array to provider (no validation)
- Proxy `tool_calls` in response (no execution)
- **Orchestrator executes tools** (via MCP/Tools Track)

---

## Error Taxonomy

### HTTP Status Code Mapping

| Status Code | Error Type | When to Use |
|-------------|------------|-------------|
| **400** | `invalid_request_error` | Missing required fields, invalid JSON, malformed request |
| **401** | `authentication_error` | Missing or invalid JWT token |
| **403** | `permission_denied_error` | Token valid but missing required scope |
| **404** | `not_found_error` | Model not found, endpoint not found |
| **408** | `timeout_error` | Provider timeout (10+ seconds) |
| **422** | `validation_error` | Invalid parameter values (e.g., `temperature` > 2.0) |
| **429** | `rate_limit_error` | Gateway or provider rate limit exceeded |
| **500** | `internal_server_error` | Gateway internal error (bug) |
| **502** | `bad_gateway_error` | Provider returned invalid response |
| **503** | `service_unavailable_error` | Provider down, circuit breaker open |
| **504** | `gateway_timeout_error` | Provider timeout (network-level) |

### Error Response Format

**Standard OpenAI Error:**
```json
{
    "error": {
        "message": "Provider OpenAI rate limit exceeded",
        "type": "rate_limit_error",
        "code": "rate_limit_exceeded"
    }
}
```

**Enhanced Gateway Error (Optional Extensions):**
```json
{
    "error": {
        // OpenAI-compatible fields
        "message": "Provider OpenAI rate limit exceeded",
        "type": "rate_limit_error",
        "code": "rate_limit_exceeded",

        // Gateway-specific extensions (non-standard but helpful)
        "provider": "openai",
        "model": "gpt-4o-mini",
        "retry_after": 30,
        "suggestion": "Try again in 30 seconds or use local model",
        "request_id": "abc-123-def-456"
    }
}
```

### Provider Error Mapping

**OpenAI Errors → Gateway Errors:**
| OpenAI Error | Gateway Status | Gateway Type |
|--------------|----------------|--------------|
| `invalid_request_error` | 400 | `invalid_request_error` |
| `authentication_error` | 502 | `provider_authentication_error` |
| `rate_limit_error` | 429 | `provider_rate_limit_error` |
| `server_error` | 502 | `provider_error` |
| `timeout` | 504 | `provider_timeout_error` |

**Mistral Errors → Gateway Errors:**
| Mistral Error | Gateway Status | Gateway Type |
|---------------|----------------|--------------|
| `400 Bad Request` | 400 | `invalid_request_error` |
| `401 Unauthorized` | 502 | `provider_authentication_error` |
| `429 Too Many Requests` | 429 | `provider_rate_limit_error` |
| `500 Internal Error` | 502 | `provider_error` |

**Local Provider Errors → Gateway Errors:**
| Local Error | Gateway Status | Gateway Type |
|-------------|----------------|--------------|
| Connection refused | 503 | `provider_unavailable_error` |
| Process crash | 503 | `provider_unavailable_error` |
| Timeout | 504 | `provider_timeout_error` |

### Error Logging

**Structured Logs (using `shared.logging_utils`):**
```python
# src/inference-gateway/app/error_handling/logger.py
from shared.logging_utils.fastapi import configure_logging

logger = configure_logging(service_name="gateway_errors")

def log_error(
    error_type: str,
    status_code: int,
    message: str,
    request_id: str,
    provider: str | None = None,
    model: str | None = None,
    user_id: str | None = None
):
    """Log error with full context."""

    logger.error(
        f"Gateway error: {error_type}",
        extra={
            "error_type": error_type,
            "status_code": status_code,
            "message": message,
            "request_id": request_id,
            "provider": provider,
            "model": model,
            "user_id": user_id,
            "timestamp": datetime.now(UTC).isoformat()
        }
    )
```

**Error Response Builder:**
```python
class ErrorResponse(BaseModel):
    """OpenAI-compatible error response."""

    error: dict

    @classmethod
    def from_exception(
        cls,
        exc: Exception,
        request_id: str,
        provider: str | None = None,
        model: str | None = None
    ) -> tuple["ErrorResponse", int]:
        """Convert exception to error response."""

        if isinstance(exc, ModelNotFoundError):
            return cls(
                error={
                    "message": str(exc),
                    "type": "not_found_error",
                    "code": "model_not_found",
                    "request_id": request_id
                }
            ), 404

        elif isinstance(exc, ProviderRateLimitError):
            return cls(
                error={
                    "message": str(exc),
                    "type": "rate_limit_error",
                    "code": "provider_rate_limit",
                    "provider": provider,
                    "retry_after": exc.retry_after,
                    "request_id": request_id
                }
            ), 429

        elif isinstance(exc, ProviderTimeoutError):
            return cls(
                error={
                    "message": str(exc),
                    "type": "timeout_error",
                    "code": "provider_timeout",
                    "provider": provider,
                    "suggestion": "Retry request or try different model",
                    "request_id": request_id
                }
            ), 504

        # ... more mappings

        else:
            # Unknown error (500)
            return cls(
                error={
                    "message": "Internal server error",
                    "type": "internal_server_error",
                    "code": "unknown_error",
                    "request_id": request_id
                }
            ), 500
```

---

## Rationale

### Why OpenAI Compatibility?

**Ecosystem Adoption:**
- OpenAI API is de facto standard for LLM APIs
- VLLM, LMStudio, Ollama all provide OpenAI-compatible endpoints
- Most LLM tools (LangChain, etc.) support OpenAI format
- Python `openai` SDK widely used and familiar

**Migration Simplicity:**
```python
# Before (direct OpenAI)
client = OpenAI(base_url="https://api.openai.com/v1")

# After (via Gateway) - SAME CODE
client = OpenAI(base_url="http://inference-gateway:8002")
```

**Future-Proof:**
- New providers likely to adopt OpenAI format (momentum)
- Gateway normalizes differences (provider-agnostic clients)

### Why Comprehensive Error Taxonomy?

**Operator Debuggability:**
```
Bad Error:
  "Error 500: Internal Server Error"
  → Operator: "What failed? Where? Why?"

Good Error:
  {
    "error": {
      "message": "Provider OpenAI timeout after 10 seconds",
      "type": "provider_timeout_error",
      "provider": "openai",
      "model": "gpt-4o-mini",
      "request_id": "abc-123",
      "suggestion": "Check OpenAI status page or try local model"
    }
  }
  → Operator: "OpenAI is slow, check status or switch to local"
```

**Retry Logic:**
- 429 = Retry after N seconds (header-based)
- 503 = Retry immediately with different provider
- 504 = Retry once, then give up
- 500 = Don't retry (Gateway bug)

### Why Streaming Pass-Through?

**Latency Sensitivity:**
```
Buffered Streaming (BAD):
  Provider sends chunk → Gateway buffers → waits for 10 chunks → sends batch
  First chunk latency: 2-5 seconds (terrible UX)

Pass-Through Streaming (GOOD):
  Provider sends chunk → Gateway forwards immediately
  First chunk latency: 200-500ms (good UX)
```

**Implementation:**
```python
async def stream_chat_completion(request):
    """Stream response without buffering."""

    async def generate():
        async for chunk in provider.stream_chat(request):
            # Forward chunk immediately (no buffering)
            yield f"data: {chunk.json()}\n\n"

        # Send terminator
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"}
    )
```

---

## Consequences

### Positive

✅ **Zero Migration Effort:** Orchestrator code unchanged (change `base_url` only)
✅ **Ecosystem Compatibility:** Works with OpenAI SDK, LangChain, etc.
✅ **Provider Abstraction:** Clients don't know if backend is OpenAI, Mistral, or local
✅ **Clear Errors:** Operators understand failures and can take action
✅ **Retry-Friendly:** Error codes guide retry logic (when to retry, when to fail)

### Negative

❌ **Provider Normalization Overhead:** Must map provider differences to OpenAI format
❌ **Streaming Complexity:** SSE streaming has edge cases (connection drops, partial chunks)
❌ **Version Drift:** OpenAI may add new fields (must keep up)

### Mitigation

**Provider Normalization:**
- Most providers already OpenAI-compatible (VLLM, LMStudio)
- Mistral differences minimal (mostly field names)
- Local providers follow OpenAI format

**Streaming Complexity:**
- Use battle-tested FastAPI `StreamingResponse`
- Proper exception handling for connection drops
- Integration tests with real streaming responses

**Version Drift:**
- Monitor OpenAI changelog
- Unsupported fields ignored gracefully
- Optional fields with safe defaults

---

## Acceptance Criteria

✅ **Compatibility:**
- OpenAI Python SDK works with Gateway (no code changes)
- Sync requests match OpenAI response format exactly
- Streaming SSE matches OpenAI format (data prefix, DONE terminator)

✅ **Vision & Tools:**
- Vision messages proxied transparently (provider must support)
- Tool definitions proxied transparently (orchestrator executes)

✅ **Error Handling:**
- All errors return OpenAI-compatible error object
- HTTP status codes follow standard mapping
- Retry-After header present on 429 responses
- Error messages actionable (operator knows what to do)

✅ **Performance:**
- Streaming first chunk <200ms added latency
- Sync response parsing <10ms overhead
- Error serialization <5ms

---

## References

### Related ADRs

- **ADR-050:** Inference Gateway and Responsibility Split
- **ADR-052:** Model Routing and Provider Fallback (error handling integration)

### Existing Code

- `src/orchestrator/app/orchestrator/llm_client.py` - OpenAI SDK usage
- `src/orchestrator/app/orchestrator/llm_router.py` - Streaming response handling
- `src/shared/logging_utils/fastapi.py` - Structured error logging

### External References

- OpenAI API Docs: https://platform.openai.com/docs/api-reference
- OpenAI Errors: https://platform.openai.com/docs/guides/error-codes
- SSE Specification: https://html.spec.whatwg.org/multipage/server-sent-events.html
- VLLM OpenAI Compatibility: https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html

---

**Document Owner:** Backend Team
**Last Updated:** 2025-11-02
**Status:** Approved for Implementation
