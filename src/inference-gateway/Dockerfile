# Inference Gateway — multi-stage

# Stage 1: Build dependencies
ARG BASE_REGISTRY=docker.io
FROM ${BASE_REGISTRY}/python:3.12-slim AS builder
WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG OFFLINE=0

# Optional enterprise CA bundle: drop *.crt/*.pem into src/certs/ and image
# builds trust them (corporate TLS interception / internal Artifactory CA).
# Empty in public checkouts — the append is a no-op then.
COPY certs /certs
RUN cat /certs/*.crt /certs/*.pem >> /etc/ssl/certs/ca-certificates.crt 2>/dev/null || true
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Copy requirements and prebuilt wheels (from host)
COPY inference-gateway/requirements.txt .
COPY wheelhouse /wheelhouse

# Install runtime dependencies: offline from wheelhouse (OFFLINE=1) or from PyPI (OFFLINE=0)
RUN --mount=type=secret,id=netrc,target=/root/.netrc,required=false \
    if [ "$OFFLINE" = "1" ]; then \
        pip install --no-cache-dir --no-index --find-links=/wheelhouse -r requirements.txt; \
    else \
        pip install --no-cache-dir --index-url "$PIP_INDEX_URL" -r requirements.txt; \
    fi

# Stage 2: Runtime — wheelhouse and build inputs do not ship in this image
FROM ${BASE_REGISTRY}/python:3.12-slim
WORKDIR /app

# Installed site-packages and console scripts from the builder
COPY --from=builder /usr/local /usr/local

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy inference-gateway service code and shared code
COPY inference-gateway/app /app/app
COPY shared /app/shared

# Fix file permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; import sys; sys.exit(0) if urllib.request.urlopen('http://localhost:8002/health', timeout=5).getcode() == 200 else sys.exit(1)"]

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
