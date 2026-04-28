# Stage 1: Build dependencies
FROM python:3.12-slim AS builder
WORKDIR /app

# Install curl and Docker CLI for MCP STDIO support
# Docker CLI allows spawning MCP servers like: docker mcp gateway run
# Note: docker.io package doesn't include CLI, we need docker-ce-cli from Docker repo
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with docker group access
# docker-ce-cli creates a docker group; add appuser to it for socket access
RUN groupadd -r appuser && \
    useradd -r -g appuser appuser && \
    usermod -aG docker appuser || true

# Copy requirements and prebuilt wheels (from host, not a builder stage)
COPY orchestrator/requirements.txt .
COPY wheelhouse /app/wheelhouse

# Install runtime dependencies from wheelhouse and remove wheelhouse after
RUN pip install --no-cache-dir --no-index --find-links=/app/wheelhouse -r requirements.txt \
    && rm -rf /app/wheelhouse

# Copy orchestrator service code and shared code
COPY orchestrator/app /app/app
COPY shared /app/shared

# Fix file permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
