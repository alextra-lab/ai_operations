# Embedding Service — multi-stage

# Stage 1: Build dependencies
ARG BASE_REGISTRY=docker.io/library
FROM ${BASE_REGISTRY}/python:3.12-slim AS builder
WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG OFFLINE=0
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu

# Copy requirements and prebuilt wheels (from host)
COPY embedding/requirements.txt .
COPY wheelhouse /wheelhouse

# Install runtime dependencies: offline from wheelhouse (OFFLINE=1) or from PyPI (OFFLINE=0)
RUN if [ "$OFFLINE" = "1" ]; then \
        pip install --no-cache-dir --no-index --find-links=/wheelhouse -r requirements.txt; \
    else \
        pip install --no-cache-dir --index-url "$TORCH_INDEX_URL" --extra-index-url "$PIP_INDEX_URL" -r requirements.txt; \
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
