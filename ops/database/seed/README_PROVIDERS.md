# Provider Configuration Guide

## Overview

This guide explains the relationship between gateway providers, embedding models, and when to use each seed file.

## Key Concepts

### 1. Provider Type (`models.provider_type`)

The **type** of provider - an enum value indicating the API protocol/integration (per ADR-050):

- `'local'` - **Python in-process models** (SentenceTransformer), no HTTP API, integrated into application
- `'openai'` - **OpenAI-compatible API** (LMStudio, Ollama, vLLM, actual OpenAI) - all OpenAI-compatible providers
- `'anthropic'` - Anthropic Claude API
- `'mistral'` - Mistral AI API
- `'azure'` - Azure OpenAI (different auth pattern)
- `'other'` - Custom providers

**Always required** for all models.

**Reference:** `docs/development/adrs/ADR-050-Inference-Gateway-and-Responsibility-Split.md`

### 2. Provider Name (`models.provider`)

The **configured provider name** - references `gateway_providers.name`:

- `'LMStudio'` - Model served through LMStudio gateway
- `'OpenAI Production'` - Model served through OpenAI gateway
- `NULL` - Model served directly (not through inference gateway)

**Nullable** - use NULL for direct-served models.

### 3. Gateway Providers (`gateway_providers` table)

Configured provider instances in the inference gateway:

- Name: Human-readable identifier (e.g., "LMStudio")
- Base URL: Provider endpoint
- Priority: Routing priority
- Config: Provider-specific settings

## Architecture Patterns

### Pattern 1: Python In-Process Models (Integrated)

**When to use (ADR-050):**

- SentenceTransformer models loaded directly in Python
- No HTTP API, integrated into application
- Built-in models like all-MiniLM-L6-v2

**Configuration:**

```sql
-- Model configuration (no gateway provider needed)
provider_type: 'local'     ← Python in-process (SentenceTransformer)
provider: NULL             ← Not served through HTTP/gateway

-- Example: all-MiniLM-L6-v2
```

**Seed files:**

1. ✅ `006_seed_embedding_models.sql` - all-MiniLM-L6-v2 model

### Pattern 2: OpenAI-Compatible API Models

**When to use (ADR-050):**

- Models served through LMStudio, Ollama, vLLM, or OpenAI
- OpenAI-compatible HTTP API
- Need gateway routing, load balancing, or metrics

**Configuration:**

```sql
-- Gateway provider (OpenAI-compatible)
INSERT INTO gateway_providers (name, provider_type, base_url, ...)
VALUES ('LMStudio', 'openai', 'http://host.docker.internal:1234/v1', ...);

-- Model configuration
provider_type: 'openai'    ← OpenAI-compatible API protocol
provider: 'LMStudio'       ← Gateway provider name

-- Examples: BGE-M3, Nomic Embed (served through LMStudio)
provider: 'LMStudio'  ← References gateway_providers.name
```

**Seed files:**

1. ✅ `006_seed_embedding_models.sql` - Creates embedding models with appropriate provider values (LMStudio for OpenAI-compatible models, NULL for local models)
2. ✅ `010_seed_gateway_providers.sql` - Creates LMStudio gateway provider

## Seed File Usage

### Required Seeds

```bash
# 1. Create LMStudio gateway provider (required for OpenAI-compatible models)
psql -f ops/database/seed/010_seed_gateway_providers.sql

# 2. Create embedding models (includes both local and LMStudio models)
psql -f ops/database/seed/006_seed_embedding_models.sql
```

## Decision Guide

### Q: Which provider_type should I use?

**Use provider_type='local' (Python in-process) if:**

- ✅ SentenceTransformer models loaded directly in Python code
- ✅ No HTTP API - integrated into application
- ✅ Built-in models (all-MiniLM-L6-v2)
- ✅ No gateway routing needed

**Use provider_type='openai' (OpenAI-compatible) if:**

- ✅ Models served through LMStudio, Ollama, vLLM, or OpenAI
- ✅ OpenAI-compatible HTTP API
- ✅ Need gateway routing, fallback, or metrics
- ✅ Models accessed via `/v1/embeddings` endpoint

### Q: Can I have both?

**Yes!** You can have:

- Some models with `provider_type='local', provider=NULL` (Python in-process)
- Other models with `provider_type='openai', provider='LMStudio'` (LMStudio gateway)
- Additional models with `provider_type='openai', provider='OpenAI Production'` (OpenAI gateway)

Example:

```sql
-- Built-in Python in-process model (ADR-050: 'local')
'all-MiniLM-L6-v2'          provider_type='local', provider=NULL

-- LMStudio models (ADR-050: 'openai' for OpenAI-compatible)
'text-embedding-bge-m3'     provider_type='openai', provider='LMStudio'
'text-embedding-nomic-*'    provider_type='openai', provider='LMStudio'

-- Remote OpenAI (ADR-050: 'openai' for OpenAI-compatible)
'text-embedding-3-small'    provider_type='openai', provider='OpenAI Production'
```

## Migration Script

If you need to update existing models:

```sql
-- Check current configuration
SELECT model_id, provider_type, provider, embedding_dimensions
FROM models
WHERE model_type = 'embedding'
ORDER BY provider NULLS FIRST;

-- Move model from direct-served to LMStudio gateway
UPDATE models
SET provider = 'LMStudio'
WHERE model_id = 'text-embedding-bge-m3';

-- Move model from LMStudio to direct-served
UPDATE models
SET provider = NULL
WHERE model_id = 'all-MiniLM-L6-v2';
```

## Backend Handling

The backend automatically handles NULL providers:

```python
# src/corpus_svc/app/routers/collections.py
provider_from_registry = str(row[0]) if row[0] else "local"
```

This converts:

- `provider='LMStudio'` → `"LMStudio"` (gateway name)
- `provider=NULL` → `"local"` (direct-served)

## Summary

| Scenario | provider_type | provider | Gateway Required? | ADR-050 |
|----------|---------------|----------|-------------------|---------|
| Python in-process (SentenceTransformer) | `'local'` | `NULL` | No | ✅ Integrated |
| LMStudio (OpenAI-compatible) | `'openai'` | `'LMStudio'` | Yes | ✅ OpenAI API |
| Ollama (OpenAI-compatible) | `'openai'` | `'Ollama'` | Yes | ✅ OpenAI API |
| vLLM (OpenAI-compatible) | `'openai'` | `'vLLM'` | Yes | ✅ OpenAI API |
| OpenAI | `'openai'` | `'OpenAI Production'` | Yes | ✅ OpenAI API |
| Anthropic | `'anthropic'` | `'Anthropic'` | Yes | ✅ Claude API |

## Files Reference

- `006_seed_embedding_models.sql` - Creates embedding models (both local and LMStudio)
- `010_seed_gateway_providers.sql` - Creates LMStudio gateway provider
- `033_fix_embedding_model_provider_type.sql` - Migration to fix existing data (per ADR-050)

## Architecture Reference

- **ADR-050:** Inference Gateway and Responsibility Split
  - Defines `provider_type='local'` as Python in-process (SentenceTransformer)
  - Defines `provider_type='openai'` as OpenAI-compatible API (LMStudio, Ollama, vLLM)
