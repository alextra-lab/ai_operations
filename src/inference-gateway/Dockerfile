# Stage 1: Build dependencies
FROM python:3.14-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy requirements and prebuilt wheels (from host, not a builder stage)
COPY inference-gateway/requirements.txt .
COPY wheelhouse /app/wheelhouse

# Install runtime dependencies from wheelhouse and remove wheelhouse after
RUN pip install --no-cache-dir --no-index --find-links=/app/wheelhouse -r requirements.txt \
    && rm -rf /app/wheelhouse

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
