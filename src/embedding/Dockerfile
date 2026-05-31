# Stage 1: Build dependencies
ARG BASE_REGISTRY=docker.io/library
FROM ${BASE_REGISTRY}/python:3.12-slim AS builder
WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.org/simple

# --- Set environment variables (safe defaults, no secrets) ---
# TRANSFORMERS_OFFLINE and HF_HUB_OFFLINE are omitted here intentionally:
# for OFFLINE=1 builds, set them via compose environment: block so online builds
# can freely download models from HuggingFace Hub.
ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/models \
    PYTHONPATH="/app"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Volatile build args — declared here to avoid busting the apt-get cache layer above
ARG OFFLINE=0
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu

# Copy requirements and prebuilt wheels (from host, not a builder stage)
COPY embedding/requirements.txt .
COPY wheelhouse /app/wheelhouse

# Install runtime dependencies: offline from wheelhouse (OFFLINE=1) or from PyPI (OFFLINE=0)
RUN if [ "$OFFLINE" = "1" ]; then \
        pip install --no-cache-dir --no-index --find-links=/app/wheelhouse -r requirements.txt; \
    else \
        pip install --no-cache-dir --index-url "$TORCH_INDEX_URL" --extra-index-url "$PIP_INDEX_URL" -r requirements.txt; \
    fi && rm -rf /app/wheelhouse

# Copy backend/orchestrator-api service code and shared code
COPY embedding/app /app/app
COPY shared /app/shared

# Fix file permissions
RUN chown -R appuser:appuser /app

# Create model directory
RUN mkdir -p /opt/models && chown -R appuser:appuser /opt/models

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
