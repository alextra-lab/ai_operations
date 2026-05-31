# BUILD_BOOTSTRAP_PLAN — Build System & Reproducible Bootstrap

**Status:** 🔄 Active — M1 pending execution
**Date:** 2026-05-30
**ADR:** [ADR-074 — Multi-Profile Container Build & Reproducible Bootstrap](../adrs/ADR-074-multi-profile-build-and-bootstrap.md)
**Linear Project:** AIO - Build System & Bootstrap
**Relation to Roadmap:** Foundational pre-condition beneath all existing AIO phases (which assume the platform already builds). Does not replace MASTER_ROADMAP_V2 milestones; it unblocks them.

---

## Overview

This plan takes `ai_operations` from a cold checkout to a reproducible, running stack across
three build profiles:

| Profile | Package sources | LLM backend |
|---|---|---|
| **local** | public PyPI / docker.io / npm | LMStudio / cloud (OpenAI-compatible) |
| **enterprise** | Artifactory mirrors (DockerHub, PyPI, npm) | Internal LLMaaS / vLLM (OpenAI-compatible) |
| **train (offline)** | `src/wheelhouse` + `src/npm_cache` | — |

**Working method:** trial by fire — bring up the local backend-core first, fix breakages as we
hit them, document each fix, then layer in the full stack and the enterprise/offline paths.

---

## Phase M1 — Local backend-core, query end-to-end

**Target services:** postgres-db, vector-db, redis-cache, db-init, embedding-service, corpus-service, inference-gateway, orchestrator-api
**Deferred to M2:** llm-guard-svc, ui-webapp

### Deliverables

| # | Task | Primary files | Links |
|---|---|---|---|
| M1-1 | Bootstrap wrapper: idempotent `docker network create observability` + `mkdir -p data/{postgres,qdrant,redis,models,llm-guard-models,retrieval/tmp}` | `ops/bootstrap/up.sh` *(new)* | — |
| M1-2 | Fix port 8002 collision: remap embedding host port `8002→8005`; update `EMBEDDING_SERVICE_URL` default | `deploy/docker-compose.yml` line 276, `config/env/env.template` | ADR-074 |
| M1-3 | `db-init` one-shot service in compose: init SQL → migrations → seeds → intent-defaults; gate orchestrator/gateway/corpus on `service_completed_successfully` | `deploy/docker-compose.yml`, `ops/database/init_entrypoint.sh` *(new)* | AIO-33, AIO-6 |
| M1-4 | Parametrize all 5 Python Dockerfiles + frontend with `BASE_REGISTRY`, `PIP_INDEX_URL`, `OFFLINE` ARGs; remove dead/stale bits; retire `Dockerfile.pipBuild` variants | All service `Dockerfile` files | ADR-074 |
| M1-5 | `deploy/docker-compose.local.yml` override: backend-core only, relax orchestrator→llm-guard `depends_on` | `deploy/docker-compose.local.yml` *(new)* | — |
| M1-6 | Stage embedding model `all-minilm-l6-v2` (~90 MB, 384-dim) via `ops/bootstrap/download_embedding_models.py` | `data/models/` | — |
| M1-7 | Fix `passlib==1.7.4` + `bcrypt>=5` auth incompatibility if hit at orchestrator/gateway startup | `src/orchestrator/requirements.txt`, `src/shared/requirements.txt` | — |
| M1-8 | Seed OpenAI-compatible provider row (default: LMStudio `host.docker.internal:1234`); wire user's actual LLM endpoint | `ops/database/seed/010_seed_gateway_providers.sql` | — |

### Success criteria

- [x] `ops/bootstrap/up.sh --profile local` completes without errors (network + dirs created)
- [x] `docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.local.yml up --build` succeeds
- [x] All 8 target services report `healthy` in `docker compose ps` (7 running + db-init exited 0)
- [x] DB populated: `intent_model_defaults`, `gateway_providers`, `intent_types` (not `intents`), `use_cases`, `models` tables exist and have rows
- [x] `curl localhost:18000/health` → 200; `localhost:18005/health` (embedding) → 200; `localhost:18002/health` (gateway) → 200 (ports remapped to 18-band per AIO-36)
- [ ] Authenticated POST query to `orchestrator-api:18000` returns a RAG pipeline response (pending LMStudio on :1234 — AIO-42)

### Open items to resolve during M1
- ~~DB bootstrap ordering: confirm `000_complete_init.sql` vs. migrations 027–039 overlap~~ Resolved — AIO-65 consolidated all 027–039 into init; overlap eliminated
- Decide M1 LLM endpoint (LMStudio default or user's cloud/LLMaaS — defer until M1-8)
- Confirm whether MCP stdio (`docker-ce-cli` in orchestrator image) is needed for M1 or deferrable

---

## Phase M2 — Full local stack (llm-guard + Angular UI)

**Adds to M1:** llm-guard-svc, ui-webapp

### Deliverables

| # | Task | Primary files | Links |
|---|---|---|---|
| M2-1 | Resolve llm-guard Dockerfile spaCy contradiction: `Dockerfile` force-pins `spacy==3.7.5` while `requirements.txt` asks `>=3.8.14,<3.9.0` | `src/llm_guard_svc/Dockerfile` | AIO-3, AIO-2, AIO-1 |
| M2-2 | Stage llm-guard ONNX models via `ops/bootstrap/download_llm_guard_models.py` (post-ADR-073 simplification) | `data/llm-guard-models/` | AIO-3 |
| M2-3 | Bring up llm-guard-svc healthy; restore orchestrator→llm-guard `depends_on` in full compose | `deploy/docker-compose.yml` | — |
| M2-4 | Reconcile Node version: README/CONTRIBUTING say 24, `frontend-angular/Dockerfile` uses 26, frontend README says "18+" → choose and canonicalize | `src/frontend-angular/Dockerfile`, `README.md`, `CONTRIBUTING.md` | — |
| M2-5 | Build and bring up ui-webapp healthy | `src/frontend-angular/Dockerfile` | — |

### Success criteria

- [ ] All 9 services healthy
- [ ] `curl localhost:8081/health` (llm-guard) → 200
- [ ] Browser: load `:4200`, log in with demo credentials (`docs/demo/DEMO_CREDENTIALS.md`), submit a query, receive a response

---

## Phase M3 — Enterprise (Artifactory/GitLab-CI) + train (offline) paths

### Deliverables

| # | Task | Primary files | Links |
|---|---|---|---|
| M3-1 | Capture enterprise specifics: Artifactory URLs, HF model channel, GitLab CI topology | `docs/development/analysis/enterprise-build-requirements.md` *(new)* | — |
| M3-2 | Verify parametrized Dockerfiles build with `BASE_REGISTRY`/`PIP_INDEX_URL`/`NPM_REGISTRY` set to Artifactory values | All service Dockerfiles | ADR-074 |
| M3-3 | Enterprise HF model sourcing (no HF direct): stage `all-minilm-l6-v2` + llm-guard models from Artifactory or approved pre-stage channel | `ops/bootstrap/download_*.py` | — |
| M3-4 | Validate internal LLMaaS/vLLM OpenAI-compatible provider row | `ops/database/seed/010_seed_gateway_providers.sql` | — |
| M3-5 | Fix `ops/bootstrap/build_wheelhouse.sh` two-pass: resolve `transformers` pin conflict (`constraints.txt >=5.9.0` vs llm-guard's older pin) and spaCy contradiction | `ops/bootstrap/build_wheelhouse.sh`, `src/llm_guard_svc/requirements.txt`, `constraints.txt` | — |
| M3-6 | Verify `OFFLINE=1` train path builds and runs from pre-staged data + wheelhouse | All service Dockerfiles | ADR-074 |
| M3-7 | Sketch GitLab CI build/push pipeline against Artifactory DockerHub mirror | `deploy/.gitlab-ci.yml` *(new, draft)* | — |
| M3-8 | Correct `docs/operations/AIR_GAPPED_DEPLOYMENT.md` (conflates mirror-based enterprise with offline train) | `docs/operations/AIR_GAPPED_DEPLOYMENT.md` | — |

### Success criteria

- [ ] Artifactory-style build (URLs substituted or tunnelled) succeeds without public registry access
- [ ] `OFFLINE=1` build succeeds with PyPI/HF egress blocked (simulated via firewall or hosts)
- [ ] Stack runs against an OpenAI-compatible endpoint in both enterprise and train paths
- [ ] `AIR_GAPPED_DEPLOYMENT.md` accurately separates enterprise (mirror-based) from train (offline)

---

## Phase M4 — Canonical bootstrap documentation

### Deliverables

| # | Task | Primary files | Links |
|---|---|---|---|
| M4-1 | `GETTING_STARTED.md`: clean checkout → running stack for all 3 profiles; includes model prereqs and DB bootstrap (current docs omit these) | `GETTING_STARTED.md` *(new, repo root)* | AIO-27 |
| M4-2 | Bootstrap troubleshooting guide: network, arch/platform, port conflicts, DB init, offline model failures | `docs/development/guides/bootstrap-troubleshooting.md` *(new)* | — |
| M4-3 | Fix broken links in `README.md` and `docs/development/guidelines/Dependency_Management.md`; refresh stale `docs/README.md` index (wrong ADR count, dead roadmap links) | `README.md`, `docs/README.md`, `docs/development/guidelines/Dependency_Management.md` | AIO-27 |
| M4-4 | Add missing `src/orchestrator/README.md` and `src/shared/README.md` | Both files *(new)* | — |
| M4-5 | Reconcile inference-gateway status: its README says "Phase 4.5 / In Development" while CLAUDE.md and platform treat it as a live service | `src/inference-gateway/README.md` | — |
| M4-6 | Update `CLAUDE.md` build/run section with dual-profile (`local` and `enterprise`) commands | `CLAUDE.md` | — |
| M4-7 | Refresh `docs/development/adrs/README.md` index (wrong ADR count, stale "latest ADR" pointer) | `docs/development/adrs/README.md` | AIO-31 |

### Success criteria

- [ ] Developer with no prior knowledge of the repo reaches a running local stack using `GETTING_STARTED.md` alone
- [ ] All links in `README.md` and `docs/development/adrs/README.md` resolve correctly
- [ ] `CLAUDE.md` accurately reflects build commands for local and enterprise profiles
- [ ] Both missing service READMEs exist and are accurate

---

**Last Updated:** 2026-05-30
**Maintained By:** AIOps team
**Linear Project:** AIO - Build System & Bootstrap
**ADR:** ADR-074-multi-profile-build-and-bootstrap.md
