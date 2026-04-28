# Phase 7: Documentation Overhaul

**Timeline:** February 2026 (1-2 weeks)
**Status:** 📋 Planned
**Dependencies:** Phase 6 (Stabilization) complete
**Goal:** User-ready documentation for departmental deployment

---

## Overview

Shift documentation focus from development to user-facing guides. The application is validated; now users need to know how to use it.

**Key Activities:**
1. Create 4 core user guides
2. Clean up obsolete development documentation
3. Update API documentation with examples

---

## P7-DOC-01: User Guides

**Duration:** 5-7 days
**Priority:** 🔴 Highest

### Guide 1: Analyst Guide

**Audience:** SOC Analysts (primary users)
**Location:** `docs/user-guides/analyst-guide.md`

**Table of Contents:**
1. Introduction
   - What is AI Operations Platform?
   - Key capabilities
2. Getting Started
   - Logging in
   - Navigating the interface
   - Understanding your dashboard
3. Using Use Cases
   - Finding available use cases
   - Executing a use case
   - Understanding results
   - Formatting (Mermaid, LaTeX)
4. Conversations
   - Starting a conversation
   - Multi-turn interactions
   - Exporting conversations
5. Searching the Corpus
   - Semantic search
   - RAG Q&A
   - Understanding sources
6. Tips and Best Practices
   - Writing effective queries
   - When to use which feature
7. Troubleshooting
   - Common issues
   - Getting help

**Estimated Length:** 2,000-3,000 words

---

### Guide 2: Admin Guide

**Audience:** System Administrators
**Location:** `docs/user-guides/admin-guide.md`

**Table of Contents:**
1. Introduction
   - Admin responsibilities
   - Access requirements
2. User Management
   - Creating users
   - Assigning roles
   - Managing sessions
   - Deactivating users
3. Role Management
   - Understanding roles
   - Role-use case assignments
   - Custom roles
4. System Configuration
   - General settings
   - Model configuration
   - Provider management
5. Audit Logs
   - Viewing audit history
   - Filtering and searching
   - Compliance reporting
6. Gateway Management
   - Provider health
   - Rate limit monitoring
   - Usage metrics
7. Tool Management
   - Viewing registered tools
   - Tool health monitoring
   - Tool configuration
8. Maintenance Tasks
   - Database health
   - Log management
   - Backup procedures

**Estimated Length:** 3,000-4,000 words

---

### Guide 3: Developer Guide (Use Case Creation)

**Audience:** Use Case Developers
**Location:** `docs/user-guides/developer-guide.md`

**Table of Contents:**
1. Introduction
   - What are use cases?
   - Developer role
2. Use Case Concepts
   - Templates and patterns
   - Multi-role prompts
   - RAG configuration
   - Tool integration
3. Creating a Use Case
   - Using the wizard
   - Step 1: Basic Info
   - Step 2: Category & Lifecycle
   - Step 3: Prompts (pattern library)
   - Step 4: Configuration
   - Step 5: Preview & Save
4. Prompt Engineering
   - System prompts
   - Developer prompts
   - Few-shot examples
   - Pattern library reference
5. Testing Use Cases
   - Validation checks
   - Test execution
   - Iterating on prompts
6. Publishing & Lifecycle
   - Draft vs Published
   - Versioning
   - Cloning use cases
7. Advanced Topics
   - RAG tuning
   - Tool selection
   - Parameter schemas

**Estimated Length:** 4,000-5,000 words

---

### Guide 4: Corpus Manager Guide

**Audience:** Document Librarians / Corpus Managers
**Location:** `docs/user-guides/corpus-manager-guide.md`

**Table of Contents:**
1. Introduction
   - Corpus management role
   - Document lifecycle
2. Document Upload
   - Supported formats
   - Upload interface
   - Drag and drop
3. Collections
   - Understanding collections
   - Creating collections
   - Collection settings
4. Chunking Strategies
   - What is chunking?
   - Available strategies
   - Choosing a strategy
   - Manual vs auto chunking
5. Document Analysis
   - Preflight reports
   - Strategy comparison
   - Quality assessment
6. Managing Documents
   - Document library
   - Filtering and search
   - Document details
   - Reprocessing
7. Best Practices
   - Document preparation
   - Collection organization
   - Quality maintenance

**Estimated Length:** 2,500-3,500 words

---

## P7-DOC-02: Documentation Cleanup

**Duration:** 2-3 days

### Objective

Remove or archive obsolete development documentation to reduce confusion.

### Actions

| Action | Target | Result |
|--------|--------|--------|
| Archive | Obsolete plan files | Move to `archive/` |
| Delete | Duplicate/superseded docs | Remove entirely |
| Consolidate | Overlapping content | Merge into single source |
| Update | Stale README files | Refresh content |

### Files to Review

**Plans Directory (~30 files):**
- Archive completed phase plans
- Remove superseded implementation plans
- Keep only active/future plans

**Sessions Directory (~50+ files):**
- Archive sessions older than 30 days
- Keep recent sessions for reference

**Tasks Directory:**
- Move completed tasks to `completed/tasks/`
- Archive old task files

### Cleanup Checklist

- [ ] Review all files in `docs/development/plans/`
- [ ] Archive obsolete plans
- [ ] Update `README_PLANS.md`
- [ ] Review `docs/development/sessions/`
- [ ] Archive old sessions
- [ ] Update root `docs/README.md`
- [ ] Verify all links work

---

## P7-DOC-03: API Documentation

**Duration:** 1-2 days

### Objective

Update API documentation with practical examples.

### Actions

| Document | Action |
|----------|--------|
| `docs/api/authentication.md` | Add curl examples |
| `docs/api/use-cases.md` | Add execution examples |
| `docs/api/documents.md` | Add upload examples |
| `docs/api/conversations.md` | Add thread examples |
| `docs/api/tools.md` | Add tool query examples |

### Example Format

```markdown
## Execute Use Case

**Endpoint:** `POST /api/v1/use-cases/{id}/execute`

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/use-cases/123/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": "Analyze this threat indicator: 192.0.2.1"}'
```

**Example Response:**
```json
{
  "run_id": "abc-123",
  "status": "completed",
  "output": "Analysis results...",
  "metrics": {...}
}
```
```

---

## Exit Criteria

### P7-DOC-01: User Guides
- [ ] Analyst Guide complete (2,000+ words)
- [ ] Admin Guide complete (3,000+ words)
- [ ] Developer Guide complete (4,000+ words)
- [ ] Corpus Manager Guide complete (2,500+ words)
- [ ] All guides reviewed for accuracy

### P7-DOC-02: Cleanup
- [ ] Obsolete docs archived
- [ ] README files updated
- [ ] No broken links
- [ ] Navigation clear

### P7-DOC-03: API Docs
- [ ] All major endpoints have examples
- [ ] Examples tested and working

### Phase 7 Complete
- [ ] Users can self-serve with documentation
- [ ] Documentation is current and accurate
- [ ] Ready for departmental deployment

---

**Document Owner:** Project team
**Created:** November 26, 2025
**Status:** Planned - Awaiting Phase 6 Completion
