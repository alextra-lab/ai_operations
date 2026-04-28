# Testcontainers Implementation Example

This document provides a concrete example of how Testcontainers could be implemented in the AI Operations Platform project.

## Example: PostgreSQL Integration Test

### Current Implementation (Docker Compose)

```python
# tests/integration/test_user_management.py
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.orchestrator.app.db.database import AsyncSessionLocal, init_db
from src.shared.auth.models import User, UserRole

@pytest_asyncio.fixture
async def db_session():
    """Uses pre-existing PostgreSQL container at localhost:5433"""
    await init_db()  # Connects to existing container
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()

@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    """Test user creation - may fail if previous test left data."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed",
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.commit()

    assert user.id is not None
    assert user.username == "testuser"
```

**Setup required:**

```bash
./ops/testing/start_test_services.sh  # Manual step
pytest tests/integration/test_user_management.py
```

### Testcontainers Implementation

```python
# tests/integration/test_user_management.py
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from testcontainers.postgres import PostgresContainer

from src.orchestrator.app.db.models import Base
from src.shared.auth.models import User, UserRole

@pytest.fixture(scope="function")
def postgres_container():
    """Fresh PostgreSQL container for each test."""
    container = PostgresContainer("postgres:17-alpine")
    container.start()

    # Apply migrations (example - would use actual migration runner)
    # run_migrations(container.get_connection_url())

    yield container
    container.stop()

@pytest_asyncio.fixture
async def db_session(postgres_container):
    """Database session using Testcontainers PostgreSQL."""
    # Convert postgresql:// to postgresql+psycopg:// for async
    connection_url = postgres_container.get_connection_url()
    async_url = connection_url.replace("postgresql://", "postgresql+psycopg://")

    engine = create_async_engine(async_url, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session

    await engine.dispose()

@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    """Test user creation - guaranteed clean database state."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed",
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.commit()

    assert user.id is not None
    assert user.username == "testuser"
```

**Setup required:**

```bash
pytest tests/integration/test_user_management.py
# Containers start/stop automatically!
```

## Reusable Fixtures Pattern

### Container Fixtures Module

```python
# tests/fixtures/testcontainers.py
"""Reusable Testcontainers fixtures for integration tests."""
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.core.container import DockerContainer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.orchestrator.app.db.models import Base


@pytest.fixture(scope="session")
def postgres_container():
    """PostgreSQL container shared across test session."""
    container = PostgresContainer("postgres:17-alpine")
    container.start()

    # Apply migrations once per session
    # from ops.migrations.runner import run_migrations
    # run_migrations(container.get_connection_url())

    yield container
    container.stop()


@pytest.fixture(scope="session")
def qdrant_container():
    """Qdrant vector database container."""
    container = DockerContainer("qdrant/qdrant:v1.16.0")
    container.with_exposed_ports(6333, 6334)
    container.with_wait_for_logs("Qdrant is ready to accept connections")
    container.start()

    yield container
    container.stop()


@pytest.fixture(scope="session")
def redis_container():
    """Redis cache container."""
    container = DockerContainer("redis:7-alpine")
    container.with_exposed_ports(6379)
    container.with_wait_for_logs("Ready to accept connections")
    container.start()

    yield container
    container.stop()


@pytest_asyncio.fixture
async def db_session(postgres_container):
    """Async database session using Testcontainers PostgreSQL."""
    connection_url = postgres_container.get_connection_url()
    async_url = connection_url.replace("postgresql://", "postgresql+psycopg://")

    engine = create_async_engine(async_url, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def qdrant_url(qdrant_container):
    """Qdrant connection URL."""
    host = qdrant_container.get_container_host_ip()
    port = qdrant_container.get_exposed_port(6333)
    return f"http://{host}:{port}"


@pytest.fixture
def redis_url(redis_container):
    """Redis connection URL."""
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    return f"redis://{host}:{port}"
```

### Usage in Tests

```python
# tests/integration/test_retrieval_service.py
import pytest
from tests.fixtures.testcontainers import db_session, qdrant_url

@pytest.mark.asyncio
async def test_document_retrieval(db_session, qdrant_url):
    """Test document retrieval with isolated containers."""
    # Both PostgreSQL and Qdrant are fresh for this test
    # No interference from other tests

    # Test implementation...
    pass
```

## Hybrid Approach: Supporting Both

```python
# tests/integration/conftest.py
"""Integration test configuration supporting both Docker Compose and Testcontainers."""
import os
import pytest
from testcontainers.postgres import PostgresContainer

# Environment variable to choose approach
USE_TESTCONTAINERS = os.getenv("USE_TESTCONTAINERS", "false").lower() == "true"


if USE_TESTCONTAINERS:
    # Testcontainers approach
    @pytest.fixture(scope="session")
    def postgres_container():
        container = PostgresContainer("postgres:17-alpine")
        container.start()
        yield container
        container.stop()

    @pytest_asyncio.fixture
    async def db_session(postgres_container):
        # Use Testcontainers PostgreSQL
        connection_url = postgres_container.get_connection_url()
        # ... setup async engine ...
        yield session
else:
    # Docker Compose approach (existing)
    @pytest_asyncio.fixture
    async def db_session():
        """Uses pre-existing Docker Compose container."""
        await init_db()
        async with AsyncSessionLocal() as session:
            yield session
```

**Usage:**

```bash
# Use Testcontainers
USE_TESTCONTAINERS=true pytest tests/integration/

# Use Docker Compose (default)
pytest tests/integration/
```

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/tests.yml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
          pip install testcontainers[postgres]

      - name: Run tests with Testcontainers
        run: |
          USE_TESTCONTAINERS=true pytest tests/integration/ -v

      # No need for:
      # - docker-compose up
      # - wait for services
      # - docker-compose down
```

## Performance Comparison

### Test Execution Time

**Docker Compose (current):**

```
Setup:     ~30 seconds (manual script)
Test run:  ~10 seconds
Cleanup:   ~5 seconds (manual script)
Total:     ~45 seconds
```

**Testcontainers:**

```
Container startup: ~5 seconds (first time, cached after)
Test run:          ~10 seconds
Container cleanup: ~2 seconds (automatic)
Total:             ~17 seconds (subsequent runs: ~12 seconds)
```

**With parallel execution (Testcontainers):**

```
4 workers × 12 seconds = ~12 seconds total
vs.
1 worker × 45 seconds = ~45 seconds total
```

## Migration Checklist

- [ ] Add `testcontainers[postgres]` to `requirements-dev.txt`
- [ ] Create `tests/fixtures/testcontainers.py` with reusable fixtures
- [ ] Update `tests/integration/conftest.py` to support both approaches
- [ ] Create example test using Testcontainers
- [ ] Update CI/CD to use Testcontainers
- [ ] Document in `docs/testing/TESTING_GUIDE.md`
- [ ] Migrate 2-3 test files as proof of concept
- [ ] Gather team feedback
- [ ] Plan full migration timeline
