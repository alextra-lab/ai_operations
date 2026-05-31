# Stage 1: Build dependencies
ARG BASE_REGISTRY=docker.io/library
FROM ${BASE_REGISTRY}/python:3.12-slim AS builder
WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG OFFLINE=0
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy requirements and prebuilt wheels (from host, not a builder stage)
COPY inference-gateway/requirements.txt .
COPY wheelhouse /app/wheelhouse

# Install runtime dependencies: offline from wheelhouse (OFFLINE=1) or from PyPI (OFFLINE=0)
RUN if [ "$OFFLINE" = "1" ]; then \
        pip install --no-cache-dir --no-index --find-links=/app/wheelhouse -r requirements.txt; \
    else \
        pip install --no-cache-dir --index-url "$PIP_INDEX_URL" -r requirements.txt; \
    fi && rm -rf /app/wheelhouse

# Copy inference-gateway service code and shared code
COPY inference-gateway/app /app/app
COPY shared /app/shared

# Fix file permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
