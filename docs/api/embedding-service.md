# Embedding Service API

**Service:** `embedding-service`
**Version:** v1
**Port:** 8005 (test), 8005 (production)

---

## Overview

The Embedding Service generates text embeddings for semantic search and RAG operations. It supports multiple providers:

| Provider | Model | Dimensions | Use Case |
|----------|-------|------------|----------|
| **local** | all-MiniLM-L6-v2 | 384 | Air-gapped, no API costs |
| **openai** | LMStudio models (nomic-embed, bge-m3, etc.) | 768-1024 | Higher quality, requires LMStudio |

---

## Authentication

All endpoints require JWT Bearer token authentication.

```bash
# Get token
TOKEN=$(curl -s -X POST "http://localhost:8006/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" \
  -d "password=adminpassword" | jq -r '.access_token')

# Use in requests
curl -H "Authorization: Bearer $TOKEN" http://localhost:8005/health
```

---

## Health Check

### `GET /health`

Returns service health and available providers.

**Response:**

```json
{
  "status": "healthy",
  "service": "embedding-service",
  "version": "v1",
  "providers": {
    "openai": {
      "available": true,
      "api_key_configured": true,
      "connection": true
    },
    "local": {
      "available": true,
      "sentence_transformers_installed": true,
      "models_loaded": true,
      "default_model_set": true
    }
  }
}
```

---

## Embedding Endpoints

### `POST /embed` - Default Provider

Generate embeddings using the default provider (configured in `models.yaml`).

**Request:**

```bash
curl -X POST http://localhost:8005/embed \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["What is a security incident?", "How to respond to ransomware?"],
    "model": null
  }'
```

**Response:**

```json
{
  "vectors": [
    [0.0123, -0.0456, ...],
    [0.0789, -0.0321, ...]
  ],
  "model": "all-minilm-l6-v2",
  "usage": {
    "prompt_tokens": 15,
    "total_tokens": 15
  }
}
```

---

### `POST /embed/provider/{provider_name}` - Specific Provider

Generate embeddings using a named provider.

**Local Provider Example:**

```bash
curl -X POST http://localhost:8005/embed/provider/local \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["test embedding with local model"]
  }'
```

**Response:**

```json
{
  "vectors": [[0.0123, -0.0456, ...]],
  "model": "all-minilm-l6-v2",
  "usage": {"prompt_tokens": 5, "total_tokens": 5}
}
```

**OpenAI/LMStudio Provider Example:**

```bash
curl -X POST http://localhost:8005/embed/provider/openai \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["test embedding with LMStudio"]
  }'
```

**Response:**

```json
{
  "vectors": [[0.0456, -0.0789, ...]],
  "model": "text-embedding-nomic-embed-text-v1.5",
  "usage": {"prompt_tokens": 5, "total_tokens": 5}
}
```

---

### `POST /v1/embeddings` - OpenAI-Compatible Format

Drop-in replacement for OpenAI's embeddings API.

**Request:**

```bash
curl -X POST http://localhost:8005/v1/embeddings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "What is a security incident?",
    "model": "local"
  }'
```

**Note:** The `model` parameter accepts `"local"` or `"openai"` (provider names), not model names.

**Response:**

```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "embedding": [0.0123, -0.0456, ...],
      "index": 0
    }
  ],
  "model": "all-minilm-l6-v2",
  "usage": {
    "prompt_tokens": 6,
    "total_tokens": 6
  }
}
```

---

### `GET /embed/models` - List Available Models

Returns all available models across providers.

**Request:**

```bash
curl http://localhost:8005/embed/models \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**

```json
{
  "local": {
    "all-minilm-l6-v2": {
      "dimensions": 384,
      "default": true,
      "batch_size": 16
    }
  },
  "openai": {
    "text-embedding-nomic-embed-text-v1.5": {
      "dimensions": 768,
      "default": true,
      "batch_size": 16,
      "server_model_name": "text-embedding-nomic-embed-text-v1.5@q4_k_m"
    },
    "text-embedding-bge-m3": {
      "dimensions": 1024,
      "default": false,
      "batch_size": 8,
      "server_model_name": "text-embedding-bge-m3"
    }
  }
}
```

---

## Admin Endpoints

### `GET /admin/status`

Comprehensive service status including configuration.

```bash
curl http://localhost:8005/admin/status \
  -H "Authorization: Bearer $TOKEN"
```

### `POST /admin/reload`

Hot-reload configuration without restart.

```bash
curl -X POST http://localhost:8005/admin/reload \
  -H "Authorization: Bearer $TOKEN"
```

### `GET /admin/health`

Detailed health check for each provider.

```bash
curl http://localhost:8005/admin/health \
  -H "Authorization: Bearer $TOKEN"
```

---

## Configuration

### Configuration File Location

The service looks for `models.yaml` in this order:

1. `CONFIG_PATH` environment variable
2. `/opt/models/models.yaml`
3. `/etc/embedding/models.yaml`
4. Built-in `app/config/models.yaml`

### Example Configuration

```yaml
# src/embedding/app/config/models.yaml
default_provider: local

providers:
  # LMStudio/OpenAI-compatible provider
  - name: openai
    type: OPENAI_COMPATIBLE
    enabled: true
    priority: 10
    connection:
      url: http://host.docker.internal:1234/v1  # LMStudio on host
      auth_type: API_KEY
      api_key_env: OPENAI_API_KEY
      timeout_seconds: 60
      max_retries: 3
    models:
      - name: text-embedding-nomic-embed-text-v1.5
        dimensions: 768
        server_model_name: text-embedding-nomic-embed-text-v1.5@q4_k_m
        default: true
        batch_size: 16
      - name: text-embedding-bge-m3
        dimensions: 1024
        server_model_name: text-embedding-bge-m3
        default: false
        batch_size: 8

  # Local model provider (built-in, always available)
  - name: local
    type: LOCAL_MODEL
    enabled: true
    priority: 20
    models:
      - name: all-minilm-l6-v2
        dimensions: 384
        path: /opt/models/all-minilm-l6-v2
        default: true
        batch_size: 16
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | API key for OpenAI provider | Required for OpenAI |
| `CONFIG_PATH` | Path to models.yaml | Auto-detected |
| `MODEL_DIR` | Local model directory | `/opt/models` |
| `LOG_LEVEL` | Logging level | `INFO` |

---

## Docker Compose Configuration

### Test Environment

```yaml
# deploy/docker-compose.test.yml
embedding-service:
  build:
    context: ../src
    dockerfile: embedding/Dockerfile
  container_name: embedding-service-test
  environment:
    - ENV=testing
    - LOG_LEVEL=INFO
    - QDRANT_URL=http://qdrant-test:6333
    - OPENAI_API_KEY=${OPENAI_API_KEY:-sk-lmstudio}
  volumes:
    - ../data/models:/opt/models:cached
  ports:
    - "8005:8000"
```

### LMStudio Integration

To use LMStudio as the OpenAI provider:

1. Start LMStudio on your host machine
2. Load an embedding model (e.g., `nomic-embed-text-v1.5`)
3. Ensure the server is running on port 1234
4. The Docker container connects via `host.docker.internal:1234`

**Verify LMStudio is running:**

```bash
curl http://localhost:1234/v1/models | jq '.data[].id'
```

---

## Usage Examples

### Python with requests

```python
import requests

BASE_URL = "http://localhost:8005"
TOKEN = "your-jwt-token"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Generate embeddings with local model
response = requests.post(
    f"{BASE_URL}/embed/provider/local",
    headers=headers,
    json={"texts": ["Hello, world!", "Security incident report"]}
)

embeddings = response.json()["vectors"]
print(f"Generated {len(embeddings)} embeddings with {len(embeddings[0])} dimensions")
```

### Python with OpenAI client

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-jwt-token",  # Use JWT token as API key
    base_url="http://localhost:8005/v1"
)

response = client.embeddings.create(
    model="local",  # Provider name, not model name
    input=["Hello, world!", "Security incident report"]
)

embeddings = [item.embedding for item in response.data]
```

### Bash script for batch processing

```bash
#!/bin/bash
set -e

BASE_URL="http://localhost:8005"
TOKEN=$(curl -s -X POST "http://localhost:8006/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" -d "password=adminpassword" | jq -r '.access_token')

# Test both providers
echo "=== Local Provider ==="
curl -s -X POST "$BASE_URL/embed/provider/local" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"texts": ["test"]}' | jq '{model, dims: (.vectors[0] | length)}'

echo "=== OpenAI/LMStudio Provider ==="
curl -s -X POST "$BASE_URL/embed/provider/openai" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"texts": ["test"]}' | jq '{model, dims: (.vectors[0] | length)}'
```

---

## Troubleshooting

### Provider Not Available

**Symptom:** Health check shows `"providers": {}`

**Cause:** Configuration file not found or invalid

**Fix:**

1. Check CONFIG_PATH is set correctly
2. Verify models.yaml syntax
3. Check Docker volume mounts

```bash
docker exec embedding-service-test cat /app/app/config/models.yaml
```

### OpenAI Provider Missing API Key

**Symptom:** `"Error initializing provider: Missing required API key"`

**Fix:** Add `OPENAI_API_KEY` to docker-compose environment:

```yaml
environment:
  - OPENAI_API_KEY=${OPENAI_API_KEY:-sk-lmstudio}
```

### LMStudio Connection Failed

**Symptom:** OpenAI provider shows `"connection": false`

**Causes:**

1. LMStudio not running
2. Wrong port configured
3. `host.docker.internal` not resolving (Linux)

**Fix for Linux:**

```yaml
# docker-compose.yml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

### Local Model Not Loading

**Symptom:** `"models_loaded": false`

**Fix:** Ensure model files exist:

```bash
ls -la data/models/all-minilm-l6-v2/
# Should contain model files
```

---

## Related Documentation

- [Embedding Model Architecture Guide](../development/guides/embedding-model-architecture-guide.md)
- [Collection Management API](./collection-management.md)
- [Document Management API](./documents.md)

---

**Last Updated:** November 30, 2025
