# Stage 1: Build dependencies
FROM python:3.12-slim AS builder
WORKDIR /app

# --- Set environment variables (safe defaults, no secrets) ---
ENV PYTHONUNBUFFERED=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HOME=/opt/models \
    HF_HUB_OFFLINE=1 \
    PYTHONPATH="/app"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy requirements and prebuilt wheels (from host, not a builder stage)
COPY embedding/requirements.txt .
COPY wheelhouse /app/wheelhouse

# Install runtime dependencies from wheelhouse and remove wheelhouse after
RUN pip install --no-cache-dir --no-index --find-links=/app/wheelhouse -r requirements.txt \
    && rm -rf /app/wheelhouse

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
