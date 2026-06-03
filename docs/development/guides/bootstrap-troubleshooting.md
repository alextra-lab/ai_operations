# Bootstrap Troubleshooting Guide (local profile)

Failure modes encountered during M1–M3 bootstrap, with exact symptoms and fixes.
All commands assume you are in the repo root. See ADR-074 for the build strategy.

---

## 1. `observability` network not found

**Symptom**

```
Error response from daemon: network observability not found
```

or containers start but immediately exit because they cannot reach each other.

**Cause**

The `observability` Docker network must be created externally before any `docker compose` or
`make` command. It is not created by compose itself.

**Fix**

```bash
docker network create observability
```

Safe to re-run — `make setup` includes this call and suppresses the "already exists" error.

---

## 2. Port already in use

**Symptom**

```
Error response from daemon: driver failed programming external connectivity: \
Bind for 0.0.0.0:18002 failed: port is already allocated
```

**Cause**

Another process (or a previous compose stack that wasn't fully stopped) holds the host port.

**Fix**

```bash
# Find what owns the port (example: 18002)
lsof -i :18002

# Stop all compose services cleanly
make down

# If a previous full-stack run is lingering
make down-full

# Then restart
make up
```

Port reference:

| Service | Host port | Container port |
|---|---|---|
| ui-webapp | 4200 | 80 |
| orchestrator-api | 18000 | 8000 |
| corpus-service | 18001 | 8001 |
| inference-gateway | 18002 | 8002 |
| postgres-db | 5532 | 5432 |
| vector-db (Qdrant) | 6333 / 6334 | 6333 / 6334 |
| redis-cache | 6379 | 6379 |
| embedding-service | 18005 | 8000 |
| llm-guard-svc | 18081 | 8081 |

---

## 3. DB bootstrap failures

### 3a. `db-init` exits non-zero / schema errors

**Symptom**

```
db-init exited with code 1
ERROR: relation "users" already exists
```

or services start but immediately fail with `relation does not exist` errors.

**Cause**

`db-init` is a one-shot container (`restart: "no"`) that runs the init SQL against
`postgres-db`. If it ran previously against a dirty volume, or the Postgres container was not
yet healthy when init ran, the schema can be partial or duplicated.

**Fix**

```bash
# Wipe the Postgres volume and re-init from scratch
make down
docker volume rm $(docker volume ls -q | grep postgres) 2>/dev/null || true
rm -rf data/postgres
make setup    # re-creates data/postgres dir
make up       # db-init runs again against a clean DB
```

### 3b. Seed ordering — intent model defaults not populated

**Symptom**

Orchestrator returns `ValueError: No model configured for intent` on the first query.

**Cause**

`db-init` seeds the `intent_model_defaults` table only when the
`INTENT_MODEL_*` env vars are set. An empty `.env` leaves the table empty.

**Fix**

Add at least one intent model default to `config/env/.env`:

```bash
INTENT_MODEL_QUERY=gpt-4o-mini
INTENT_MODEL_RULE_GENERATION=gpt-4o-mini
INTENT_MODEL_SUMMARIZATION=gpt-4o-mini
INTENT_MODEL_ENRICHMENT=gpt-4o-mini
```

Then restart so `db-init` re-runs (or insert directly via psql):

```bash
make down && make up
```

---

## 4. Model not found at startup

### 4a. Embedding model

**Symptom**

`embedding-service` exits at startup:

```
FileNotFoundError: Model directory not found: /app/models/...
```

**Cause**

`make models` (or `make models-embedding`) was not run before `make up`.

**Fix**

```bash
make models-embedding   # downloads to data/ on the host
make up                 # volume-mounts data/ into the container
```

### 4b. llm-guard ONNX models

**Symptom**

`llm-guard-svc` exits or its healthcheck fails:

```
FileNotFoundError: /app/models/...onnx not found
```

**Cause**

`make models-llm-guard` was not run, or the volume mount path is wrong.

**Fix**

```bash
make models-llm-guard   # downloads ONNX models to data/llm-guard-models/
```

The compose file mounts `data/llm-guard-models` → `/app/models` inside the container.
Verify the download completed:

```bash
ls data/llm-guard-models/
```

### 4c. `OFFLINE=1` / `make build-offline` blocking download at build time

**Symptom**

Build succeeds but runtime model download fails, or pip packages are missing.

**Cause**

`make build-offline` passes `--build-arg OFFLINE=1`, which disables pip network access and
HuggingFace downloads inside the build. The wheelhouse and model files must already exist in
`src/wheelhouse/` and `data/` before building.

**Fix** — for online (local) builds, use the standard build path:

```bash
make build   # online build — does NOT pass OFFLINE=1
make models  # download models separately
make up
```

Use `make build-offline` only when you have pre-populated `src/wheelhouse/` and `data/`.

---

## 5. Architecture / platform mismatch on x86_64 hosts

**Symptom**

```
WARNING: The requested image's platform (linux/arm64) does not match the detected host
platform (linux/amd64).
```

or containers crash immediately with `exec format error`.

**Cause**

The compose file defaults `platform: linux/arm64` (Apple Silicon). On amd64 hosts Docker will
attempt to run arm64 images under emulation, which is slow and often broken.

**Fix**

Set the platform override before building and starting:

```bash
export DOCKER_DEFAULT_PLATFORM=linux/amd64
make build
make up
```

Add it to your shell profile to avoid repeating it. Note: `db-init` has `platform: linux/arm64`
hardcoded in `deploy/docker-compose.yml` — if you hit issues with that specific container on
amd64, override it:

```bash
# Temporary workaround — edit deploy/docker-compose.yml
# Change:  platform: linux/arm64
# To:      platform: linux/amd64
```

---

## 6. `passlib` / `bcrypt` auth errors

**Symptom**

```
AttributeError: module 'bcrypt' has no attribute '__about__'
```

or login requests return 500 / `Internal Server Error` immediately after startup.

**Cause**

`passlib==1.7.4` probes `bcrypt.__about__` during import, which was removed in `bcrypt>=4.x`.
The shared auth module uses `bcrypt` directly (not via passlib), but if passlib is installed
with its `[bcrypt]` extra it pulls an older bcrypt version that conflicts with
`bcrypt>=5.0.0` required by the services.

The `requirements.txt` pins `passlib==1.7.4` (without the `[bcrypt]` extra) to avoid this.

**Fix**

Rebuild the affected image to ensure the correct package versions are installed:

```bash
make down
docker compose -f deploy/docker-compose.yml build --no-cache orchestrator-api
make up
```

If the error persists inside a running container, verify the installed versions:

```bash
docker exec orchestrator-api pip show bcrypt passlib
# bcrypt should be >=5.0.0; passlib should be 1.7.4
```

---

## 7. `llm-guard-svc` healthcheck timeout on first boot

**Symptom**

`make up-full` stalls or `llm-guard-svc` shows as `unhealthy` for several minutes:

```
llm-guard-svc  | Loading ONNX model... (this may take a while)
```

Other services that depend on `llm-guard-svc` may refuse to start.

**Cause**

The llm-guard service loads several ONNX models into memory on startup. On first boot (or
after a cache miss) this takes 2–5 minutes depending on hardware. The default Docker
healthcheck interval fires before the models finish loading.

**Fix**

Wait. The service will eventually become healthy. Monitor progress:

```bash
docker logs -f llm-guard-svc
```

If it stays unhealthy after 10 minutes, check model files are present (see §4b above).

**For development**: skip llm-guard entirely by using `make up` (not `make up-full`).
`llm-guard-svc` is in the `full` compose profile and is not started by the default target.
Set `LLM_GUARD_ENABLED=false` in `config/env/.env` to disable guard checks in the
orchestrator even when the service is absent.

---

## Quick diagnostic checklist

Run this sequence when something is broken:

```bash
# 1. Check network exists
docker network ls | grep observability

# 2. Check all containers
make status

# 3. Tail logs for the failing service
make logs SVC=<container-name>

# 4. Validate .env
python ops/validate_configuration.py

# 5. Confirm models are present
ls data/models/ data/llm-guard-models/
```

Container names: `orchestrator-api`, `corpus-service`, `embedding-service`,
`inference-gateway`, `llm-guard-svc`, `ui-webapp`, `postgres-db`, `vector-db`,
`redis-cache`, `db-init`.
