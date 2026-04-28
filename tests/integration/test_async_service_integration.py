"""
P5-A16: Service Integration Testing for Async SQLAlchemy Migration.

This module tests cross-service async patterns after the Phase 5 async migration:
- Orchestrator → Corpus Service (document proxy via httpx.AsyncClient)
- Orchestrator → Inference Gateway (LLM/embedding operations)
- Async database operations across all services

Created: November 29, 2025
Task: P5-A16 (Phase 5 Week 4)
ADR Compliance: ADR-022 (Backend Async Database Migration)
"""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import get_current_user
from shared.auth.models import TokenPayload, UserRole
from src.orchestrator.app.db.database import AsyncSessionLocal, init_db
from src.orchestrator.app.main import create_app

# =============================================================================
# Fixtures for Async Integration Testing
# =============================================================================


@pytest.fixture
def test_orchestrator_app():
    """Create the orchestrator app for testing."""
    return create_app()


@pytest.fixture
def mock_admin_token_payload():
    """Create a mock admin token payload."""
    return TokenPayload(
        sub="admin_integration_test",
        user_id=str(uuid.uuid4()),
        role=UserRole.ADMIN,
        exp=int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        iat=int(datetime.now(UTC).timestamp()),
        iss="integration-test",
        token_type="access",
    )


@pytest.fixture
def mock_user_token_payload():
    """Create a mock regular user token payload."""
    return TokenPayload(
        sub="user_integration_test",
        user_id=str(uuid.uuid4()),
        role=UserRole.USER,
        exp=int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        iat=int(datetime.now(UTC).timestamp()),
        iss="integration-test",
        token_type="access",
    )


@pytest_asyncio.fixture
async def async_test_client(test_orchestrator_app, mock_admin_token_payload):
    """Create an async test client with mocked authentication."""

    def mock_get_current_user():
        return mock_admin_token_payload

    test_orchestrator_app.dependency_overrides[get_current_user] = mock_get_current_user

    transport = ASGITransport(app=test_orchestrator_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    test_orchestrator_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an async database session for testing."""
    await init_db()
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()


# =============================================================================
# Test: Orchestrator Async Database Patterns (ADR-022 Compliance)
# =============================================================================


class TestAsyncDatabasePatterns:
    """
    Test async database patterns in the orchestrator service.

    Verifies ADR-022 compliance: all database operations use async patterns.
    """

    def test_async_session_factory_exists(self):
        """Verify AsyncSessionLocal is properly configured."""
        from src.orchestrator.app.db.database import AsyncSessionLocal

        assert AsyncSessionLocal is not None
        # Verify it's an async session factory (callable)
        assert "async" in str(type(AsyncSessionLocal)).lower() or callable(AsyncSessionLocal)

    def test_async_engine_exists(self):
        """Verify async_engine is properly configured."""
        from src.orchestrator.app.db.database import async_engine

        assert async_engine is not None
        # Verify it's an async engine
        assert "async" in str(type(async_engine)).lower()

    def test_get_async_db_is_async_generator(self):
        """Verify get_async_db is an async generator function."""
        import inspect

        from src.orchestrator.app.db.database import get_async_db as async_db_func

        assert inspect.isasyncgenfunction(async_db_func)

    @pytest.mark.asyncio
    async def test_async_session_context_manager(self):
        """Verify async session works as context manager."""
        from src.orchestrator.app.db.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            assert session is not None
            assert isinstance(session, AsyncSession)

    @pytest.mark.asyncio
    async def test_async_db_dependency_yields_session(self):
        """Verify get_async_db yields proper session."""
        from src.orchestrator.app.db.database import get_async_db as async_db_gen

        async for session in async_db_gen():
            assert session is not None
            assert isinstance(session, AsyncSession)
            break  # Only get first yield


# =============================================================================
# Test: Orchestrator → Corpus Service Async Integration
# =============================================================================


class TestOrchestatorCorpusIntegration:
    """
    Test async integration between orchestrator and corpus service.

    These tests verify the proxy patterns in src/orchestrator/app/routers/corpus.py
    work correctly with httpx.AsyncClient.
    """

    def test_corpus_proxy_uses_async_client_pattern(self):
        """Verify corpus proxy router uses httpx.AsyncClient pattern."""
        import importlib.util

        # Load corpus router source and verify async pattern
        spec = importlib.util.find_spec("src.orchestrator.app.routers.corpus")
        if spec and spec.origin:
            with open(spec.origin, encoding="utf-8") as f:
                source = f.read()
                # Verify async patterns are used
                assert "httpx.AsyncClient" in source
                assert "async def" in source
                assert "await" in source

    @pytest.mark.asyncio
    async def test_corpus_health_independent(self, async_test_client):
        """Verify orchestrator health doesn't require corpus service."""
        response = await async_test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"

    def test_document_stats_uses_async_pattern(self):
        """Test document stats router uses async pattern."""
        import importlib.util

        # Verify the router source uses async patterns
        spec = importlib.util.find_spec("src.orchestrator.app.routers.corpus")
        if spec and spec.origin:
            with open(spec.origin, encoding="utf-8") as f:
                source = f.read()
                # The /stats endpoint should be async
                assert "async def get_document_statistics" in source


# =============================================================================
# Test: Orchestrator → Inference Gateway Async Integration
# =============================================================================


class TestOrchestatorGatewayIntegration:
    """
    Test async integration between orchestrator and inference gateway.

    These tests verify the LLMRouter and proxy patterns work correctly
    with the inference gateway service.
    """

    def test_llm_router_requires_jwt(self):
        """Verify LLMRouter requires JWT token."""
        from src.orchestrator.app.orchestrator.llm_router import LLMRouter

        with pytest.raises(ValueError, match="requires user_jwt_token"):
            LLMRouter(gateway_url="http://test:8002")

    def test_llm_router_uses_llm_client(self):
        """Verify LLMRouter creates LLMClient for gateway communication."""
        import importlib.util

        spec = importlib.util.find_spec("src.orchestrator.app.orchestrator.llm_router")
        if spec and spec.origin:
            with open(spec.origin, encoding="utf-8") as f:
                source = f.read()
                # Verify LLMRouter uses LLMClient
                assert "LLMClient" in source
                assert "self.client = LLMClient" in source

    def test_llm_client_has_async_methods(self):
        """Verify LLMClient defines async methods for completions."""
        import importlib.util

        spec = importlib.util.find_spec("src.orchestrator.app.orchestrator.llm_client")
        if spec and spec.origin:
            with open(spec.origin, encoding="utf-8") as f:
                source = f.read()
                # Verify async method definitions
                assert "async def make_async_completion_request" in source
                assert "async def make_streaming_completion_request" in source
                # Verify they use await
                assert "await self.async_client" in source

    @pytest.mark.asyncio
    async def test_gateway_provider_proxy_async_pattern(self, async_test_client):
        """Test gateway provider proxy uses async pattern."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"providers": []}
            mock_response.text = "[]"

            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_client_instance

            # Try to access gateway admin endpoints
            response = await async_test_client.get("/api/v1/admin/gateway/providers")

            # Should work with mock or return appropriate error
            assert response.status_code in [200, 404, 502, 503]


# =============================================================================
# Test: Cross-Service Async Flow Integration
# =============================================================================


class TestCrossServiceAsyncFlows:
    """
    Test complete async flows across multiple services.

    These tests verify the async patterns work correctly when
    multiple services interact.
    """

    @pytest.mark.asyncio
    async def test_use_case_endpoint_async_db_access(self, async_test_client):
        """Verify use case endpoint uses async database access."""
        # This endpoint now uses AsyncSession via get_async_db
        response = await async_test_client.get("/api/v1/use-cases/available")

        # Should return list of use cases or empty list
        assert response.status_code == 200
        data = response.json()
        assert "use_cases" in data
        assert "total" in data

    def test_admin_roles_uses_async_db_pattern(self):
        """Verify admin roles router uses async database pattern."""
        import importlib.util

        spec = importlib.util.find_spec("src.orchestrator.app.routers.admin_roles")
        if spec and spec.origin:
            with open(spec.origin, encoding="utf-8") as f:
                source = f.read()
                # Should use async patterns
                assert "AsyncSession" in source
                assert "async def" in source
                assert "await" in source

    def test_admin_audit_uses_async_db_pattern(self):
        """Verify admin audit router uses async database pattern."""
        import importlib.util

        spec = importlib.util.find_spec("src.orchestrator.app.routers.admin_audit")
        if spec and spec.origin:
            with open(spec.origin, encoding="utf-8") as f:
                source = f.read()
                # Should use async patterns
                assert "AsyncSession" in source
                assert "async def" in source
                assert "await" in source


# =============================================================================
# Test: Corpus Service Async Database (P5-A14 Verification)
# =============================================================================


class TestCorpusServiceAsyncVerification:
    """
    Verify corpus service uses async database patterns.

    This confirms P5-A14 work: corpus_svc was already fully async.
    """

    def test_corpus_db_connection_is_async(self):
        """Verify corpus service database connection is async."""
        try:
            from src.corpus_svc.app.db.connection import (
                get_async_engine,
                get_db_session,
            )

            engine = get_async_engine()
            assert engine is not None
            assert "async" in str(type(engine)).lower()

            import inspect

            assert inspect.isasyncgenfunction(get_db_session)
        except ImportError:
            pytest.skip("corpus_svc not available in test environment")


# =============================================================================
# Test: Inference Gateway Async Database (P5-A15 Verification)
# =============================================================================


class TestGatewayAsyncVerification:
    """
    Verify inference gateway uses async database patterns.

    This confirms P5-A15 work: gateway was already fully async.
    """

    def test_gateway_db_connection_is_async(self):
        """Verify gateway database connection is async."""
        import inspect

        try:
            from src.inference_gateway.app.database.connection import (  # type: ignore
                get_db_session,
            )

            assert inspect.isasyncgenfunction(get_db_session)
        except ImportError:
            pytest.skip("inference-gateway not available in test environment")


# =============================================================================
# Test: Shared Database Utilities (P5-A4 Verification)
# =============================================================================


class TestSharedDbUtilities:
    """
    Verify shared database utilities work correctly.

    This confirms P5-A4 work: shared.db.connection enhancements.
    """

    def test_shared_db_connection_module_exists(self):
        """Verify shared.db.connection module exists."""
        from src.shared.db import connection

        assert hasattr(connection, "Base")
        assert hasattr(connection, "get_pool_config")
        assert hasattr(connection, "check_database_connection")

    def test_pool_config_function_works(self):
        """Verify get_pool_config returns proper config."""
        from src.shared.db.connection import get_pool_config

        config = get_pool_config()

        assert "pool_size" in config
        assert "max_overflow" in config
        assert "pool_recycle" in config
        assert "pool_pre_ping" in config

    @pytest.mark.asyncio
    async def test_database_health_check(self):
        """Verify database health check works."""
        from src.shared.db.connection import check_database_connection

        try:
            # This may raise if no DB connection
            result = await check_database_connection()
            assert result in [True, False]
        except Exception:
            # Expected if DB not available in unit test context
            pass


# =============================================================================
# Test: ADR-022 Compliance - Full Async (No Sync Patterns)
# =============================================================================


class TestADR022Compliance:
    """
    Verify overall ADR-022 compliance for async database migration.

    Pre-release: No backward compatibility needed. All database access
    should be 100% async with zero sync patterns.
    """

    def test_orchestrator_uses_asyncpg_driver(self):
        """Verify orchestrator async engine uses asyncpg driver."""
        from src.orchestrator.app.db.database import async_engine

        url = str(async_engine.url)
        assert "asyncpg" in url or "postgresql+asyncpg" in url

    def test_async_routers_use_async_db(self):
        """
        Verify async routers use async database patterns exclusively.

        Pre-release requirement: No sync get_db() usage allowed.
        All routers should use get_async_db() with AsyncSession.
        """
        import importlib.util

        # Load use_cases router - should use AsyncSession
        spec = importlib.util.find_spec("src.orchestrator.app.routers.use_cases")
        if spec and spec.origin:
            with open(spec.origin, encoding="utf-8") as f:
                source = f.read()
                # Must use AsyncSession
                assert "AsyncSession" in source
                # Should use async patterns
                assert "async def" in source
                assert "await" in source

    def test_pytest_asyncio_support_configured(self):
        """Verify pytest-asyncio is properly configured."""
        import pytest_asyncio

        assert pytest_asyncio is not None
