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

We provide multiple ways to build and run the LLM-Guard service, each addressing different deployment scenarios:

### Option 1: Using Docker Compose with Volume (Standard)

The LLM-Guard service is included in the main docker-compose.yml file and uses a named volume for model persistence:

```bash
# Build and start the entire stack including LLM-Guard
docker-compose -f deploy/docker-compose.yml up -d

# Or just build and start LLM-Guard service alone
docker-compose -f deploy/docker-compose.yml up -d llm-guard
```

### Option 2: Using the Build Script with Local Download (Recommended)

For more reliable builds, especially when dealing with network connectivity issues:

```bash
# Make the script executable
chmod +x ops/bootstrap/build_llm_guard.sh

# Run the build script to pre-download models and build the container
ops/bootstrap/build_llm_guard.sh

# Then start the service
docker-compose -f deploy/docker-compose.yml up -d llm-guard
```

This method:

- Creates a virtual environment to safely install dependencies
- Downloads models to a local cache directory before building
- Makes the Docker build more reliable by separating model download from the build process

### Option 3: Self-Contained Image Build (Best for Airgapped Environments)

This approach builds a self-contained image with models bundled directly:

```bash
# Make script executable
chmod +x ops/bootstrap/build_llm_guard_image.sh

# Build a self-contained image
ops/bootstrap/build_llm_guard_image.sh

# Modify docker-compose.yml to use the pre-built image
# Then run:
docker-compose -f deploy/docker-compose.yml up -d llm-guard
```

The script will generate instructions for updating your docker-compose.yml file.

### Option 4: Manual Model Download

If you prefer to directly download models yourself:

```bash
# Install dependencies in a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install "transformers[torch]"

# Download models to a local directory
python src/llm-guard/download_models.py --output-dir ./data/llm-guard-models

# Build and run with Docker Compose
docker-compose -f deploy/docker-compose.yml build llm-guard
docker-compose -f deploy/docker-compose.yml up -d llm-guard
```

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

## Hugging Face Token

Some models (like the prompt injection detection model) may require authentication to download. If you encounter an authentication error during the build process, you will need to provide a Hugging Face token.

### Getting a Token

1. Create a Hugging Face account at [huggingface.co](https://huggingface.co)
2. Go to your profile settings and navigate to the "Access Tokens" section
3. Create a new token with "read" permissions
4. Use this token when building the image

### Using the Token

With the build script:

```bash
./ops/bootstrap/build_llm_guard_image.sh --hf-token "YOUR_HF_TOKEN"
```

Or when building directly:

```bash
docker build --build-arg HF_TOKEN="YOUR_HF_TOKEN" -t llm-guard:latest ./src/llm-guard
```

## Troubleshooting

If you encounter issues with model downloads during Docker builds:

1. Use the provided `build_llm_guard_image.sh` script with a valid Hugging Face token
2. Ensure your network can reach huggingface.co
3. Check that the required model volume is properly mounted
4. If using a proxy, make sure it doesn't block access to Hugging Face
5. For build issues with system dependencies, the Dockerfile now includes all necessary build tools

### Common Error Messages

- **"Repository protectai/deberta-v3-base-prompt-injection-v2 not found"**: This model requires authentication. Provide a valid Hugging Face token.
- **"Failed building wheel for thinc"**: This is resolved in the updated Dockerfile by adding the necessary build dependencies.

## Models

The service uses the following models:

- `protectai/deberta-v3-base-prompt-injection-v2`: For prompt injection detection (requires Hugging Face authentication)
