# Model Selection Guide: When to Use Claude 4.5 vs Auto

**Purpose:** Guide for selecting the appropriate AI model for each task in the AI Operations Platform project.

---

## Quick Decision Matrix

| Task Type | Recommended Model | Reasoning |
|-----------|-------------------|-----------|
| **Architectural Decisions** | 🟣 **Claude 4.5** | Complex system design, trade-offs, ADR creation |
| **New Feature Design** | 🟣 **Claude 4.5** | Novel functionality, integration patterns |
| **Complex Debugging** | 🟣 **Claude 4.5** | Multi-layer issues, performance bottlenecks |
| **Large Refactoring** | 🟣 **Claude 4.5** | System-wide changes, dependency management |
| **CRUD Operations** | 🔵 **Auto** | Straightforward create/read/update/delete |
| **UI Components** | 🔵 **Auto** | Following existing ADR-012 patterns |
| **Test Writing** | 🔵 **Auto** | Unit tests, integration tests (established patterns) |
| **Documentation** | 🔵 **Auto** | Markdown docs, API documentation |
| **Bug Fixes (Isolated)** | 🔵 **Auto** | Single component, clear root cause |

---

## Model Characteristics

### 🟣 Claude 4.5 (Advanced) - Use When:

**Strengths:**
- Deep reasoning about complex systems
- Novel problem-solving and creative solutions
- Multi-layer architectural thinking
- Trade-off analysis and decision-making
- Handling ambiguity and open-ended problems

**Best For:**
1. **Architecture & Design**
   - Creating ADRs (Architecture Decision Records)
   - Designing new features with no existing patterns
   - System integration planning
   - Database schema design (new tables/relationships)
   - API contract design (breaking changes)

2. **Complex Implementation**
   - Multi-service coordination
   - State management across boundaries
   - Performance optimization (requires profiling)
   - Security implementation (RLS, encryption, auth flows)
   - RAG pipeline design and tuning

3. **Debugging & Investigation**
   - Multi-layer performance issues
   - Race conditions and concurrency bugs
   - Memory leaks and resource exhaustion
   - Complex integration failures
   - Root cause analysis across services

4. **Major Refactoring**
   - Service boundary changes
   - Database migrations with data preservation
   - Breaking API changes
   - Framework upgrades (Angular, FastAPI)

---

### 🔵 Auto (Claude 3.5 Sonnet) - Use When:

**Strengths:**
- Fast execution for routine tasks
- Excellent at following established patterns
- High-quality code generation for known patterns
- Good for incremental improvements
- Cost-effective for bulk work

**Best For:**
1. **Standard CRUD Operations**
   - User management (create, update, delete)
   - Role management (assign, remove)
   - Configuration management (get, set)
   - Audit log queries (filter, export)

2. **UI Components (Following ADR-012)**
   - Material components with Layered Pattern
   - Forms with validation (ReactiveFormsModule)
   - Tables with pagination (MatTable)
   - Dialogs and modals (MatDialog)
   - WCAG 2.1 AA compliant components

3. **Backend API Endpoints (RESTful)**
   - List/Get/Create/Update/Delete endpoints
   - Filtering and pagination
   - Pydantic schema validation
   - Standard error handling
   - Audit logging integration

4. **Testing**
   - Unit tests (Jest, pytest)
   - Integration tests (established patterns)
   - Component tests (Angular TestBed)
   - API tests (FastAPI TestClient)
   - Coverage improvements

5. **Documentation**
   - API documentation (OpenAPI)
   - User guides
   - Task specifications (following templates)
   - Session logs
   - README updates

6. **Bug Fixes (Isolated)**
   - Single component issues
   - Validation errors
   - Display bugs
   - Missing error handling
   - Linter/type errors

---

## Phase 4 Admin Essentials - Model Recommendations

| Task | Model | Why |
|------|-------|-----|
| **P4-ADMIN-01: User Management UI** | 🔵 **Auto** | Standard CRUD, follows existing patterns (auth router, Material forms) |
| **P4-ADMIN-02: Role Management UI** | 🔵 **Auto** | Display & assignment UI, backend complete (P4-TASK-14) |
| **P4-ADMIN-03: System Config UI** | 🟣 **Claude 4.5** | JSON schema-driven forms, config validation, novel implementation |
| **P4-ADMIN-04: Audit Logs UI + API** | 🔵 **Auto** | Query & display interface, standard filtering/export |
| **P4-MULTI-COLLECTION** | 🟣 **Claude 4.5** | RAG architecture, multi-collection search, score normalization |
| **P2-FIX-13: Simplified Pricing** | 🔵 **Auto** | Replace 15-tier with 3-category, schema + API changes |
| **P4-F12: Testing & Documentation** | 🔵 **Auto** | Test writing, documentation, established patterns |

---

## Detailed Task Breakdowns

### P4-ADMIN-01: User Management UI (🔵 Auto)

**Why Auto:**
- Backend API pattern already exists (create_user endpoint)
- UI follows ADR-012 Layered Pattern (established)
- Material components (Table, Dialog, Forms) - known patterns
- CRUD operations with validation - straightforward
- Similar to existing components (Use Case List, Document Library)

**What to Implement:**
- UserListComponent (Material Table + pagination)
- UserCreateDialogComponent (ReactiveForm)
- UserEditDialogComponent (ReactiveForm)
- PasswordResetDialogComponent
- SessionViewerComponent
- Backend: 7 new endpoints (RESTful CRUD)

**Complexity:** Low-Medium (3-4 days, mostly UI work)

---

### P4-ADMIN-02: Role Management UI (🔵 Auto)

**Why Auto:**
- Backend complete (P4-TASK-14, ADR-041)
- Display role-to-use-case assignments - straightforward
- Assign/remove use cases - simple actions
- Material Cards/Expansion Panels - known pattern
- Follow existing role management backend API

**What to Implement:**
- RoleListComponent (cards)
- RoleDetailComponent (3 sections)
- AssignUseCaseDialogComponent
- RoleMembersComponent
- Backend: 2 helper endpoints (list roles, get members)

**Complexity:** Low-Medium (2-3 days, backend mostly done)

---

### P4-ADMIN-03: System Config UI (🟣 Claude 4.5)

**Why Claude 4.5:**
- **Novel implementation:** JSON schema-driven form generation
- **Complex validation:** Pydantic schemas → frontend forms
- **Architecture decision:** Config storage (JSONB vs env vars)
- **Integration:** YAML import/export with validation
- **Restart logic:** Determining which settings require restart
- **Security:** Config masking for sensitive values

**What to Implement:**
- JSON Schema → ReactiveForm generator (NEW pattern)
- Config validation before save (schema validation)
- YAML import/export with preview
- system_config table (JSONB storage)
- 4 config sections (corpus, auth, features, system)

**Complexity:** Medium-High (3-4 days, schema-driven forms are complex)

**Note:** This is the most architecturally interesting admin task. Claude 4.5 can design the schema-driven form system properly.

---

### P4-ADMIN-04: Audit Logs UI + API (🔵 Auto)

**Why Auto:**
- Standard query interface with filters
- Material Table with pagination - established
- Export to CSV/JSON - straightforward
- Stats dashboard with charts - standard visualization
- Backend: RESTful query API with filtering

**What to Implement:**
- AuditLogListComponent (Material Table)
- AuditLogFiltersComponent (form)
- AuditStatsDashboardComponent (charts)
- Backend: 4 endpoints (query, stats, export, list actions)

**Complexity:** Low-Medium (2-3 days, query + display)

---

### P4-MULTI-COLLECTION: Multi-Collection RAG Search (🟣 Claude 4.5)

**Why Claude 4.5:**
- **RAG architecture:** Multi-collection search strategy
- **Score normalization:** Combine results across collections
- **Ranking algorithm:** Cross-collection relevance scoring
- **Performance:** Parallel vs sequential retrieval
- **Architecture:** Collection weighting, user preferences
- **Deduplication:** Handle same document in multiple collections

**What to Implement:**
- Multi-collection search algorithm
- Score normalization across embeddings
- Collection weighting (user preferences)
- Result deduplication
- Performance optimization (parallel retrieval)

**Complexity:** High (2-3 days, RAG architecture work)

**Note:** This requires deep understanding of vector search, scoring, and RAG pipelines. Claude 4.5 is essential.

---

## When to Switch Models Mid-Task

### Start with Auto, Switch to Claude 4.5 If:

1. **Unexpected Complexity**
   - "This is more complex than I thought"
   - Multiple architectural decisions emerging
   - Novel patterns required

2. **Integration Challenges**
   - Multiple services need coordination
   - Breaking changes discovered
   - Performance bottlenecks

3. **Design Ambiguity**
   - Requirements unclear or conflicting
   - Multiple valid approaches
   - Trade-offs need deep analysis

### Start with Claude 4.5, Switch to Auto For:

1. **Boilerplate After Design**
   - Architecture decided, now implement CRUD
   - Design complete, write tests
   - Patterns established, apply to remaining components

2. **Straightforward Subtasks**
   - Documentation after feature complete
   - Test coverage for designed system
   - UI components following established pattern

---

## Cost Considerations

| Model | Relative Cost | When to Optimize |
|-------|---------------|------------------|
| Claude 4.5 | **3-5x** more expensive | Use only when complexity justifies cost |
| Auto (3.5 Sonnet) | **Baseline** | Default for routine tasks |

**Budget Strategy:**
- Use Claude 4.5 for ~20% of tasks (architecture, design, complex debugging)
- Use Auto for ~80% of tasks (implementation, tests, docs)
- This balances quality with cost-effectiveness

---

## Summary Table: Phase 4 Admin Essentials

| Task ID | Task Name | Days | Model | Key Reason |
|---------|-----------|------|-------|------------|
| **P4-ADMIN-01** | User Management UI | 3-4 | 🔵 **Auto** | Standard CRUD, established patterns |
| **P4-ADMIN-02** | Role Management UI | 2-3 | 🔵 **Auto** | Backend done, display only |
| **P4-ADMIN-03** | System Config UI | 3-4 | 🟣 **Claude 4.5** | JSON schema-driven forms (novel) |
| **P4-ADMIN-04** | Audit Logs UI + API | 2-3 | 🔵 **Auto** | Query & display (standard) |
| **P4-MULTI-COLLECTION** | Multi-Collection Search | 2-3 | 🟣 **Claude 4.5** | RAG architecture & scoring |
| **P2-FIX-13** | Simplified Pricing | 1-2 | 🔵 **Auto** | Replace model, schema changes |
| **P4-F12** | Testing & Docs | 7-9 | 🔵 **Auto** | Test writing, documentation |

**Total Days:** 20-28 days
**Claude 4.5 Days:** 5-7 days (~25%)
**Auto Days:** 15-21 days (~75%)

---

## Tips for Effective Model Usage

### When Using Claude 4.5:

1. **Start with context:** Provide full architectural context
2. **Ask for trade-offs:** Request analysis of multiple approaches
3. **Request ADRs:** For significant decisions, ask for ADR draft
4. **Iterative refinement:** Don't rush, let model think deeply
5. **Question assumptions:** Ask "What if?" scenarios

### When Using Auto:

1. **Reference patterns:** Point to existing similar components
2. **Be specific:** Provide exact file paths, function names
3. **Request tests:** Always ask for unit tests with implementation
4. **Follow conventions:** Explicitly mention ADR-012, WCAG, etc.
5. **Batch similar tasks:** Do all CRUD endpoints at once

---

**Document Owner:** Project team
**Created:** 2025-10-26
**Status:** Active Reference - Updated per Phase 4 Admin Essentials
