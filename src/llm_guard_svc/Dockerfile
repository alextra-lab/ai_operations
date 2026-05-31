ARG BASE_REGISTRY=docker.io/library
FROM ${BASE_REGISTRY}/python:3.12-slim
WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.org/simple

# --- Set environment variables (safe defaults, no secrets) ---
# TRANSFORMERS_OFFLINE and HF_HUB_OFFLINE are omitted here intentionally:
# for OFFLINE=1 builds, set them via compose environment: block so online builds
# can freely download models from HuggingFace Hub.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8081 \
    HF_HOME=/app/models \
    PYTHONPATH="/app"

# --- OS dependencies for runtime and wheels ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates g++ build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# --- Create non-root user ---
RUN groupadd -r guarduser && useradd -r -g guarduser guarduser

# --- Prepare models directory ---
RUN mkdir -p /app/models

# Declare volatile build args AFTER apt-get to avoid busting the cache layer above
ARG OFFLINE=0

# --- spaCy language model wheels (kept in sync with build_wheelhouse.sh) ---
# en_core_web_sm-3.7.1 / zh_core_web_sm-3.7.0 require spacy>=3.7.2,<3.8.0.
# OFFLINE builds pick them up from the wheelhouse; online builds fetch them
# from the explosion/spacy-models GitHub releases.
ARG EN_MODEL_URL=https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl
ARG ZH_MODEL_URL=https://github.com/explosion/spacy-models/releases/download/zh_core_web_sm-3.7.0/zh_core_web_sm-3.7.0-py3-none-any.whl

# --- Copy requirements and prebuilt wheelhouse (host must build it for python 3.12/linux) ---
COPY llm_guard_svc/requirements.txt .
COPY wheelhouse /app/wheelhouse

# --- Install runtime dependencies: offline from wheelhouse (OFFLINE=1) or from PyPI (OFFLINE=0) ---
# The spaCy language models are installed in the same resolution pass so pip can
# verify the spacy>=3.7.2,<3.8.0 dependency is satisfied by requirements.txt.
RUN if [ "$OFFLINE" = "1" ]; then \
        pip install --no-cache-dir --no-index --find-links=/app/wheelhouse \
            -r requirements.txt \
            /app/wheelhouse/en_core_web_sm-3.7.1-py3-none-any.whl \
            /app/wheelhouse/zh_core_web_sm-3.7.0-py3-none-any.whl; \
    else \
        pip install --no-cache-dir --index-url "$PIP_INDEX_URL" \
            -r requirements.txt "${EN_MODEL_URL}" "${ZH_MODEL_URL}"; \
    fi && rm -rf /app/wheelhouse

# --- Copy service and shared code ---
COPY llm_guard_svc/app /app/app
COPY shared /app/shared

# --- Set permissions ---
RUN chown -R guarduser:guarduser /app

USER guarduser

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

EXPOSE ${PORT}

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8081"]
