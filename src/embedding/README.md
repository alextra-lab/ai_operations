# Embedding Service

The Embedding Service is a component of the AI Operations Platform system, providing text embedding generation using both OpenAI-compatible inference servers and local models.

## Features

- **Multiple Provider Support**:
  - Integration with OpenAI-compatible inference servers
  - Local model embedding using [sentence-transformers](https://www.sbert.net/)
  - Automatic fallback between providers

- **OpenAI Compatibility**:
  - Drop-in replacement for OpenAI's `/v1/embeddings` endpoint
  - Compatible with standard OpenAI client libraries

- **Configuration Management**:
  - YAML-based configuration files
  - Environment variable fallbacks
  - Hot reload capability via SIGHUP signal or admin endpoint

- **Observability**:
  - Comprehensive logging
  - Structured health checks
  - Detailed status monitoring

## API Endpoints

### Embedding Endpoints

- `POST /embed`: Generate embeddings using the default provider
  - Request: `EmbeddingRequest` with texts to embed
  - Response: `EmbeddingResponse` with embedding vectors

- `POST /embed/provider/{provider_name}`: Generate embeddings using a specific provider
  - Request: `EmbeddingRequest` with texts to embed
  - Response: `EmbeddingResponse` with embedding vectors

- `POST /embed/openai`: Generate embeddings in OpenAI-compatible format
  - Request: `OpenAIEmbeddingRequest` with input texts
  - Response: `OpenAIEmbeddingResponse` with OpenAI-compatible response format

- `GET /embed/models`: List available embedding models
  - Response: Dictionary mapping provider names to model information

- `POST /v1/embeddings`: OpenAI-compatible endpoint
  - Request: Standard OpenAI embeddings request format
  - Response: Standard OpenAI embeddings response format

### Admin Endpoints

- `POST /admin/reload`: Reload provider configuration
  - Response: `AdminConfigReloadResponse` with reload status and provider info

- `GET /admin/health`: Check health status of all providers
  - Response: Health status information for each provider

- `POST /admin/reload-signal`: Send SIGHUP signal to trigger configuration reload
  - Response: Signal status information

- `GET /admin/status`: Get comprehensive service status
  - Response: Status information including provider health, available models, and configuration

## Configuration

The service can be configured through a YAML file at one of these locations (in order of precedence):

1. Path specified by `CONFIG_PATH` environment variable
2. `/opt/models/models.yaml`
3. `/etc/embedding/models.yaml`
4. The package's default `app/config/models.yaml`

If no configuration file is found, the service will create a default configuration based on environment variables.

### Configuration Format

```yaml
default_provider: openai

providers:
  # OpenAI-compatible provider configuration
  openai:
    type: OPENAI_COMPATIBLE
    enabled: true
    priority: 10
    connection:
      url: http://localhost:8000/v1
      auth_type: API_KEY
      api_key_env: OPENAI_API_KEY
      timeout_seconds: 30
      max_retries: 3
    models:
      - name: text-embedding-3-small
        dimensions: 384
        server_model_name: text-embedding-3-small
        default: true
        batch_size: 32

  # Local model provider configuration (for fallback)
  local:
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

## Environment Variables

- `OPENAI_API_KEY`: API key for OpenAI-compatible provider
- `OPENAI_BASE_URL`: Base URL for OpenAI-compatible provider
- `MODEL_DIR`: Directory for local model files (default: `/opt/models`)
- `CONFIG_PATH`: Path to configuration file
- `DEBUG`: Enable debug mode (set to `true` to include error details in responses)
- `OTEL_EXPORTER_OTLP_ENDPOINT`: OpenTelemetry exporter endpoint

## Local Development

### Prerequisites

- Python 3.12+
- FastAPI
- OpenAI Python SDK
- Sentence Transformers (for local model provider)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Running the Service

```bash
# Run with default configuration
uvicorn app.main:app --reload

# Run with custom configuration
CONFIG_PATH=/path/to/config.yaml uvicorn app.main:app --reload
```

### Testing

```bash
# Run tests
pytest
```

## Docker Deployment

```bash
# Build the image
docker build -t embedding-service .

# Run the container
docker run -p 8000:8000 \
  -v /path/to/models:/opt/models \
  -v /path/to/config:/etc/embedding \
  -e OPENAI_API_KEY=your-api-key \
  -e OPENAI_BASE_URL=http://your-inference-server:8000/v1 \
  embedding-service
```

## Air-Gapped Deployment

For deployment in air-gapped environments, the embedding service can operate without internet access by:

1. Pre-downloading and including embedding models in the image or mounting them from a volume
2. Connecting to a local OpenAI-compatible inference server
3. Using a fallback to direct model loading if the inference server is unavailable

## Usage Examples

### Python Client

```python
import requests

# Generate embeddings using the default provider
response = requests.post(
    "http://localhost:8000/embed",
    json={
        "texts": ["Hello, world!", "Embedding example"],
        "model": "text-embedding-3-small"
    }
)
embeddings = response.json()["vectors"]

# Generate embeddings using the OpenAI-compatible endpoint
response = requests.post(
    "http://localhost:8000/v1/embeddings",
    json={
        "input": ["Hello, world!", "Embedding example"],
        "model": "text-embedding-3-small"
    }
)
embeddings = [item["embedding"] for item in response.json()["data"]]
```

### OpenAI Client Library

```python
from openai import OpenAI

# Initialize the client with the embedding service URL
client = OpenAI(
    api_key="your-api-key",
    base_url="http://localhost:8000/v1"
)

# Generate embeddings
response = client.embeddings.create(
    model="text-embedding-3-small",
    input=["Hello, world!", "Embedding example"]
)

# Get the embeddings
embeddings = [item.embedding for item in response.data]
