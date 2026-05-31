# Development Session - 2026-05-31
**Focus:** M1 — First clean-checkout build, local backend-core   **Status:** Complete

## Work Completed
- AIO-35: `ops/bootstrap/up.sh` profile wrapper (local/enterprise/train)
- AIO-36: Port collision fixed → 18-band host ports (18000/18001/18002/18005)
- AIO-37: `db-init` one-shot compose service + `ops/database/init_entrypoint.sh`
- AIO-38: All 5 Python Dockerfiles parametrized with `BASE_REGISTRY/PIP_INDEX_URL/OFFLINE` ARGs; 4 stale `.pipBuild` variants deleted; `src/.dockerignore` + root `.dockerignore` fixed
- AIO-39: `deploy/docker-compose.local.yml` override; `llm-guard-svc`/`ui-webapp` gated behind `profiles: [full]`
- AIO-40: `all-minilm-l6-v2` model staged to `data/models/` (87 MB, safetensors)
- All 8 M1 services confirmed healthy; DB populated (gateway_providers 1, models 10, intent_types 11, use_cases 13)

## Key Decisions
- 18-band host ports (18000–18081) — clean, clearly owned by this stack
- `profiles: [full]` to exclude llm-guard/UI from M1 vs override/delete approach
- Seeds run **before** migrations (documented in `run_migrations.sh`: "Use after init + seed") — entrypoint was initially wrong order
- env.template URL variables like `QDRANT_URL=http://${QDRANT_HOST}:${QDRANT_PORT}` do not expand via `xargs` — replaced with literal inter-container values

## Breakages Fixed During Trial Run
1. BuildKit manifest timeout → `DOCKER_BUILDKIT=0` + pre-pull `python:3.12-slim`
2. `src/frontend-angular/node_modules/` (673 MB) streamed into Python build contexts → `src/.dockerignore`
3. Root `.dockerignore` used `node_modules/` not `**/node_modules/` → fixed
4. `compose up` doesn't accept `--build-arg` (Compose v5) → separated `compose build` + `compose up`
5. `000_complete_init.sql` bare `CREATE TYPE model_type_enum/model_provider_enum` → DO/EXCEPTION guards
6. `005_seed_models.sql` missing `provider_type` (NOT NULL) column → added with correct enum values
7. Init SQL ran before seeds (migration 036 needs seeded intent_categories) → swapped to init→seeds→migrations
8. Migration 037 GRANTs to `admin_role` which doesn't exist on fresh DB → DO/EXCEPTION guards
9. Phase 4 intent-defaults exits 1 when no `INTENT_MODEL_*` vars → non-fatal `|| echo`
10. Composed URLs in `.env` (`QDRANT_URL=http://${QDRANT_HOST}:...`) not expanded by `xargs` → literal values

## AIO-42 Notes (e2e RAG)
- ModelSelector not loaded per-request: router created LLMRouter without model_selector; fixed by calling `load_intent_defaults_from_async_db` and passing result to ModelSelector before each request
- Gateway model registry JOIN: `models.provider` must match `gateway_providers.name` exactly (case-sensitive); qwen model needed `provider = 'LMStudio'` and `is_available = true`
- Successful query: qwen3.6-35b-a3b-ud-mlx via LMStudio, 26→665 tokens, 8.5s

## Next Steps
- AIO-43 (new): Pin `torch` CPU-only in `src/embedding/requirements.txt` to eliminate 1.1 GB CUDA bloat
- AIO-44 (new): Consolidate `000_complete_init.sql` + migrations 027-039 into single authoritative init (authorized by Alex 2026-05-31 — app is not in production)
- M2: llm-guard-svc + Angular UI (`--profile full`)
