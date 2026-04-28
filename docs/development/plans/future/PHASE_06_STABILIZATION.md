# Phase 6: Stabilization & Validation

**Timeline:** January - February 2026 (2-3 weeks)
**Status:** 🔄 In Progress (55%)
**Dependencies:** Phase 5 (Infrastructure Overhaul) ✅ complete
**Goal:** Prove the application works end-to-end with real demos

---

## Overview

This phase shifts focus from building to validating. The application is feature-complete for pre-release; now we need to prove it works.

**Key Activities:**
1. ✅ UI walkthrough for all pages and roles
2. ✅ Core pipeline validation with real data
3. ⏳ First real MCP tool integration (Elasticsearch)
4. ⏳ Demo scripts for stakeholder presentations

---

## P6-STAB-01: UI Walkthrough Assessment ✅ COMPLETE

**Duration:** 3-4 days
**Actual:** 1 day (Nov 30, 2025)
**Status:** ✅ Complete

### Summary

Systematic verification of Angular frontend via API testing and browser walkthrough.

### Results

| Category | Issues Found | Fixed | Status |
|----------|-------------|-------|--------|
| Critical (500 errors) | 2 | 2 | ✅ Fixed |
| Medium (Test users) | 1 | 1 | ✅ Resolved |
| Low (Deferred feature) | 1 | - | ⏸️ Backlog |

### Critical Fixes Applied

1. **Database Migration 002** (`scripts/migrations/002_sync_query_history_and_context_threads.sql`)
   - Renamed `query_history.execution_time_ms` → `processing_time_ms`
   - Added 8 columns to `context_threads` table
   - Created 4 new indexes

2. **Test User Discovery**
   - All users (admin, analyst, testuser) use password: `adminpassword`

### Deferred Feature

- **Chunking Presets** → [BACKLOG_CHUNKING_PRESETS.md](../../tasks/BACKLOG_CHUNKING_PRESETS.md)
- Auto-chunking workflow is primary feature and works correctly

### Pages Verified (Browser Walkthrough)

| Page | Status |
|------|--------|
| Login | ✅ |
| Dashboard | ✅ |
| SOC Dashboard | ✅ |
| Use Cases | ✅ |
| Document Library | ✅ |
| User Management | ✅ |
| Conversations | ✅ |

### Deliverables

- [x] Issues list with severity ratings
- [x] All critical/high issues fixed
- [x] UI verification report: [Session Log](../../sessions/2025-11-30-p6-stab-01-ui-walkthrough.md)

---

## P6-STAB-02: Core Pipeline Validation ✅ COMPLETE

**Duration:** 3-4 days
**Actual:** 1 day (Nov 30, 2025) + 0.5 day (Dec 9, 2025)
**Status:** ✅ Complete

### Summary

Validated all four core application pipelines. Fixed embedding service provider factory bug during validation. Fixed critical RAG collection bugs that were preventing sources from being returned.

### Bugs Fixed

**Bug 1: Embedding Service Provider Factory (Nov 30)**
- **File:** `src/embedding/app/providers/factory.py`
- Fixed attribute name mismatch: `enabled` → `is_enabled`, `type` → `provider_type`
- Both local and LMStudio embedding providers now working

**Bug 2: RAG Collection Configuration (Dec 9) - P2-FIX-12**
- **Files:** Multiple (see task document)
- Fixed collection name resolution (database name → Qdrant name)
- Fixed provider parameter not being passed to embedding client
- Fixed context source transformation losing required fields
- **Task:** [P2-FIX-12](../../completed/tasks/P2_FIX_12_RAG_COLLECTION_BUG_FIX.md)

### Results

| Demo | Status | Notes |
|------|--------|-------|
| Demo 1: Document Ingestion | ✅ Passed | Fixed embedding service bug |
| Demo 2: RAG Q&A | ✅ Passed | Fixed collection bugs (Dec 9) |
| Demo 3: Use Case Execution | ✅ Passed | Fixed collection bugs (Dec 9) |
| Demo 4: Multi-turn Conversation | ✅ Passed | Client-side storage per ADR-030 |

### Embedding Providers Validated

| Provider | Model | Dimensions |
|----------|-------|------------|
| local | all-MiniLM-L6-v2 | 384 |
| openai (LMStudio) | text-embedding-nomic-embed-text-v1.5 | 768 |

### Deliverables

- [x] All 4 demos working
- [x] Issues found and fixed (embedding service bug, RAG collection bugs)
- [x] API documentation created: `docs/api/embedding-service.md`
- [x] Session log: `docs/development/sessions/2025-11-30-p6-stab-02-pipeline-validation.md`
- [x] RAG bug fix session log: `docs/development/sessions/2025-12-09-rag-collection-bug-fix-completion.md`

---

## P6-STAB-03: First Real MCP Tool - Elasticsearch

**Duration:** 5-7 days

### Objective

Connect the first real MCP tool to prove the Tools Track infrastructure works.

### Why Elasticsearch

- Highly relevant for SOC use case
- Well-documented MCP server available
- Elastic provides demo security data
- Demonstrates real-world value

### Implementation Steps

#### Step 1: Deploy Elasticsearch (Day 1)

**Option A: Docker (Recommended)**
```yaml
# Add to docker-compose.yml
elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
  environment:
    - discovery.type=single-node
    - xpack.security.enabled=false
  ports:
    - "9200:9200"
  volumes:
    - es_data:/usr/share/elasticsearch/data
```

**Option B: Elastic Cloud Trial**
- 14-day free trial
- No infrastructure management
- Pre-configured security

#### Step 2: Load Demo Data (Day 1-2)

**Elasticsearch Sample Data Options:**

| Dataset | Description | SOC Relevance |
|---------|-------------|---------------|
| `kibana_sample_data_logs` | Web server logs | ⭐⭐ Good |
| Security solution demo | Pre-built security events | ⭐⭐⭐ Perfect |
| BOTS Dataset | Boss of the SOC competition | ⭐⭐⭐ Perfect |

**Load via Kibana or API:**
```bash
# Load sample data via API
curl -X POST "localhost:9200/_sample_data/logs"
```

#### Step 3: Configure MCP Tool (Day 2-3)

**Register Elasticsearch tool in AI Operations Platform (AIOP):**

```json
{
  "tool_id": "elasticsearch_query",
  "name": "Elasticsearch Security Query",
  "description": "Query security logs and events in Elasticsearch",
  "category": "database",
  "tool_purpose": "retrieval",
  "service_location": "retrieval_service",
  "mcp_server_type": "http",
  "mcp_endpoint": "http://elasticsearch:9200",
  "requires_authentication": false,
  "config_options": {
    "default_index": "kibana_sample_data_logs",
    "max_results": 100
  }
}
```

#### Step 4: Create Use Case (Day 3-4)

**"Security Log Query" Use Case:**

```yaml
name: Security Log Query
description: Query Elasticsearch for security events
category: security
system_prompt: |
  You are a security analyst assistant. Use the Elasticsearch tool
  to query security logs and provide analysis.
tools:
  - elasticsearch_query
parameters:
  - name: query
    type: text
    description: What to search for in security logs
```

#### Step 5: Demo and Validate (Day 4-5)

**Demo Scenario:**
1. User asks: "Show me failed login attempts in the last 24 hours"
2. LLM generates Elasticsearch query
3. Tool executes query against ES
4. Results returned and formatted
5. LLM provides analysis

### Deliverables

- [ ] Elasticsearch running with demo data
- [ ] MCP tool registered and healthy
- [ ] Use case created and tested
- [ ] Demo script for stakeholders

---

## P6-STAB-04: Demo Scripts Suite

**Duration:** 2-3 days

### Objective

Create reproducible demo scripts for stakeholder presentations and testing.

### Scripts to Create

| Script | Purpose | Type |
|--------|---------|------|
| `demo_01_document_lifecycle.py` | Upload, chunk, embed, search | CLI |
| `demo_02_rag_qa.py` | Ask questions, verify sources | CLI |
| `demo_03_use_case_execute.py` | Run use case via API | CLI |
| `demo_04_elasticsearch_query.py` | MCP tool demo | CLI |
| `demo_05_conversation.py` | Multi-turn interaction | CLI |
| `demo_06_full_walkthrough.sh` | Run all demos in sequence | Shell |

### Script Template

```python
#!/usr/bin/env python3
"""
Demo: Document Lifecycle
Demonstrates: Upload → Chunk → Embed → Search
"""

import requests
from pathlib import Path

API_BASE = "http://localhost:8000/api/v1"
TOKEN = "..."  # Or load from env

def main():
    print("=" * 50)
    print("DEMO: Document Lifecycle")
    print("=" * 50)

    # Step 1: Upload
    print("\n[1/4] Uploading document...")
    # ...

    # Step 2: Chunk
    print("\n[2/4] Analyzing chunks...")
    # ...

    # Step 3: Embed
    print("\n[3/4] Generating embeddings...")
    # ...

    # Step 4: Search
    print("\n[4/4] Searching for content...")
    # ...

    print("\n✅ Demo complete!")

if __name__ == "__main__":
    main()
```

### Location

```
scripts/demos/
├── demo_01_document_lifecycle.py
├── demo_02_rag_qa.py
├── demo_03_use_case_execute.py
├── demo_04_elasticsearch_query.py
├── demo_05_conversation.py
├── demo_06_full_walkthrough.sh
├── README.md
└── requirements.txt
```

### Deliverables

- [ ] 6 demo scripts created
- [ ] README with usage instructions
- [ ] All demos run successfully
- [ ] Video recordings (optional)

---

## Exit Criteria

### P6-STAB-01: UI Walkthrough
- [ ] All pages tested for all roles
- [ ] Zero critical/high issues remaining
- [ ] Verification report complete

### P6-STAB-02: Pipeline Validation ✅
- [x] Document ingestion demo working
- [x] RAG Q&A demo working
- [x] Use case execution demo working
- [x] Conversation demo working

### P6-STAB-03: Elasticsearch Tool
- [ ] ES deployed with demo data
- [ ] MCP tool registered and healthy
- [ ] Security Log Query use case working
- [ ] Demo scenario reproducible

### P6-STAB-04: Demo Scripts
- [ ] All 6 scripts created
- [ ] All scripts run successfully
- [ ] Documentation complete

### Phase 6 Complete
- [ ] Application proven working end-to-end
- [ ] First MCP tool operational
- [ ] Ready for user documentation

---

**Document Owner:** Project team
**Created:** November 26, 2025
**Status:** Planned - Awaiting Phase 5 Completion
