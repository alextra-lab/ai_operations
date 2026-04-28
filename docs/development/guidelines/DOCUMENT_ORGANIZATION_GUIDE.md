# Documentation Organization Guide

**Last Updated:** 2025-10-12
**Purpose:** Clarify the purpose and relationships between documentation folders

---

## Documentation Structure Overview

```text
$PROJECT_ROOT/docs/
├── README.md                    # Documentation index (start here)
├── api/                         # API specifications (for integrators)
├── architecture/                # System architecture (high-level designs)
├── development/                 # Developer documentation
│   ├── adrs/                   # Architecture Decision Records
│   ├── analysis/               # Technical investigations
│   ├── architecture/           # Development architecture details
│   ├── completed/              # Completed work artifacts
│   ├── guidelines/             # Development standards
│   ├── guides/                 # How-to guides
│   ├── plans/                  # Implementation plans
│   ├── sessions/               # Work session summaries
│   ├── specs/                  # Feature specifications
│   ├── tasks/                  # Active/planned tasks
│   └── templates/              # Document templates
├── testing/                     # Testing documentation
└── archive/                     # Historical/deprecated docs
```

---

## Folder Purposes & When to Use

### `/docs/README.md`

**Purpose:** Documentation index and navigation guide
**Create when:** New documentation sections added
**Contains:** Links to key documents organized by topic

---

### `/docs/api/`

**Purpose:** API specifications for external integrators
**Audience:** Frontend developers, API consumers, third-party integrators

**Create when:** Public API endpoints added or changed
**Examples:**

- `authentication.md` - Authentication flows and JWT specs
- `conversations.md` - Conversation/thread API contracts

- `documents.md` - Document management API

**NOT for:**

- Implementation details (use `/development/`)
- Architecture decisions (use `/development/adrs/`)

---

### `/docs/architecture/`

**Purpose:** High-level system architecture and design patterns
**Audience:** Architects, senior developers, stakeholders
**Create when:** System-wide architectural patterns established
**Examples:**

- `RAG_Architecture.md` - Retrieval-Augmented Generation design
- `authentication_patterns.md` - Auth/authz patterns

- `service_decoupling.md` - Microservice boundaries
- `TOOLS_ARCHITECTURE_DIAGRAMS.md` - Visual architecture diagrams

**Key distinction:** **Cross-cutting** concerns that affect multiple services

**NOT for:**

- Specific feature designs (use `/development/architecture/`)
- Implementation plans (use `/development/plans/`)

---

### `/docs/development/`

**Purpose:** ALL development-related documentation

**Principle:** `docs/development/` = BUILD the app | Other folders = USE the app

---

#### `/docs/development/adrs/` (Architecture Decision Records)

**Purpose:** Record significant architectural decisions with context and alternatives
**Format:** Use ADR template (template.md)

**Create when:**

- Making architectural decision that affects system design
- Choosing between multiple technical approaches

- Establishing patterns/conventions
- Making technology selections

**Naming:** `ADR-NNN-short-title.md` (check existing numbers first!)

**Examples:**

- `ADR-001-hybrid-tools-architecture.md` - Tools integration strategy

- `ADR-016-Dynamic-Intent-System.md` - Intent type system design

**NOT for:**

- Implementation details (use `/plans/` or `/guides/`)
- Bug fixes or refactoring (use `/sessions/` or `/completed/`)

---

#### `/docs/development/analysis/`

**Purpose:** Technical investigations, gap analysis, impact assessments
**Create when:**

- Analyzing technical problems or inconsistencies
- Investigating performance issues
- Assessing feasibility of features

- Documenting findings from audits

**Examples:**

- `API_CONTRACT_MISMATCHES.md` - Audit of API inconsistencies
- `gap_list.md` - Feature gaps identified

- `metrics_trace.md` - Metrics implementation analysis

**NOT for:**

- Solutions/implementations (use `/plans/` or `/guides/`)
- Decisions (use `/adrs/`)

---

#### `/docs/development/architecture/`

**Purpose:** Development-specific architecture details (feature-level)
**Create when:** Documenting architecture of specific features or components

**Examples:**

- `VISUALIZATION_ARCHITECTURE.md` - Chart/graph rendering architecture

**Distinction from `/docs/architecture/`:**

- `/docs/architecture/` - System-wide, cross-cutting (RAG, Auth, Service Boundaries)
- `/docs/development/architecture/` - Feature-specific (Visualization, Specific workflows)

---

#### `/docs/development/completed/`

**Purpose:** Archive of completed work (tasks, reports, summaries)
**Create when:** Work is finished and you want historical record
**Structure:**

- `/completed/tasks/` - Completed task specifications
- `/completed/reports/` - Implementation reports and summaries

**Examples:**

- `P2_FIX_09_EXECUTION_METRICS_ENHANCEMENT.md` - Completed fix
- `P2_F5_ANALYTICS_VISUALIZATION_COMPLETE.md` - Completed feature

**Process:** Move from `/tasks/` to `/completed/tasks/` when done

---

#### `/docs/development/guidelines/`

**Purpose:** Development standards, coding conventions, best practices

**Create when:** Establishing team standards or patterns
**Examples:**

- `ANGULAR_DEVELOPMENT_GUIDELINES.md` - Angular coding standards
- `DOCUMENTATION_GUIDELINES.md` - How to write docs
- `Dependency_Management.md` - Package management rules
- `PYTHON_PROTOCOL_PATTERNS.md` - Protocol parameter names, positional-only, Ruff ARG002

**NOT for:**

- Specific how-to guides (use `/guides/`)
- Project-specific decisions (use `/adrs/`)

---

#### `/docs/development/guides/`

**Purpose:** Step-by-step how-to guides for developers

**Create when:** Teaching how to perform a specific development task
**Examples:**

- `INTENT_SYSTEM_USAGE_GUIDE.md` - How to use dynamic intents
- `TOOLS_START_HERE.md` - Tools integration getting started
- `cursor-documentation-workflow.md` - How to document with Cursor

**Format:** Practical, example-driven, actionable steps

**NOT for:**

- Standards/conventions (use `/guidelines/`)

- Architectural decisions (use `/adrs/`)

---

#### `/docs/development/plans/`

**Purpose:** Implementation plans and roadmaps
**Create when:** Planning multi-step features or initiatives
**Examples:**

- `UI_DEVELOPMENT_PLAN.md` - Complete UI implementation roadmap
- `UNIFIED_BACKEND_IMPLEMENTATION_PLAN.md` - Backend feature plan

- `DYNAMIC_INTENT_IMPLEMENTATION_ROADMAP.md` - Intent system rollout
- `TOOLS_IMPLEMENTATION_PLAN.md` - Tools integration phases

**Format:** Phased, with deliverables, success criteria, timelines

**NOT for:**

- Decisions (use `/adrs/`)
- How-to instructions (use `/guides/`)

---

#### `/docs/development/sessions/`

**Purpose:** Brief summaries of work sessions (NOT verbose reports)

**Create when:** Completing a focused work session (daily/feature completion)
**Format:** Concise bullet points, what changed, next steps
**Naming:** `YYYY-MM-DD-brief-description.md`

**Examples:**

- `2025-10-12-llm-content-rendering-completion.md` - Feature completion
- `2025-10-10-p2-f4-thread-conversations.md` - Session summary

**Keep brief:** 1-2 pages max

**NOT for:**

- Detailed implementation docs (use `/plans/` or `/guides/`)
- Long analysis (use `/analysis/`)

---

#### `/docs/development/specs/`

**Purpose:** Detailed feature specifications and requirements
**Create when:** Defining requirements before implementation

**Examples:**

- `DEVELOPMENT_CLARIFICATIONS_SUMMARY.md` - Clarified requirements

**NOT for:**

- Implementation plans (use `/plans/`)
- Decisions (use `/adrs/`)

---

#### `/docs/development/tasks/`

**Purpose:** Active or planned task specifications

**Create when:** Planning specific development tasks
**Examples:**

- `P2_FIX_10_RLS_ENFORCEMENT.md` - Planned fix

- `TASK_001_API_CONTRACT_ALIGNMENT.md` - Planned task

**Process:**

1. Create task spec here
2. Work on task
3. Move to `/completed/tasks/` when done

---

#### `/docs/development/templates/`

**Purpose:** Templates for creating new documents
**Examples:**

- ADR template
- Feature implementation prompt templates

---

### `/docs/testing/`

**Purpose:** Testing documentation (guides, setup, troubleshooting)
**Audience:** Developers, QA, CI/CD
**Examples:**

- `TESTING_GUIDE.md` - How to run tests
- `TEST_ENVIRONMENT_SETUP.md` - Test environment configuration
- `TROUBLESHOOTING.md` - Common test issues

**NOT for:**

- Development guidelines (use `/development/guidelines/`)
- Test plans for specific features (use `/development/plans/`)

---

### `/docs/archive/`

**Purpose:** Historical or deprecated documentation
**Move here when:** Documentation no longer relevant but valuable for history
**Examples:**

- `ARCHIVED_Streamlit_UI_Development_Plan.md` - Previous UI approach
- Deprecated guides and outdated implementation docs

**NOT for:**

- Active documentation (use appropriate folder)

---

## Decision Tree: Where Should My Document Go?

### Is it an API specification for external consumers?

**YES** → `/docs/api/`
**NO** → Continue...

### Is it a system-wide architectural pattern?

**YES** → `/docs/architecture/`

**NO** → Continue...

### Is it related to testing?

**YES** → `/docs/testing/`
**NO** → Continue...

### Development-related? (Most documents)

**YES** → Choose subfolder in `/docs/development/`:

#### Architecture Decision Record?

- Significant decision with alternatives considered?
- **YES** → `/docs/development/adrs/` (use template, check ADR numbers!)

#### Technical Investigation/Analysis?

- Problem analysis, gap analysis, feasibility study?
- **YES** → `/docs/development/analysis/`

#### Feature-Specific Architecture?

- Detailed architecture of single feature/component?

- **YES** → `/docs/development/architecture/`

#### Development Standard/Convention?

- Coding standards, team conventions, best practices?
- **YES** → `/docs/development/guidelines/`

#### How-To Guide?

- Step-by-step instructions for developers?
- **YES** → `/docs/development/guides/`

#### Implementation Plan/Roadmap?

- Multi-phase feature implementation?
- **YES** → `/docs/development/plans/`

#### Work Session Summary?

- Brief summary of completed work?

- **YES** → `/docs/development/sessions/`

#### Feature Specification?

- Detailed requirements before implementation?
- **YES** → `/docs/development/specs/`

#### Task Specification?

- Specific development task (active or planned)?
- **YES** → `/docs/development/tasks/` (move to `/completed/tasks/` when done)

#### Completed Work?

- Historical record of finished work?
- **YES** → `/docs/development/completed/`

#### Template?

- Template for creating new documents?
- **YES** → `/docs/development/templates/`

---

## Common Mistakes & Corrections

### ❌ **WRONG: Created ADR without checking existing numbers**

**Result:** Two ADR-015 files
**Correction:** Always `ls docs/development/adrs/ADR-*.md | sort` first

### ❌ **WRONG: Created verbose summary document in root**

**Result:** Documentation sprawl
**Correction:** Use `/development/sessions/` for brief summaries

### ❌ **WRONG: Put implementation details in `/docs/architecture/`**

**Result:** Confusion between high-level and feature-level
**Correction:** System-wide → `/architecture/`, feature-level → `/development/architecture/`

### ❌ **WRONG: Created multiple documents about same topic**

**Result:** Conflicting information
**Correction:** Update existing document or consolidate

### ❌ **WRONG: Put development guide in `/docs/` root**

**Result:** Hard to find, doesn't follow structure
**Correction:** `/docs/development/guides/`

---

## Documentation Maintenance

### Regular Reviews

- **Weekly:** Check for duplicate or outdated docs
- **Monthly:** Review `/development/tasks/` and move completed items
- **Quarterly:** Archive outdated docs to `/archive/`

### Before Creating New Document

1. Check if similar document exists
2. Determine correct folder using decision tree
3. Follow naming conventions
4. Use templates where available
5. Update `/docs/README.md` with link

### When Completing Work

1. Update status in document
2. Move task from `/tasks/` to `/completed/tasks/`
3. Create brief session summary in `/sessions/`
4. Update related plans/guides as needed

---

## Quick Reference

| Document Type | Location | Example |
| ------------- | -------- | ------- |
| **API spec for consumers** | `/api/` | `authentication.md` |
| **System architecture** | `/architecture/` | `RAG_Architecture.md` |
| **Architecture decision** | `/development/adrs/` | `ADR-016-Dynamic-Intent-System.md` |
| **Technical analysis** | `/development/analysis/` | `gap_list.md` |
| **Feature architecture** | `/development/architecture/` | `VISUALIZATION_ARCHITECTURE.md` |
| **Coding standards** | `/development/guidelines/` | `ANGULAR_DEVELOPMENT_GUIDELINES.md` |
| **How-to guide** | `/development/guides/` | `INTENT_SYSTEM_USAGE_GUIDE.md` |
| **Implementation plan** | `/development/plans/` | `UI_DEVELOPMENT_PLAN.md` |
| **Work session** | `/development/sessions/` | `2025-10-12-feature-completion.md` |
| **Feature spec** | `/development/specs/` | `DEVELOPMENT_CLARIFICATIONS_SUMMARY.md` |
| **Active task** | `/development/tasks/` | `TASK_001_API_CONTRACT_ALIGNMENT.md` |
| **Completed work** | `/development/completed/` | `P2_FIX_09_EXECUTION_METRICS_ENHANCEMENT.md` |
| **Testing docs** | `/testing/` | `TESTING_GUIDE.md` |
| **Historical docs** | `/archive/` | `ARCHIVED_Streamlit_UI_Development_Plan.md` |

---

## Questions?

If unsure where a document belongs:

1. Check this guide's decision tree
2. Look for similar existing documents
3. Ask: "Is this for building the app or using the app?"
   - Building → `/development/` (find appropriate subfolder)
   - Using → `/api/`, `/testing/`, or `/architecture/`

When in doubt, prefer:

- **Updating existing docs** over creating new ones
- **Brief summaries** over verbose reports
- **Practical guides** over theoretical discussions
- **Clear hierarchy** over flat organization

---

**Principle:** Good documentation is findable, maintainable, and actionable.
