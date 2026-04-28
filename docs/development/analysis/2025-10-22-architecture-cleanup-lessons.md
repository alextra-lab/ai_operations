# Architecture Cleanup Lessons Learned - P4-F10

**Date:** October 22, 2025
**Context:** P4-F10 implementation revealed architectural issues
**Outcome:** Service boundaries clarified, architecture corrected

---

## What We Discovered

### **Problem: Features in Wrong Containers**

During P4-F10 implementation, features were initially placed in wrong services:
- Chunking service in **orchestrator** (should be corpus)
- Preflight analyzer split across services
- Test suites in **orchestrator** (should be corpus)
- Exemplars as separate infrastructure (should be documents)

**Root Cause:** Confusion about service responsibilities in Docker microservices

---

## Key Learnings

### **1. Service Names Matter**

**Before:** `corpus-service` (ambiguous)
- "Retrieval" sounds like a feature, not a service purpose
- Unclear if it's just semantic search or full corpus management

**After:** `corpus-service` (clear)
- Immediately communicates: "This manages the corpus"
- All corpus features naturally belong here
- No confusion about placement

**Lesson:** **Name services by their domain responsibility, not their primary feature**

---

### **2. Docker Containers = Hard Service Boundaries**

**Critical Understanding:**
- Each container has its own filesystem
- `src/orchestrator/` is NOT accessible from `src/corpus_svc/` container
- Cross-container imports are impossible (not just bad practice)
- Must communicate via HTTP APIs

**What Happened:**
- Code tried: `from ....backend.app.schemas import ...`
- Runtime: `ModuleNotFoundError` (backend doesn't exist in corpus container)
- Fix: Move features to correct container

**Lesson:** **Test cross-service imports immediately - they'll fail at runtime**

---

### **3. Corpus Service = Document + Chunking + Embeddings + Search**

**Realization:** "Corpus manager" is not just document storage

**Complete Corpus Responsibilities:**
- ✅ Document ingestion and storage
- ✅ Collection organization
- ✅ **Chunking strategies** (how to break documents)
- ✅ **Embedding generation** (vectorization)
- ✅ **Vector storage** (Qdrant management)
- ✅ **Semantic search** (retrieval)
- ✅ **Quality validation** (preflight, test suites, metrics)
- ✅ **Exemplars** (curated corpus content)

**Lesson:** **If it touches the corpus (documents, chunks, vectors), it belongs in corpus service**

---

### **4. Exemplars ARE Corpus Content**

**Initial Plan:** Separate `fewshot_exemplars` table with dedicated service

**Realization During Review:**
- Exemplars have text content → need embeddings → vectors in Qdrant
- Exemplars need semantic search → same as documents
- Exemplars need collections → same organization
- Exemplars need access control → same permissions

**Conclusion:** Exemplars are just specialized documents!

**Implementation:**
```python
# Instead of separate table:
CREATE TABLE fewshot_exemplars (...)

# Use existing infrastructure:
INSERT INTO documents (
  document_type = 'exemplar',
  metadata = '{"exemplar_type": "sigma-rule", "quality_score": 0.95}'
)
```

**Lesson:** **Before building new infrastructure, ask: "Can existing infrastructure handle this with metadata?"**

---

### **5. Orchestrator = Gateway Pattern**

**Discovery:** Orchestrator isn't just use case execution

**Dual Role:**
1. **API Gateway** - All frontend calls come here first
2. **Use Case Executor** - Orchestrates LLM + tools + RAG

**Pattern:**
```
Frontend → Orchestrator (auth/proxy) → Corpus Service
           ↓
      Use Case Execution
```

**Why This Works:**
- Single authentication point
- Centralized rate limiting
- Simplified frontend (one API URL)
- Internal services can be private
- Clean separation of concerns

**Lesson:** **Document gateway responsibilities explicitly (ADR-035)**

---

## Architectural Decisions Made

### **Decision 1: Service Rename**
**Action:** `corpus-service` → `corpus-service`
**Impact:** Docker-compose, env vars, documentation
**Benefit:** Clear naming, no more "where does X go?" questions

### **Decision 2: Feature Migration**
**Action:** Moved corpus features FROM orchestrator TO corpus
**Files:** Chunking, preflight, test suites (~2,000 lines)
**Benefit:** Proper service boundaries, self-contained services

### **Decision 3: Exemplar Simplification**
**Action:** Deleted separate exemplar infrastructure
**Replaced With:** Documents with `document_type="exemplar"`
**Benefit:** ~800 lines eliminated, reuse existing code

### **Decision 4: ADR-035 Created**
**Purpose:** Document service boundaries permanently
**Content:** Responsibilities, communication patterns, gateway role
**Benefit:** Future developers know where features belong

---

## Impact on Future Work

### **Phase 7: Async Migration**

**Easier Now:**
- Service boundaries clear
- No cross-service imports to untangle
- Each service migrates independently

**Directory Rename Planned:**
- `src/orchestrator/` → `src/orchestrator/` (matches responsibility)
- `src/corpus_svc/` → `src/corpus/` (matches service name)

### **Layer 4: Frontend Integration**

**Clearer Now:**
- Frontend calls orchestrator gateway only
- Corpus features accessed via orchestrator proxy
- No confusion about which service handles what

---

## Testing Impact

**Tests Must Match Service:**
- Corpus tests use `src.retrieval.app.*` imports (will be `src.corpus.app.*` in Phase 7)
- Orchestrator tests use `src.backend.app.*` imports
- Absolute imports for tests (prevents relative import issues)

---

## Documentation Impact

**3 ADRs Updated:**
- ADR-021: Addendum 2 - Exemplars as documents
- ADR-034: Revised exemplar storage
- ADR-035: NEW - Service boundaries

**Future ADRs Should Consider:**
- Which container will this feature run in?
- Does it cross service boundaries (requires API)?
- Can existing infrastructure handle it (avoid duplication)?

---

## Recommendations for Future Features

### **Before Implementing, Ask:**

1. **Which service?**
   - Corpus service: If it touches documents/chunks/vectors/embeddings
   - Orchestrator: If it's use case execution/policy/auth
   - Shared: If it's truly common utilities (logging, telemetry)

2. **Does infrastructure exist?**
   - Check for similar features (avoid duplication)
   - Consider metadata enrichment vs new tables
   - Prefer existing patterns

3. **Service communication?**
   - Same container: Relative imports OK
   - Different containers: HTTP API required
   - Test cross-service calls early

4. **Name clearly?**
   - Service names should reflect responsibility
   - Feature names should indicate which service
   - Document in ADRs

---

## Summary

**Time Investment:** Significant (architecture cleanup mid-implementation)
**Value Delivered:** Clean, maintainable architecture
**Code Impact:** ~2,000 lines migrated, ~800 lines eliminated
**Future Benefit:** Clear boundaries prevent similar issues

**Key Takeaway:** **Architecture reviews during implementation catch issues early. Worth the investment.**

---

**Status:** Lessons documented for future reference
**Related:** ADR-035, P4-F10 session log, MASTER_ROADMAP.md v2.5
