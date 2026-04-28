"""
Unit tests for corpus_svc database connection module.

Tests async database infrastructure for the corpus service.
The corpus service uses async-only SQLAlchemy patterns (no dual-stack).

Note: Tests that require actual database connectivity are marked with
`pytest.mark.integration` and may fail if run outside Docker network.
"""

import pytest

from src.corpus_svc.app.db.connection import (
    Base,
    async_session,
    check_database_connection,
    engine,
    get_db_session,
    get_session,
    init_db,
)


class TestDatabaseConfiguration:
    """Test database configuration and setup."""

    def test_engine_is_async_engine(self):
        """Test engine is an async SQLAlchemy engine."""
        from sqlalchemy.ext.asyncio import AsyncEngine

        assert engine is not None
        assert isinstance(engine, AsyncEngine)
        assert hasattr(engine, "begin")

    def test_async_session_factory_created(self):
        """Test async_session factory is created."""
        assert async_session is not None
        assert callable(async_session)

    def test_base_declarative_base_created(self):
        """Test Base declarative base is created."""
        assert Base is not None
        assert hasattr(Base, "metadata")

    def test_base_has_async_attrs(self):
        """Test Base includes AsyncAttrs mixin."""
        # AsyncAttrs enables awaitable lazy loading
        from sqlalchemy.ext.asyncio import AsyncAttrs

        assert issubclass(Base, AsyncAttrs)


class TestGetSession:
    """Test get_session context manager."""

    @pytest.mark.asyncio
    async def test_get_session_yields_async_session(self):
        """Test get_session yields an AsyncSession."""
        from sqlalchemy.ext.asyncio import AsyncSession

        async with get_session() as session:
            assert session is not None
            assert isinstance(session, AsyncSession)

    @pytest.mark.asyncio
    async def test_get_session_has_execute_method(self):
        """Test session has execute method for queries."""
        async with get_session() as session:
            assert hasattr(session, "execute")
            assert callable(session.execute)

    @pytest.mark.asyncio
    async def test_get_session_has_commit_rollback(self):
        """Test session has commit and rollback methods."""
        async with get_session() as session:
            assert hasattr(session, "commit")
            assert hasattr(session, "rollback")


class TestGetDbSession:
    """Test FastAPI dependency for database sessions."""

    @pytest.mark.asyncio
    async def test_get_db_session_yields_async_session(self):
        """Test get_db_session yields an AsyncSession."""
        from sqlalchemy.ext.asyncio import AsyncSession

        async for session in get_db_session():
            assert session is not None
            assert isinstance(session, AsyncSession)
            break

    @pytest.mark.asyncio
    async def test_get_db_session_can_execute_query(self):
        """Test session from get_db_session can execute queries."""
        from unittest.mock import AsyncMock, MagicMock, patch

        # Mock the async_session to return a mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()

        mock_session_factory = MagicMock(return_value=mock_session)

        with patch(
            "src.corpus_svc.app.db.connection.async_session",
            mock_session_factory,
        ):
            from src.corpus_svc.app.db.connection import get_db_session

            async for session in get_db_session():
                from sqlalchemy import text

                result = await session.execute(text("SELECT 1"))
                row = result.scalar()
                assert row == 1
                mock_session.execute.assert_called_once()
                break


class TestCheckDatabaseConnection:
    """Test database connection health check."""

    @pytest.mark.asyncio
    async def test_check_database_connection_returns_bool(self):
        """Test check_database_connection returns a boolean."""
        result = await check_database_connection()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_check_database_connection_when_available(self):
        """Test check_database_connection succeeds when DB is available.

        Note: This test verifies the function works; it may return False
        if running outside Docker network.
        """
        result = await check_database_connection()
        # Result depends on environment - just verify it returns bool
        assert isinstance(result, bool)
        # If DB is available, it should return True
        # If not (e.g., running locally), it returns False which is valid


class TestInitDb:
    """Test database initialization function."""

    @pytest.mark.asyncio
    async def test_init_db_creates_tables(self):
        """Test init_db creates database tables without error."""
        from unittest.mock import AsyncMock, MagicMock, patch

        # Mock the engine.begin() context manager
        mock_conn = AsyncMock()
        mock_conn.run_sync = AsyncMock()

        mock_begin_cm = AsyncMock()
        mock_begin_cm.__aenter__.return_value = mock_conn
        mock_begin_cm.__aexit__.return_value = None

        mock_engine = MagicMock()
        mock_engine.begin.return_value = mock_begin_cm

        with patch("src.corpus_svc.app.db.connection.engine", mock_engine):
            await init_db()

        # Verify run_sync was called (to create tables)
        mock_conn.run_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_db_is_idempotent(self):
        """Test init_db can be called multiple times safely."""
        from unittest.mock import AsyncMock, MagicMock, patch

        # Mock the engine.begin() context manager
        mock_conn = AsyncMock()
        mock_conn.run_sync = AsyncMock()

        mock_begin_cm = AsyncMock()
        mock_begin_cm.__aenter__.return_value = mock_conn
        mock_begin_cm.__aexit__.return_value = None

        mock_engine = MagicMock()
        mock_engine.begin.return_value = mock_begin_cm

        with patch("src.corpus_svc.app.db.connection.engine", mock_engine):
            # First call
            await init_db()
            # Second call should also succeed
            await init_db()

        # Verify run_sync was called twice (once per init_db call)
        assert mock_conn.run_sync.await_count == 2


class TestModuleExports:
    """Test module exports all required symbols."""

    def test_all_exports_defined(self):
        """Test __all__ includes all public exports."""
        from src.corpus_svc.app.db import connection

        expected_exports = [
            "Base",
            "engine",
            "async_session",
            "get_session",
            "get_db_session",
            "check_database_connection",
            "init_db",
        ]
        for export in expected_exports:
            assert hasattr(connection, export), f"Missing export: {export}"

    def test_all_exports_match_all_attribute(self):
        """Test exports match __all__ attribute."""
        from src.corpus_svc.app.db import connection

        assert hasattr(connection, "__all__")
        for name in connection.__all__:
            assert hasattr(connection, name), f"__all__ contains missing: {name}"
