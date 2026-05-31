# Development Session - 2026-05-31
**Focus:** Pre-M2 cleanup — torch CPU-only pin (AIO-64) + DB init consolidation (AIO-65)   **Status:** Complete

## Work Completed

- **AIO-64** — torch CPU-only pin across all 3 build profiles (commit `f2a113b`)
  - `src/embedding/Dockerfile`: added `TORCH_INDEX_URL` ARG (after apt-get layers to avoid cache busting); non-OFFLINE branch uses pytorch CPU index as primary, PyPI as fallback
  - `ops/bootstrap/up.sh`: added `TORCH_INDEX_URL` build-arg per profile (local = pytorch CPU, enterprise = Artifactory placeholder, train omitted)
  - `ops/bootstrap/build_wheelhouse.sh`: pytorch CPU index as primary in pass-1 so offline wheelhouse carries `+cpu` wheel (~1.1 GB saved)

- **AIO-65** — DB init consolidation (commit `ac5e465`)
  - All 16 migration files 027–039 deleted; `run_migrations.sh` + `migrations/` retained for future use
  - DDL from 036–039 folded into `000_complete_init.sql` (39 tables, up from 37)
  - Data ops from 033_fix / 034_set_documents / 036 data / 037_rename moved to seed files 012–014
  - Migration 033_fix fully redundant — dropped (inserts already in seed/010, UPDATE duplicated seed/006)
  - GRANT statements from 037 deliberately omitted — they reference roles that don't exist; app uses single DB user with RLS
  - Schema equivalence verified via Docker pg_dump diff (old flow vs new flow — structurally identical)
  - Rollback updated; ops/database docs updated (MIGRATION_SUMMARY, README, INDEX)

## Key Decisions

- `TORCH_INDEX_URL` as a build ARG (not hardcoded in requirements.txt) — keeps index selection a build concern, compatible with all 3 profiles
- Index URL ordering: pytorch CPU as `--index-url` (primary), PyPI as `--extra-index-url` — necessary because pip resolves `torch>=2.8.0` from the primary index first
- Data-bearing migrations moved to seeds (not embedded in init) — preserves Phase 2 seed-before-migration ordering that 036 data depends on
- Alembic deferred to AIO-66 (follow-up, blocked by AIO-65) — consolidation is a clean schema baseline for future Alembic revision 0

## Next Steps

- M1 epic branch (`starry-plaza-1s/aio-34-m1-epic-local-backend-core-query-end-to-end`) needs PR before M2 work starts on AIO-43
- AIO-66 (Alembic adoption + schema-ownership ADR) can begin after M1 merge
- M2 work (AIO-43 epic: llm-guard-svc + Angular UI) unblocked
