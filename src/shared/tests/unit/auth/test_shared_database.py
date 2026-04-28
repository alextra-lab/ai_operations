"""
Unit tests for shared.auth.database module.

Tests cover:
- DatabaseManager initialization
- Table creation
- Session management
- Connection testing
- Module-level convenience functions
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import database

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


class TestDatabaseManagerInit:
    """Test DatabaseManager initialization."""

    @pytest.mark.asyncio
    async def test_init_with_url(self):
        """Test initialization with explicit URL."""
        mgr = database.DatabaseManager(database_url=TEST_DB_URL)
        assert mgr.database_url == TEST_DB_URL
        assert mgr.engine is not None
        assert mgr.SessionLocal is not None

    @pytest.mark.asyncio
    async def test_init_from_env(self):
        """Test initialization from environment variables."""
        env_vars = {
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": "pass",
            "POSTGRES_HOST": "host",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "db",
            "DATABASE_URL": "",  # Clear to force building from components
        }
        with patch.dict("os.environ", env_vars, clear=False):
            mgr = database.DatabaseManager()
            assert "postgresql+asyncpg://" in mgr.database_url
            assert "user" in mgr.database_url


class TestDatabaseManagerCreateTables:
    """Test DatabaseManager.create_tables method."""

    @pytest.mark.asyncio
    async def test_create_tables_success(self):
        """Test create_tables executes without error on SQLite."""
        mgr = database.DatabaseManager(database_url=TEST_DB_URL)
        # This should work on an in-memory SQLite database
        with patch.object(database, "logger"):
            await mgr.create_tables()

    @pytest.mark.asyncio
    async def test_create_tables_logs_success(self):
        """Test create_tables logs success message."""
        mgr = database.DatabaseManager(database_url=TEST_DB_URL)
        with patch.object(database, "logger") as mock_logger:
            await mgr.create_tables()
            mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_create_tables_error_logs_and_raises(self):
        """Test create_tables logs error and re-raises on failure."""
        mgr = database.DatabaseManager(database_url=TEST_DB_URL)

        # Mock the engine's begin to simulate an error
        mock_conn = AsyncMock()
        mock_conn.run_sync = AsyncMock(side_effect=Exception("DB error"))

        mock_begin_cm = AsyncMock()
        mock_begin_cm.__aenter__.return_value = mock_conn
        mock_begin_cm.__aexit__.return_value = None

        with (
            patch.object(mgr, "engine") as mock_engine,
            patch.object(database, "logger") as mock_logger,
        ):
            mock_engine.begin.return_value = mock_begin_cm
            with pytest.raises(Exception, match="DB error"):
                await mgr.create_tables()
            mock_logger.error.assert_called()


class TestDatabaseManagerGetSession:
    """Test DatabaseManager.get_session method."""

    @pytest.mark.asyncio
    async def test_get_session_yields_async_session(self):
        """Test get_session yields an AsyncSession."""
        mgr = database.DatabaseManager(database_url=TEST_DB_URL)
        async with mgr.get_session() as session:
            assert isinstance(session, AsyncSession)

    @pytest.mark.asyncio
    async def test_get_session_handles_error(self):
        """Test get_session handles errors and rolls back."""
        mgr = database.DatabaseManager(database_url=TEST_DB_URL)

        with pytest.raises(ValueError, match="Test error"):
            async with mgr.get_session():
                raise ValueError("Test error")


class TestDatabaseManagerTestConnection:
    """Test DatabaseManager.test_connection method."""

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test test_connection returns True on success."""
        mgr = database.DatabaseManager(database_url=TEST_DB_URL)
        # SQLite in-memory should connect successfully
        result = await mgr.test_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """Test test_connection returns False on failure."""
        mgr = database.DatabaseManager(database_url=TEST_DB_URL)

        # Mock the engine to simulate connection failure
        mock_conn_cm = AsyncMock()
        mock_conn_cm.__aenter__.side_effect = Exception("Connection failed")

        with (
            patch.object(mgr, "engine") as mock_engine,
            patch.object(database, "logger"),
        ):
            mock_engine.connect.return_value = mock_conn_cm
            result = await mgr.test_connection()
            assert result is False

    @pytest.mark.asyncio
    async def test_test_connection_logs_success(self):
        """Test test_connection logs success message."""
        mgr = database.DatabaseManager(database_url=TEST_DB_URL)
        with patch.object(database, "logger") as mock_logger:
            await mgr.test_connection()
            mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_test_connection_logs_error(self):
        """Test test_connection logs error on failure."""
        mgr = database.DatabaseManager(database_url=TEST_DB_URL)

        mock_conn_cm = AsyncMock()
        mock_conn_cm.__aenter__.side_effect = Exception("Connection failed")

        with (
            patch.object(mgr, "engine") as mock_engine,
            patch.object(database, "logger") as mock_logger,
        ):
            mock_engine.connect.return_value = mock_conn_cm
            await mgr.test_connection()
            mock_logger.error.assert_called()


class TestModuleFunctions:
    """Test module-level convenience functions."""

    @pytest.mark.asyncio
    async def test_get_db_manager_returns_manager(self):
        """Test get_db_manager returns a DatabaseManager instance."""
        with patch.object(database, "_db_manager", None):
            mgr = database.get_db_manager()
            assert isinstance(mgr, database.DatabaseManager)

    @pytest.mark.asyncio
    async def test_get_db_manager_returns_same_instance(self):
        """Test get_db_manager returns the same instance (singleton)."""
        with patch.object(database, "_db_manager", None):
            mgr1 = database.get_db_manager()
            mgr2 = database.get_db_manager()
            assert mgr1 is mgr2

    @pytest.mark.asyncio
    async def test_get_db_yields_session(self):
        """Test get_db yields a session from the manager."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_manager = MagicMock()

        # Create a proper async context manager
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session
        mock_session_cm.__aexit__.return_value = None
        mock_manager.get_session.return_value = mock_session_cm

        with patch.object(database, "get_db_manager", return_value=mock_manager):
            async for session in database.get_db():
                assert session is mock_session

    @pytest.mark.asyncio
    async def test_init_database_calls_create_tables(self):
        """Test init_database calls manager's create_tables."""
        mock_manager = MagicMock()
        mock_manager.create_tables = AsyncMock()

        with patch.object(database, "get_db_manager", return_value=mock_manager):
            await database.init_database()
            mock_manager.create_tables.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_test_database_connection_returns_result(self):
        """Test test_database_connection returns manager's result."""
        mock_manager = MagicMock()
        mock_manager.test_connection = AsyncMock(return_value=True)

        with patch.object(database, "get_db_manager", return_value=mock_manager):
            result = await database.test_database_connection()
            assert result is True
            mock_manager.test_connection.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_test_database_connection_returns_false_on_failure(self):
        """Test test_database_connection returns False on failure."""
        mock_manager = MagicMock()
        mock_manager.test_connection = AsyncMock(return_value=False)

        with patch.object(database, "get_db_manager", return_value=mock_manager):
            result = await database.test_database_connection()
            assert result is False
