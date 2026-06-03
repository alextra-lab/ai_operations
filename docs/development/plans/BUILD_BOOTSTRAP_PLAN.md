# BUILD_BOOTSTRAP_PLAN — Build System & Reproducible Bootstrap

**Status:** 🔄 Active — M1 + M2 Complete, M3 next
**Date:** 2026-05-30
**Last Updated:** 2026-06-03
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
| **offline** | `src/wheelhouse` + `src/npm_cache` (`make build-offline` / `OFFLINE=1`) | — |

> **Note:** The `train` profile name from `ops/bootstrap/up.sh` was retired when `up.sh` was
> replaced by the Makefile (PR #81). The concept survives as `make build-offline` / the
> `OFFLINE` Dockerfile ARG.

**Working method:** trial by fire — bring up the local backend-core first, fix breakages as we
hit them, document each fix, then layer in the full stack and the enterprise/offline paths.

---

## Phase M1 — Local backend-core, query end-to-end ✅ COMPLETE (2026-05-31, AIO-34 / PR #80)

**Target services:** postgres-db, vector-db, redis-cache, db-init, embedding-service, corpus-service, inference-gateway, orchestrator-api
**Deferred to M2:** llm-guard-svc, ui-webapp

### Deliverables

| # | AIO | Task | Primary files |
|---|---|---|---|
| M1-1 | AIO-35 ✅ | Bootstrap wrapper: idempotent `docker network create observability` + `mkdir -p data/{postgres,qdrant,redis,models,llm-guard-models,retrieval/tmp}` | `Makefile` (`make setup`) — replaced `ops/bootstrap/up.sh` |
| M1-2 | AIO-36 ✅ | Fix port 8002 collision: remap embedding host port `8002→8005`; update `EMBEDDING_SERVICE_URL` default; full 18-band host-port scheme (18000–18081) | `deploy/docker-compose.yml`, `config/env/env.template` |
| M1-3 | AIO-37 ✅ | `db-init` one-shot service in compose: init SQL → seeds → migrations → intent-defaults; gate orchestrator/gateway/corpus on `service_completed_successfully` | `deploy/docker-compose.yml`, `ops/database/init_entrypoint.sh` |
| M1-4 | AIO-38 ✅ | Parametrize all 5 Python Dockerfiles + frontend with `BASE_REGISTRY`, `PIP_INDEX_URL`, `OFFLINE` ARGs; remove dead/stale bits; retire `Dockerfile.pipBuild` variants | All service `Dockerfile` files |
| M1-5 | AIO-39 ✅ | `deploy/docker-compose.local.yml` override: backend-core only; llm-guard-svc/ui-webapp behind `profiles: [full]` | `deploy/docker-compose.local.yml` |
| M1-6 | AIO-40 ✅ | Stage embedding model `all-minilm-l6-v2` (~90 MB, 384-dim) via `ops/bootstrap/download_embedding_models.py` | `data/models/` |
| M1-7 | AIO-41 ✅ | Fix `passlib==1.7.4` + `bcrypt>=5` auth incompatibility | `src/orchestrator/requirements.txt`, `src/shared/requirements.txt` |
| M1-8 | AIO-42 ✅ | Seed OpenAI-compatible provider row (LMStudio `host.docker.internal:1234`); validate end-to-end RAG query | `ops/database/seed/010_seed_gateway_providers.sql` |

Post-M1 cleanup (AIO-64/65, shipped in same window):

| AIO | Task |
|---|---|
| AIO-64 ✅ | Pin torch CPU-only via `TORCH_INDEX_URL` ARG across all build profiles — drops embedding image ~1.1 GB |
| AIO-65 ✅ | Consolidate migrations 027–039 into `000_complete_init.sql`; overlap eliminated |

### Success criteria

- [x] `make setup && make build && make up` completes without errors (network + dirs created)
- [x] `docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.local.yml up --build` succeeds
- [x] All 8 target services report `healthy` in `docker compose ps` (7 running + db-init exited 0)
- [x] DB populated: `intent_model_defaults`, `gateway_providers`, `intent_types`, `use_cases`, `models` tables exist and have rows
- [x] `curl localhost:18000/health` → 200; `localhost:18005/health` (embedding) → 200; `localhost:18002/health` (gateway) → 200
- [x] Authenticated POST query to `orchestrator-api:18000` returns a RAG pipeline response (AIO-42 — ModelSelector load-per-request fix; verified via LMStudio qwen3.6-35b, 26→665 tokens, 8.5 s)

---

## Phase M2 — Full local stack (llm-guard + Angular UI) ✅ COMPLETE (2026-06-01, AIO-43)

**Adds to M1:** llm-guard-svc, ui-webapp

### Deliverables

| # | AIO | Task | Primary files |
|---|---|---|---|
| M2-1 | AIO-46 ✅ | Resolve llm-guard Dockerfile spaCy contradiction: `Dockerfile` force-pinned `spacy==3.7.5` while `requirements.txt` asked `>=3.8.14,<3.9.0` | `src/llm_guard_svc/Dockerfile` |
| M2-2 | AIO-47 ✅ | Stage llm-guard ONNX models via `ops/bootstrap/download_llm_guard_models.py` (repo_id→dir map; `ignore_patterns`; no HF_HOME pollution; added missing `sentencepiece` dep) | `data/llm-guard-models/` |
| M2-3 | AIO-48 ✅ | Bring up llm-guard-svc healthy; restore orchestrator→llm-guard `depends_on: service_healthy` in full compose | `deploy/docker-compose.yml` |
| M2-4 | AIO-49 ✅ | Canonicalize Node version to 24 across `Dockerfile`, `README.md`, `CONTRIBUTING.md` | `src/frontend-angular/Dockerfile`, `README.md`, `CONTRIBUTING.md` |
| M2-5 | AIO-50 ✅ | Build and bring up ui-webapp healthy; fix ng2-charts v10 migration (`NgChartsModule`→`BaseChartDirective`); fix nginx `BACKEND_HOST` | `src/frontend-angular/Dockerfile`, nginx config |

### Success criteria

- [x] All 9 services healthy
- [x] `curl localhost:8081/health` (llm-guard) → 200; all 6 scanners active; `/api/validate` detects prompt injection
- [x] Browser: load `:4200`, demo login + query 200 through nginx proxy; SPA renders (0 console errors)

> **LLG-04 impact (2026-06-02, AIO-69–73 / PRs #92–97):** After M2 completed, the LLG-04
> epic replaced the `llm_guard` Python library inside `llm-guard-svc` with native ONNX +
> Presidio/GLiNER scanners. Service remains on the same port with the same HTTP contract;
> compose wiring unchanged. `llm_guard` and its `transformers==4.51.3` hard-pin are removed;
> `transformers>=4.53.0,<4.54.0` unpinned. Affects M3-3 and M3-5 — see below.
>
> **AIO-74 (2026-06-03, PR #98):** Guard client payload bug fixed — `LLMGuardClient` was
> sending `{"query":…}` → 422 → silent guard-off in Pipeline+Steps path. Now sends
> `{"input_text":…}` with `strict_mode` wired end-to-end.

---

## Phase M3 — Enterprise (Artifactory/GitLab-CI) + offline paths (AIO-44)

### Open bug affecting this phase

| AIO | Title | Status |
|---|---|---|
| AIO-67 | Makefile `up`/`down`/`build` don't pass `--env-file config/env/.env` → env vars resolve blank | Approved — fix before M3 validation |
| ~~AIO-68~~ | ~~Prompt-injection model is HF-gated → `make models` fails without a token~~ | **Closed as moot:** LLG-04 (AIO-73) replaced `protectai/deberta-v3-small-prompt-injection-v2` with the native ONNX classifier; `download_llm_guard_models.py` no longer downloads that gated model directly |

### Deliverables

| # | AIO | Task | Primary files |
|---|---|---|---|
| M3-1 | AIO-51 | Capture enterprise specifics: Artifactory URLs, HF model channel, GitLab CI topology | `docs/development/analysis/enterprise-build-requirements.md` *(new)* |
| M3-2 | AIO-52 | Verify parametrized Dockerfiles build with `BASE_REGISTRY`/`PIP_INDEX_URL`/`NPM_REGISTRY` set to Artifactory values | All service Dockerfiles |
| M3-3 | AIO-53 | Enterprise HF model sourcing: stage `all-minilm-l6-v2` + native scanner models (`gliner_multi_pii-v1` + mdeberta backbone tokenizer via `stage_gliner_backbone_tokenizer()`) from Artifactory or approved pre-stage channel | `ops/bootstrap/download_*.py` |
| M3-4 | AIO-54 | Validate internal LLMaaS/vLLM OpenAI-compatible provider row | `ops/database/seed/010_seed_gateway_providers.sql` |
| M3-5 | AIO-55 | ~~Fix `build_wheelhouse.sh` two-pass: resolve `transformers` pin conflict and spaCy contradiction~~ **Resolved by LLG-04 (AIO-73, 2026-06-02):** `llm_guard` removed; `transformers>=4.53.0,<4.54.0`; spaCy contradiction gone. New wheelhouse requirements: add `gliner==0.2.26`, `presidio-analyzer`, `presidio-anonymizer`, `bc-detect-secrets`; stage mdeberta backbone tokenizer offline. | `ops/bootstrap/build_wheelhouse.sh` |
| M3-6 | AIO-56 | Verify `make build-offline` / `OFFLINE=1` path builds and runs from pre-staged data + wheelhouse | All service Dockerfiles |
| M3-7 | AIO-57 | Correct `docs/operations/AIR_GAPPED_DEPLOYMENT.md` (conflates mirror-based enterprise with offline build) | `docs/operations/AIR_GAPPED_DEPLOYMENT.md` |

### Additional approved ticket

| AIO | Task | Notes |
|---|---|---|
| AIO-66 | Adopt Alembic: consolidated schema as revision 0 + ADR for schema-ownership | Approved; follow-on to AIO-65; not blocking M3 but should land before M4 docs |

### Success criteria

- [ ] AIO-67 resolved: `make up` / `make build` correctly load `config/env/.env`
- [ ] Artifactory-style build (URLs substituted or tunnelled) succeeds without public registry access
- [ ] `make build-offline` succeeds with PyPI/HF egress blocked (simulated via firewall or hosts)
- [ ] Stack runs against an OpenAI-compatible endpoint in both enterprise and offline paths
- [ ] `AIR_GAPPED_DEPLOYMENT.md` accurately separates enterprise (mirror-based) from offline (wheelhouse)

---

## Phase M4 — Canonical bootstrap documentation (AIO-45)

### Deliverables

| # | AIO | Task | Primary files |
|---|---|---|---|
| M4-1 | AIO-58 | `GETTING_STARTED.md`: clean checkout → running stack for all profiles; includes model prereqs and DB bootstrap | `GETTING_STARTED.md` *(new, repo root)* |
| M4-2 | AIO-59 | Bootstrap troubleshooting guide: network, arch/platform, port conflicts, DB init, offline model failures | `docs/development/guides/bootstrap-troubleshooting.md` *(new)* |
| M4-3 | AIO-60 | Fix broken links in `README.md` and `docs/development/guidelines/Dependency_Management.md`; refresh stale `docs/README.md` index | `README.md`, `docs/README.md`, `docs/development/guidelines/Dependency_Management.md` |
| M4-4 | AIO-61 | Add missing `src/orchestrator/README.md` and `src/shared/README.md` | Both files *(new)* |
| M4-5 | AIO-62 | Reconcile inference-gateway status: README says "Phase 4.5 / In Development" while platform treats it as live | `src/inference-gateway/README.md` |
| M4-6 | AIO-63 | Update `CLAUDE.md` build/run section with dual-profile (`local` and `enterprise`) commands | `CLAUDE.md` |
| M4-7 | AIO-31 | Refresh `docs/development/adrs/README.md` index (wrong ADR count, stale "latest ADR" pointer) | `docs/development/adrs/README.md` |

### Success criteria

- [ ] Developer with no prior knowledge reaches a running local stack using `GETTING_STARTED.md` alone
- [ ] All links in `README.md` and `docs/development/adrs/README.md` resolve correctly
- [ ] `CLAUDE.md` accurately reflects build commands for local and enterprise profiles
- [ ] Both missing service READMEs exist and are accurate

---

**Last Updated:** 2026-06-03
**Maintained By:** AIOps team
**Linear Project:** AIO - Build System & Bootstrap
**ADR:** ADR-074-multi-profile-build-and-bootstrap.md
