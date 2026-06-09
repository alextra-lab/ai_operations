# Getting Started — local profile

> **Beta platform.** This stack has not been deployed to production. Expect rough edges.
> Enterprise bootstrap is managed internally by the enterprise team and is not covered here.

Clean checkout to a running stack in five steps.

---

## Prerequisites

| Tool | Version | Required for |
|---|---|---|
| Docker + Compose v2 plugin | Latest | Everything |
| Python | 3.12 | Ops scripts (`make setup`, `python ops/...`) |
| Node | ≥ 24 | Frontend development only — not needed to run the stack |

**Platform:** The compose file defaults to `linux/arm64` (Apple Silicon). On x86_64 / amd64 hosts, set this before building:

```bash
export DOCKER_DEFAULT_PLATFORM=linux/amd64
```

---

## Step 1 — One-time setup

```bash
make setup
```

This creates the `observability` Docker network, the `data/` directory tree, and copies
`config/env/env.template` → `config/env/.env` (only if `.env` doesn't exist yet).

---

## Step 2 — Edit `.env`

Open `config/env/.env` and set the three required secrets before doing anything else:

```bash
POSTGRES_PASSWORD=<strong-password>
JWT_SECRET=<random-string-minimum-32-chars>
TOOL_SECRETS_KEY=<random-string-minimum-32-chars-for-aes256>
```

Generate suitable values:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Set up an isolated Python environment for the host ops scripts
(`validate_configuration.py`, the test runner, etc.) so their dependencies stay off
your system Python:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-ops.txt
```

Validate the full config once edited:

```bash
python ops/validate_configuration.py
```

Everything else in `.env` has working defaults for local development.

---

## Step 3 — Build images

```bash
make build
```

Pulls Python 3.12-slim and Node 24 base images from `docker.io/library`, installs
dependencies from PyPI. First build takes 10–15 minutes; subsequent builds use the Docker
layer cache.

On x86_64 make sure `DOCKER_DEFAULT_PLATFORM=linux/amd64` is exported (see Prerequisites).

---

## Step 4 — Download models

```bash
make models
```

Downloads the sentence-transformer embedding model and llm-guard ONNX models into `data/`.
Requires internet access (~1–2 GB). Skip if you have already populated `data/models/` and
`data/llm-guard-models/` from a previous run.

---

## Step 5 — Start the stack

```bash
make up          # backend-core (no UI or llm-guard)
make up-full     # full stack including llm-guard-svc and ui-webapp
```

`make up` starts seven services:

| Container | Host port | Purpose |
|---|---|---|
| `orchestrator-api` | 18000 | Central FastAPI backend |
| `corpus-service` | 18001 | Document ingestion + vector indexing |
| `inference-gateway` | 18002 | OpenAI-compatible LLM proxy |
| `embedding-service` | 18005 | Sentence-transformer embeddings |
| `postgres-db` | 5532 | PostgreSQL |
| `vector-db` | 6333 / 6334 | Qdrant vector database |
| `redis-cache` | 6379 | Rate limit counters |
| `db-init` | — | One-shot schema + seed (exits when done) |

`make up-full` additionally starts `llm-guard-svc` (18081) and `ui-webapp` (4200).

> **llm-guard on first boot** loads several ONNX models and takes 2–5 minutes to become
> healthy. Use `make up` during development unless you specifically need prompt scanning.

---

## Verify

### Container health

```bash
make status            # show all containers and their ports
make logs              # tail all logs
make logs SVC=orchestrator-api   # tail one service
```

### Health endpoints

```bash
curl http://localhost:18000/health   # → {"status":"healthy"}
curl http://localhost:18001/health   # corpus-service
curl http://localhost:18002/health   # inference-gateway
curl http://localhost:18005/health   # embedding-service
curl http://localhost:6333/          # Qdrant (→ 200 OK)
```

All five should respond before you proceed.

### DB bootstrap

`db-init` runs once and exits. Confirm it completed cleanly:

```bash
docker logs db-init | tail -5
# Expected: "Database initialization complete"
```

If `db-init` exited with an error, see the
[bootstrap troubleshooting guide](docs/development/guides/bootstrap-troubleshooting.md).

---

## Common next steps

```bash
# Stop the stack
make down        # backend-core
make down-full   # full stack

# Restart after code or config changes
make restart

# Rebuild a single service after code changes
docker compose --env-file config/env/.env -f deploy/docker-compose.yml build orchestrator-api

# Open a shell in a running container
make shell SVC=orchestrator-api

# Run the test suite
python ops/testing/run_all_tests.py
```

---

## Troubleshooting

See **[docs/development/guides/bootstrap-troubleshooting.md](docs/development/guides/bootstrap-troubleshooting.md)** for the full list of known failure modes:

- `observability` network not found
- Port already in use
- `db-init` schema errors / seed not running
- Model files not found
- Architecture mismatch on x86_64
- `passlib` / `bcrypt` auth errors
- `llm-guard-svc` healthcheck timeout

---

## Further reading

- [Architecture overview](README.md#architecture)
- [Configuration reference](README.md#configuration-management)
- [Enterprise profile bootstrap](ENTERPRISE_GETTING_STARTED.md)
- [Offline & enterprise build modes](docs/operations/AIR_GAPPED_DEPLOYMENT.md)
- [Testing guide](docs/testing/TESTING_GUIDE.md)
- [ADR-074 — Build strategy](docs/development/adrs/ADR-074-multi-profile-build-and-bootstrap.md)
