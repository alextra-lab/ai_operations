# Corpus Service - Single Stage, Wheelhouse + NLTK Data

ARG BASE_REGISTRY=docker.io/library
FROM ${BASE_REGISTRY}/python:3.12-slim

WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG OFFLINE=0

# Install runtime OS dependencies for document processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libmagic1 \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -s /bin/bash -m appuser

# Python requirements and prebuilt wheelhouse (host must build wheels for python 3.12/linux!)
COPY corpus_svc/requirements.txt .
COPY wheelhouse /app/wheelhouse

# Install Python dependencies and NLTK data in a single layer so wheelhouse is cleaned up before commit
RUN if [ "$OFFLINE" = "1" ]; then \
        pip install --no-cache-dir --no-index --find-links=/app/wheelhouse -r requirements.txt; \
    else \
        pip install --no-cache-dir --index-url "$PIP_INDEX_URL" -r requirements.txt; \
    fi && \
    mkdir -p /usr/local/share/nltk_data && \
    if [ "$OFFLINE" = "1" ] && [ -d /app/wheelhouse/nltk_data ]; then \
        cp -r /app/wheelhouse/nltk_data/* /usr/local/share/nltk_data/; \
    else \
        python -c "import nltk; [nltk.download(d, download_dir='/usr/local/share/nltk_data') for d in ['punkt', 'punkt_tab', 'stopwords']]" || true; \
    fi && \
    rm -rf /app/wheelhouse

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
    CMD curl -f http://localhost:8001/health || exit 1

ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
