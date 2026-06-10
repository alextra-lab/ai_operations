# db-init — runs SQL migrations and the intent-defaults seeder via psycopg
# (init_db.py). Pure Python: no OS packages, no apt — builds air-gapped with
# just a base-image mirror and a pip source.

# Stage 1: Build dependencies
ARG BASE_REGISTRY=docker.io/library
FROM ${BASE_REGISTRY}/python:3.12-slim AS builder

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG OFFLINE=0

# psycopg v3 is used by init_db.py and seed_intent_defaults_from_env.py
# (build context is the repo root, so the wheelhouse lives at src/wheelhouse)
COPY src/wheelhouse /wheelhouse
RUN if [ "$OFFLINE" = "1" ]; then \
        pip install --no-cache-dir --no-index --find-links=/wheelhouse psycopg psycopg-binary; \
    else \
        pip install --no-cache-dir --index-url "$PIP_INDEX_URL" psycopg psycopg-binary; \
    fi

# Stage 2: Runtime
FROM ${BASE_REGISTRY}/python:3.12-slim

COPY --from=builder /usr/local /usr/local

WORKDIR /ops/database
COPY ops/database/ /ops/database/

CMD ["python", "/ops/database/init_db.py"]
