# Development Plans - Navigation Guide

**Purpose:** Organized development plans, roadmaps, and feature specifications
**Updated:** February 3, 2026

---

## Quick Navigation

### **For Project Status**

- **[Project Overview](../../PROJECT_OVERVIEW.md)** - Executive summary and system overview
- **[Master Roadmap](MASTER_ROADMAP_V2.md)** - Single source of truth for project progress

### **For Current Work**

- **[Phase 5: Infrastructure Overhaul](active/PHASE_05_INFRASTRUCTURE_OVERHAUL.md)** - Active development
- **[P3-F6 Use Case Validation Spec](features/completed/P3-F6_USE_CASE_VALIDATION_TESTING_SPEC.md)** - Feature spec

### **For Historical Context**

- **[Phase 1: Foundation](completed/PHASE_01_FOUNDATION.md)** - Angular setup, auth, security (100%)
- **[Phase 2: Core Interface](completed/PHASE_02_CORE_INTERFACE.md)** - Query, documents, conversations (100%)
- **[Phase 3: Use Case Management](completed/PHASE_03_USE_CASE_MGMT.md)** - Use case wizard, pattern library (100%)
- **[Phase 4: Security & Enterprise](completed/PHASE_04_SECURITY_ENTERPRISE.md)** - Security & enterprise (100%)

### **For Future Planning**

- **[Phase 6: Stabilization](future/PHASE_06_STABILIZATION.md)** - Stabilization
- **[Phase 7: Documentation](future/PHASE_07_DOCUMENTATION.md)** - Documentation
- **[Phase 8: Agentic AI](future/PHASE_08_AGENTIC_AI.md)** - Agentic AI

---

## Folder Organization

### **active/**

Plans for features currently in development.

- `PHASE_05_INFRASTRUCTURE_OVERHAUL.md` - Phase 5 active work

### **completed/**

Plans for finished phases (archived for reference).

- `PHASE_01_FOUNDATION.md` - Phase 1 complete (100%)
- `PHASE_02_CORE_INTERFACE.md` - Phase 2 complete (100%)
- `PHASE_03_USE_CASE_MGMT.md` - Phase 3 complete (100%)
- `PHASE_04_SECURITY_ENTERPRISE.md` - Phase 4 complete (100%)

### **future/**

Plans for upcoming phases (not yet started).

- `PHASE_06_STABILIZATION.md` - Phase 6
- `PHASE_07_DOCUMENTATION.md` - Phase 7
- `PHASE_08_AGENTIC_AI.md` - Phase 8

### **features/**

Detailed feature specifications and implementation guides.

**active/:** (none currently)

**completed/:**

- `P3-F2_USE_CASE_MANAGEMENT_SPEC.md` - Use Case CRUD, wizard, pattern library
- `P3-F5_OUTPUT_FORMATTING_ENGINE_SPEC.md` - Output formatting with visualizations (Oct 21, 2025)
- `P3-F6_USE_CASE_VALIDATION_TESTING_SPEC.md` - Use case validation testing

### **archive/**

Obsolete or superseded plans (kept for historical reference).

- `UI_DEVELOPMENT_PLAN_ORIGINAL_2025-10-19.md` - Original monolithic plan (backup)
- `DYNAMIC_INTENT_IMPLEMENTATION_ROADMAP.md` - Duplicate of implementation roadmap
- `P2_IMPLEMENTATION_ORDER.md` - Phase 2 complete
- `PHASE_2.6_UX_REFINEMENTS.md` - Phase 2 enhancements complete

---

## Specialized Plans

### **Implementation Plans**

- **[IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md)** - High-level project roadmap
- **[OPTIMAL_IMPLEMENTATION_SEQUENCE.md](OPTIMAL_IMPLEMENTATION_SEQUENCE.md)** - Backend implementation dependencies

### **Backend Plans**

- **[BACKEND_ASYNC_MIGRATION_PLAN.md](BACKEND_ASYNC_MIGRATION_PLAN.md)** - Phase 7 async migration details

### **Performance Plans**

- **[PERFORMANCE_OPTIMIZATION_ROADMAP.md](PERFORMANCE_OPTIMIZATION_ROADMAP.md)** - Phase 6 performance details

### **Tools Track Plans**

- **[TOOLS_IMPLEMENTATION_PLAN.md](TOOLS_IMPLEMENTATION_PLAN.md)** - T1: Tool registration & discovery
- **[TOOLS_IMPLEMENTATION_PLAN_PART2.md](TOOLS_IMPLEMENTATION_PLAN_PART2.md)** - T2: MCP integration
- **[TOOLS_IMPLEMENTATION_PLAN_PART3.md](TOOLS_IMPLEMENTATION_PLAN_PART3.md)** - T3: Testing & validation
- **[TOOLS_IMPLEMENTATION_GUIDE.md](TOOLS_IMPLEMENTATION_GUIDE.md)** - T4: Security & permissions

---

## Document Types

### **Phase Files**

High-level phase overview with feature summaries, progress tracking, and links to detailed specs.

**Format:** `PHASE_0X_NAME.md`
**Location:** `active/`, `completed/`, or `future/`
**Length:** 10-15 pages
**Audience:** Tech leads, project managers

### **Feature Specs**

Detailed implementation guides for specific features with code examples, API contracts, and acceptance criteria.

**Format:** `PX-FY_FEATURE_NAME_SPEC.md`
**Location:** `features/active/` or `features/completed/`
**Length:** Variable (5-50 pages)
**Audience:** Implementing engineers

### **Roadmaps**

Strategic planning documents showing overall project direction, dependencies, and timelines.

**Format:** `*_ROADMAP.md`
**Location:** Root of `plans/`
**Length:** 10-20 pages
**Audience:** Executives, stakeholders

---

## Finding What You Need

### **I want to know...**

**"What's the overall project status?"**
→ [PROJECT_OVERVIEW.md](../../PROJECT_OVERVIEW.md)

**"What are we working on now?"**
→ [MASTER_ROADMAP_V2.md](MASTER_ROADMAP_V2.md) → [Phase 5](active/PHASE_05_INFRASTRUCTURE_OVERHAUL.md)

**"What's the detailed spec for [feature]?"**
→ [features/active/](features/active/) or [features/completed/](features/completed/)

**"What did we complete in Phase X?"**
→ [completed/PHASE_0X_*.md](completed/)

**"What's planned for the future?"**
→ [future/](future/) or [MASTER_ROADMAP_V2.md](MASTER_ROADMAP_V2.md)

**"How do backend implementations work?"**
→ [OPTIMAL_IMPLEMENTATION_SEQUENCE.md](OPTIMAL_IMPLEMENTATION_SEQUENCE.md)

**"What about Tools Track?"**
→ [TOOLS_IMPLEMENTATION_PLAN.md](TOOLS_IMPLEMENTATION_PLAN.md) and related files

---

## Update Process

### **When to Update Plans**

- **Weekly:** During active development (Phase 3)
- **At Milestones:** Feature completion, phase transitions
- **On Decisions:** Architecture decisions, scope changes

### **How to Update**

1. Update the relevant phase file
2. Update MASTER_ROADMAP_V2.md if progress changed
3. Update PROJECT_OVERVIEW.md if milestones changed
4. Commit with message: `docs: Update plans - [what changed]`

### **Moving Plans Between Folders**

- **active/ → completed/:** When phase finishes, update status to ✅
- **future/ → active/:** When phase starts, update status to 🔄
- **anywhere → archive/:** When plan superseded, add date to filename

---

## Related Documentation

### **Architecture**

- [ADRs](../adrs/) - Architecture decision records
- [Architecture Specs](../../architecture/) - System architecture details

### **Development Guidelines**

- [Guidelines](../guidelines/) - Development patterns and conventions
- [Guides](../guides/) - How-to guides for developers

### **Task Management**

- [Tasks](../tasks/) - Active task specifications
- [Completed Tasks](../completed/tasks/) - Historical task records

---

**Last Updated:** February 3, 2026
**Maintained By:** Project team
**Questions?** See [Documentation Organization Guide](../guidelines/DOCUMENT_ORGANIZATION_GUIDE.md)

---

## Folder Status (Current)

| Folder | Contents | Status |
|--------|----------|--------|
| `active/` | PHASE_05_INFRASTRUCTURE_OVERHAUL.md | 1 file |
| `completed/` | PHASE_01, PHASE_02, PHASE_03, PHASE_04 (+ P4-MULTI-COLLECTION-RAG-SEARCH) | 4+ files |
| `future/` | PHASE_06, PHASE_07, PHASE_08 | 3 files |
| `features/active/` | (none) | 0 files |
| `features/completed/` | P3-F2, P3-F5, P3-F6 | 3 files |
