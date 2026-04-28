# ADR-035: Service Boundary Clarification

**Status:** ✅ Accepted
**Date:** 2025-10-22
**Deciders:** Architecture Team
**Tags:** architecture, microservices, boundaries, corpus, orchestrator

---

## Context

**What is the issue we're addressing?**

During P4-F10 implementation, confusion arose about which features belong in which service container:

- Chunking strategies were added to orchestrator service (backend) instead of retrieval service
- Corpus validation features split across containers
- Import paths crossing service boundaries
- Docker container isolation not respected in code organization

**Current confusion:**
- `src/orchestrator/` contains orchestrator BUT ALSO corpus management features
- `src/corpus_svc/` is the corpus manager but missing some corpus features
- Cross-container imports attempted (impossible in Docker)
- Unclear which service owns which responsibility

---

## Decision

**What did we decide?**

**Clarify and enforce strict service boundaries with clear responsibilities:**

### **Retrieval Service = Corpus Manager**

**Container:** `corpus-service` (port 8001/8004)
**Location:** `src/corpus_svc/`
**Database:** PostgreSQL (documents, collections, chunks metadata)
**Vector Store:** Qdrant (embeddings)

**Responsibilities:**
- ✅ Document ingestion and storage
- ✅ Collection management
- ✅ Chunking strategies (ALL 8 strategies from P4-F9)
- ✅ Embedding generation and vector storage
- ✅ Semantic search and retrieval
- ✅ Preflight analysis (chunking strategy recommendation)
- ✅ Corpus test suites (retrieval quality validation)
- ✅ Retrieval metrics (Hit@K, MRR, nDCG)
- ✅ Exemplar management (as documents with `document_type="exemplar"`)
- ✅ Usage analytics

**Endpoints:**
- `/api/v1/documents/*` - Document CRUD
- `/api/v1/collections/*` - Collection management
- `/api/v1/query/*` - Semantic search
- `/api/v1/chunking/*` - Chunking strategies (P4-F9)
- `/api/v1/test-suites/*` - Corpus validation (P4-F10)
- `/api/v1/analytics/*` - Usage analytics

---

### **Orchestrator Service = Use Case Execution Engine**

**Container:** `orchestrator-api` (port 8000/8006)
**Location:** `src/orchestrator/` (poorly named, but keep for now)
**Database:** PostgreSQL (use cases, run manifests, query history)

**Responsibilities:**
- ✅ Use case configuration and management
- ✅ LLM orchestration and execution
- ✅ Intent parsing
- ✅ Policy enforcement
- ✅ Run manifest telemetry
- ✅ Query history (stateless sessions)
- ✅ Authentication and authorization
- ✅ Prompt patterns library
- ✅ Token analytics and pricing
- ✅ Model registry
- ✅ Use case validation (configuration validation, not corpus validation)

**Endpoints:**
- `/api/v1/use-cases/*` - Use case management
- `/api/v1/orchestrator/*` - Use case execution
- `/api/v1/capabilities/*` - System capabilities
- `/api/v1/run-manifests/*` - Telemetry data
- `/api/v1/query-history/*` - Session queries
- `/api/v1/models/*` - Model configuration
- `/api/v1/admin/*` - Admin features

---

### **Shared Module = Common Utilities**

**Location:** `src/shared/`
**Copied into:** Both containers during build

**Responsibilities:**
- ✅ Authentication (JWT, users, roles)
- ✅ Logging utilities
- ✅ Telemetry utilities
- ✅ Common types/schemas used by both services

**NOT for:**
- ❌ Business logic (belongs in services)
- ❌ Service-specific schemas (keep in service)
- ❌ Cross-service dependencies (use APIs instead)

---

## Communication Pattern

### **Frontend ↔ Backend Communication**

**IMPORTANT:** The **orchestrator-api acts as the backend API gateway/proxy** for the frontend.

```
┌─────────────┐
│   Frontend  │ (Angular, port 4200/4201)
│  (UI Web)   │
└──────┬──────┘
       │ ALL API calls go to orchestrator-api:8000/8006
       ↓
┌──────────────────────┐
│  Orchestrator-API    │ (Backend Gateway)
│  (port 8000/8006)    │
└──────┬───────────────┘
       │
       ├→ Handles: Use case execution, auth, query history
       │
       └→ Proxies to: Retrieval service for corpus operations
                      ↓
              ┌───────────────────┐
              │ Retrieval Service │ (Corpus Manager)
              │  (port 8001/8004) │
              └───────────────────┘
```

**Key Points:**
- ✅ Frontend calls **ONLY** orchestrator-api (single entry point)
- ✅ Orchestrator proxies corpus operations to retrieval service
- ✅ Retrieval service is internal (not exposed to frontend directly)
- ✅ Orchestrator handles all authentication/authorization

**Example Flow: Document Upload**
```
1. Frontend: POST /api/v1/documents/upload → Orchestrator (port 8006)
2. Orchestrator validates auth, then proxies:
   POST {CORPUS_SVC_URL}/api/v1/documents/upload
3. Retrieval service processes document
4. Response flows back: Retrieval → Orchestrator → Frontend
```

### **Service-to-Service Communication**

**Orchestrator → Retrieval (Internal):** HTTP APIs via CORPUS_SVC_URL

**Example: Orchestrator needs corpus search**
```python
# ❌ WRONG: Direct import
from retrieval.app.services.query_service import QueryService

# ✅ CORRECT: HTTP API call via service URL
import httpx
response = await httpx.post(
    f"{CORPUS_SVC_URL}/api/v1/query/semantic",
    json=query_data
)
```

**Example: Both services need chunking**
```python
# ❌ WRONG: Chunking in shared (it's corpus-specific)
# ❌ WRONG: Chunking in orchestrator (not its responsibility)

# ✅ CORRECT: Chunking in retrieval service
# Orchestrator calls retrieval's /api/v1/chunking endpoint if needed
```

---

## Rationale

**Why this separation?**

1. **Docker Isolation:** Each container has independent filesystem
2. **Microservice Pattern:** Services communicate via APIs, not imports
3. **Single Responsibility:** Each service has clear, focused purpose
4. **Independent Scaling:** Can scale retrieval (corpus-heavy) separately from orchestrator (LLM-heavy)
5. **Clear Ownership:** No confusion about where features belong

**Key Insight:** **Retrieval = Corpus Manager** is not just a service, it's THE corpus service. All corpus operations belong there, including chunking, preflight, and validation.

---

## Consequences

### Positive

- ✅ Clear service boundaries prevent architecture drift
- ✅ Impossible to create cross-container import spaghetti
- ✅ Each service can be developed/deployed independently
- ✅ Easier onboarding (clear responsibility map)
- ✅ Better testability (services are isolated)

### Negative

- ⚠️ HTTP calls add latency vs direct imports (acceptable tradeoff)
- ⚠️ API versioning needed for service communication
- ⚠️ More complex local development (need both containers running)

### Neutral

- 📝 `src/orchestrator/` poorly named (should be `src/orchestrator/`) - rename in Phase 7
- 📝 Some features migrated during P4-F10 cleanup

---

## Implementation

**Completed in P4-F10:**

- ✅ Moved chunking service from orchestrator → retrieval
- ✅ Moved preflight service to retrieval (corpus analysis)
- ✅ Moved test suites to retrieval (corpus validation)
- ✅ Removed duplicate exemplar infrastructure (use documents)
- ✅ Updated imports to respect container boundaries

**Future Work:**

- 📝 Rename `src/orchestrator/` → `src/orchestrator/` (Phase 7)
- 📝 Document service API contracts
- 📝 Add service health checks and dependencies

---

## Related

- [ADR-030: No Transcripts; Run Manifests Only](ADR-030-No-Transcripts-Run-Manifests.md)
- [ADR-021: Collection-Based Document Management](ADR-021-Collection-Based-Document-Management.md)
- [ADR-034: Use Case Validation & Test Harness](ADR-034-Use-Case-Validation-Harness.md)
- [Stateless Core v1 Implementation Plan](../plans/STATELESS_CORE_V1_IMPLEMENTATION_PLAN.md)

---

**Status:** ✅ Accepted - October 22, 2025
**Template Version:** 1.0
**Based On:** [Michael Nygard's ADR pattern](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
