# Development Plans - Navigation Guide

**Last Updated:** November 26, 2025
**Status:** Cleaned and restructured

---

## Quick Start

| What You Need | Go To |
|---------------|-------|
| **Current work** | [MASTER_ROADMAP_V2.md](MASTER_ROADMAP_V2.md) |
| **Phase 5 details** | [active/PHASE_05_INFRASTRUCTURE_OVERHAUL.md](active/PHASE_05_INFRASTRUCTURE_OVERHAUL.md) |
| **Completed work history** | [archive/MASTER_ROADMAP_V1_PHASES_1-4.md](archive/MASTER_ROADMAP_V1_PHASES_1-4.md) |

---

## Current Structure

### Active Roadmap

📘 **[MASTER_ROADMAP_V2.md](MASTER_ROADMAP_V2.md)** - Single source of truth

| Phase | Name | Status | Link |
|-------|------|--------|------|
| **5** | Infrastructure Overhaul | 🔄 Active | [active/PHASE_05_INFRASTRUCTURE_OVERHAUL.md](active/PHASE_05_INFRASTRUCTURE_OVERHAUL.md) |
| 6 | Stabilization & Validation | 📋 Next | [future/PHASE_06_STABILIZATION.md](future/PHASE_06_STABILIZATION.md) |
| 7 | Documentation Overhaul | 📋 Future | [future/PHASE_07_DOCUMENTATION.md](future/PHASE_07_DOCUMENTATION.md) |
| 8+ | Agentic AI | 📋 Backlog | [future/PHASE_08_AGENTIC_AI.md](future/PHASE_08_AGENTIC_AI.md) |

### Completed Phases

| Phase | Name | Link |
|-------|------|------|
| 1 | Foundation & Security | [completed/PHASE_01_FOUNDATION.md](completed/PHASE_01_FOUNDATION.md) |
| 2 | Core Interface | [completed/PHASE_02_CORE_INTERFACE.md](completed/PHASE_02_CORE_INTERFACE.md) |
| 3 | Use Case Management | [completed/PHASE_03_USE_CASE_MGMT.md](completed/PHASE_03_USE_CASE_MGMT.md) |
| 4 | Security & Enterprise | [completed/PHASE_04_SECURITY_ENTERPRISE.md](completed/PHASE_04_SECURITY_ENTERPRISE.md) |

### Archives

| Document | Content |
|----------|---------|
| [MASTER_ROADMAP_V1_PHASES_1-4.md](archive/MASTER_ROADMAP_V1_PHASES_1-4.md) | Full roadmap through Phase 4.5 + Tools T1-T6 |
| [ENTERPRISE_FEATURES_BACKLOG.md](archive/ENTERPRISE_FEATURES_BACKLOG.md) | Deferred enterprise features |

---

## Directory Structure

```
docs/development/plans/
├── MASTER_ROADMAP_V2.md          # 📘 ACTIVE ROADMAP
├── README_PLANS.md               # This file
├── README.md                     # General plans readme
│
├── active/                       # Current phase (one file only)
│   └── PHASE_05_INFRASTRUCTURE_OVERHAUL.md
│
├── future/                       # Upcoming phases
│   ├── PHASE_06_STABILIZATION.md
│   ├── PHASE_07_DOCUMENTATION.md
│   └── PHASE_08_AGENTIC_AI.md
│
├── completed/                    # Phase completion reports
│   ├── PHASE_01_FOUNDATION.md
│   ├── PHASE_02_CORE_INTERFACE.md
│   ├── PHASE_03_USE_CASE_MGMT.md
│   ├── PHASE_04_SECURITY_ENTERPRISE.md
│   └── P4-MULTI-COLLECTION-RAG-SEARCH.md
│
├── archive/                      # Historical/superseded (25 files)
│   ├── MASTER_ROADMAP_V1_PHASES_1-4.md
│   ├── ENTERPRISE_FEATURES_BACKLOG.md
│   ├── [Tools implementation plans]
│   ├── [Old phase plans]
│   └── [Historical documents]
│
└── features/                     # Feature specifications
    ├── active/                   # (empty)
    └── completed/
        ├── P3-F2_USE_CASE_MANAGEMENT_SPEC.md
        ├── P3-F5_OUTPUT_FORMATTING_ENGINE_SPEC.md
        └── P3-F6_USE_CASE_VALIDATION_TESTING_SPEC.md
```

---

## Archive Contents (25 files)

Historical documents preserved for reference:

| Category | Files |
|----------|-------|
| **Master Roadmap V1** | `MASTER_ROADMAP_V1_PHASES_1-4.md` |
| **Enterprise Backlog** | `ENTERPRISE_FEATURES_BACKLOG.md` |
| **Tools Track** | 6 files (implementation plans, guides) |
| **Infrastructure Plans** | `BACKEND_ASYNC_MIGRATION_PLAN.md`, `PHASE_07_INFRASTRUCTURE_REFACTOR.md` |
| **Completed Initiatives** | Inference Gateway, Stateless Core, Config Centralization |
| **Old Phase Plans** | P5 Integration, P6 Performance, P7 Async (superseded) |
| **Historical Plans** | UI Development, Implementation Roadmap, etc. |

---

## Path References Note

⚠️ **Important:** Many archived documents contain references to `src/orchestrator` and `src/corpus_svc`.

These paths will be renamed during Phase 5:
- `src/orchestrator` → `src/orchestrator`
- `src/corpus_svc` → `src/corpus_svc`

**Active documents will be updated during the Phase 5 rename.**
**Archived documents will NOT be updated** (they reflect historical state).

---

## Maintenance

### When working on current phase:
1. Update `active/PHASE_05_INFRASTRUCTURE_OVERHAUL.md`
2. Update `MASTER_ROADMAP_V2.md` status

### When completing a phase:
1. Move from `active/` to `completed/`
2. Move next phase from `future/` to `active/`
3. Update `MASTER_ROADMAP_V2.md`

### Commit messages:
```
docs: Update PHASE_05 progress - [milestone]
docs: Complete Phase 5, start Phase 6
docs: Archive [document] - [reason]
```

---

## Status Legend

| Symbol | Meaning |
|--------|---------|
| 🔄 | Active - Current work |
| 📋 | Planned - Future work |
| ✅ | Complete |

---

**Document Owner:** Project team
**Last Updated:** November 26, 2025
