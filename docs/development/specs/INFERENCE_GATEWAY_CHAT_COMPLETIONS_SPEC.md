# Inference Gateway – Chat Completions Spec (OpenAI-compatible)

Status: Draft

Date: 2025-11-02

## Overview

This document specifies the `/v1/chat/completions` endpoint implemented by the
Inference Gateway. The goal is OpenAI compatibility with centralized routing,
rate limits, metering, and error taxonomy (ADR-054).

## Endpoint

- Method: POST
- Path: `/v1/chat/completions`
- Auth: Service-to-service JWT (ADR-049); scopes: `inference:chat`
- Headers:
  - `Authorization: Bearer <S2S_JWT>`
  - `X-Request-ID` (optional; generated if absent)
  - `X-Tenant-ID` (optional; preferred claim-based)
  - `Content-Type: application/json`

## Request Schema (compatible subset)

```json
{
  "model": "alias-or-provider-model-id",
  "messages": [
    { "role": "system|user|assistant|tool", "content": "..." }
  ],
  "temperature": 0.0,
  "max_tokens": 1024,
  "top_p": 1.0,
  "stream": false,
  "stop": ["\n\n"],
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0,
  "user": "optional-user-surrogate"
}
```

Notes:
- `model` may be a logical alias; Gateway resolves to provider target (ADR-052).
- Unsupported fields are ignored to preserve compatibility.

## Response (sync)

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1730520000,
  "model": "resolved-provider-model-id",
  "choices": [
    {
      "index": 0,
      "message": { "role": "assistant", "content": "..." },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 123,
    "completion_tokens": 45,
    "total_tokens": 168
  }
}
```

## Streaming (SSE)

- Request: set `stream: true`.
- Response: `Content-Type: text/event-stream`.
- Each chunk is a `data: {...}` JSON object; final chunk is `data: [DONE]`.
- Gateway flushes promptly; preserves ordering; includes request-level `id`.

Example chunk:

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion.chunk",
  "created": 1730520001,
  "model": "resolved-provider-model-id",
  "choices": [
    {
      "index": 0,
      "delta": { "content": "partial" },
      "finish_reason": null
    }
  ]
}
```

## Error Responses

- 400 Validation error (missing/invalid fields)
- 401/403 Auth failures
- 408 Timeout
- 429 Rate limit exceeded (Retry-After)
- 5xx Upstream/provider errors

Error body (OpenAI-style):

```json
{
  "error": { "message": "...", "type": "rate_limit_error", "code": "429" }
}
```

## Rate Limiting & Quotas

- Enforced per ADR-053 (tenant/provider/model). On 429, return Retry-After.
- Quota exhaustion may return 402/403 with structured details.

## Observability & Cost

- Usage and cost recorded per request (ADR-055). Include alias, provider, model.
- Headers: `X-Request-ID` echoed; tracing context propagated.

## Performance Budgets

- Streaming first-byte target: <200ms added overhead vs provider.
- p95 added latency (non-stream): <10ms at moderate RPS.

## Compatibility Notes

- Response fields should include `usage` if provider reports it; otherwise, use
  safe defaults and mark as estimated where applicable.
