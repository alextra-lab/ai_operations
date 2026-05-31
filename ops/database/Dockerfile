FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# psycopg v3 is used by seed_intent_defaults_from_env.py
RUN pip install --no-cache-dir psycopg psycopg-binary

WORKDIR /ops/database
COPY ops/database/ /ops/database/
RUN chmod +x /ops/database/run_migrations.sh /ops/database/init_entrypoint.sh

CMD ["/ops/database/init_entrypoint.sh"]
