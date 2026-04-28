# LLM-Guard Dockerfile
# Streamlined version that expects models to be mounted at runtime
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8081 \
    TRANSFORMERS_CACHE=/app/models \
    HF_HOME=/app/models

# Create and set working directory
WORKDIR /app

# Install dependencies for running the app
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    g++ \
    git \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create models directory where external models will be mounted
RUN mkdir -p /app/models

# Install application dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir wheel setuptools && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir "transformers[torch]" --extra-index-url https://download.pytorch.org/whl/cpu

# Download and install SpaCy model
RUN python -m spacy download en_core_web_sm && \
    python -m spacy download zh_core_web_sm

# Create a non-root user
RUN groupadd -r guarduser && useradd -r -g guarduser guarduser

# Copy source code
COPY . .

# Make sure models directory is accessible
RUN chown -R guarduser:guarduser /app

# Switch to non-root user
USER guarduser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Start the app
CMD ["python", "app.py"]
