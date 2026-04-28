# Corpus Service - Single Stage, Fully Offline, Wheelhouse + NLTK Data

FROM python:3.12-slim

WORKDIR /app

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

# Install Python dependencies OFFLINE from wheelhouse
RUN pip install --no-cache-dir --no-index --find-links=/app/wheelhouse -r requirements.txt \
    && rm -rf /app/wheelhouse/*.whl

# Copy prebuilt NLTK data to system NLTK data directory
RUN mkdir -p /usr/local/share/nltk_data && \
    cp -r /app/wheelhouse/nltk_data/* /usr/local/share/nltk_data/ && \
    rm -rf /app/wheelhouse/nltk_data

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
