# Embedding Service — multi-stage

# Stage 1: Build dependencies
ARG BASE_REGISTRY=docker.io
FROM ${BASE_REGISTRY}/python:3.12-slim AS builder
WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG OFFLINE=0
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
# Opt-in local embedding (torch + sentence-transformers). Default 0 = lean, CPU-only
# image with no torch and no nvidia-* CUDA wheels. Set 1 only with a CPU torch source.
ARG WITH_LOCAL_EMBEDDING=0

# Optional enterprise CA bundle: drop *.crt/*.pem into src/certs/ and image
# builds trust them (corporate TLS interception / internal Artifactory CA).
# Empty in public checkouts — the append is a no-op then.
COPY certs /certs
RUN cat /certs/*.crt /certs/*.pem >> /etc/ssl/certs/ca-certificates.crt 2>/dev/null || true
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Copy requirements and prebuilt wheels (from host)
COPY embedding/requirements.txt embedding/requirements-local.txt ./
COPY wheelhouse /wheelhouse

# Base runtime deps (no torch): offline from wheelhouse (OFFLINE=1) or from PyPI (OFFLINE=0).
RUN --mount=type=secret,id=netrc,target=/root/.netrc,required=false \
    if [ "$OFFLINE" = "1" ]; then \
        pip install --no-cache-dir --no-index --find-links=/wheelhouse -r requirements.txt; \
    else \
        pip install --no-cache-dir --index-url "$PIP_INDEX_URL" -r requirements.txt; \
    fi

# Optional local-embedding extras (torch + sentence-transformers). Default off → no torch,
# no nvidia-* CUDA wheels. When on, torch comes from TORCH_INDEX_URL (must be a CPU index)
# or the wheelhouse (OFFLINE=1); without a CPU torch source this pulls the CUDA build.
RUN --mount=type=secret,id=netrc,target=/root/.netrc,required=false \
    if [ "$WITH_LOCAL_EMBEDDING" = "1" ]; then \
        if [ "$OFFLINE" = "1" ]; then \
            pip install --no-cache-dir --no-index --find-links=/wheelhouse -r requirements-local.txt; \
        else \
            pip install --no-cache-dir --index-url "$TORCH_INDEX_URL" --extra-index-url "$PIP_INDEX_URL" -r requirements-local.txt; \
        fi; \
    fi

# Stage 2: Runtime — wheelhouse and build inputs do not ship in this image
FROM ${BASE_REGISTRY}/python:3.12-slim
WORKDIR /app

# --- Set environment variables (safe defaults, no secrets) ---
# TRANSFORMERS_OFFLINE and HF_HUB_OFFLINE are omitted here intentionally:
# for OFFLINE=1 builds, set them via compose environment: block so online builds
# can freely download models from HuggingFace Hub.
ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/models \
    PYTHONPATH="/app"

# Installed site-packages and console scripts from the builder
COPY --from=builder /usr/local /usr/local

# Trust the optional enterprise CA bundle at runtime too — the builder's trust
# store does not carry over. Online builds fetch models from HuggingFace Hub (or
# an internal mirror) at runtime over TLS; httpx/huggingface_hub honor
# SSL_CERT_FILE when trust_env is enabled (the default). No-op in public checkouts.
COPY certs /certs
RUN cat /certs/*.crt /certs/*.pem >> /etc/ssl/certs/ca-certificates.crt 2>/dev/null || true
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy service code and shared code
COPY embedding/app /app/app
COPY shared /app/shared

# Fix file permissions and create model directory
RUN chown -R appuser:appuser /app && \
    mkdir -p /opt/models && chown -R appuser:appuser /opt/models

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; import sys; sys.exit(0) if urllib.request.urlopen('http://localhost:8000/health', timeout=5).getcode() == 200 else sys.exit(1)"]

# Expose port
EXPOSE 8000

# Run service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
