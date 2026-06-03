# AI Operations Platform - Master Roadmap V2

**Version:** 2.1
**Last Updated:** 2026-06-03
**Purpose:** Single source of truth for current and future development
**Status:** Build Bootstrap M3 next; LLG Hardening AIO-75/76 open

---

## Document History

This roadmap supersedes `MASTER_ROADMAP_V1_PHASES_1-4.md` which covered:

- ✅ Phase 1: Foundation & Security (Complete)
- ✅ Phase 2: Core Interface & Features (Complete)
- ✅ Phase 3: Use Case Management (Complete)
- ✅ Phase 4: Security & Enterprise (Complete)
- ✅ Phase 4.5: Inference Gateway (Complete)
- ✅ Tools Track T1-T6 (Infrastructure Complete)

**Reference:** [MASTER_ROADMAP_V1_PHASES_1-4.md](archive/MASTER_ROADMAP_V1_PHASES_1-4.md)

---

## Overall Progress Dashboard

### Phase Summary

| Track | Name | Status | Linear Project |
|-------|------|--------|----------------|
| 1–4, 4.5, T1–T6 | Foundation → Security → Tools | ✅ Archived | — |
| 5 | Infrastructure Overhaul (async SQLAlchemy, renames) | ✅ Complete (Dec 2025) | — |
| 5.5 | RBAC V2 Fix | 🔄 Phases 1–3 ✅ / Phases 4–5 Backlog | AIO - RBAC V2 Completion |
| 6 | Platform Stabilization | 🔄 STAB-01/02 ✅ / STAB-03/04 + MVP Gate Backlog | AIO - Platform Stabilization |
| Bootstrap | Build System & Bootstrap | 🔄 M1 ✅ M2 ✅ / M3 Active | AIO - Build System & Bootstrap |
| LLG | LLM Guard Hardening (LLG-04) | 🔄 Steps 0–4 ✅ / AIO-75/76 Open | AIO - LLM Guard Hardening |
| QE | Quality Engineering (deferred test failures) | 📋 Backlog | AIO - Quality Engineering |
| DB | Database and Config | 📋 Backlog | AIO - Database and Config |
| 7 | User Documentation | 📋 Backlog | AIO - User Documentation |
| 8+ | Agentic AI / Future | 📋 Backlog | AIO - Agentic AI and Future |

### Current State (June 2026)

| Metric | Value |
|--------|-------|
| **Active tracks** | Build Bootstrap (M3), LLG Hardening (AIO-75/76) |
| **Next milestone** | LLG AIO-75/76 → Dependabot security → Bootstrap M3 |
| **Platform** | Fully builds and runs locally (M1+M2 ✅); llm-guard-svc on native ONNX + Presidio/GLiNER (LLG-04 ✅) |
| **RBAC V2** | Phases 1–3 shipped; Integration testing + cleanup (Phases 4–5) deferred to backlog |
| **Pre-release readiness** | Blocked by Bootstrap M3 (enterprise path) and RBAC V2 Phase 4 (integration testing) |

---

## Active Tracks

### Build System & Bootstrap — [BUILD_BOOTSTRAP_PLAN.md](BUILD_BOOTSTRAP_PLAN.md)

| Milestone | Status | Key tickets |
|-----------|--------|-------------|
| M1 — Local backend-core | ✅ Complete (2026-05-31) | AIO-34–42, AIO-64/65 |
| M2 — Full local stack (llm-guard + UI) | ✅ Complete (2026-06-01) | AIO-43, AIO-46–50 |
| M3 — Enterprise + offline paths | 🔄 Next | AIO-44, AIO-51–57, AIO-67 |
| M4 — Canonical bootstrap docs | 📋 Approved | AIO-45, AIO-58–63 |

### LLM Guard Hardening — LLG-04 complete; two bugs deferred

| Ticket | Title | Status |
|--------|-------|--------|
| AIO-1–4, AIO-69–74 | LLG-04 (parity harness → native ONNX/Presidio/GLiNER → guard client fix) | ✅ Done |
| **AIO-75** | `LLM_GUARD_ENABLED=false` bypass not forwarded to `GuardValidate` | Approved |
| **AIO-76** | Secrets scanner temp file with raw prompt left on disk on exception | Approved |

### Dependabot Security (post-LLG-04)

7 `transformers` alerts in `llm_guard_svc/requirements.txt` should auto-close on Dependabot rescan (pin now `>=4.53.0,<4.54.0`). 7 phantom `uv.lock` alerts need manual triage. Resolve before starting M3.

---

## Open / Backlog Tracks

### RBAC V2 Completion — AIO - RBAC V2 Completion

Phases 1–3 (schema, backend, frontend) shipped Dec 2025. Phases 4–5 deferred.

| Ticket | Title | Status |
|--------|-------|--------|
| AIO-5 | Phase 4: Integration Testing | Backlog |
| AIO-6 | Database Seed Alignment for RBAC V2 | Backlog |
| AIO-7 | Phase 5: Cleanup and Docs | Backlog |

**[→ ADR-060](../adrs/ADR-060-Corrected-RBAC-Architecture.md)** | **[→ Implementation Plan](RBAC_V2_IMPLEMENTATION_PLAN.md)**

### Platform Stabilization — AIO - Platform Stabilization

P6-STAB-01 (UI walkthrough) and P6-STAB-02 (core pipeline validation) completed Nov–Dec 2025.

| Ticket | Title | Status |
|--------|-------|--------|
| AIO-8 | P6-STAB-04: Demo Scripts Suite | Backlog |
| AIO-9 | P6-STAB-03: Elasticsearch MCP Tool | Backlog |
| AIO-10 | MVP Gate Review | Backlog |

### Quality Engineering — AIO - Quality Engineering

Deferred test failures from P2/P3 era. No active work; picked up when stabilization resumes.

| Tickets | Description |
|---------|-------------|
| AIO-17–23 | P2/P3 deferred test failures (MatDialog mocks, Observable mocks, bundle budgets, OnPush, triage) |

### Database and Config — AIO - Database and Config

| Ticket | Title | Status |
|--------|-------|--------|
| AIO-30 | ADR-061 Vault Integration Decision | Backlog |
| AIO-31 | Canonicalize Duplicate ADRs (ADR-052/053) | Backlog |
| AIO-32 | Config Gateway Service Adoption | Backlog |
| AIO-33 | Database Refresh Completion | Backlog |

---

## Future Tracks

### User Documentation — AIO - User Documentation

| Ticket | Title |
|--------|-------|
| AIO-24 | API Documentation Update |
| AIO-25 | Corpus Manager Guide |
| AIO-26 | Developer User Guide |
| AIO-27 | Documentation Cleanup |
| AIO-28 | Admin User Guide |
| AIO-29 | Analyst User Guide |

### Agentic AI and Future — AIO - Agentic AI and Future

| Ticket | Title |
|--------|-------|
| AIO-13 | Multi-Agent Workflow Architecture ADR |
| AIO-14 | Agent Memory and Tool Chaining Design |
| AIO-15 | Autonomous Tasks Design |
| AIO-16 | Enterprise Features Backlog Review |

---

## Deferred Features

Enterprise-scale features deferred; not needed for 5–10 user departmental deployment.

| Feature | Original Phase |
|---------|----------------|
| SOAR/ITSM Integration | P5 |
| Workflow Automation | P5 |
| Enterprise Reporting | P5 |
| i18n | P6 |
| PWA | P6 |
| Advanced Performance Optimization | P6 |

**[→ Enterprise Features Backlog](archive/ENTERPRISE_FEATURES_BACKLOG.md)**

---

## Quick Navigation

| Area | Document |
|------|----------|
| Build Bootstrap plan | [BUILD_BOOTSTRAP_PLAN.md](BUILD_BOOTSTRAP_PLAN.md) |
| RBAC V2 implementation | [RBAC_V2_IMPLEMENTATION_PLAN.md](RBAC_V2_IMPLEMENTATION_PLAN.md) |
| ADR index | [adrs/README.md](../adrs/README.md) |
| Phase 5 detail (archived) | [active/PHASE_05_INFRASTRUCTURE_OVERHAUL.md](active/PHASE_05_INFRASTRUCTURE_OVERHAUL.md) |
| Phase 6 detail | [future/PHASE_06_STABILIZATION.md](future/PHASE_06_STABILIZATION.md) |
| Phase 7 detail | [future/PHASE_07_DOCUMENTATION.md](future/PHASE_07_DOCUMENTATION.md) |
| Phase 8 detail | [future/PHASE_08_AGENTIC_AI.md](future/PHASE_08_AGENTIC_AI.md) |
| Master Roadmap V1 (Phases 1–4) | [archive/MASTER_ROADMAP_V1_PHASES_1-4.md](archive/MASTER_ROADMAP_V1_PHASES_1-4.md) |

---

**Document Owner:** AIOps team
**Last Updated:** 2026-06-03
**Version:** 2.1 — Rewritten from v2.7 (Dec 2025) to reflect June 2026 reality; stale weekly timelines, completed phase detail, and outdated exit criteria removed; all tracks sourced from Linear AIOps project state.
