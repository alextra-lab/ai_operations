FROM python:3.12-slim
WORKDIR /app

# --- Set environment variables (safe defaults, no secrets) ---
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8081 \
    HF_HOME=/app/models \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_OFFLINE=1 \
    PYTHONPATH="/app"

# --- OS dependencies for runtime and wheels ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates g++ build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# --- Prepare models directory ---
RUN mkdir -p /app/models

# --- Copy requirements and prebuilt wheelhouse (host must build it for python 3.12/linux) ---
COPY llm_guard_svc/requirements.txt .
COPY wheelhouse /app/wheelhouse

# --- Install all runtime dependencies from the wheelhouse, strictly offline ---
# Install spacy-3.7.5 explicitly from wheelhouse FIRST (required by language models) \
# This ensures the correct version is installed before llm-guard potentially pulls in spacy-3.8.11 \
RUN pip install --no-cache-dir --no-index --find-links=/app/wheelhouse "spacy==3.7.5" \
    # Install requirements.txt (spacy is listed but already installed, pip will skip) \
    && pip install --no-cache-dir --no-index --find-links=/app/wheelhouse -r requirements.txt \
    && pip install --no-cache-dir --no-index --find-links=/app/wheelhouse "transformers[torch]" \
    # Reinstall llm-guard and optimum (from PyPI, fallback is online) \
    # Note: spacy-3.7.5 is already installed, pip won't upgrade it \
    && pip install --no-cache-dir "llm-guard[onnxruntime-cpu]>=0.3.16" "optimum[onnxruntime]>=1.25.2" \
    && pip install --no-cache-dir --upgrade bitsandbytes \
    && pip install --no-cache-dir --no-index --find-links=/app/wheelhouse spacy-pkuseg==0.0.33 \
    # Install spaCy language models (require spacy>=3.7.2,<3.8.0, spacy-3.7.5 already installed) \
    # Must include --find-links so pip can verify spacy dependency is satisfied from wheelhouse \
    && pip install --no-cache-dir --no-index --find-links=/app/wheelhouse /app/wheelhouse/en_core_web_sm-3.7.1-py3-none-any.whl /app/wheelhouse/zh_core_web_sm-3.7.0-py3-none-any.whl \
    && python -m spacy link en_core_web_sm en_core_web_sm \
    && rm -rf /app/wheelhouse

# --- Download and pre-install SpaCy models and pkuseg (online step, can be moved to wheelhouse build if needed) ---
#RUN python -m spacy download en_core_web_sm && \
#    pip install --no-cache-dir https://github.com/explosion/spacy-models/releases/download/zh_core_web_sm-3.8.0/zh_core_web_sm-3.8.0-py3-none-any.whl && \
#    pip install --no-cache-dir spacy-pkuseg

# --- Create non-root user ---
RUN groupadd -r guarduser && useradd -r -g guarduser guarduser

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
