# Offline & Enterprise Deployment

> **Clarification (ADR-074):** "Air-gapped" in this repo means two distinct things that are
> often conflated. This document describes both clearly and separately.

## Two distinct deployment modes

| Mode | What it is | How |
|---|---|---|
| **Enterprise** | Mirror-based — uses Artifactory instead of public registries | `make build PROFILE=enterprise` |
| **Offline (local)** | Wheelhouse-based — no PyPI access needed at build time | `make build-offline` |

**Enterprise ≠ air-gapped.** Enterprise machines have network access; they just route through
internal Artifactory mirrors (Docker Hub, PyPI, npm) rather than the public internet. The
build process is otherwise identical to local.

**Offline** is a personal-developer convenience: once `src/wheelhouse/` is populated, Python
packages are installed from local `.whl` files. Docker base image pulls still require network
access unless you also override `BASE_REGISTRY`.

---

## Enterprise profile (Artifactory mirrors)

Managed internally by the enterprise team. The Makefile passes three ARGs when
`PROFILE=enterprise`:

```makefile
BASE_REGISTRY   = <ARTIFACTORY_DOCKER_REGISTRY_PLACEHOLDER>
PIP_INDEX_URL   = <ARTIFACTORY_PYPI_URL_PLACEHOLDER>
TORCH_INDEX_URL = <ARTIFACTORY_TORCH_CPU_URL_PLACEHOLDER>
```

The actual Artifactory URLs are provided by your enterprise team and are not committed to
this repository. Substitute them when running the build:

```bash
make build PROFILE=enterprise \
  BASE_REGISTRY=your-artifactory.example.com/docker \
  PIP_INDEX_URL=https://your-artifactory.example.com/artifactory/api/pypi/pypi/simple \
  TORCH_INDEX_URL=https://your-artifactory.example.com/artifactory/api/pypi/torch-cpu/simple
```

Or export them before calling `make`:

```bash
export BASE_REGISTRY=...
export PIP_INDEX_URL=...
export TORCH_INDEX_URL=...
make build PROFILE=enterprise
```

Each parametrized Dockerfile accepts these ARGs and uses them for the base image pull and
pip install. No Dockerfile edits are required.

**CI/CD:** Enterprise builds run in GitLab CI. The pipeline sets these variables via CI
environment configuration. Local developers on the enterprise network do not build images
manually — images are distributed via the internal Artifactory Docker registry.

---

## Offline build (local wheelhouse)

`make build-offline` passes `--build-arg OFFLINE=1` to the build. Each Dockerfile installs
Python dependencies from `src/wheelhouse/` rather than PyPI:

```dockerfile
# In each service Dockerfile (simplified):
ARG OFFLINE=0
RUN if [ "$OFFLINE" = "1" ]; then \
      pip install --no-index --find-links=/app/wheelhouse -r requirements.txt; \
    else \
      pip install --index-url "$PIP_INDEX_URL" -r requirements.txt; \
    fi
```

### Step 1 — Build the wheelhouse (internet-connected machine)

```bash
bash ops/bootstrap/build_wheelhouse.sh
# Populates src/wheelhouse/ with .whl files for all Python services
```

### Step 2 — Build the npm cache (optional, for offline frontend builds)

```bash
bash ops/bootstrap/build_npm_cache_linux.sh
# Must be run inside a Linux container to produce Linux-compatible native binaries
```

### Step 3 — Build images offline

```bash
make build-offline
# Equivalent to: docker compose build --build-arg OFFLINE=1
```

### Offline build scope

| Dependency type | Offline? | Notes |
|---|---|---|
| Python packages | ✅ Yes | Installed from `src/wheelhouse/` |
| npm packages | ⚠️ Partial | Most packages cached; native binaries (e.g. `lmdb`) may still download |
| Docker base images | ❌ No | Still pulled from `docker.io/library` unless `BASE_REGISTRY` is also overridden |

To make base image pulls offline as well, combine both ARGs:

```bash
DOCKER_BUILDKIT=0 docker compose --env-file config/env/.env \
  -f deploy/docker-compose.yml build \
  --build-arg OFFLINE=1 \
  --build-arg BASE_REGISTRY=<your-local-mirror>
```

---

## Tokenizer bundling for offline environments

If the deployment environment has no access to HuggingFace, pre-stage the tokenizer files
on an internet-connected machine and transfer them:

```bash
# On internet-connected machine
bash ops/bootstrap/prepare_tokenizers.sh
# Creates tokenizer_bundle.tar.gz from data/tokenizers/

# Transfer to offline host, then extract:
tar -xzf tokenizer_bundle.tar.gz
# Extracts into data/tokenizers/
```

Supported tokenizer models: `foundation-sec`, `phi-4-mini`, `mistral-large`, `mistral-small`,
`gpt-oss`, `llama`.

Models for the embedding service and llm-guard-svc are downloaded separately:

```bash
make models-embedding     # → data/models/
make models-llm-guard     # → data/llm-guard-models/
```

Transfer `data/models/` and `data/llm-guard-models/` alongside the tokenizer bundle.

---

## Related

- **[ADR-074](../development/adrs/ADR-074-multi-profile-build-and-bootstrap.md)** — Multi-profile build strategy
- **[ADR-019](../development/adrs/ADR-019-Offline-Tokenizer-Strategy.md)** — Offline tokenizer strategy
- **[ADR-051](../development/adrs/ADR-051-Provider-Secrets-and-Service-to-Service-Auth.md)** — Provider secrets (enterprise S2S auth)
- **[Bootstrap troubleshooting](../development/guides/bootstrap-troubleshooting.md)** — Common startup failures
