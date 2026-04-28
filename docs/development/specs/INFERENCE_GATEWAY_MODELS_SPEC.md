# Inference Gateway – Models Spec (OpenAI-compatible)

Status: Draft

Date: 2025-11-02

## Overview

Specifies `/v1/models` for model discovery and metadata augmentation. The
Gateway aggregates models across providers and exposes a unified list.

## Endpoints

- GET `/v1/models`
  - Returns list of available models (OpenAI shape: `{ data: [...] }`).
  - Includes `id`, `owned_by`, and optional metadata extensions (see below).

- GET `/v1/models/{model_id}` (optional)
  - Returns extended metadata when the upstream supports it.

## Response (examples)

```json
{
  "object": "list",
  "data": [
    { "id": "gpt-4o-mini", "object": "model", "owned_by": "openai" },
    { "id": "local-embed-384d", "object": "model", "owned_by": "local" }
  ]
}
```

Extensions (metadata, optional when available):

```json
{
  "context_window": 128000,
  "max_output_tokens": 4096,
  "supports_tools": true,
  "supports_vision": false,
  "embedding_dimensions": 384
}
```

## Behavior

- Aggregates providers registered in the Gateway control plane.
- Marks models unavailable if provider health reports down.
- May map aliases to target models (documented in control plane).

## Errors

- 401/403 Auth failures
- 5xx on internal errors

## Observability

- Log provider discovery durations and model counts.
