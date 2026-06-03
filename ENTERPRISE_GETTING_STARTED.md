# Getting Started — enterprise profile

> **Beta platform.** This stack has not been deployed to production. Expect rough edges.
> Local profile bootstrap is covered separately: [GETTING_STARTED.md](GETTING_STARTED.md).

> **Enterprise ≠ air-gapped (ADR-074).** Enterprise machines have network access. They
> route through internal Artifactory mirrors (Docker Hub, PyPI, PyTorch) instead of the
> public internet and use an internal LLMaaS/vLLM endpoint instead of LMStudio.
> No wheelhouse or offline mode is needed. See
> [Offline & Enterprise Deployment](docs/operations/AIR_GAPPED_DEPLOYMENT.md) for the
> distinction and for deep build mechanics.

A developer inside an enterprise network can be up and running in five steps. Most of the
heavy lifting — building images, pushing to the internal registry, and configuring model
paths — is done by your enterprise team. Your job is to pull and start.

---

## Prerequisites

| Tool | Version | Required for |
|---|---|---|
| Docker + Compose v2 plugin | Latest | Everything |
| Python | 3.12 | Ops scripts (`make setup`, `python ops/...`) |
| Node | ≥ 24 | Frontend development only — not needed to run the stack |

**Enterprise-specific prerequisites (contact your enterprise team for values):**

| Requirement | What you need |
|---|---|
| Artifactory Docker registry access | Credentials + registry URL to `docker login` |
| Internal LLMaaS/vLLM endpoint | OpenAI-compatible base URL (e.g. `https://llmaas.internal.example.com/v1`) |
| Pre-staged models | Paths to `data/models/`, `data/llm-guard-models/`, `data/tokenizers/` — or the source to stage from |
| Network/proxy settings | `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` if required by your network |

**Platform:** The compose file defaults to `linux/arm64` (Apple Silicon). On x86_64 / amd64 hosts, set this before building or pulling:

```bash
export DOCKER_DEFAULT_PLATFORM=linux/amd64
```

---

## What your enterprise team must provide

These values are **not committed to this repository**. Your enterprise team is the source of truth for each of them.

| Value | What it is | Where it's used |
|---|---|---|
| `BASE_REGISTRY` | Artifactory-hosted Docker Hub mirror | Makefile `BUILD_ARGS` — rewrites `FROM` base image pulls away from `docker.io/library` |
| `PIP_INDEX_URL` | Artifactory PyPI remote URL | Makefile `BUILD_ARGS` — used as `pip --index-url` during image builds |
| `TORCH_INDEX_URL` | Artifactory PyTorch CPU wheel remote URL | Makefile `BUILD_ARGS` — used for torch installs during image builds |
| Artifactory Docker registry URL | Where pre-built images are pushed and pulled from | `docker login` + `docker pull` / `docker compose pull` |
| LLMaaS/vLLM base URL | Internal OpenAI-compatible inference endpoint | `gateway_providers` table — see Step 4 |
| Pre-staged model paths | Populated `data/models/`, `data/llm-guard-models/` directories | Bind-mounted into embedding-service and llm-guard-svc |

> **Build ARGs live in the Makefile, not in `.env`.** Do not look for `BASE_REGISTRY`,
> `PIP_INDEX_URL`, or `TORCH_INDEX_URL` in `config/env/env.template` — they are not there.
> They are build-time ARGs passed to `docker compose build`, substituted by your enterprise
> team or CI/CD system before a build runs.

---

## Step 1 — One-time setup

```bash
make setup
```

Identical to the local profile. Creates the `observability` Docker network, the `data/`
directory tree, and copies `config/env/env.template` → `config/env/.env` (only if `.env`
doesn't exist yet).

---

## Step 2 — Edit `.env`

Open `config/env/.env` and set the three required secrets:

```bash
POSTGRES_PASSWORD=<strong-password>
JWT_SECRET=<random-string-minimum-32-chars>
TOOL_SECRETS_KEY=<random-string-minimum-32-chars-for-aes256>
```

Generate suitable values:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Validate the full config once edited:

```bash
python ops/validate_configuration.py
```

Everything else in `.env` has working defaults. Proxy settings (`HTTP_PROXY`, `HTTPS_PROXY`,
`NO_PROXY`) are not in `env.template` — if your network requires them, set them in your shell
environment before running Docker commands.

---

## Step 3 — Get images

### Path A — Pull pre-built images (recommended for most developers)

Your enterprise CI/CD system builds images with the three Artifactory ARGs set and pushes
them to the internal Artifactory Docker registry. Developers pull rather than build:

```bash
# Log in to your internal Artifactory Docker registry
docker login <ARTIFACTORY_DOCKER_REGISTRY>

# Pull all service images
docker compose --env-file config/env/.env -f deploy/docker-compose.yml pull
```

Your enterprise team will provide the registry URL and login instructions.

> This repo's own GitHub Actions CI (lint and tests only) does **not** build or push images.
> Image distribution is handled by the internal enterprise CI/CD pipeline.

### Path B — Build locally (advanced, requires Makefile configuration)

If you need to build images yourself, your enterprise team must first substitute the three
placeholder strings in the Makefile (lines 12–14):

```makefile
# Current Makefile enterprise profile (placeholders — not functional as-is)
BUILD_ARGS = --build-arg BASE_REGISTRY=<ARTIFACTORY_DOCKER_REGISTRY_PLACEHOLDER> \
             --build-arg PIP_INDEX_URL=<ARTIFACTORY_PYPI_URL_PLACEHOLDER> \
             --build-arg TORCH_INDEX_URL=<ARTIFACTORY_TORCH_CPU_URL_PLACEHOLDER>
```

Once your enterprise team substitutes real Artifactory URLs, run:

```bash
make build PROFILE=enterprise
```

The `enterprise` profile uses the base `deploy/docker-compose.yml` only (no local override).
Each service Dockerfile accepts `BASE_REGISTRY` to rewrite the `FROM` base image pull and
`PIP_INDEX_URL` as `pip --index-url`. No Dockerfile edits are required.

For full ARG and Dockerfile mechanics, see
[Offline & Enterprise Deployment](docs/operations/AIR_GAPPED_DEPLOYMENT.md#enterprise-profile-artifactory-mirrors).

---

## Step 4 — Stage models (no direct HuggingFace access)

The enterprise environment has no direct HuggingFace access. `make models` is **not** the
right command here — it downloads directly from HuggingFace and will fail.

### Option A — Pull from a connected jump host (primary path)

On an internet-connected host, run:

```bash
make models-embedding    # → data/models/
make models-llm-guard    # → data/llm-guard-models/
bash ops/bootstrap/prepare_tokenizers.sh  # → data/tokenizers/
```

Transfer the three directories to your machine and place them at the same paths inside the
repo root. The download scripts skip any directory that is already populated — so a pre-staged
`data/` is consumed directly on first `make up`.

Full transfer and tokenizer-bundle instructions:
[Offline & Enterprise Deployment](docs/operations/AIR_GAPPED_DEPLOYMENT.md#offline-build-local-wheelhouse).

### Option B — Mirror via Artifactory (if your team has set one up)

If your Artifactory instance mirrors HuggingFace, set `HF_ENDPOINT` before running the
download scripts:

```bash
export HF_ENDPOINT=https://your-artifactory.example.com/artifactory/api/huggingface
make models-embedding
make models-llm-guard
```

`huggingface_hub` (bundled in the images) honors `HF_ENDPOINT` transparently. Confirm the
mirror URL and any auth requirements with your enterprise team.

> **Note:** `HF_ENDPOINT` and model-mirror configuration are not wired into
> `config/env/env.template` today — this is a known integration gap. Set the variable in your
> shell or discuss with your enterprise team for a managed pre-staging flow.

---

## Step 5 — Point inference at your internal LLMaaS/vLLM endpoint

The inference gateway uses a **database-driven provider registry** (`gateway_providers` table).
The default seed row points at a local LMStudio instance (`http://host.docker.internal:1234/v1`),
which is not available in an enterprise environment. Repoint it to your internal LLMaaS or vLLM
endpoint before starting.

The provider `type` stays `'openai'` — vLLM and LLMaaS expose OpenAI-compatible APIs.

### Option A — Edit the seed file (recommended, idempotent)

Edit `ops/database/seed/010_seed_gateway_providers.sql`. Replace the default `base_url`:

```sql
-- Change this line:
'http://host.docker.internal:1234/v1',

-- To your internal endpoint:
'https://llmaas.internal.example.com/v1',
```

The `ON CONFLICT (name) DO UPDATE SET base_url = EXCLUDED.base_url` clause makes this
idempotent — rerunning the seed (via `make db-reset` or direct `psql`) updates the existing
row safely.

### Option B — Admin REST API (no restart required)

Once the stack is running, update the provider row via the inference-gateway admin API
(port 18002):

```bash
# 1. Find the provider ID
curl http://localhost:18002/admin/providers

# 2. Update base_url (replace <PROVIDER_ID> with the value from step 1)
curl -X PUT http://localhost:18002/admin/providers/<PROVIDER_ID> \
  -H "Content-Type: application/json" \
  -d '{"base_url": "https://llmaas.internal.example.com/v1"}'

# 3. Reload the router to pick up the change
curl -X POST http://localhost:18002/admin/router/reload

# 4. Test connectivity (hits the provider's /models endpoint)
curl -X POST http://localhost:18002/admin/providers/<PROVIDER_ID>/test
```

### Option C — Direct SQL

```sql
UPDATE gateway_providers
SET base_url = 'https://llmaas.internal.example.com/v1'
WHERE name = 'LMStudio';
```

Then POST to `/admin/router/reload` or restart the inference-gateway container to reload.

---

## Step 6 — Start the stack

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

## Enterprise CI/CD pattern

Your enterprise CI/CD system (external to this repository) owns the image build and
distribution pipeline:

1. CI reads the three Artifactory values from pipeline/CI variables (`BASE_REGISTRY`,
   `PIP_INDEX_URL`, `TORCH_INDEX_URL`).
2. Runs `make build PROFILE=enterprise` with those values substituted, producing images
   sourced entirely from Artifactory.
3. Pushes the built images to the internal Artifactory Docker registry.
4. Developers pull those images (Step 3 Path A above) rather than building locally.

> **This repo's own CI** (`.github/workflows/ci.yml`) runs lint and tests only — it does
> not build or push Docker images. The enterprise image pipeline is managed separately by
> your infrastructure team.

---

## Values not in this repository

The following are intentionally absent from this repo and must be obtained from your
enterprise team:

- Artifactory Docker registry URL and login credentials
- `BASE_REGISTRY`, `PIP_INDEX_URL`, `TORCH_INDEX_URL` values
- Internal LLMaaS/vLLM base URL and API key
- Pre-staged model paths or Artifactory HuggingFace mirror URL
- Network proxy settings (`HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`)
- Any enterprise-specific `.env` overrides beyond the three required secrets

---

## Common operations

```bash
# Stop the stack
make down        # backend-core
make down-full   # full stack

# Restart after config changes
make restart

# Open a shell in a running container
make shell SVC=orchestrator-api

# Run the test suite
python ops/testing/run_all_tests.py
```

---

## Troubleshooting

See **[docs/development/guides/bootstrap-troubleshooting.md](docs/development/guides/bootstrap-troubleshooting.md)** for the full list of known failure modes. Most apply equally to enterprise and local profiles:

- `observability` network not found
- Port already in use
- `db-init` schema errors / seed not running
- Model files not found
- Architecture mismatch on x86_64
- `llm-guard-svc` healthcheck timeout

Enterprise-specific: if image pulls fail, confirm `docker login <ARTIFACTORY_REGISTRY>` succeeded and that your network/proxy settings are active in the shell before running Docker commands.

---

## Further reading

- [Getting Started — local profile](GETTING_STARTED.md)
- [Offline & Enterprise Deployment](docs/operations/AIR_GAPPED_DEPLOYMENT.md) — deep build mechanics, ARG/Dockerfile detail, model pre-staging and tokenizer bundle transfer
- [ADR-074 — Multi-profile build strategy](docs/development/adrs/ADR-074-multi-profile-build-and-bootstrap.md)
- [Architecture overview](README.md#architecture)
- [Configuration reference](README.md#configuration-management)
- [Bootstrap troubleshooting](docs/development/guides/bootstrap-troubleshooting.md)
- [Testing guide](docs/testing/TESTING_GUIDE.md)
