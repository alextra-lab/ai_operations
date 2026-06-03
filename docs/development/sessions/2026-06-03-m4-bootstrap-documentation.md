# Development Session - 2026-06-03
**Focus:** M4 — Canonical bootstrap documentation (AIO-57 through AIO-62, AIO-78)   **Status:** Complete

## Work Completed

- **AIO-60** (PR #116): Fixed all broken internal doc links across README.md, docs/README.md, Dependency_Management.md, adrs/README.md. Full ADR index reconciliation (58 unique numbers, 12 previously-missing ADRs indexed, two new categories: Inference Gateway & Providers + MCP & Tooling). Beta status callout added.
- **AIO-78** (PR #117): Swept `**Status:** ✅ Production Ready` headers from 14 files across docs/api/, docs/user-guides/, docs/development/guides/ — replaced with `Implemented`. Decision: production status lives in README.md and project versioning, not individual doc headers.
- **AIO-61** (PR #118): New `src/orchestrator/README.md` (pipeline, Step protocol, MCP wiring, routers, env vars) and `src/shared/README.md` (COPY-not-pip mechanism, all modules with exact exported symbols, add-a-module pattern).
- **AIO-62** (PR #119): Rewrote `src/inference-gateway/README.md` — removed "Phase 4.5 - In Development" framing, corrected port, documented all endpoints, rate limiting (per-scope token bucket), circuit breaker (3-state), DB-driven provider management.
- **AIO-59** (PR #120): New `docs/development/guides/bootstrap-troubleshooting.md` — 7 failure modes from M1–M3, each with copy-pasteable symptom, root cause, fix.
- **AIO-57** (PR #121): Rewrote `docs/operations/AIR_GAPPED_DEPLOYMENT.md` — separated enterprise (Artifactory mirrors, network present) from offline (OFFLINE=1 + wheelhouse, Python only). Removed fake env vars and stale paths.
- **AIO-58** (PR #122): New `GETTING_STARTED.md` at repo root — five-step local profile bootstrap (setup → .env → build → models → up), service table, health endpoint verification, troubleshooting pointer.

## Key Decisions

- Enterprise ≠ air-gapped: enterprise uses Artifactory mirrors (network present); offline uses `OFFLINE=1` + wheelhouse. Documented separately per ADR-074.
- "Production Ready" status claims belong only in README.md and project versioning — not in individual feature doc headers.
- ADR-052/053 duplicate files left to AIO-31; only represented accurately in the index.
- Next available ADR number: **ADR-075**.

## Next Steps

- M4 milestone is complete; M5 (Infrastructure Overhaul) is the active phase.
