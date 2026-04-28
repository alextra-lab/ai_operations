# Inference Gateway – Embeddings Spec (OpenAI-compatible)

Status: Draft

Date: 2025-11-02

## Overview

Specifies `/v1/embeddings` implemented by the Inference Gateway. Supports
routing to remote providers and delegation to the existing Embedding Service
for local models, with batching and order preservation.

## Endpoint

- Method: POST
- Path: `/v1/embeddings`
- Auth: S2S JWT; scopes: `inference:embed`
- Headers: `Authorization`, `X-Request-ID`, `X-Tenant-ID`, `Content-Type`

## Request Schema

```json
{
  "model": "alias-or-provider-model-id-or-local",
  "input": ["text1", "text2", "..."]
}
```

Notes:
- `input` can be a string or list of strings; normalized to list internally.
- `model` may be a logical alias (ADR-052). `local` may delegate to Embedding
  Service for SentenceTransformers.

## Response

```json
{
  "object": "list",
  "data": [
    { "object": "embedding", "embedding": [0.1, 0.2, ...], "index": 0 },
    { "object": "embedding", "embedding": [0.1, 0.2, ...], "index": 1 }
  ],
  "model": "resolved-provider-model-id-or-local",
  "usage": { "prompt_tokens": 0, "total_tokens": 0 }
}
```

## Behavior

- Batching: Gateway splits large inputs by configured batch size per model.
- Order: Output `index` preserves input ordering across batches.
- Dimensions: Exposed via `/v1/models` metadata; not repeated per response.

## Errors

- 400 Invalid input types or empty list
- 401/403 Auth failures
- 429 Rate limiting per ADR-053
- 5xx Upstream errors

## Observability

- Record per-request count of vectors, per-batch timings, and total latency.
- Include alias/provider/model in logs and usage records (ADR-055).

## Performance Budgets

- Batch-level overhead <10ms per batch; total overhead proportional to batches.
- Concurrency limited per provider/model to avoid saturation.
