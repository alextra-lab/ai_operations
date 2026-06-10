# db-init — runs SQL migrations (psql) and the intent-defaults seeder (psycopg).
# NOTE: postgresql-client is the one remaining apt dependency in this project's
# images — the migration runner shells out to psql, which has no pip equivalent.
# Fully air-gapped builds must either mirror this package or substitute a base
# image that already ships psql.

# Stage 1: Build dependencies
ARG BASE_REGISTRY=docker.io/library
FROM ${BASE_REGISTRY}/python:3.12-slim AS builder

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG OFFLINE=0

# psycopg v3 is used by seed_intent_defaults_from_env.py
# (build context is the repo root, so the wheelhouse lives at src/wheelhouse)
COPY src/wheelhouse /wheelhouse
RUN if [ "$OFFLINE" = "1" ]; then \
        pip install --no-cache-dir --no-index --find-links=/wheelhouse psycopg psycopg-binary; \
    else \
        pip install --no-cache-dir --index-url "$PIP_INDEX_URL" psycopg psycopg-binary; \
    fi

# Stage 2: Runtime
FROM ${BASE_REGISTRY}/python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local /usr/local

WORKDIR /ops/database
COPY ops/database/ /ops/database/
RUN chmod +x /ops/database/run_migrations.sh /ops/database/init_entrypoint.sh

CMD ["/ops/database/init_entrypoint.sh"]
