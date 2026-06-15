# LLM Guard Service — multi-stage
# No OS compilers needed: online builds install binary wheels; offline builds
# install from the wheelhouse, whose sdists are compiled by
# ops/bootstrap/build_wheelhouse.sh on the connected host.

# Stage 1: Build dependencies
ARG BASE_REGISTRY=docker.io
FROM ${BASE_REGISTRY}/python:3.12-slim AS builder
WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG OFFLINE=0
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
# Opt-in model/ML scanner stack (torch, transformers, onnxruntime, gliner, spaCy).
# Default 0 = lean, CPU-only image with no torch and no nvidia-* CUDA wheels. The service
# is disabled by default and loads models lazily, so the lean image is the normal
# enterprise case. Set 1 only with the models staged and a CPU torch source.
ARG WITH_LLM_GUARD_MODELS=0

# Optional enterprise CA bundle: drop *.crt/*.pem into src/certs/ and image
# builds trust them (corporate TLS interception / internal Artifactory CA).
# Empty in public checkouts — the append is a no-op then.
COPY certs /certs
RUN cat /certs/*.crt /certs/*.pem >> /etc/ssl/certs/ca-certificates.crt 2>/dev/null || true
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# --- Copy requirements and prebuilt wheelhouse (host must build it for python 3.12/linux) ---
# NOTE (LLG-04 finale): no model files are downloaded during the build. The
# native scanners' ML models (the 3 ONNX classifiers + GLiNER + its mdeberta-v3
# backbone tokenizer) are staged separately by the operator into the mounted
# models volume before enabling the service — see src/llm_guard_svc/README.md.
# The former en/zh spaCy model wheels were dropped: the native PII path calls
# Presidio pattern recognizers directly (no spaCy NlpEngine), so no spaCy model
# is needed (the `spacy` library remains only as a presidio-analyzer dependency).
COPY llm_guard_svc/requirements.txt llm_guard_svc/requirements-models.txt ./
COPY wheelhouse /wheelhouse

# --- Base runtime deps (no torch): offline from wheelhouse (OFFLINE=1) or PyPI (OFFLINE=0) ---
RUN --mount=type=secret,id=netrc,target=/root/.netrc,required=false \
    if [ "$OFFLINE" = "1" ]; then \
        pip install --no-cache-dir --no-index --find-links=/wheelhouse -r requirements.txt; \
    else \
        pip install --no-cache-dir --index-url "$PIP_INDEX_URL" -r requirements.txt; \
    fi

# --- Optional model/ML scanner stack (torch, transformers, onnxruntime, gliner, spaCy) ---
# Default off → no torch, no nvidia-* CUDA wheels. When on, torch comes from
# TORCH_INDEX_URL (must be a CPU index) or the wheelhouse (OFFLINE=1); without a CPU torch
# source this pulls the CUDA build.
RUN --mount=type=secret,id=netrc,target=/root/.netrc,required=false \
    if [ "$WITH_LLM_GUARD_MODELS" = "1" ]; then \
        if [ "$OFFLINE" = "1" ]; then \
            pip install --no-cache-dir --no-index --find-links=/wheelhouse -r requirements-models.txt; \
        else \
            pip install --no-cache-dir --index-url "$TORCH_INDEX_URL" --extra-index-url "$PIP_INDEX_URL" \
                -r requirements-models.txt; \
        fi; \
    fi

# Stage 2: Runtime — wheelhouse and build inputs do not ship in this image
FROM ${BASE_REGISTRY}/python:3.12-slim
WORKDIR /app

# --- Set environment variables (safe defaults, no secrets) ---
# TRANSFORMERS_OFFLINE and HF_HUB_OFFLINE are omitted here intentionally:
# for OFFLINE=1 builds, set them via compose environment: block so online builds
# can freely download models from HuggingFace Hub.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8081 \
    HF_HOME=/app/models \
    PYTHONPATH="/app"

# --- Installed site-packages and console scripts from the builder ---
COPY --from=builder /usr/local /usr/local

# --- Create non-root user ---
RUN groupadd -r guarduser && useradd -r -g guarduser guarduser

# --- Prepare models directory ---
RUN mkdir -p /app/models

# --- Copy service and shared code ---
COPY llm_guard_svc/app /app/app
COPY shared /app/shared

# --- Set permissions ---
RUN chown -R guarduser:guarduser /app

USER guarduser

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; import sys; sys.exit(0) if urllib.request.urlopen('http://localhost:8081/health', timeout=5).getcode() == 200 else sys.exit(1)"]

EXPOSE ${PORT}

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8081"]
