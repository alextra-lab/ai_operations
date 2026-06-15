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
this repository.

**Recommended — set them once in a local Make config.** Copy the template and edit it; the
Makefile auto-includes `config/make.local.mk` (gitignored), so `PROFILE`, the Artifactory
URLs, and `DOCKER_DEFAULT_PLATFORM` apply to every `make` command without re-typing:

```bash
cp config/make.local.mk.template config/make.local.mk
# edit config/make.local.mk, then:
make build      # PROFILE=enterprise and the URLs are picked up automatically
make up
```

**One-off — pass them on the command line** (overrides `config/make.local.mk`):

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

### Torch / local ML is opt-in (default OFF) — no nvidia in default images

By default, **`embedding-service` and `llm-guard-svc` build without PyTorch** (and therefore
without the multi-GB `nvidia-*` CUDA wheels that `torch` pulls in on x86_64 **and** arm64).
This is the right default for enterprise: there is usually no CPU-torch (`torch==X+cpu`) source
behind the Artifactory mirrors, and the deploy targets are CPU-only. `TORCH_INDEX_URL` above is
unused unless you opt in.

Two build flags gate the torch/ML stack (both default `0` on every profile):

| Flag | Service | What it installs when `=1` |
|---|---|---|
| `WITH_LOCAL_EMBEDDING` | `embedding-service` | `torch` + `sentence-transformers` (local SentenceTransformer provider) |
| `WITH_LLM_GUARD_MODELS` | `llm-guard-svc` | `torch`, `transformers`, `onnxruntime`, `gliner`, `spaCy` (model-based scanners) |

**Default behavior (flags off):**
- `embedding-service` starts with **no active provider** → embedding requests return
  `503 "No providers available"` until one is enabled in `app/config/models.yaml`.
- `llm-guard-svc` starts, loads models lazily (nothing at startup), and **stays disabled**
  (`LLM_GUARD_ENABLED=false`); `/health` passes, so the `ui-webapp → llm-guard` compose
  dependency is satisfied. Model scanners simply never load.

**To enable local torch-based features**, you need both the flag **and** a CPU-torch source —
there is no `+cpu` wheel on a plain PyPI mirror, only at `download.pytorch.org/whl/cpu`:

```bash
# Stage the CPU torch wheels into the wheelhouse on an internet-connected machine:
pip download torch==<ver>+cpu --index-url https://download.pytorch.org/whl/cpu \
  --only-binary=:all: --platform manylinux2014_x86_64  --python-version 312 -d src/wheelhouse
pip download torch==<ver>+cpu --index-url https://download.pytorch.org/whl/cpu \
  --only-binary=:all: --platform manylinux2014_aarch64 --python-version 312 -d src/wheelhouse

# Then build offline with the flag on (no torch index consulted):
make build-offline SVC=embedding-service WITH_LOCAL_EMBEDDING=1
make build-offline SVC=llm-guard-svc     WITH_LLM_GUARD_MODELS=1
```

If your Artifactory **does** proxy a CPU torch index, point `TORCH_INDEX_URL` at it and use a
normal (online) `make build … WITH_LOCAL_EMBEDDING=1` instead.

**CI/CD:** Enterprise builds run in GitLab CI. The pipeline sets these variables via CI
environment configuration. Local developers on the enterprise network do not build images
manually — images are distributed via the internal Artifactory Docker registry.

---

## Offline build (local wheelhouse)

`make build-offline` passes `--build-arg OFFLINE=1` to the build. Each Dockerfile installs
Python dependencies from `src/wheelhouse/` rather than PyPI:

```dockerfile
# In each service Dockerfile (simplified) — runs in a builder stage; the
# wheelhouse is not shipped in the final image:
ARG OFFLINE=0
RUN if [ "$OFFLINE" = "1" ]; then \
      pip install --no-index --find-links=/wheelhouse -r requirements.txt; \
    else \
      pip install --index-url "$PIP_INDEX_URL" -r requirements.txt; \
    fi
```

The images install no OS packages (`apt-get` is not used in any service
Dockerfile), so offline image builds need no Debian mirror — only the base
image (`BASE_REGISTRY`) and the wheelhouse.

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
