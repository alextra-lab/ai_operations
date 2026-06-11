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

**Platform:** The base compose file (the one the enterprise profile uses) is
platform-neutral — builds, pulls, and runs follow the host platform, so amd64
hosts need no override. The `linux/arm64` pins exist only in the local-profile
overlay. Set `DOCKER_DEFAULT_PLATFORM` only when cross-building (e.g. producing
amd64 images on an Apple Silicon machine):

```bash
export DOCKER_DEFAULT_PLATFORM=linux/amd64
```

Or set it once in `config/make.local.mk` (see Path B below) so it applies to every `make` command without re-exporting.

---

## What your enterprise team must provide

These values are **not committed to this repository**. Your enterprise team is the source of truth for each of them.

| Value | What it is | Where it's used |
|---|---|---|
| `BASE_REGISTRY` | Artifactory-hosted Docker Hub mirror | Makefile `BUILD_ARGS` — rewrites `FROM` base image pulls away from `docker.io/library` |
| `PIP_INDEX_URL` | Artifactory PyPI remote URL | Makefile `BUILD_ARGS` — used as `pip --index-url` during image builds |
| `TORCH_INDEX_URL` | Artifactory PyTorch CPU wheel remote URL | Makefile `BUILD_ARGS` — used for torch installs during image builds |
| `NPM_REGISTRY` | Artifactory npm remote URL | Frontend (`ui-webapp`) build — `npm ci` registry; without it npm hits `registry.npmjs.org` and fails with `ENOTFOUND` |
| Artifactory Docker registry URL | Where pre-built images are pushed and pulled from | `docker login` + `docker pull` / `docker compose pull` |
| LLMaaS/vLLM base URL | Internal OpenAI-compatible inference endpoint | `gateway_providers` table — see Step 4 |
| Pre-staged model paths | Populated `data/models/`, `data/llm-guard-models/` directories | Bind-mounted into embedding-service and llm-guard-svc |

> **Build ARGs are not in `.env`.** Do not look for `BASE_REGISTRY`, `PIP_INDEX_URL`, or
> `TORCH_INDEX_URL` in `config/env/env.template` — they are not there. They are build-time
> ARGs passed to `docker compose build`. Supply them in `config/make.local.mk` (see Path B),
> on the `make` command line, or via CI/CD variables before a build runs.

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

The validator loads `config/env/.env` itself — you do not need to export it into your
shell first (shell environment variables take precedence over the file if both are set).

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

# Pull all images (service + infra) from your registry
make pull
```

`make pull` exports `BASE_REGISTRY` from `config/make.local.mk` so the infra images
(`postgres`, `qdrant/qdrant`, `redis`) and the service images all resolve to your
Artifactory rather than Docker Hub. If you invoke compose directly instead, export the
registry first so the `image:` names interpolate:

```bash
BASE_REGISTRY=<your-artifactory>/docker \
  docker compose --env-file config/env/.env -f deploy/docker-compose.yml pull
```

Your enterprise team will provide the registry URL and login instructions.

> This repo's own GitHub Actions CI (lint and tests only) does **not** build or push images.
> Image distribution is handled by the internal enterprise CI/CD pipeline.

### Path B — Build locally (advanced, requires local Make configuration)

If you need to build images yourself, supply the three Artifactory URLs your enterprise team
provides. The recommended way is a local, gitignored Make config that the Makefile
auto-includes — set the values once and every `make` command picks them up:

```bash
cp config/make.local.mk.template config/make.local.mk
```

Edit `config/make.local.mk` with the real values (and `DOCKER_DEFAULT_PLATFORM` on amd64 hosts):

```makefile
PROFILE         = enterprise
BASE_REGISTRY   = your-artifactory.example.com/docker
PIP_INDEX_URL   = https://your-artifactory.example.com/artifactory/api/pypi/pypi/simple
TORCH_INDEX_URL = https://your-artifactory.example.com/artifactory/api/pypi/torch-cpu/simple
NPM_REGISTRY    = https://your-artifactory.example.com/artifactory/api/npm/npm/
```

Then build with no extra flags:

```bash
make build      # PROFILE=enterprise and the URLs are picked up automatically
```

For a one-off build without the file, pass the values on the command line instead — they
override `config/make.local.mk`:

```bash
make build PROFILE=enterprise \
  BASE_REGISTRY=... PIP_INDEX_URL=... TORCH_INDEX_URL=...
```

The Makefile's committed defaults are `<…PLACEHOLDER>` strings that intentionally fail the
build until you override them via either method above.

The `enterprise` profile uses the base `deploy/docker-compose.yml` only (no local override).
Each service Dockerfile accepts `BASE_REGISTRY` to rewrite the `FROM` base image pull and
`PIP_INDEX_URL` as `pip --index-url`. No Dockerfile edits are required.

**npm registry authentication.** If your Artifactory npm repo requires a login (most do),
`NPM_REGISTRY` alone is not enough — npm needs credentials in an `.npmrc`, and it does **not**
accept them in the URL (`https://user:pass@host/...` is ignored). Put them in a gitignored
file the frontend build reads:

```bash
# Paste your Artifactory "Set Me Up" npm snippet (registry + _auth/_authToken +
# always-auth) into this file. It is gitignored and only exists in the discarded
# build stage — it never ships in the image.
$EDITOR src/frontend-angular/.npmrc.local
```

A `401`/`403` from `npm ci` means missing or invalid auth here; `ENOTFOUND` means the registry
URL itself isn't reaching the mirror.

For full ARG and Dockerfile mechanics, see
[Offline & Enterprise Deployment](docs/operations/AIR_GAPPED_DEPLOYMENT.md#enterprise-profile-artifactory-mirrors).

### Corporate TLS interception / internal CA (`SSL: CERTIFICATE_VERIFY_FAILED`)

If your network intercepts TLS or Artifactory serves a certificate from an internal CA,
`make build` fails at the `pip install` (or npm) step with
`SSL: CERTIFICATE_VERIFY_FAILED` — build containers trust only public CAs by default.
Fix it once:

```bash
# Drop your enterprise CA chain (PEM format) into src/certs/ — gitignored
cp /path/to/enterprise-root-ca.crt src/certs/
make build
```

Every image build appends `src/certs/*.crt` / `*.pem` to the container's trust bundle and
points `PIP_CERT` / `SSL_CERT_FILE` at it (pip, Python's urllib, and the frontend's npm
via `NODE_EXTRA_CA_CERTS` all honor it). The directory is empty in public checkouts and
the mechanism is a no-op then.

Two related trust stores this does **not** cover:

- **`docker login` / `docker pull` (Path A)** — registry trust belongs to the Docker
  *daemon*, not the build. Configure `/etc/docker/certs.d/<registry-host>/ca.crt`
  (Linux) or add the CA to the OS keychain (Docker Desktop).
- **Runtime egress** (e.g. the gateway calling your LLMaaS endpoint over TLS) — if that
  endpoint also presents an internal CA, that is deployment configuration, not image
  build; ask your enterprise team for the standard approach.

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
