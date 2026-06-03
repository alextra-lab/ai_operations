# AI Operations Platform - Documentation

**Last Updated:** 2026-06-03
**Total Documents:** 90+ markdown files
**Organization:** Purpose-driven, lifecycle-aware structure

> **Status: Beta — not production-ready.** This platform has not yet been deployed to or validated in a production environment. Intended for local evaluation use at this stage.

---

## 📚 Documentation Philosophy

This documentation is organized by **purpose and lifecycle**:

1. **Development Docs** (`development/`) - Everything needed to BUILD the app
2. **Product Docs** (other folders) - Everything needed to USE/OPERATE the app

### Core Principle

> **Folder organization by purpose, original filenames preserved for reference integrity**

---

## 🗂️ Folder Structure

### `docs/development/` - THE WORKSHOP 🔨

**All documentation for building the application**

```
development/
├── plans/          # Implementation plans & roadmaps
│   ├── MASTER_ROADMAP_V2.md                 # ⭐ Single source of truth
│   ├── README.md                             # Navigation guide
│   │
│   ├── active/                               # Current work
│   │   └── PHASE_05_INFRASTRUCTURE_OVERHAUL.md  # Phase 5 (in progress)
│   │
│   ├── completed/                            # Finished phases
│   │   ├── PHASE_01_FOUNDATION.md            # Phase 1 (100%)
│   │   ├── PHASE_02_CORE_INTERFACE.md        # Phase 2 (100%)
│   │   ├── PHASE_03_USE_CASE_MGMT.md         # Phase 3 (100%)
│   │   └── PHASE_04_SECURITY_ENTERPRISE.md   # Phase 4 (100%)
│   │
│   ├── future/                               # Upcoming phases
│   │   ├── PHASE_06_STABILIZATION.md         # Phase 6
│   │   ├── PHASE_07_DOCUMENTATION.md         # Phase 7
│   │   └── PHASE_08_AGENTIC_AI.md            # Phase 8
│   │
│   ├── features/                             # Feature specifications
│   │   ├── active/
│   │   └── completed/
│   │       # (Features documented in phase files)
│   │
│   ├── archive/                              # Obsolete plans
│   │   ├── UI_DEVELOPMENT_PLAN_ORIGINAL_2025-10-19.md
│   │   ├── DYNAMIC_INTENT_IMPLEMENTATION_ROADMAP.md
│   │   ├── P2_IMPLEMENTATION_ORDER.md
│   │   └── PHASE_2.6_UX_REFINEMENTS.md
│   │
│   └── [Specialized Plans]
│       ├── IMPLEMENTATION_ROADMAP.md
│       ├── BACKEND_ASYNC_MIGRATION_PLAN.md
│       ├── PERFORMANCE_OPTIMIZATION_ROADMAP.md
│       ├── TOOLS_IMPLEMENTATION_PLAN*.md (4 files)
│       └── BUILD_BOOTSTRAP_PLAN.md          # ⭐ Build system & reproducible bootstrap (M1-M4)
│
├── tasks/          # Active work items (10 files)
│
├── adrs/           # Architecture Decision Records (ADR-001 through ADR-074 + template)
│   ├── README.md                                    # ADR Index
│   ├── template.md                                  # ADR Template
│   ├── ADR-001 through ADR-074                     # All ADRs
│   └── ADR-074 (Latest/Proposed): Multi-Profile Build & Bootstrap  # ⭐ Most Recent
│
├── specs/          # Feature specifications (1 file)
│
├── guides/         # Developer how-to documentation (5 files)
│
├── guidelines/     # Development patterns (8 files)
│   └── DOCUMENT_ORGANIZATION_GUIDE.md (moved from root)
│
├── analysis/       # Technical investigations (9 files)
│
├── sessions/       # Daily summaries (27 files)
│
├── templates/      # Document templates (2 files)
│
└── completed/      # Finished work (24 files)
    ├── tasks/      # Completed task implementations
    └── reports/    # Verification reports
```

### Product Documentation (Root `docs/` Folders)

**Documentation for using and operating the application**

```
docs/
├── api/                # API contracts & endpoints
│   ├── authentication.md     # Auth API reference
│   └── documents.md          # Document management API
├── architecture/       # System design & architecture
├── deployment/        # Deployment checklists & guides
├── operations/         # Operations & air-gapped deployment
├── testing/            # Testing procedures & guides
├── archive/            # Historical/superseded documentation
│
└── README.md           # This file - navigation guide

```

---

## 📖 Document Types Explained

### Industry-Standard Types

| Type | Purpose | Location |
|------|---------|----------|
| **Plan** | Implementation roadmap with phases/features | `development/plans/` |
| **ADR** | Architecture Decision Record (why we chose X) | `development/adrs/` |
| **Spec** | Requirements & clarifications | `development/specs/` |
| **Guide** | Step-by-step how-to instructions | `development/guides/` |
| **Guideline** | General patterns & best practices | `development/guidelines/` |
| **Analysis** | Technical investigation & findings | `development/analysis/` |
| **Task** | Specific work item (P2_FIX_XX) | `development/tasks/` or `completed/tasks/` |
| **Session** | Daily work summary | `development/sessions/` |
| **Template** | Reusable document pattern | `development/templates/` |

### ADR (Architecture Decision Record) Format

ADRs follow the industry-standard format popularized by Michael Nygard:

```markdown
# ADR-XXX: Decision Title

**Status:** Proposed | Accepted | Deprecated
**Date:** YYYY-MM-DD
**Deciders:** Team/Role

## Context
What is the issue we're addressing?

## Decision
What did we decide?

## Consequences
**Positive:**
- Benefits

**Negative:**
- Tradeoffs

## References
- Links to related docs
```

See `development/adrs/template.md` for complete format.

---

## 🔍 Finding Documents

### For Developers Building Features

**Start Here:**

1. `PROJECT_OVERVIEW.md` - Executive summary and project status (designated overview at docs root)
2. `development/plans/MASTER_ROADMAP_V2.md` - Single source of truth
3. `development/plans/active/` - Current work (see plans README for latest phase)
4. `development/tasks/` - Active work items
5. `development/guides/` - Implementation patterns
6. `development/adrs/` - Architecture decisions
7. `architecture/` - System architecture details

### For Understanding the Application

**Start Here:**

1. `../README.md` (project root) - Project overview
2. `api/` - API contracts
3. `architecture/` - System design
4. `deployment/` and `operations/` - Setup and deployment guides
5. `testing/` - QA procedure

### For AI Assistant Context

**Always include:**

- `development/plans/` - Implementation roadmaps
- `development/specs/` - Requirements
- `development/adrs/` - Architectural decisions

**Include when relevant:**

- `development/guides/` - Implementation patterns
- `development/analysis/` - Technical investigations
- `development/tasks/` - Active work items
- `api/` and `architecture/` - System contracts

**Exclude to reduce noise:**

- `development/sessions/` - Historical daily logs
- `development/completed/` - Already implemented
- `archive/` - Superseded information

---

## 📝 Document Lifecycle

### Creation → Completion Flow

```
1. INVESTIGATION
   Problem discovered → development/analysis/[name].md

2. DECISION
   Architecture choice → development/adrs/NNN-title.md

3. SPECIFICATION
   Requirements defined → development/specs/[name].md

4. PLANNING
   Implementation planned → development/plans/[TRACK]_PLAN.md

5. TASK CREATION
   Work item created → development/tasks/P2_FIX_XX.md

6. IMPLEMENTATION
   (Code changes, tests, verification)
   Daily log → development/sessions/YYYY-MM-DD.md

7. COMPLETION
   Move task → development/completed/tasks/P2_FIX_XX.md

8. EXTRACTION
   Extract insights → api/, architecture/, configuration/
   (For user-facing documentation)
```

---

## ✅ Quality Standards

### File Organization Rules

1. **Preserve original filenames**- Maintains reference integrity
2. **Organize by purpose** - Folder indicates document type
3. **Use industry terms** - ADRs, specs, plans (not "findings")

4. **Lifecycle management** - Active → Completed → Extracted → Archived

### Status Indicators in Documents

Use these in document headers:

- `Status: ✅ COMPLETED (YYYY-MM-DD)`
- `Status: 🔄 IN PROGRESS`
- `Status: ⏳ PENDING`
- `Status: ❌ BLOCKED`
- `Status: 📋 PLANNED`

---

## 🎯 Maintenance Guidelines

### When to Create New Documents

| Situation | Document Type | Location |
|-----------|--------------|----------|
| Make architecture decision | ADR | `development/adrs/NNN-title.md` |
| Plan new feature | Task  `development/tasks/P2_FIX_XX.md` |
| Daily work summary | Session | `development/sessions/SESSION_SUMMARY_YYYY_MM_DD.md` |
| Investigate issue | Analysis | `development/analysis/[description].md` |
| Define requirements | Spec | `development/specs/[name].md` |
| Create how-to | Guide | `development/guides/[name].md` |

### When to Move Documents

- Task completed → `development/completed/tasks/`
- Analysis resolved → `development/completed/analysis/` (if needed)
- Document superseded → `archive/`
- Insights extracted → Update product docs (`api/`, `architecture/`, etc.)

---

## 🔗 Related Documentation

- `development/guidelines/DOCUMENTATION_GUIDELINES.md` - Documentation system guidelines

---

## 📞 Quick Reference

**Question** | **Go To**
-------------|----------
"What's the project status?" | `PROJECT_OVERVIEW.md`
"What's being built now?" | `development/plans/MASTER_ROADMAP_V2.md`
"What's the current work?" | `development/plans/active/PHASE_05_INFRASTRUCTURE_OVERHAUL.md`
"How do I implement X?" | `development/guides/`
"Why did we choose Y?" | `development/adrs/`
"What are the requirements?" | `development/specs/`
"What's the API for X?" | `api/`
"How is the system designed?" | `architecture/`
"What tasks are pending?" | `development/tasks/`
"What was completed?" | `development/completed/`

---

**For AI Assistants:** When implementing features, include `@development/plans/`, `@development/adrs/`, `@development/specs/`, and `@development/guides/` in context. Original filenames preserved for reference integrity.
