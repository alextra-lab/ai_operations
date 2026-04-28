#!/bin/bash

# Builds one wheelhouse with two transformers versions:
# - Pass 1: requirements-all-no-llm-guard.txt + constraints.txt -> transformers 4.53.x for orchestrator, embedding, corpus_svc, inference-gateway, shared
# - Pass 2: llm_guard_svc/requirements.txt -> transformers 4.51.3 for llm_guard_svc (llm-guard pin)
# Must be run from <project root>. Clean src/wheelhouse prior to running.

docker run --rm \
-v "$PWD/src/wheelhouse:/wheelhouse" \
-v "$PWD:/requirements" \
python:3.12-slim \
/bin/bash -c "
  set -e
  apt-get update && \
  apt-get install -y build-essential gcc libffi-dev python3-dev cargo curl unzip && \
  pip install --upgrade pip nltk && \
  pip wheel --resume-retries=5 --no-cache-dir --wheel-dir /wheelhouse -r /requirements/requirements-all-no-llm-guard.txt -c /requirements/constraints.txt && \
  pip wheel --resume-retries=5 --no-cache-dir --wheel-dir /wheelhouse -r /requirements/src/llm_guard_svc/requirements.txt && \
  curl -L -o /tmp/en_core_web_sm-3.7.1-py3-none-any.whl https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl && \
  unzip -t /tmp/en_core_web_sm-3.7.1-py3-none-any.whl && \
  cp /tmp/en_core_web_sm-3.7.1-py3-none-any.whl /wheelhouse/ && \
  curl -L -o /tmp/zh_core_web_sm-3.7.0-py3-none-any.whl https://github.com/explosion/spacy-models/releases/download/zh_core_web_sm-3.7.0/zh_core_web_sm-3.7.0-py3-none-any.whl && \
  unzip -t /tmp/zh_core_web_sm-3.7.0-py3-none-any.whl && \
  cp /tmp/zh_core_web_sm-3.7.0-py3-none-any.whl /wheelhouse/ && \
  mkdir -p /tmp/nltk_data && \
  python -m nltk.downloader -d /tmp/nltk_data punkt stopwords && \
  mkdir -p /wheelhouse/nltk_data && \
  cp -r /tmp/nltk_data/* /wheelhouse/nltk_data/
"
