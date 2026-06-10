# Corpus Service — multi-stage, wheelhouse + NLTK data
# No OS packages required: PDF parsing is pdfplumber/pypdfium2 (bundled wheels),
# file typing is extension-based, DB driver is psycopg3[binary]/asyncpg.

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

# Python requirements and prebuilt wheelhouse (host must build wheels for python 3.12/linux!)
COPY corpus_svc/requirements.txt .
COPY wheelhouse /wheelhouse

# Install Python dependencies and NLTK data: offline from wheelhouse (OFFLINE=1) or from PyPI (OFFLINE=0)
RUN if [ "$OFFLINE" = "1" ]; then \
        pip install --no-cache-dir --no-index --find-links=/wheelhouse -r requirements.txt; \
    else \
        pip install --no-cache-dir --index-url "$PIP_INDEX_URL" -r requirements.txt; \
    fi && \
    mkdir -p /usr/local/share/nltk_data && \
    if [ -d /wheelhouse/nltk_data ] && [ -n "$(ls -A /wheelhouse/nltk_data 2>/dev/null)" ]; then \
        echo "NLTK data: using staged src/wheelhouse/nltk_data"; \
        cp -r /wheelhouse/nltk_data/* /usr/local/share/nltk_data/; \
    elif [ "$OFFLINE" != "1" ]; then \
        python -c "import nltk; [nltk.download(d, download_dir='/usr/local/share/nltk_data', quiet=True) for d in ['punkt', 'punkt_tab', 'stopwords']]" \
          || echo "WARN: NLTK data not fetched (no network / mirror blocked). Stage it into src/wheelhouse/nltk_data for air-gapped/enterprise builds. The active chunker does not require it."; \
    else \
        echo "WARN: OFFLINE build with no src/wheelhouse/nltk_data staged — skipping NLTK data."; \
    fi

# Stage 2: Runtime — wheelhouse and build inputs do not ship in this image
FROM ${BASE_REGISTRY}/python:3.12-slim

WORKDIR /app

# Installed site-packages, console scripts, and NLTK data from the builder
COPY --from=builder /usr/local /usr/local

# Non-root user for security
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -s /bin/bash -m appuser

# Copy service code
COPY corpus_svc/app /app/app
COPY shared /app/shared

# Create data dirs and set permissions
RUN mkdir -p /data/documents /data/tmp && \
    chown -R appuser:appuser /data && \
    chmod -R 755 /data

USER appuser

ENV PYTHONPATH=/app
ENV TEMP_PATH=/data/tmp
ENV NLTK_DATA=/usr/local/share/nltk_data

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; import sys; sys.exit(0) if urllib.request.urlopen('http://localhost:8001/health', timeout=5).getcode() == 200 else sys.exit(1)"]

ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
