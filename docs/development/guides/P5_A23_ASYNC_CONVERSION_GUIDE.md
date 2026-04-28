# P5-A23: Async Database Conversion Guide

**Purpose:** Step-by-step instructions for converting the orchestrator service from sync to async SQLAlchemy patterns.
**ADR Reference:** ADR-022 (Backend Async Database Migration)
**Created:** November 29, 2025
**Status:** Reference Guide for Implementation

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Conversion Patterns Reference](#2-conversion-patterns-reference)
3. [File Inventory](#3-file-inventory)
4. [Conversion Order](#4-conversion-order)
5. [Detailed Instructions by File](#5-detailed-instructions-by-file)
6. [Verification Steps](#6-verification-steps)
7. [Common Pitfalls](#7-common-pitfalls)

---

## 1. Prerequisites

### Required Knowledge

- SQLAlchemy 2.0 async patterns
- FastAPI async dependencies
- Python async/await syntax

### Files That Are ALREADY Async (Do Not Modify)

These routers were converted in P5-A9 through P5-A13:

- `admin_audit.py` - ✅ Fully async
- `admin_config.py` - ✅ Fully async
- `admin_roles.py` - ✅ Fully async
- `query_history.py` - ✅ Fully async (uses AsyncHistoryService)
- `auth/router.py` - ✅ Fully async

### Shared Module Location

All database utilities should be imported from:

```python
from ..db.database import get_async_db, AsyncSessionLocal
```

---

## 2. Conversion Patterns Reference

### 2.1 Import Changes

**REMOVE these imports:**

```python
from collections.abc import Generator
from sqlalchemy.orm import Session
from ..db.database import SessionLocal
```

**ADD these imports:**

```python
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.database import get_async_db
```

### 2.2 Remove Local get_db() Definition

**DELETE this pattern (found in many routers):**

```python
def get_db() -> Generator[Session, None, None]:
    """Database dependency for API routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 2.3 Function Signature Changes

**BEFORE:**

```python
async def my_endpoint(
    db: Session = Depends(get_db),
    ...
):
```

**AFTER:**

```python
async def my_endpoint(
    db: AsyncSession = Depends(get_async_db),
    ...
):
```

### 2.4 Query Pattern Conversions

#### Simple Query → Select

```python
# BEFORE
item = db.query(Model).filter(Model.id == item_id).first()

# AFTER
stmt = select(Model).where(Model.id == item_id)
result = await db.execute(stmt)
item = result.scalar_one_or_none()
```

#### Query All → Select All

```python
# BEFORE
items = db.query(Model).filter(Model.active == True).all()

# AFTER
stmt = select(Model).where(Model.active == True)
result = await db.execute(stmt)
items = result.scalars().all()
```

#### Count Query

```python
# BEFORE
count = db.query(Model).filter(Model.active == True).count()

# AFTER
stmt = select(func.count()).select_from(Model).where(Model.active == True)
result = await db.execute(stmt)
count = result.scalar() or 0
```

#### Complex Query with Joins

```python
# BEFORE
results = (
    db.query(Model)
    .join(OtherModel)
    .filter(Model.id == item_id)
    .order_by(Model.created_at.desc())
    .offset(offset)
    .limit(limit)
    .all()
)

# AFTER
stmt = (
    select(Model)
    .join(OtherModel)
    .where(Model.id == item_id)
    .order_by(Model.created_at.desc())
    .offset(offset)
    .limit(limit)
)
result = await db.execute(stmt)
results = result.scalars().all()
```

### 2.5 Write Operation Conversions

#### Create/Add

```python
# BEFORE
db.add(new_item)
db.commit()
db.refresh(new_item)

# AFTER
db.add(new_item)
await db.commit()
await db.refresh(new_item)
```

#### Update (in-place)

```python
# BEFORE
item.name = new_name
db.commit()
db.refresh(item)

# AFTER
item.name = new_name
await db.commit()
await db.refresh(item)
```

#### Bulk Update

```python
# BEFORE
db.query(Model).filter(Model.category == cat).update({"active": False})
db.commit()

# AFTER
stmt = update(Model).where(Model.category == cat).values(active=False)
await db.execute(stmt)
await db.commit()
```

#### Delete

```python
# BEFORE
db.delete(item)
db.commit()

# AFTER
await db.delete(item)
await db.commit()
```

#### Bulk Delete

```python
# BEFORE
db.query(Model).filter(Model.expired == True).delete()
db.commit()

# AFTER
stmt = delete(Model).where(Model.expired == True)
await db.execute(stmt)
await db.commit()
```

### 2.6 Error Handling

```python
# BEFORE
try:
    db.add(item)
    db.commit()
except Exception as e:
    db.rollback()
    raise

# AFTER
try:
    db.add(item)
    await db.commit()
except Exception as e:
    await db.rollback()
    raise
```

### 2.7 Service Class Changes

**BEFORE:**

```python
class MyService:
    def __init__(self, db: Session):
        self.db = db

    def get_item(self, item_id: str) -> Model | None:
        return self.db.query(Model).filter(Model.id == item_id).first()
```

**AFTER:**

```python
class MyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_item(self, item_id: str) -> Model | None:
        stmt = select(Model).where(Model.id == item_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
```

---

## 3. File Inventory

### 3.1 Routers Requiring Conversion (12 files)

| File | Has Local get_db | Imports SessionLocal | Priority |
|------|------------------|---------------------|----------|
| `templates.py` | ✅ | ✅ | Medium |
| `tools_analytics.py` | ✅ | ✅ | Low |
| `use_case_management.py` | ✅ | ✅ | High |
| `models.py` | ✅ | ✅ | Medium |
| `tools_developer.py` | ✅ | ✅ | Medium |
| `tools_admin.py` | ✅ | ✅ | Medium |
| `tools_registration.py` | ✅ | ✅ | Medium |
| `tools_health.py` | ✅ | ✅ | Medium |
| `tools_testing.py` | ✅ | ✅ | Medium |
| `orchestrator.py` | ✅ | ✅ | High |
| `use_case_validation.py` | ✅ | ✅ | High |
| `use_cases.py` | ✅ (partial) | ✅ | High |

### 3.2 Routers Importing get_db from database.py (8 files)

These import get_db but don't define local versions:

| File | Notes |
|------|-------|
| `run_manifests.py` | Mixed - uses both get_db and AsyncSession |
| `token_analytics.py` | Uses sync Session |
| `admin_pricing.py` | Uses sync Session |
| `health.py` | Uses sync get_db |
| `suite_testing.py` | Uses sync Session |
| `prompt_patterns.py` | Uses sync get_db |
| `capabilities.py` | May be mixed |
| `summaries.py` | May be mixed |
| `admin.py` | Uses SessionLocal |

### 3.3 Services Requiring Conversion (16 files)

| Service | Used By Routers | Complexity |
|---------|-----------------|------------|
| `tool_service.py` | tools_admin, tools_developer | Medium |
| `tool_permission_service.py` | tools_admin, tools_developer | Medium |
| `secrets_manager.py` | tools_admin | Medium |
| `model_registry_service.py` | models, orchestrator | High |
| `tool_registration_service.py` | tools_registration | High |
| `tool_discovery_service.py` | tools_admin | Medium |
| `tool_health_monitor.py` | tools_health | Medium (partial async) |
| `tool_executor.py` | tools_testing, use_cases | High (partial async) |
| `token_tracker.py` | admin, token_analytics | Medium |
| `history_service.py` | query_history | Already async version exists |
| `pricing_history_service.py` | admin_pricing | Medium |
| `telemetry_service.py` | various | Medium |
| `telemetry_integration_service.py` | various | Medium |
| `use_case_config_loader.py` | orchestrator, use_cases | Low |
| `suite_testing_service.py` | suite_testing | Medium |
| `run_manifest_service.py` | run_manifests | Medium |

### 3.4 Middleware (2 files)

| File | Issue |
|------|-------|
| `audit.py` | Imports SessionLocal |
| `rls.py` | Imports SessionLocal |

### 3.5 Utilities (2 files)

| File | Issue |
|------|-------|
| `llm/template_loader.py` | Uses Session |
| `utils/cost_estimator.py` | Uses Session |

### 3.6 Auth Module (2 files)

| File | Status |
|------|--------|
| `auth/router.py` | Partially async - has get_db_for_auth (async) |
| `auth/utils.py` | Has sync get_db and sync helper functions |

---

## 4. Conversion Order

Execute in this order to avoid breaking dependencies:

### Phase 1: Utilities (No Service Dependencies)

1. `utils/cost_estimator.py`
2. `llm/template_loader.py`

### Phase 2: Base Services (No Service Dependencies)

3. `services/tool_service.py`
4. `services/tool_permission_service.py`
5. `services/secrets_manager.py`
6. `services/token_tracker.py`
7. `services/pricing_history_service.py`
8. `services/telemetry_service.py`
9. `services/model_registry_service.py`
10. `services/use_case_config_loader.py`

### Phase 3: Dependent Services

11. `services/tool_registration_service.py` (uses ToolService)
12. `services/tool_discovery_service.py`
13. `services/tool_health_monitor.py`
14. `services/tool_executor.py`
15. `services/suite_testing_service.py`
16. `services/run_manifest_service.py`
17. `services/telemetry_integration_service.py`

### Phase 4: Middleware

18. `middleware/audit.py`
19. `middleware/rls.py`

### Phase 5: Auth Module

20. `auth/utils.py`

### Phase 6: Simple Routers (Direct DB Only)

21. `routers/templates.py`
22. `routers/tools_analytics.py`
23. `routers/health.py`
24. `routers/prompt_patterns.py`

### Phase 7: Service-Using Routers

25. `routers/models.py`
26. `routers/tools_developer.py`
27. `routers/tools_admin.py`
28. `routers/tools_registration.py`
29. `routers/tools_health.py`
30. `routers/tools_testing.py`
31. `routers/token_analytics.py`
32. `routers/admin_pricing.py`
33. `routers/admin.py`
34. `routers/suite_testing.py`
35. `routers/capabilities.py`
36. `routers/summaries.py`
37. `routers/run_manifests.py`

### Phase 8: Complex Routers

38. `routers/use_case_management.py`
39. `routers/orchestrator.py`
40. `routers/use_case_validation.py`
41. `routers/use_cases.py` (remove remaining sync)

### Phase 9: Final Cleanup

42. `db/database.py` - Remove all sync exports

---

## 5. Detailed Instructions by File

### 5.1 Service Conversion Template

For each service file:

1. **Update imports at top of file:**

```python
# REMOVE
from sqlalchemy.orm import Session

# ADD
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
```

2. **Update class **init**:**

```python
# CHANGE
def __init__(self, db: Session):
# TO
def __init__(self, db: AsyncSession):
```

3. **Convert each method:**
   - Add `async` keyword to method signature
   - Convert `db.query()` to `select()` patterns
   - Add `await` to all database operations

4. **Update callers in routers** to use `await`

### 5.2 Router Conversion Template

For each router file:

1. **Update imports:**

```python
# REMOVE
from collections.abc import Generator
from sqlalchemy.orm import Session
from ..db.database import SessionLocal

# ADD
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.database import get_async_db
```

2. **DELETE the local get_db function entirely**

3. **Update all endpoint signatures:**

```python
# CHANGE
db: Session = Depends(get_db)
# TO
db: AsyncSession = Depends(get_async_db)
```

4. **Convert all database operations** using patterns from Section 2

5. **Update service instantiation** (services now need await on methods):

```python
# BEFORE
service = ToolService(db)
result = service.get_tool(tool_id)

# AFTER
service = ToolService(db)
result = await service.get_tool(tool_id)
```

---

## 6. Verification Steps

### After Each File Conversion

1. **Syntax Check:**

```bash
python -m py_compile src/orchestrator/app/path/to/file.py
```

2. **Import Check:**

```bash
python -c "from src.orchestrator.app.path.to.module import *"
```

3. **Run Related Unit Tests:**

```bash
python -m pytest src/orchestrator/tests/unit/path/to/test_file.py -v
```

### After Each Phase

1. **Run Full Service Tests:**

```bash
cd src/orchestrator && bash run_tests.sh
```

2. **Start Container:**

```bash
docker-compose -f deploy/docker-compose.test.yml up orchestrator-api --build
```

3. **Test Health Endpoint:**

```bash
curl http://localhost:8006/health
```

### Final Verification

1. **Search for Remaining Sync Patterns:**

```bash
grep -rn "SessionLocal\|def get_db.*Generator\|db\.query(" src/orchestrator/app/ --include="*.py"
```

Should return 0 results (except database.py which will be cleaned in Phase 9).

2. **Run Integration Tests:**

```bash
python -m pytest tests/integration/test_async_service_integration.py -v
```

---

## 7. Common Pitfalls

### 7.1 Forgetting await

**WRONG:**

```python
result = db.execute(stmt)  # Missing await!
```

**CORRECT:**

```python
result = await db.execute(stmt)
```

### 7.2 Wrong Result Extraction

**WRONG:**

```python
result = await db.execute(stmt)
item = result.first()  # Wrong method
```

**CORRECT:**

```python
result = await db.execute(stmt)
item = result.scalar_one_or_none()  # For single item
items = result.scalars().all()  # For list
```

### 7.3 Boolean Comparisons in Where Clauses

**WRONG:**

```python
stmt = select(Model).where(Model.active)  # Implicit boolean
```

**CORRECT:**

```python
stmt = select(Model).where(Model.active == True)  # noqa: E712
```

### 7.4 Calling Async Service Methods Without Await

**WRONG:**

```python
service = MyService(db)
result = service.get_item(id)  # Missing await!
```

**CORRECT:**

```python
service = MyService(db)
result = await service.get_item(id)
```

### 7.5 Missing Import for `func`

When using `count()`, you need:

```python
from sqlalchemy import func
```

### 7.6 Forgetting to Update Related Tests

Each converted file needs its unit tests updated to:

- Use `pytest.mark.asyncio` decorator
- Use `async def` test functions
- Mock AsyncSession instead of Session
- Use `AsyncMock` for database mocks

---

## 8. Example Full File Conversion

See `routers/admin_roles.py` for a reference of a properly converted async router.

---

## Document History

| Date | Change |
|------|--------|
| Nov 29, 2025 | Initial creation |

**Document Owner:** Project team
