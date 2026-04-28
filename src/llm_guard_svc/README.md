# LLM-Guard Service

An API service that provides input validation and sanitization for LLM interactions using [LLM-Guard](https://github.com/protectai/llm-guard).

## Features

- Prompt injection detection and prevention
- Sensitive information detection and redaction
- Content moderation (toxicity, banned topics)
- Code detection
- Gibberish detection
- Language filtering

## Architecture

The service exposes a FastAPI application that provides endpoints for validating text inputs before they are sent to LLMs. This adds a crucial security layer to the AI Operations platform.

## Building and Running

### Prerequisites

Before building and running the LLM-Guard service, you must have the required models available in the `data/llm-guard-models` directory. The service will not function without these models.

The service requires the following models to be present (directory names must match):

- `Isotonic/distilbert_finetuned_ai4privacy_v2` → `distilbert_finetuned_ai4privacy_v2`
- `madhurjindal/autonlp-Gibberish-Detector-492513457` → `madhurjindal-autonlp-Gibberish-Detector-492513457`
- `protectai/xlm-roberta-base-language-detection-onnx` → `protectai-xlm-roberta-base-language-detection-onnx`
- `protectai/deberta-v3-small-prompt-injection-v2` → `protectai-deberta-v3-small-prompt-injection-v2`

You can download models using the bootstrap script (recommended):

```bash
python ops/bootstrap/download_llm_guard_models.py --output-dir data/llm-guard-models
```

Or download manually from Hugging Face using git:

```bash
# Create models directory if it doesn't exist
mkdir -p data/llm-guard-models

# Download each required model (target directory names must match guard.py expectations)
git clone https://huggingface.co/Isotonic/distilbert_finetuned_ai4privacy_v2 data/llm-guard-models/distilbert_finetuned_ai4privacy_v2
git clone https://huggingface.co/madhurjindal/autonlp-Gibberish-Detector-492513457 data/llm-guard-models/madhurjindal-autonlp-Gibberish-Detector-492513457
git clone https://huggingface.co/protectai/xlm-roberta-base-language-detection-onnx data/llm-guard-models/protectai-xlm-roberta-base-language-detection-onnx
git clone https://huggingface.co/protectai/deberta-v3-small-prompt-injection-v2 data/llm-guard-models/protectai-deberta-v3-small-prompt-injection-v2
```

### Using Docker Compose (Standard)

Once the models are downloaded, you can build and run the LLM-Guard service using Docker Compose:

```bash
# Build and start the entire stack including LLM-Guard
docker-compose -f deploy/docker-compose.yml build
docker-compose -f deploy/docker-compose.yml up -d

# Or just build and start LLM-Guard service alone
docker-compose -f deploy/docker-compose.yml build llm-guard
docker-compose -f deploy/docker-compose.yml up -d llm-guard
```

The service is configured to mount the models directory from `data/llm-guard-models` to `/app/models` inside the container.

## API Usage

### Main Endpoint

```
POST /api/validate
```

#### Request Body

```json
{
  "input_text": "Text to validate",
  "context": {
    "optional_context": "value"
  },
  "strict_mode": false
}
```

#### Response

```json
{
  "sanitized_text": "Text after sanitization",
  "risk_score": 0.25,
  "modified": true,
  "details": {
    "scanner_results": {}
  }
}
```

### Health Check

```
GET /health
```

## Troubleshooting

If you encounter issues with the LLM-Guard service:

1. Ensure all required models are properly downloaded to the `data/llm-guard-models` directory
2. Verify the models are correctly mounted to the container via the volume configuration
3. Check the container logs for any startup errors: `docker logs llm-guard`
4. Ensure your network can reach huggingface.co if downloading models
5. If using a proxy, make sure it doesn't block necessary connections

### Common Error Messages

- **"Cannot access files in /app/models"**: Verify that the models directory is properly mounted and has the required files
- **"Failed building wheel for thinc"**: This is resolved in the Dockerfile by including the necessary build dependencies

## Models

The service uses the following models:

- `Isotonic/distilbert_finetuned_ai4privacy_v2`: For PII and sensitive information detection
- `madhurjindal/autonlp-Gibberish-Detector-492513457`: For gibberish detection
- `protectai/xlm-roberta-base-language-detection-onnx`: For language detection
- `protectai/deberta-v3-small-prompt-injection-v2`: For prompt injection detection
