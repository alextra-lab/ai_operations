# AI Operations Platform - Master Roadmap V2

**Version:** 2.0
**Date:** December 8, 2025
**Status:** CRITICAL FIX - RBAC V2 Architecture
**Purpose:** Single source of truth for current and future development

---

## Document History

This roadmap supersedes `MASTER_ROADMAP_V1_PHASES_1-4.md` which covered:

- ✅ Phase 1: Foundation & Security (Complete)
- ✅ Phase 2: Core Interface & Features (Complete)
- ✅ Phase 3: Use Case Management (Complete)
- ✅ Phase 4: Security & Enterprise (Complete - 95%)
- ✅ Phase 4.5: Inference Gateway (Complete)
- ✅ Tools Track T1-T6 (Infrastructure Complete)

**Reference:** [MASTER_ROADMAP_V1_PHASES_1-4.md](archive/MASTER_ROADMAP_V1_PHASES_1-4.md)

---

## Strategic Context

### Current State (November 2025)

| Metric | Value |
|--------|-------|
| **Application Status** | Feature-complete for pre-release |
| **Target Users** | 5-10 (single department, multiple teams) |
| **Infrastructure** | Needs final refactoring before production |
| **MCP Tools** | Framework complete, no tools connected |
| **Documentation** | Development-focused, needs user guides |

### Strategic Pivot

**FROM:** Building new infrastructure features
**TO:** Stabilization, validation, user documentation

**Key Decisions:**

1. Application is feature-rich enough for pre-release
2. No new features until core is validated
3. Service renaming + async migration before demos
4. User guides take priority over developer docs
5. First real MCP tool (Elasticsearch) after infrastructure

---

## Overall Progress Dashboard

### Project Status

| Metric | Value |
|--------|-------|
| **Current Phase** | Phase 5.5: RBAC V2 Fix (IN PROGRESS) |
| **Overall Completion** | 87% (Phase 1 ✅, Phase 2 ✅, Phase 3 ✅, Database Refresh partial ✅) |
| **Phases 1-4 + Tools** | 100% Complete (archived) |
| **Pre-Release Target** | Q1 2026 (AT RISK) |

### Phase Summary

| Phase | Name | Status | Duration | Timeline |
|-------|------|--------|----------|----------|
| 1-4 | Foundation through Security | ✅ Archive | - | Sep-Nov 2025 |
| 4.5 | Inference Gateway | ✅ Archive | - | Nov 2025 |
| T1-T6 | Tools Track | ✅ Archive | - | Nov 2025 |
| 5 | Infrastructure Overhaul | ✅ Complete | 4-5 weeks | Nov 2025 |
| **5.5** | **RBAC V2 Fix** | 🔄 **IN PROGRESS (Phase 1 ✅, Phase 2 ✅, Phase 3 ✅)** | 7 weeks | Dec 2025 - Jan 2026 |
| 6 | Stabilization & Validation | ⏸️ Blocked | 2-3 weeks | Post-RBAC |
| 7 | Documentation Overhaul | 📋 Future | 1-2 weeks | Feb 2026 |
| 8+ | Agentic AI / Future | 📋 Backlog | TBD | Q2 2026+ |

---

## Quick Navigation

### Active Development

- **[Phase 6: Stabilization & Validation](future/PHASE_06_STABILIZATION.md)** - Current work (25% - P6-STAB-01 ✅)

### Completed Phases

- **[Phase 5: Infrastructure Overhaul](active/PHASE_05_INFRASTRUCTURE_OVERHAUL.md)** - ✅ Complete

### Future Phases

- **[Phase 7: Documentation Overhaul](future/PHASE_07_DOCUMENTATION.md)** - User guides, cleanup
- **[Phase 8: Agentic AI](future/PHASE_08_AGENTIC_AI.md)** - Future features backlog

### Archives

- **[Master Roadmap V1 (Phases 1-4)](archive/MASTER_ROADMAP_V1_PHASES_1-4.md)** - Completed work
- **[Enterprise Features Backlog](archive/ENTERPRISE_FEATURES_BACKLOG.md)** - Deferred features

---

## Phase 5: Infrastructure Overhaul (Active)

**Timeline:** December 2025 - January 2026 (4-5 weeks)
**Status:** ✅ Complete (Week 6 - P5-A22 ✅ Complete)
**Goal:** Clean, modern infrastructure foundation before demos and documentation

### Scope

**Part 1: Service Rename (Week 1)**

| Current | New | Rationale |
|---------|-----|-----------|
| `src/orchestrator` | `src/orchestrator` | Describes LLM pipeline orchestration role |
| `src/corpus_svc` | `src/corpus_svc` | Describes document/corpus management role |
| `src/frontend-angular` | Keep as-is | User preference |

**Part 2: Async SQLAlchemy Migration (Weeks 2-5)**

- Modern async/await patterns throughout
- Non-blocking database operations
- Better concurrency handling
- Future-proof architecture

### Why Now

1. **Measure twice, cut once** - Get foundation right before building demos
2. All artifacts (demos, docs, scripts) will reference correct paths
3. No rework needed after demo creation
4. Async migration touches same files - do together

### Key Milestones

| Week | Milestone | Tasks | Status |
|------|-----------|-------|--------|
| 1 | Rename Complete | Directories, imports, Docker, docs | ✅ Nov 26 |
| 2 | Database Infra | Async engine, fixtures, shared utilities, pool config | ✅ Nov 26 |
| **2.5** | **Security Fix** | **P5-SEC-01: Stateless PII Enforcement** | ✅ Nov 28 |
| 3 | Orchestrator Async | 14 routers converted | ✅ Nov 28 |
| 4 | Corpus + Gateway Async | P5-A14 ✅, P5-A15 ✅, P5-A16 ✅ | ✅ Nov 29 |
| 5 | Sync Pattern Removal | [P5-A23](../completed/tasks/P5_A23_REMOVE_SYNC_DATABASE_PATTERNS.md) | ✅ Nov 29 |
| 6 | Tests + Validation | P5-A17 ✅, P5-A18 ✅, P5-A19 ✅, P5-A20 ✅, P5-A21 ✅, P5-A22 ✅ | ✅ Dec 1 |

### ✅ Security Task Complete: P5-SEC-01

**Completed:** November 28, 2025
**Priority:** Critical (Security)
**Actual Effort:** 3 hours

ADR-030 violation fixed: frontend can no longer bypass stateless architecture.

**Implementation:**

- ✅ Added `ENABLE_TRANSCRIPT_STORAGE` feature flag (default: `false`)
- ✅ Guarded 7 write endpoints with 501 Not Implemented
- ✅ Removed direct history calls from frontend
- ✅ ADR-030 enforcement mechanism documented
- ✅ 26 tests (11 backend + 15 frontend)

**Task Document:** [P5-SEC-01](completed/tasks/P5_SEC_01_STATELESS_PII_ENFORCEMENT.md)

**[→ See Complete Phase 5 Details](active/PHASE_05_INFRASTRUCTURE_OVERHAUL.md)**

---

## Phase 5.5: RBAC V2 Architecture Fix (CRITICAL)

**Timeline:** December 8, 2025 - January 26, 2026 (7 weeks)
**Status:** 🔄 **IN PROGRESS - Phase 1 ✅, Phase 2 ✅, Phase 3 ✅, Database Refresh (partial) ✅ (Dec 11, 2025)**
**Priority:** SHOW STOPPING - Blocks production use
**Goal:** Fix broken RBAC system with two-tier architecture + team isolation

### Problem

Current RBAC implementation is fundamentally broken:

- Role Management UI shows wrong roles (`analyst`, `developer` don't exist)
- Missing actual system roles (`use_case_publisher`, `conversations_privileged`)
- Single role per user (should be multi-role)
- No team isolation for dev teams
- No document collection access control

### Solution

**ADR-060:** Two-tier RBAC with team-based development

- **Tier 1:** System roles (capabilities) - `admin`, `corpus_admin`, `use_case_admin`, `tools_admin`, `conversations`, `role_admin`
- **Tier 2:** Grouping roles (resource access) - `threat_hunting`, `incident_response`, etc.
- **Tier 3:** Developer teams - `team:csirt_security`, `team:soc_governance`

### Deliverables

✅ **ADR-060:** Corrected RBAC Architecture (70 pages) - **COMPLETE**
✅ **Implementation Plan:** RBAC_V2_IMPLEMENTATION_PLAN.md (50 pages) - **COMPLETE**
✅ **Phase 1:** Database schema (5 days) - **COMPLETE (Dec 2025)**
✅ **Phase 2:** Backend implementation (10 days) - **COMPLETE (Dec 8, 2025)**
✅ **Phase 3:** Frontend implementation (10 days) - **COMPLETE (Dec 9, 2025)** - All tasks (3.1, 3.2, 3.3, 3.4, 3.5, 3.6) ✅
📋 **Phase 4:** Testing & deployment (5 days) - NOT STARTED
📋 **Phase 5:** Cleanup & documentation (5 days) - NOT STARTED

### Key Milestones

| Week | Milestone | Status |
|------|-----------|--------|
| 1 | Database migrations + team_id column | ✅ Complete (Dec 2025) |
| 2-3 | Backend RBAC V2 service + APIs | ✅ Complete (Service + Models + APIs + Unit Tests + Use Case Mgmt + API Docs ✅) |
| 4-5 | Frontend role management UI | ✅ Complete (Models ✅, Grouping Roles UI ✅, Developer Teams UI ✅, User Mgmt ✅, Use Case Manager ✅, Navigation ✅) |
| 6 | Integration testing + production deploy | 📋 Not started |
| 7 | Cleanup deprecated code + docs | 📋 Not started |

**[→ See ADR-060](../adrs/ADR-060-Corrected-RBAC-Architecture.md)**
**[→ See Implementation Plan](RBAC_V2_IMPLEMENTATION_PLAN.md)**

---

## Phase 6: Stabilization & Validation (Blocked)

**Timeline:** Post-RBAC V2 (2-3 weeks)
**Status:** ⏸️ **BLOCKED by RBAC V2 Fix**
**Goal:** Prove the application works end-to-end

### Scope

**P6-STAB-01: UI Walkthrough Assessment** ✅ **COMPLETE (Nov 30, 2025)**

- ✅ Page-by-page verification (API + browser)
- ✅ 2 critical database issues fixed (migration 002)
- ✅ 1 feature deferred (chunking presets → backlog)
- ✅ All pages loading without errors

**P6-STAB-02: Core Pipeline Validation** ✅ **COMPLETE (Nov 30, 2025 + Dec 9, 2025)**

- ✅ Document ingestion end-to-end (embedding service bug fixed)
- ✅ RAG Q&A with real corpus (RAG collection bugs fixed - P2-FIX-12)
- ✅ Use case execution demos (RAG collection bugs fixed - P2-FIX-12)
- ✅ Multi-turn conversation tests (client-side per ADR-030)
- ✅ **P2-FIX-12:** RAG Collection Configuration Bug Fix (Dec 9, 2025)

**P6-STAB-03: First Real MCP Tool - Elasticsearch**

- Deploy ES with security demo data
- Configure MCP tool connection
- Create "Security Log Query" use case
- Demo: Analyst queries logs via LLM

**P6-STAB-04: Demo Scripts Suite**

- CLI scripts for each capability
- Reproducible stakeholder demos
- Video-recordable walkthroughs

**[→ See Complete Phase 6 Details](future/PHASE_06_STABILIZATION.md)**

---

## Phase 7: Documentation Overhaul (Future)

**Timeline:** February 2026 (1-2 weeks)
**Status:** 📋 Planned
**Goal:** User-ready documentation

### Scope

**P7-DOC-01: User Guides (Priority)**

| Guide | Audience |
|-------|----------|
| Analyst Guide | SOC Analysts using the app |
| Admin Guide | System administrators |
| Developer Guide | Use case creators |
| Corpus Manager Guide | Document librarians |

**P7-DOC-02: Documentation Cleanup**

- Archive obsolete development docs
- Consolidate overlapping plans
- Update all README files

**P7-DOC-03: API Documentation**

- Update OpenAPI specs
- Add request/response examples

**[→ See Complete Phase 7 Details](future/PHASE_07_DOCUMENTATION.md)**

---

## Phase 8+: Agentic AI (Future Backlog)

**Timeline:** Q2 2026+
**Status:** 📋 Backlog
**Goal:** Next-generation AI capabilities

### Planned Features

| Feature | Description |
|---------|-------------|
| Multi-Agent Workflows | Multiple AI agents collaborating |
| Autonomous Tasks | AI-initiated actions with approval gates |
| Agent Memory | Persistent learning across sessions |
| Tool Chaining | Automatic tool sequencing |
| Complex Reasoning | Multi-step reasoning with backtracking |

**[→ See Complete Phase 8 Details](future/PHASE_08_AGENTIC_AI.md)**

---

## Deferred Features

Enterprise-scale features deferred to backlog:

| Feature | Original Phase | Status |
|---------|----------------|--------|
| SOAR/ITSM Integration | P5 | Backlog |
| Workflow Automation | P5 | Backlog |
| Enterprise Reporting | P5 | Backlog |
| i18n | P6 | Backlog |
| PWA | P6 | Backlog |
| Advanced Performance Opt | P6 | Backlog |

**Rationale:** Not needed for 5-10 user departmental deployment.

**[→ See Enterprise Features Backlog](archive/ENTERPRISE_FEATURES_BACKLOG.md)**

---

## Timeline Overview

### Q4 2025 (December)

| Week | Milestone |
|------|-----------|
| Dec 2-6 | Phase 5 Week 1: Service Rename |
| Dec 9-13 | Phase 5 Week 2: Database Infrastructure |
| Dec 16-20 | Phase 5 Week 3: Orchestrator Async |
| Dec 23-27 | Holiday buffer |

### Q1 2026 (January - February)

| Week | Milestone |
|------|-----------|
| Jan 6-10 | Phase 5 Week 5: Sync Pattern Removal (P5-A23) |
| Jan 13-17 | Phase 5 Week 6: Tests + Validation |
| Jan 20-31 | Phase 6: Stabilization & Validation |
| Feb 1-14 | Phase 7: Documentation Overhaul |
| **Feb 15** | **🎯 MVP Ready for Department Use** |

### Q2 2026+

- Phase 8: Agentic AI features
- Enterprise features as needed

---

## Success Criteria

### Phase 5 Exit Criteria

- [ ] All services renamed and working
- [ ] 100% async database operations
- [ ] All tests passing (85+ files migrated)
- [ ] Performance validated (no regression)
- [ ] Docker builds successful

### Phase 6 Exit Criteria

- [ ] UI walkthrough complete (all pages, all roles)
- [ ] Core pipelines validated with demos
- [ ] First MCP tool (Elasticsearch) working
- [ ] Demo scripts reproducible

### Phase 7 Exit Criteria

- [ ] 4 user guides published
- [ ] Documentation cleaned up
- [ ] API docs updated

### MVP Ready Criteria

- [ ] Application stable for 5-10 users
- [ ] User guides available
- [ ] At least one MCP tool working
- [ ] Demo-ready for stakeholders

---

## Risk Management

| Risk | Impact | Mitigation |
|------|--------|------------|
| Async migration complexity | Medium | Staged rollout, comprehensive testing |
| Elasticsearch setup issues | Low | Use official Docker image, demo data |
| Documentation scope creep | Low | Focus on 4 core user guides only |

---

## Document Maintenance

**Update Frequency:** Weekly during active development
**Next Review:** End of Phase 5 (mid-January 2026)

**Change Process:**

1. Update this document
2. Update active phase plan
3. Commit with message: `docs: Update MASTER_ROADMAP_V2 - [what changed]`

---

**Document Owner:** Project team
**Last Updated:** December 9, 2025
**Status:** Active v2.7 - Phase 5.5 RBAC V2 Phase 3 ✅ Complete (All tasks 3.1-3.6 ✅)
