# ADR-022: Backend Database Session Migration to Async SQLAlchemy

**Status:** Accepted (Implemented in Phase 5, P5-A17–P5-A23)
**Date:** October 18, 2025
**Deciders:** Architecture Team, Backend Lead
**Tags:** database, async, sqlalchemy, architecture, refactoring

---

## Context

### Current State: Mixed Database Session Patterns

AI Operations Platform currently uses **inconsistent database session patterns** across services:

| Service | Pattern | Driver | Session Type | Query Style |
|---------|---------|--------|--------------|-------------|
| **Backend/Orchestrator** | SYNC | `postgresql+psycopg` | `Session` | `db.query(Model).filter().all()` |
| **Retrieval Service** | ASYNC | `postgresql+asyncpg` | `AsyncSession` | `await db.execute(select(Model))` |
| **Shared Auth Module** | ASYNC | `postgresql+asyncpg` | `AsyncSession` | `await db.execute(select(Model))` |

### Problem Statement

**The backend service is the ONLY component still using synchronous SQLAlchemy**, creating:

1. **Developer Confusion**
   - New developers must remember different patterns for different services
   - Recent `prompt_patterns.py` router created with async pattern by mistake
   - No clear documentation on why backend differs from other services

2. **Performance Limitations**
   - Synchronous operations block FastAPI thread pool (default 40 threads)
   - Under high concurrency, requests queue waiting for available threads
   - Connection pool pressure from long-held connections during blocking I/O
   - Suboptimal for SOC workflows with multiple concurrent analysts + automation engines

3. **Architectural Debt**
   - Each backend router defines its own `get_db()` function (code duplication)
   - Cannot leverage shared database infrastructure from `src/shared/db/connection.py`
   - Inconsistency complicates maintenance and onboarding

4. **Scalability Constraints**
   - Air-gapped deployments have limited resources
   - Thread-based concurrency less efficient than event loop for I/O-bound operations
   - Cannot handle burst traffic during security incidents as efficiently as async

### Technical Background

**Current Backend Pattern:**

```python
# src/orchestrator/app/db/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(connection_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():  # Synchronous generator
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# src/orchestrator/app/routers/use_case_management.py
async def list_use_cases(
    db: Session = Depends(get_db),  # Sync Session in async function
):
    use_cases = db.query(DBUseCase).filter(...).all()  # Blocks thread!
    return UseCaseListResponse(use_cases=use_cases)
```

**How This Works:**

- FastAPI detects synchronous database operations in `async def` functions
- Runs them in `run_in_threadpool` executor (thread pool with 40 workers)
- Each database operation blocks ONE thread until complete
- Works adequately for moderate load but doesn't scale well

**Existing Async Pattern (Retrieval & Auth):**

```python
# src/shared/db/connection.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

engine = create_async_engine(database_url, pool_pre_ping=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_async_session():
    async with async_session() as session:
        yield session

# src/corpus_svc/app/routers/documents.py
async def list_documents(
    db: AsyncSession = Depends(get_async_session),  # Async Session
):
    result = await db.execute(select(Document).where(...))  # Non-blocking!
    documents = result.scalars().all()
    return DocumentListResponse(documents=documents)
```

### Forces at Play

**Technical Forces:**

- FastAPI best practices recommend async for I/O operations
- SQLAlchemy 2.0+ fully supports async with mature APIs
- Industry trend toward async-first microservices
- Connection pooling more efficient with async (connections released during `await`)

**Business Forces:**

- SOC operations require high concurrency (multiple analysts + automation)
- Air-gapped deployments have resource constraints
- Real-time workflows (WebSockets, streaming) already require async
- Future scalability for enterprise deployments

**Organizational Forces:**

- Development team familiar with sync patterns
- Extensive test suite exists for current sync implementation
- Active development on UI and Tools - don't want to disrupt
- Migration window needed when features are stable

---

## Decision

**We will migrate the backend service to asynchronous SQLAlchemy** following the async pattern already established in Retrieval Service and Shared Auth Module.

### Migration Approach

**Strategy:** Big Bang Migration (all routers at once)
**Timing:** Phase 7 - After UI Development (Phases 1-6) and Tools Implementation complete
**Pattern Source:** Leverage `src/shared/db/connection.py` infrastructure
**Duration:** 3-4 days dedicated sprint

### Core Changes

1. **Database Layer** (`src/orchestrator/app/db/database.py`)
   - Replace `create_engine` with `create_async_engine`
   - Replace `sessionmaker` with `async_sessionmaker`
   - Update `get_db()` to async generator returning `AsyncSession`
   - Change driver from `postgresql+psycopg` to `postgresql+asyncpg`

2. **All Routers** (12+ files)
   - Change `Session` to `AsyncSession` in dependencies
   - Transform `db.query(Model)` to `select(Model)` with `await db.execute()`
   - Add `await` to `db.commit()`, `db.refresh()`, `db.rollback()`
   - Update all database operations to async pattern

3. **Middleware** (RLS, Audit, Sanitization)
   - Verify compatibility with AsyncSession
   - Update RLS session variable setting if needed
   - Ensure audit logging works with async sessions

4. **Tests** (50+ files)
   - Update pytest fixtures to use async patterns
   - Add `pytest-asyncio` markers
   - Convert all test database operations to async
   - Create shared async test fixtures

### Implementation Principles

1. **Leverage Existing Infrastructure**
   - Use `shared.db.connection` module (already proven in Retrieval Service)
   - Don't reinvent async database patterns
   - Consistent with rest of codebase

2. **Comprehensive Testing**
   - Create regression test suite BEFORE migration
   - Test each router individually during migration
   - Full integration tests before deployment
   - Performance benchmarking to validate improvements

3. **Safe Rollback Capability**
   - Git tag before migration
   - Docker image versioning
   - Blue-green deployment option
   - Documented rollback procedure

---

## Alternatives Considered

### Option 1: Keep Synchronous Pattern (Status Quo)

**Description:**
Continue using synchronous SQLAlchemy in backend indefinitely. Accept architectural inconsistency.

**Pros:**

- No migration effort required
- No risk of breaking existing functionality
- Team already familiar with pattern
- Works adequately for current load

**Cons:**

- Performance limitations persist
- Developer confusion continues
- Architectural debt compounds
- Inconsistency with other services
- Harder to scale for future

**Why Rejected:**
Short-term convenience vs. long-term technical health. The inconsistency already caused developer errors (prompt_patterns.py). As the system grows, this debt will become harder to pay.

### Option 2: Incremental Migration (Router by Router)

**Description:**
Migrate one router at a time over several weeks while maintaining both patterns.

**Pros:**

- Lower risk per change
- Easier to rollback individual routers
- Gradual team learning
- Can validate each step

**Cons:**

- Prolonged period with mixed patterns
- Increased confusion during migration
- More complex to test (two patterns coexisting)
- Requires maintaining both database connection types
- Longer total calendar time

**Why Rejected:**
Mixed patterns already cause confusion. Having BOTH sync and async patterns simultaneously would worsen the problem. Better to migrate decisively in a dedicated sprint.

### Option 3: Create Abstraction Layer

**Description:**
Create an abstraction layer that works with both sync and async, allowing gradual migration without breaking changes.

**Pros:**

- No breaking changes
- Flexibility in migration timeline
- Team can learn gradually
- Rollback trivial

**Cons:**

- Significant complexity in abstraction layer
- Performance overhead from abstraction
- Still results in mixed patterns under the hood
- More code to maintain long-term
- Doesn't solve architectural inconsistency

**Why Rejected:**
Over-engineering. The problem is not complex enough to warrant an abstraction layer. Clean, direct async implementation is simpler and more maintainable.

### Option 4: Migrate Other Services to Sync

**Description:**
Instead of migrating backend to async, migrate Retrieval and Auth to sync for consistency.

**Pros:**

- Backend stays unchanged
- Consistency achieved through sync pattern
- Simpler code (no async/await)

**Cons:**

- Regresses performance of Retrieval Service (which has heavy I/O)
- Breaks existing proven async patterns
- Goes against FastAPI and SQLAlchemy best practices
- Wrong direction for modern Python applications
- Would require rewriting 2 services instead of 1

**Why Rejected:**
Moving backward. Async is the correct pattern for I/O-heavy microservices. Retrieval Service NEEDS async for performance. Forcing it to sync would degrade system performance.

---

## Consequences

### Positive Consequences

**Architectural Consistency:**

- All services use same async database pattern
- Single source of truth for database connection (shared.db.connection)
- New developers learn one pattern, not three
- Code reviews easier with consistent patterns

**Performance Improvements:**

- Better connection pool utilization (connections released during `await`)
- Event loop handles thousands of concurrent requests vs. 40 threads
- Reduced latency under high load
- More efficient resource usage in air-gapped deployments

**Future-Proofing:**

- Aligns with FastAPI + SQLAlchemy best practices
- Easier to add WebSocket and streaming features
- Better foundation for horizontal scaling
- Industry-standard async-first architecture

**Code Quality:**

- Eliminate duplicated `get_db()` functions across routers
- Leverage shared database infrastructure
- More maintainable long-term

### Negative Consequences

**Migration Effort:**

- 3-4 days dedicated development time
- 12+ router files require modification
- 50+ test files need updates
- Documentation updates required

**Breaking Changes:**

- All existing backend tests must be updated
- pytest fixtures need async patterns
- Integration tests require async setup
- Performance benchmarks need new baselines

**Learning Curve:**

- Team must understand async/await patterns
- Different error handling (async exceptions)
- Debugging async code has different tools/techniques
- `select()` statement construction vs. `query()` method

**Risk of Regression:**

- Extensive testing needed to ensure no functionality breaks
- Potential for subtle async bugs (race conditions, improper await)
- Database transactions must be carefully reviewed
- RLS middleware needs special validation

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Breaking existing functionality** | HIGH | Comprehensive regression test suite before migration; test each router individually; full integration tests |
| **Performance degradation** | MEDIUM | Benchmark before/after; load testing; gradual rollout with monitoring |
| **Async bugs (race conditions)** | MEDIUM | Code review focused on async patterns; use async linters; thorough testing |
| **RLS middleware incompatibility** | MEDIUM | Dedicated testing for RLS session variables with async; manual verification |
| **Test suite failures** | HIGH | Update tests incrementally alongside router changes; shared async fixtures |
| **Deployment issues** | MEDIUM | Blue-green deployment; quick rollback capability; staged rollout |
| **Documentation drift** | LOW | Update docs alongside code; ADR captures decision rationale |

---

## Implementation Notes

### Phase Sequencing

**This migration is scheduled for Phase 7** - after core features stabilize:

```
Phase 1-2: Angular UI Foundation ✅ COMPLETE
Phase 3: Use Case Management & Pattern Library 🔄 IN PROGRESS
Phase 4-6: Advanced UI Features, Security, Performance ⏸️ PENDING
Tools Implementation: T1-T4 (MCP Integration) ⏸️ PENDING
Phase 7: Backend Async Migration 📋 THIS ADR
```

**Rationale for Timing:**

- UI development may require new backend endpoints - don't migrate during active feature development
- Tools implementation adds complexity to orchestrator - stabilize first
- Stable feature set allows comprehensive regression testing
- Prevents "moving target" scenario

### Files Requiring Modification

**Core Database Layer (1 file):**

- `src/orchestrator/app/db/database.py` - engine, sessionmaker, get_db()

**Routers (14 files):**

- `src/orchestrator/app/routers/admin.py`
- `src/orchestrator/app/routers/admin_pricing.py`
- `src/orchestrator/app/routers/collection_management.py`
- `src/orchestrator/app/routers/corpus.py`
- `src/orchestrator/app/routers/health.py`
- `src/orchestrator/app/routers/models.py`
- `src/orchestrator/app/routers/orchestrator.py`
- `src/orchestrator/app/routers/prompt_patterns.py`
- `src/orchestrator/app/routers/query.py`
- `src/orchestrator/app/routers/query_history.py`
- `src/orchestrator/app/routers/security.py`
- `src/orchestrator/app/routers/templates.py`
- `src/orchestrator/app/routers/token_analytics.py`
- `src/orchestrator/app/routers/use_case_management.py`
- `src/orchestrator/app/routers/use_cases.py`

**Middleware (4 files - verify compatibility):**

- `src/orchestrator/app/middleware/audit.py`
- `src/orchestrator/app/middleware/rls.py` ⚠️ Special attention needed
- `src/orchestrator/app/middleware/sanitization.py`
- `src/orchestrator/app/middleware/security_headers.py`

**Tests (50+ files):**

- All files in `src/orchestrator/tests/unit/`
- All files in `src/orchestrator/tests/integration/`
- Shared test fixtures in `tests/fixtures/`

**Configuration:**

- `src/orchestrator/requirements.txt` - add `asyncpg`
- `config/env/*.template` - update DATABASE_URL examples
- Docker environment files - update connection strings

### Dependencies

**Required:**

- `asyncpg>=0.30.0` - PostgreSQL async driver
- `sqlalchemy>=2.0.0` - Already installed, verify async support
- `pytest-asyncio>=0.23.0` - For async test support

**Optional:**

- Consider removing `psycopg` if no longer needed (check dependencies)

### Migration Pattern Reference

**Use existing pattern from `src/shared/db/connection.py`:**

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

def get_async_engine(database_url: str):
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=10,
        max_overflow=20,
        echo=False,
        future=True
    )

def get_async_sessionmaker(engine):
    return async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession
    )

async def get_async_session():
    async with async_session() as session:
        yield session
```

### Query Transformation Examples

**Before (Sync):**

```python
# Read
use_cases = db.query(DBUseCase).filter(DBUseCase.category == "security").all()
count = db.query(DBUseCase).count()
item = db.query(DBUseCase).filter(DBUseCase.id == id).first()

# Write
db.add(new_use_case)
db.commit()
db.refresh(new_use_case)

# Update
use_case.is_active = True
db.commit()
```

**After (Async):**

```python
# Read
result = await db.execute(select(DBUseCase).where(DBUseCase.category == "security"))
use_cases = result.scalars().all()

count_result = await db.execute(select(func.count()).select_from(DBUseCase))
count = count_result.scalar_one()

result = await db.execute(select(DBUseCase).where(DBUseCase.id == id))
item = result.scalar_one_or_none()

# Write
db.add(new_use_case)
await db.commit()
await db.refresh(new_use_case)

# Update
use_case.is_active = True
await db.commit()
```

### Testing Strategy

**Pre-Migration:**

1. Create comprehensive regression test suite
2. Document all current API behaviors
3. Establish performance baselines
4. Capture database query patterns

**During Migration:**

1. Update database.py first
2. Migrate one router at a time (while tests fail)
3. Update corresponding tests immediately after each router
4. Run integration tests after each router completion

**Post-Migration:**

1. Full test suite pass (unit + integration)
2. Performance benchmarking (compare to baseline)
3. Load testing (verify concurrency improvements)
4. Manual E2E testing of critical workflows

---

## References

**Related Documentation:**

- `src/shared/db/connection.py` - Reference async pattern implementation
- `src/corpus_svc/app/routers/` - Examples of async routers
- `docs/development/plans/BACKEND_ASYNC_MIGRATION_PLAN.md` - Detailed implementation plan
- `docs/development/plans/UI_DEVELOPMENT_PLAN.md` - Phase 7 integration

**External Resources:**

- [SQLAlchemy 2.0 Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [FastAPI with Async SQLAlchemy](https://fastapi.tiangolo.com/advanced/async-sql-databases/)
- [asyncpg Driver Documentation](https://magicstack.github.io/asyncpg/)

**Related ADRs:**

- ADR-018: Use Case Owned Architecture (backend routers)
- ADR-016: Dynamic Intent System (orchestrator patterns)

---

## Implementation Plan

See detailed implementation plan:
**`docs/development/plans/BACKEND_ASYNC_MIGRATION_PLAN.md`**

Includes:

- File-by-file migration checklist
- Query transformation patterns
- Test migration strategy
- Performance benchmarking approach
- Rollback procedures
- Risk mitigation details

---

## Status Updates

### 2025-10-18 - Proposed

**Changed By:** AI Assistant
**Reason:** Discovered architectural inconsistency during Pattern Library implementation. Backend is only service still using sync SQLAlchemy, causing developer confusion and performance limitations.

**Next Steps:**

1. Create detailed implementation plan
2. Review with architecture team
3. Schedule for Phase 7 (after UI + Tools complete)
4. Get stakeholder approval

---

**Template Version:** 1.0
**Based On:** [Michael Nygard's ADR pattern](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
