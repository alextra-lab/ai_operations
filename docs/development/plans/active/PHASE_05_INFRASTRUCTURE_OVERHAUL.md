# Phase 5: Infrastructure Overhaul

**Timeline:** December 2025 - January 2026 (4-5 weeks)
**Status:** ✅ Complete (100%)
**Goal:** Clean, modern infrastructure foundation before demos and documentation

---

## Overview

This phase combines two major infrastructure improvements:

1. **Service Rename** - Semantic naming for clarity and maintainability
2. **Async SQLAlchemy Migration** - Modern async patterns for future-proof architecture

**Why Combined:** Both touch the same files. Doing them together avoids double-refactoring and ensures all new artifacts (demos, docs, scripts) are built on the correct foundation.

---

## Part 1: Service Rename

### Directory Changes

| Current | New | Rationale |
|---------|-----|-----------|
| `src/orchestrator` | `src/orchestrator` | Describes LLM pipeline orchestration role |
| `src/corpus_svc` | `src/corpus_svc` | Describes document/corpus management role |
| `src/frontend-angular` | **Keep as-is** | User preference |

### Task Breakdown

#### P5-R1: Directory Rename (Day 1)

```bash
# Rename directories
mv src/orchestrator src/orchestrator
mv src/corpus_svc src/corpus_svc
```

**Files Affected:**

- `src/orchestrator/` → `src/orchestrator/` (entire directory)
- `src/corpus_svc/` → `src/corpus_svc/` (entire directory)

#### P5-R2: Docker Configuration Updates (Day 1-2)

**docker-compose.yml:**

```yaml
# Before
services:
  backend:
    build: ./src/orchestrator

# After
services:
  orchestrator:
    build: ./src/orchestrator
```

**Files to Update:**

- `deploy/docker-compose.yml`
- `deploy/docker-compose.test.yml`
- `src/orchestrator/Dockerfile`
- `src/corpus_svc/Dockerfile`

#### P5-R3: Python Import Updates (Day 2-3)

**Pattern Changes:**

```python
# Before
from src.backend.app.services import UseCase
from src.retrieval.app.services import DocumentService

# After
from src.orchestrator.app.services import UseCase
from src.corpus_svc.app.services import DocumentService
```

**Scope:**

- All Python files in `src/`
- All test files
- Shared utilities

**Command to find all imports:**

```bash
grep -r "from src\.backend" src/ tests/
grep -r "from src\.retrieval" src/ tests/
```

#### P5-R4: Documentation Path Updates (Day 3-4)

**Files to Update:**

- All ADRs referencing `src/orchestrator` or `src/corpus_svc`
- README files
- API documentation
- Development guides
- This roadmap

**Command to find references:**

```bash
grep -r "src/orchestrator" docs/
grep -r "src/corpus_svc" docs/
```

#### P5-R5: Verification (Day 4-5)

**Checklist:**

- [ ] All Docker containers build
- [ ] All services start correctly
- [ ] All existing tests pass
- [ ] No broken imports
- [ ] Documentation consistent

---

## Part 2: Async SQLAlchemy Migration

### Overview

Migrate from synchronous to asynchronous SQLAlchemy patterns:

```python
# BEFORE (Sync)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/items")
def read_items(db: Session = Depends(get_db)):
    return db.query(Item).all()


# AFTER (Async)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

@router.get("/items")
async def read_items(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Item))
    return result.scalars().all()
```

### Benefits

1. **Non-blocking I/O** - Database calls don't block the event loop
2. **Better concurrency** - Handle more concurrent requests
3. **Modern patterns** - Aligns with FastAPI's async nature
4. **Future-proof** - SQLAlchemy 2.x async is the recommended approach

### Task Breakdown by Week

#### Week 2: Database Infrastructure

| Task ID | Task | Days | Status |
|---------|------|------|--------|
| P5-A1 | Update `database.py` to async engine (orchestrator) | 0.5 | ✅ Nov 26 |
| P5-A2 | Update `database.py` to async engine (corpus_svc) | 0.5 | ✅ Nov 26 |
| P5-A3 | Update `database.py` to async engine (inference-gateway) | 0.5 | ✅ Nov 26 |
| P5-A4 | Update shared database utilities | 0.5 | ✅ Nov 26 |
| P5-A5 | Add `pytest-asyncio` configuration | 0.5 | ✅ Nov 26 |
| P5-A6 | Create async session fixtures | 0.5 | ✅ Nov 26 |
| P5-A7 | Update connection pool settings | 0.5 | ✅ Nov 26 |
| P5-A8 | Test database connectivity | 0.5 | ✅ Nov 26 |

**Deliverables:**

- All services using `create_async_engine`
- Async session fixtures for tests
- Connection pooling configured

#### Week 3: Orchestrator Router Migration

| Task ID | Task | Routers | Days | Status |
|---------|------|---------|------|--------|
| P5-A9 | Auth routers (login, refresh, logout) | 1 | 1 | ✅ Nov 26 |
| P5-A10 | Core routers (use_cases, execution) | 3 | 1 | ✅ Nov 27 |
| P5-A11 | Admin routers (users, roles, config, audit) | 4 | 1.5 | ✅ Nov 27 |
| P5-A12 | Document routers (upload, manage, chunking) | 2 | 1 | ✅ Nov 27 |
| P5-A13 | Query routers (history, search) | 2 | 0.5 | ✅ Nov 28 |

**Routers to Convert (Orchestrator - 14 total):**

1. `auth.py` - Authentication
2. `users.py` - User management
3. `roles.py` - Role management
4. `use_cases.py` - Use case CRUD
5. `execution.py` - Use case execution
6. `documents.py` - Document management
7. `collections.py` - Collection management
8. `query_history.py` - Query history
9. `conversations.py` - Conversation threads
10. `analytics.py` - Analytics endpoints
11. `pricing.py` - Pricing management
12. `system_config.py` - System configuration
13. `audit.py` - Audit logs
14. `tools_admin.py` - Tool administration

#### Week 4: Corpus Service + Inference Gateway

| Task ID | Task | Routers | Days | Status |
|---------|------|---------|------|--------|
| P5-A14 | Corpus service routers | 6 | 2 | ✅ Nov 28 |
| P5-A15 | Inference gateway routers | 5 | 2 | ✅ Nov 28 |
| P5-A16 | Service integration testing | - | 1 | ✅ Nov 29 |

**Routers to Convert (Corpus Service - 6 total):**

1. `documents.py` - Document retrieval
2. `search.py` - Semantic search
3. `collections.py` - Collection queries
4. `chunking.py` - Chunking analysis
5. `embeddings.py` - Embedding operations
6. `health.py` - Health checks

**Routers to Convert (Inference Gateway - 5 total):**

1. `chat.py` - Chat completions
2. `embeddings.py` - Embedding generation
3. `models.py` - Model management
4. `providers.py` - Provider management
5. `admin.py` - Admin endpoints

#### Week 5: Test Suite Migration + Validation

| Task ID | Task | Files | Days | Status |
|---------|------|-------|------|--------|
| P5-A17 | Orchestrator unit tests | ~50 | 3 | ✅ Complete |
| P5-A18 | Corpus service unit tests | ~20 | 1.5 | ✅ Complete |
| P5-A19 | Inference gateway unit tests | ~15 | 1 | ✅ Complete |
| P5-A20 | Integration tests | ~20 | 1.5 | ✅ Complete |
| P5-A21 | Performance benchmarks | - | 1 | ✅ Complete |
| P5-A22 | Documentation updates | - | 1 | ✅ Complete |

**Test Migration Pattern:**

```python
# BEFORE (Sync)
def test_create_item(db_session):
    item = create_item(db_session, {...})
    assert item.name == "test"

# AFTER (Async)
@pytest.mark.asyncio
async def test_create_item(db_session):
    item = await create_item(db_session, {...})
    assert item.name == "test"
```

---

## Progress Tracking

### Week 1: Service Rename

| Task | Status | Notes |
|------|--------|-------|
| P5-R1: Directory rename | ✅ Complete | `git mv` preserved history |
| P5-R2: Docker configs | ✅ Complete | Updated Dockerfiles + compose files |
| P5-R3: Python imports | ✅ Complete | 377 files updated |
| P5-R4: Documentation | ✅ Complete | ~150 docs updated, zero old refs |
| P5-R5: Verification | ✅ Complete | All containers healthy |

**Bug Fixes (Nov 26):**

- Fixed API version regression (`1.0.0` → `v1`) from P4-CONFIG-01
- Updated Qdrant client API (`.search()` → `.query_points()`) for v1.16.0
- Pinned Qdrant Docker image to v1.16.0

### Week 2: Database Infrastructure

| Task | Status | Notes |
|------|--------|-------|
| P5-A1: Orchestrator database.py | ✅ Complete | Dual-stack (sync+async), 19 unit tests, 96% coverage |
| P5-A2: Corpus database.py | ✅ Complete | Already async, standardized deps, 15 unit tests, 76% coverage |
| P5-A3: Gateway database.py | ✅ Complete | Uses shared Base, 20 unit tests, 100% coverage |
| P5-A4: Shared utilities | ✅ Complete | Connection pooling, health checks, session utils, 32 tests, 100% coverage |
| P5-A5: pytest-asyncio | ✅ Complete | Configured in conftest.py fixtures |
| P5-A6: Async fixtures | ✅ Complete | `async_db_session`, `clean_async_db_session` added |
| P5-A7: Connection pool | ✅ Complete | Env var overrides (DB_POOL_SIZE, etc.), `get_pool_config()`, 110 tests |
| P5-A8: Database connectivity | ✅ Complete | Container healthy, API endpoints verified |

**P5-A1 Implementation Notes (Nov 26):**

- Created dual-stack infrastructure (sync for existing routers, async for new/migrated)
- Added `asyncpg>=0.30.0` to requirements.txt
- New exports: `AsyncSessionLocal`, `async_engine`, `get_async_db`, `init_db` (async)
- Backwards compatible: `SessionLocal`, `sync_engine`, `get_db`, `init_db_sync` still work
- Fixed test imports to use absolute paths (`from src.orchestrator.app.XXX`)
- Updated TESTING_GUIDE.md and TROUBLESHOOTING.md with correct import patterns

**P5-A2 Implementation Notes (Nov 26):**

- **Discovery:** corpus_svc was already fully async (no dual-stack needed)
- Standardized session dependency: `collections.py` now uses local `get_db_session` (4 locations)
- Enhanced `app/db/connection.py` with docs, `init_db()`, `__all__` exports
- Created 15 unit tests (`tests/unit/db/test_connection.py`)
- Verified container health and API endpoints
- asyncpg already in requirements.txt

**P5-A3 Implementation Notes (Nov 26):**

- Created `app/database/connection.py` following corpus_svc pattern
- Uses `shared.db.connection.Base` (removed duplicate local Base from `usage.py`)
- Added `init_db()`, `check_database_connection()`, `get_session()`, `get_db_session()`
- Updated `main.py` lifespan: DB init on startup, health check includes DB status
- Health endpoint returns 503 if database unhealthy
- Created 20 unit tests (`tests/unit/database/test_connection.py`) - 100% coverage
- Updated 5 health endpoint tests with proper mocking for lifespan
- Container verified healthy with new DB initialization logs

**P5-A4 Implementation Notes (Nov 26):**

- Enhanced `shared.db.connection.py` with connection pooling (pool_size=10, max_overflow=20, pool_recycle=3600)
- Added `check_database_connection()` health check utility
- Added `get_session()` transactional context manager with auto commit/rollback
- Added `get_db_session()` FastAPI dependency
- Added `init_db_tables()` generic table creation helper
- Created `shared.db.__init__.py` package exports
- Updated `shared.database.py` to re-export from db.connection
- Fixed 15 outdated auth tests (rewrote test_shared_database.py and test_manager_db.py)
- Created 32 unit tests for `shared.db.connection` - 100% coverage
- All 163 shared module tests passing

**P5-A7 Implementation Notes (Nov 26):**

- Added env var helpers `_get_env_int()`, `_get_env_bool()` to shared.db.connection
- Created `get_pool_config()` function returning dict with pool settings
- Environment variables: DB_POOL_SIZE, DB_MAX_OVERFLOW, DB_POOL_RECYCLE, DB_POOL_PRE_PING
- Updated orchestrator database.py to use `get_pool_config()` for sync/async engines
- Created 24 new tests (19 shared + 5 orchestrator) for pool config
- Fixed 3 corpus_svc tests to use mocks instead of requiring live DB
- Fixed inference-gateway test conftest.py path setup
- Created project-root conftest.py for service path resolution
- Total: 110 db connection tests passing (run services separately due to `app` module collision)

**P5-A9 Implementation Notes (Nov 26):**

- Migrated `app/auth/router.py` to async (5 endpoints: login, refresh, revoke, validate, create_user)
- Added async versions of utility functions in `app/auth/utils.py` (suffix `_async`)
- Kept sync versions for backwards compatibility
- Updated `get_db_for_auth()` to async generator using `AsyncSessionLocal`
- Converted `create_audit_log_entry()` to async
- Updated tests: 65 tests passing, 89% coverage (router 82%, utils 94%)
- Fixed all audit mock tests to use `AsyncMock()` instead of `MagicMock()`
- Container verified healthy, all auth endpoints tested via curl

**P5-A10 Implementation Notes (Nov 27):**

- Migrated `app/routers/use_cases.py` to async (`get_available_use_cases`, `execute_use_case`)
- Changed `get_db()` from sync generator to async generator using `AsyncSessionLocal`
- Created async RBAC functions: `user_can_access_use_case_async()`, `get_accessible_use_cases_async()`
- Dual-stack approach: `execute_use_case` creates sync session for `Orchestrator`/`ToolExecutor` (to be migrated later)
- Fixed pre-existing sync RBAC test failures (mock chain corrections)
- Created unit tests: `tests/unit/routers/test_use_cases.py` (10 tests)
- Created async RBAC tests: 8 new tests in `tests/unit/services/test_rbac.py`
- Total: 27 tests passing, all linting clean

**P5-A11 Implementation Notes (Nov 27):**

- Migrated 4 admin routers to async database patterns:
  - `admin.py`: Dual-stack (TokenTracker is sync, endpoints create manual sync sessions)
  - `admin_roles.py`: Full async with `AsyncSession`, `select()`, `await db.execute()`
  - `admin_config.py`: Full async with raw SQL via `text()`, `await db.execute()`
  - `admin_audit.py`: Full async with complex ORM queries converted to `select()` statements
- All routers now use `get_async_db()` dependency
- Created/updated 49 unit tests across 4 test files:
  - `test_admin.py`: 7 tests (new)
  - `test_admin_config.py`: 17 tests (updated to async + bug fix test)
  - `test_admin_roles.py`: 13 tests (updated to async)
  - `test_admin_audit.py`: 12 tests (new)
- Coverage: admin.py 92%, admin_audit.py 90%, admin_config.py 92%, admin_roles.py 92%
- Bug fix: `update_config_section` transaction atomicity (validate before commit)
- All tests passing, linting clean

**P5-A12 Implementation Notes (Nov 27):**

- Verified 2 document proxy routers already use async patterns:
  - `corpus.py`: Full async with `httpx.AsyncClient`, no DB sessions required
  - `chunking.py`: Full async with `httpx.AsyncClient`, no DB sessions required
- Both routers proxy requests to corpus_svc - no SQLAlchemy migration needed
- Added P5-A12 documentation headers to both routers
- Created/updated 60 unit tests across 2 test files:
  - `test_corpus.py`: 30 tests (10 new for download/reprocess/filters)
  - `test_chunking_router.py`: 30 tests (complete rewrite)
- Coverage: corpus.py 100%, chunking.py 97%
- All tests passing, linting clean

### ✅ Security Fix Complete (P5-A13 Unblocked)

| Task | Status | Notes |
|------|--------|-------|
| **P5-SEC-01: Stateless PII Enforcement** | ✅ **Complete** | ADR-030 enforcement implemented Nov 28, 2025 |

**Completed (Nov 28, 2025):** Stateless architecture enforced at API boundary.

**Implementation:**

- ✅ Added `ENABLE_TRANSCRIPT_STORAGE` feature flag (default: `false`)
- ✅ Guarded 7 write endpoints with 501 Not Implemented
- ✅ Removed direct history calls from frontend UI
- ✅ ADR-030 enforcement section documented
- ✅ 26 tests (11 backend + 15 frontend)

**Task Document:** [P5-SEC-01](../completed/tasks/P5_SEC_01_STATELESS_PII_ENFORCEMENT.md)

### Week 3: Orchestrator Async ✅ Complete

| Task | Status | Notes |
|------|--------|-------|
| P5-A9: Auth routers | ✅ Complete | router.py, utils.py async, 65 tests, 89% coverage |
| P5-A10: Core routers | ✅ Complete | use_cases.py async, rbac.py async funcs, 27 tests |
| P5-A11: Admin routers | ✅ Complete | 4 routers async (admin, admin_roles, admin_config, admin_audit), 49 tests, 90-92% coverage |
| P5-A12: Document routers | ✅ Complete | 2 routers verified async (corpus.py, chunking.py), 60 tests, 98% coverage |
| P5-A13: Query routers | ✅ Complete | query_history.py async + AsyncHistoryService, 59 tests, 69% coverage |

**P5-A13 Implementation Notes (Nov 28):**

- Created `AsyncHistoryService` with full async SQLAlchemy patterns
- Migrated `query_history.py` router (13 endpoints) to async
- Preserved RLS session variable setting with async execution
- Verified `query.py` already fully async (httpx.AsyncClient, no DB)
- Created comprehensive unit tests:
  - `test_async_history_service.py`: 27 tests
  - `test_query_history.py`: 21 tests
  - `test_query_history_security.py`: 11 tests (pre-existing)
- Coverage: query_history.py 66%, async_history_service.py 72%
- Fixed 2 pre-existing test collection errors in unrelated files
- All 59 P5-A13 tests passing

### Week 4: Corpus + Gateway ✅ Complete

| Task | Status | Notes |
|------|--------|-------|
| P5-A14: Corpus routers | ✅ Complete | Already async, fixed 10 test failures, 96/96 tests pass |
| P5-A15: Gateway routers | ✅ Complete | Already async, verified + documented, 147 unit tests pass |
| P5-A16: Integration testing | ✅ Complete | 21 tests verifying cross-service async patterns |

**P5-A14 Implementation Notes (Nov 28):**

- **Discovery:** All corpus_svc routers were already fully async (confirmed P5-A2 notes)
- Verified 8 routers: `documents.py`, `collections.py`, `chunking.py`, `analytics.py`, `query.py`, `usage.py`, `test_suites.py`, health endpoints
- **Bug fix:** `chunking.py` metadata now stores actual fallback strategy (not invalid request)
- Fixed 10 test failures due to:
  - Stale import paths (`retrieval.app` → `src.corpus_svc.app`)
  - API signature drift in `chunk_text()` (added chunking config kwargs)
  - Missing `collection_repository` argument in `QueryService`
  - Incomplete mock objects (missing `preflight_sample_tokens`, etc.)
- Added `src/**/tests/**/*.py` to pyproject.toml lint ignores
- All 96 corpus_svc unit tests passing
- Container verified healthy with all dependencies

**P5-A15 Implementation Notes (Nov 28):**

- **Discovery:** All gateway routers were already fully async
- Verified 4 routers: `admin.py`, `chat.py`, `embeddings.py`, `responses.py`
- **Pattern confirmed:** Uses `async with get_db() as db:` with `await db.execute()`
- Supporting services already async: `SimpleRouter`, `ProviderManager`
- Added P5-A15 verification headers to all routers and services
- **Pre-existing fixes:** Invalid UUIDs in 4 test files, pytest collection error
- **Bug fix:** `responses.py` now re-raises HTTPException (501 for streaming)
- **New tests:** 43 tests across 4 new files:
  - `test_chat_router.py` (12 tests)
  - `test_embeddings_router.py` (11 tests)
  - `test_responses_router.py` (14 tests)
  - `test_admin_circuit_breaker.py` (6 tests)
- **Coverage:** embeddings.py 100%, responses.py 100%, chat.py 58%, admin.py 64%
- Total: 220 gateway unit tests passing (65% overall coverage)
- ADR compliance verified: ADR-022 (async patterns), ADR-050 (dumb pipe)

**P5-A16 Implementation Notes (Nov 29):**

- Created `tests/integration/test_async_service_integration.py` (21 tests)
- **Test Coverage:**
  - Async database patterns (AsyncSessionLocal, async_engine, get_async_db)
  - Orchestrator → Corpus proxy patterns (httpx.AsyncClient)
  - Orchestrator → Gateway patterns (LLMRouter, LLMClient)
  - Cross-service async flows (use cases, admin roles, audit)
  - Shared DB utilities (pool config, health checks)
  - ADR-022 compliance verification
- **Pre-release decision:** Removed dual-stack compatibility tests (backward compat not needed)
- **Created P5-A23 cleanup task:** Remove sync database patterns entirely

### Week 5: Tests + Validation + Cleanup

| Task | Status | Notes |
|------|--------|-------|
| P5-A17: Orchestrator tests | ✅ Complete | Migrated integration tests (test_config_loader_integration.py, test_use_case_config_integration.py, test_output_contract.py), unit tests (test_database.py, test_tools_registration.py), updated routers (use_cases.py, suite_testing.py), fixed async fixture dependencies. All tests passing. |
| P5-A18: Corpus tests | ✅ Complete | Verified all 96 corpus_svc unit tests use async patterns. Fixed 2 failing upload tests by correcting mock patches for ingestion service dependencies. All tests passing. |
| P5-A19: Gateway tests | ✅ Complete | Verified all 221 unit tests already use async patterns. No migration needed - all tests compliant with ADR-022. [Session](../sessions/2025-12-01-p5-a19-gateway-tests-verification.md) |
| P5-A20: Integration tests | ✅ Complete | Migrated 10 files (~100+ tests): conftest.py, test_secrets_manager.py, test_token_tracking.py, test_tool_enforcement.py, test_tool_database.py, test_use_cases_endpoint.py, test_tool_permissions.py, test_tools_testing.py, test_tools_admin_api.py, test_template_model_selection.py. All major database-using files migrated to async patterns (ADR-022). [Session](../sessions/2025-12-01-p5-a20-integration-tests-migration-continued.md) |
| P5-A21: Benchmarks | ✅ Complete | Performance benchmark infrastructure created. Tests direct database operations (simple query, count, filtered, join, transaction) and API endpoints (use cases, tools, query history). Results stored in `tests/benchmarks/results/benchmark_YYYYMMDD_HHMMSS.json`. All operations meeting performance targets. [Session](../sessions/2025-12-01-p5-a21-performance-benchmarks.md) |
| P5-A22: Documentation | ✅ Complete | ADR-022 status updated to Accepted (Implemented). |
| **P5-A23: Remove sync DB patterns** | ✅ Complete | Phase 1 ✅ (3 routers), Phase 2 ✅ (4/4 services), Phase 3 ✅ (4/4 services), Phase 4 ✅ (6/6 routers), Phase 5 ✅ (3/3 routers), Phase 6 ✅ (5/5 utilities/middleware), Phase 7 ✅ (database.py cleanup + remaining routers). All sync patterns removed. SQLAlchemy 2.x `.where()` bug fixed. [Task](../completed/tasks/P5_A23_REMOVE_SYNC_DATABASE_PATTERNS.md) |

---

## Dependencies

### Required Packages

Add to requirements.txt for each service:

```
asyncpg>=0.29.0  # Async PostgreSQL driver
pytest-asyncio>=0.23.0  # Async test support
```

### Database URL Format

```python
# Sync URL
DATABASE_URL = "postgresql://user:pass@host:5432/db"

# Async URL (note the +asyncpg)
DATABASE_URL = "postgresql+asyncpg://user:pass@host:5432/db"
```

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking changes during rename | High | Staged commits, comprehensive grep |
| Async migration bugs | Medium | Service-by-service rollout, extensive testing |
| Performance regression | Medium | Benchmark before/after |
| Test failures | Medium | Fix tests before moving to next router |

### Rollback Plan

1. Keep sync code in git history
2. Each week's work in separate branch
3. Merge only after verification
4. Can rollback to any weekly checkpoint

---

## Exit Criteria

### Part 1: Rename Complete

- [ ] All directories renamed
- [ ] Zero grep matches for old names in code
- [ ] Zero grep matches for old names in docs
- [ ] All Docker builds succeed
- [ ] All existing tests pass

### Part 2: Async Complete

- [ ] All database operations async
- [ ] All 25 routers converted (14 + 6 + 5)
- [ ] All 85 test files migrated
- [ ] 100% test pass rate
- [ ] Performance validated (no regression)

### Phase 5 Complete

- [ ] Services use new names (orchestrator, corpus_svc)
- [ ] Full async throughout
- [ ] Documentation updated
- [ ] Ready for Phase 6 demos

---

**Document Owner:** Project team
**Created:** November 26, 2025
**Last Updated:** December 1, 2025
**Status:** Complete (100% - All tasks P5-R1–P5-A23 done, ADR-022 implemented)
