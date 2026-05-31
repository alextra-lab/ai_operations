# ADR-074: Multi-Profile Container Build & Reproducible Bootstrap

**Status:** Proposed
**Date:** 2026-05-30
**Deciders:** Project team
**Tags:** build, deployment, docker, infrastructure, bootstrap

---

## Context

The `ai_operations` platform consists of 9 services (5 Python/FastAPI + 1 Angular + 3 infra)
orchestrated via Docker Compose. After ~6 months of solo development, the platform has **never
been built from a clean checkout**. Several reproducibility gaps have accumulated:

1. **Docker images assume a pre-built wheelhouse.** Every Python service Dockerfile uses
   `pip install --no-index --find-links=/app/wheelhouse`, which requires `src/wheelhouse/` to
   exist at build time. This directory is not committed. Without running
   `ops/bootstrap/build_wheelhouse.sh` first, all backend image builds fail immediately.

2. **The offline wheelhouse is a personal convenience, not the enterprise architecture.**
   The wheelhouse was built to enable building on a train with slow personal internet. The
   enterprise environment uses **GitLab CI + Artifactory**, which provides DockerHub mirrors,
   PyPI remote repositories, and npm remotes. It is mirror-based, not air-gapped. The genuine
   enterprise constraints are: **no direct HuggingFace access** (models via Artifactory or
   pre-staging) and inference via **internal LLMaaS/vLLM** (OpenAI-compatible).

3. **The `Dockerfile.pipBuild` variants are stale and broken.** They use `python:3.11-slim`
   (project targets 3.12) and contain dead `COPY wheelhouse-orchestrator` lines that fail.
   `inference-gateway` has no online variant at all.

4. **Port 8002 is double-bound** in `deploy/docker-compose.yml`: `embedding-service` maps
   `8002:8000` (line 276) and `inference-gateway` maps `8002:8002` (line 347). One service
   will fail to bind on `docker compose up`.

5. **Database bootstrap is never run by compose.** There is no `db-init` service, no
   `docker-entrypoint-initdb.d` mount, and no migration step in Compose. A plain
   `docker compose up` produces a database with only SQLAlchemy `create_all` tables — missing
   `intent_model_defaults` (only created by migration 037, no ORM model), `gateway_providers`
   seed, intents, use-cases, pricing, and RBAC data. The orchestrator's intent-based routing
   pipeline has no data and fails at runtime.

6. **Three distinct build environments need to be supported:**
   - **local:** developer machine with public internet; HuggingFace accessible; any OpenAI-compatible LLM backend.
   - **enterprise:** GitLab CI + Artifactory mirrors for pip/npm/base-images; no HuggingFace direct; internal LLMaaS/vLLM (OpenAI-compatible).
   - **train (offline):** developer machine with no/slow internet; pre-built `src/wheelhouse` and `src/npm_cache`; pre-staged models in `data/`.

---

## Decision

**Use Docker build ARGs to make all service Dockerfiles source-configurable, with one Dockerfile
per service covering all three profiles.** Supplement with a one-shot `db-init` compose service
and a compose override file for local milestone-based bring-up.

### Build ARG schema

| ARG | Default (local) | Enterprise value | Train value |
|---|---|---|---|
| `BASE_REGISTRY` | `docker.io/library` | `<artifactory-dockerhub-mirror>/` | `docker.io/library` (cached) |
| `PIP_INDEX_URL` | `https://pypi.org/simple` | `<artifactory-pypi-remote>` | *(N/A — `OFFLINE=1`)* |
| `OFFLINE` | `0` | `0` | `1` |
| `NPM_REGISTRY` | *(npm default)* | `<artifactory-npm>` | *(N/A — npm_cache)* |

When `OFFLINE=1`, the Dockerfile switches pip to `--no-index --find-links=/app/wheelhouse`,
preserving the existing wheelhouse path as an opt-in rather than the default.

### Dockerfile changes per service
- Replace `FROM python:3.12-slim` with `ARG BASE_REGISTRY=docker.io/library` followed by `FROM ${BASE_REGISTRY}/python:3.12-slim`.
- Add `ARG PIP_INDEX_URL` / `ARG OFFLINE=0`; use a shell conditional to select the pip install path.
- Frontend: add `ARG NPM_REGISTRY` for `npm ci`.
- Remove: dead `COPY wheelhouse-orchestrator` lines, `python:3.11` base drift, force-pinned `spacy==3.7.5` in llm_guard_svc (contradicts `>=3.8.14` in requirements), unconditional `TRANSFORMERS_OFFLINE=1`/`HF_HUB_OFFLINE=1` flags (gate behind `OFFLINE=1`).
- **Retire all `Dockerfile.pipBuild` variants** once the main Dockerfiles accept ARGs.
- `inference-gateway` (currently only has an offline Dockerfile) is covered by the same parametrized Dockerfile.

### Compose structure
- **`deploy/docker-compose.yml`** — base: all 9 services with cross-cutting fixes (`build.args` reference ARGs with public defaults). Receives the port-collision fix (embedding → `8005:8000`) and the `db-init` service.
- **`deploy/docker-compose.local.yml`** *(new)* — local/M1 override: trims to backend-core (defers llm-guard-svc + ui-webapp); relaxes orchestrator's hard dependency on llm-guard.
- **`Makefile`** *(replaces `ops/bootstrap/up.sh`)* — developer interface: `make setup` creates the `observability` network and `data/` subdirs (idempotent); `make build [PROFILE=local|enterprise]` assembles the correct compose files and build-args; `make up/down/logs/status` covers daily workflow. The `train` profile introduced in `up.sh` was removed — it was not a deployment tier, the wheelhouse is an offline-build mechanism exposed via `make build-offline`.

### Database bootstrap in compose
Add a one-shot `db-init` service (Alpine + psql + Python) that runs after `postgres-db` is
healthy and applies in order:
1. `ops/database/init/000_complete_init.sql`
2. `ops/database/run_migrations.sh` (tracks state in `schema_migrations` — idempotent)
3. `ops/database/seed/001_*.sql` through `011_*.sql`
4. `python ops/database/seed_intent_defaults_from_env.py`

`orchestrator-api`, `inference-gateway`, and `corpus-service` gain:
```yaml
depends_on:
  db-init:
    condition: service_completed_successfully
```

Implemented via a new `ops/database/init_entrypoint.sh` shell script COPY'd into the db-init image.

### Port collision fix
Remap `embedding-service` host port from `8002` to `8005` in `docker-compose.yml`.
Update `EMBEDDING_SERVICE_URL` default in `config/env/env.template` and the compose
environment block for services that depend on it.

---

## Alternatives Considered

### Option 1: Separate Dockerfiles per profile
**Description:** Keep `Dockerfile` (offline) and `Dockerfile.pipBuild` (online); add `Dockerfile.enterprise`.
**Pros:**
- No ARG conditionals in Dockerfiles (simpler per-file)
- Each file is fully self-contained

**Cons:**
- Three files to maintain per service (15+ Dockerfiles total)
- Drift between files already causing bugs (`python:3.11`, dead `COPY` lines, spaCy contradiction)
- No single place to see the full build picture

**Why Rejected:** The stale `Dockerfile.pipBuild` files demonstrate that multi-file maintenance does not hold. Build ARGs are a standard Docker pattern for registry/index substitution.

### Option 2: Docker BuildKit multi-stage targets
**Description:** Use `--target local|enterprise|train` build targets within a single Dockerfile.
**Pros:**
- Single file with named, explicit build targets

**Cons:**
- Forces multi-stage architecture even for services that don't benefit
- `docker compose build` target selection is more cumbersome than ARG overrides
- Overkill: the three profiles differ only in registry URLs and an offline flag

**Why Rejected:** ARGs are simpler and compose-native for URL substitution and simple boolean flags.

### Option 3: Keep and fix the Dockerfile.pipBuild variants
**Description:** Fix stale issues (`python:3.11→3.12`, dead `COPY`) and add a missing inference-gateway variant.
**Pros:**
- Minimal change to existing structure

**Cons:**
- Still two files per service to keep in sync
- Does not address the enterprise (Artifactory) profile
- Profile selection still requires a wrapper mechanism
- Solving local-only doesn't cover enterprise or validate the offline path

**Why Rejected:** Patching the variants solves local-only and still requires per-service duplication. ARGs handle all three profiles from one file.

---

## Consequences

### Positive Consequences
- One Dockerfile per service — no drift between online/offline/enterprise variants.
- All three profiles tested from the same codebase with different ARG values.
- Enterprise teams can build with `BASE_REGISTRY` + `PIP_INDEX_URL` without touching Dockerfiles.
- Train/offline path preserved as a first-class `OFFLINE=1` opt-in.
- DB bootstrap wired into compose — no manual SQL execution needed on first `docker compose up`.
- Port collision resolved permanently (embedding remapped to `:8005`).
- Stale `Dockerfile.pipBuild` variants removed, reducing maintenance surface.

### Negative Consequences
- Dockerfiles become slightly more complex (shell `if/else` for pip install path).
- New developers must understand the ARG system (mitigated by `up.sh` wrapper and M4 bootstrap guide).
- Enterprise Artifactory URLs are placeholders until M3 — enterprise profile untestable without real URLs.

### Risks and Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| `000_complete_init.sql` overlaps with migration 027+ content, causing duplicate-object errors in db-init | Medium | Verify empirically in M1; `run_migrations.sh` tracks `schema_migrations` for idempotency; wrap init SQL in `IF NOT EXISTS` guards where possible |
| spaCy / transformers pin conflict in llm_guard_svc (`requirements.txt` asks `>=3.8.14,<3.9`; historical Dockerfile hard-pins `3.7.5`) breaks M2 build | Medium | Resolve during M2 llm_guard work; options: update to spaCy 3.8.x, drop the force-pin, or evaluate llm-guard replacement (AIO-1) |
| Enterprise Artifactory URLs unknown until M3 | Low | ARG defaults are valid public values; enterprise profile documented as "fill in during M3" |
| `passlib==1.7.4` + `bcrypt>=5` auth break at orchestrator/gateway startup | Medium | Pin `bcrypt<4.1` or migrate auth hashing off passlib (fix in M1 if hit at startup) |
| `db-init` bootstrap ordering (init vs. migrations vs. seeds) may have conflicts | Medium | Confirm empirically in M1; make entrypoint check `schema_migrations` tracking table before each migration |

---

## Implementation Notes

**Files to create/modify:**
- `src/orchestrator/Dockerfile` — add `BASE_REGISTRY`, `PIP_INDEX_URL`, `OFFLINE` ARGs
- `src/corpus_svc/Dockerfile` — same
- `src/embedding/Dockerfile` — same; gate `HF_HUB_OFFLINE` / `TRANSFORMERS_OFFLINE` behind `OFFLINE=1`
- `src/inference-gateway/Dockerfile` — same (only offline variant exists today)
- `src/llm_guard_svc/Dockerfile` — same; remove `spacy==3.7.5` force-pin; gate offline flags
- `src/frontend-angular/Dockerfile` — add `NPM_REGISTRY` ARG
- `deploy/docker-compose.yml` — port fix (embedding 8002→8005), `db-init` service, `build.args`
- `deploy/docker-compose.local.yml` *(new)* — backend-core override for M1
- `ops/bootstrap/up.sh` *(new)* — profile wrapper (creates network + data dirs)
- `ops/database/init_entrypoint.sh` *(new)* — db-init container entrypoint
- `config/env/env.template` — update `EMBEDDING_SERVICE_URL` default
- `src/*/Dockerfile.pipBuild` — *deleted* once main Dockerfiles parametrized

**Execution sequence:** M1 → M4 per `docs/development/plans/BUILD_BOOTSTRAP_PLAN.md`.

**Related ADRs:**
- ADR-022 (Backend Async Database Migration) — migration system being reused in db-init
- ADR-036 (Orchestrator Pipeline Pattern) — explains intent routing dependency on `intent_model_defaults`
- ADR-073 (LLM Guard Model Selection and Storage) — informs M2/M3 model staging decisions

---

## References

- `docs/development/plans/BUILD_BOOTSTRAP_PLAN.md` — milestone execution plan
- `deploy/docker-compose.yml` — current compose (port collision at lines 276 and 347)
- `ops/bootstrap/build_wheelhouse.sh` — wheelhouse build script (train path, preserved unchanged)
- `docs/operations/AIR_GAPPED_DEPLOYMENT.md` — to be corrected in M3 (conflates enterprise and train)
- ADR-022: Backend Async Database Migration
- ADR-036: Orchestrator Pipeline Pattern
- ADR-073: LLM Guard Model Selection and Storage Strategy
- Linear: AIO - Build System & Bootstrap project

---

## Status Updates

### 2026-05-30 — Proposed
**Changed By:** Project team (Alex / Claude)
**Reason:** First clean-checkout bootstrap attempt surfaces reproducibility gaps and corrects the
enterprise/offline misclassification. Formalizes the three-profile build strategy.

---

**Template Version:** 1.0
**Based On:** [Michael Nygard's ADR pattern](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
