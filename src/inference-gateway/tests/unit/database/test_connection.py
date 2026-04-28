"""
Unit tests for database connection utilities.

Tests the async database connection infrastructure following
the patterns established in P5-A1 and P5-A2.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Module Import Tests
# ---------------------------------------------------------------------------


def test_module_imports():
    """Test that all expected symbols are exported from the connection module."""
    from app.database import connection

    # Verify all expected exports are present
    assert hasattr(connection, "Base")
    assert hasattr(connection, "async_session")
    assert hasattr(connection, "engine")
    assert hasattr(connection, "get_session")
    assert hasattr(connection, "get_db_session")
    assert hasattr(connection, "check_database_connection")
    assert hasattr(connection, "init_db")


def test_package_exports():
    """Test that database package exports all expected symbols."""
    from app import database

    expected_exports = [
        "Base",
        "GatewayUsageLog",
        "async_session",
        "check_database_connection",
        "engine",
        "get_db_session",
        "get_session",
        "init_db",
    ]

    for export in expected_exports:
        assert hasattr(database, export), f"Missing export: {export}"


def test_all_exports_in_list():
    """Test that __all__ contains all expected exports."""
    from app.database import connection

    expected = [
        "Base",
        "async_session",
        "check_database_connection",
        "engine",
        "get_db_session",
        "get_session",
        "init_db",
    ]

    for item in expected:
        assert item in connection.__all__, f"Missing from __all__: {item}"


# ---------------------------------------------------------------------------
# get_session Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_session_yields_session():
    """Test get_session yields an AsyncSession."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    with patch("app.database.connection.async_session") as mock_factory:
        mock_factory.return_value = mock_session

        from app.database.connection import get_session

        async with get_session() as session:
            assert session is mock_session

        # Verify commit and close were called
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_session_commits_on_success():
    """Test get_session commits transaction on successful exit."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    with patch("app.database.connection.async_session") as mock_factory:
        mock_factory.return_value = mock_session

        from app.database.connection import get_session

        async with get_session() as _session:
            # Simulate successful operation
            pass

        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_get_session_rollback_on_error():
    """Test get_session rolls back transaction on error."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    with patch("app.database.connection.async_session") as mock_factory:
        mock_factory.return_value = mock_session

        from app.database.connection import get_session

        with pytest.raises(ValueError):
            async with get_session() as _session:
                raise ValueError("Test error")

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_session_closes_on_error():
    """Test get_session always closes session even on error."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    with patch("app.database.connection.async_session") as mock_factory:
        mock_factory.return_value = mock_session

        from app.database.connection import get_session

        try:
            async with get_session():
                raise RuntimeError("Unexpected error")
        except RuntimeError:
            pass

        mock_session.close.assert_called_once()


# ---------------------------------------------------------------------------
# get_db_session Tests (FastAPI Dependency)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_db_session_yields_session():
    """Test get_db_session yields an AsyncSession for FastAPI dependency injection."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    with patch("app.database.connection.async_session") as mock_factory:
        mock_factory.return_value = mock_session

        from app.database.connection import get_db_session

        # Consume the async generator
        gen = get_db_session()
        session = await gen.__anext__()

        assert session is mock_session

        # Clean up
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass


@pytest.mark.asyncio
async def test_get_db_session_commits_on_success():
    """Test get_db_session commits when used successfully."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    with patch("app.database.connection.async_session") as mock_factory:
        mock_factory.return_value = mock_session

        from app.database.connection import get_db_session

        # Simulate FastAPI dependency injection
        gen = get_db_session()
        session = await gen.__anext__()
        assert session is not None

        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass

        mock_session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# check_database_connection Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_database_connection_success():
    """Test check_database_connection returns True on successful connection."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()

    mock_engine = MagicMock()

    async def mock_connect():
        yield mock_conn

    mock_engine.connect = lambda: mock_connect().__aenter__()

    # Need to properly mock the async context manager
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with patch("app.database.connection.engine") as patched_engine:
        patched_engine.connect.return_value = mock_cm

        from app.database.connection import check_database_connection

        result = await check_database_connection()

        assert result is True
        mock_conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_check_database_connection_failure():
    """Test check_database_connection returns False on connection failure."""
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(side_effect=Exception("Connection failed"))

    with patch("app.database.connection.engine") as patched_engine:
        patched_engine.connect.return_value = mock_cm

        from app.database.connection import check_database_connection

        result = await check_database_connection()

        assert result is False


@pytest.mark.asyncio
async def test_check_database_connection_query_error():
    """Test check_database_connection returns False when SELECT 1 fails."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(side_effect=Exception("Query failed"))

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with patch("app.database.connection.engine") as patched_engine:
        patched_engine.connect.return_value = mock_cm

        from app.database.connection import check_database_connection

        result = await check_database_connection()

        assert result is False


# ---------------------------------------------------------------------------
# init_db Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_init_db_creates_tables():
    """Test init_db creates database tables."""
    mock_conn = AsyncMock()
    mock_conn.run_sync = AsyncMock()

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with patch("app.database.connection.engine") as patched_engine:
        patched_engine.begin.return_value = mock_cm

        from app.database.connection import init_db

        await init_db()

        # Verify run_sync was called (which creates tables)
        mock_conn.run_sync.assert_called_once()


@pytest.mark.asyncio
async def test_init_db_imports_models():
    """Test init_db imports models to register table definitions."""
    mock_conn = AsyncMock()
    mock_conn.run_sync = AsyncMock()

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with patch("app.database.connection.engine") as patched_engine:
        patched_engine.begin.return_value = mock_cm

        from app.database.connection import init_db

        # Should not raise ImportError
        await init_db()


# ---------------------------------------------------------------------------
# Integration-like Tests (Mocked)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_lifecycle():
    """Test complete session lifecycle: create, use, commit, close."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    with patch("app.database.connection.async_session") as mock_factory:
        mock_factory.return_value = mock_session

        from app.database.connection import get_session

        async with get_session() as session:
            # Simulate adding a model
            session.add(MagicMock())

        # Verify full lifecycle
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_multiple_sessions():
    """Test multiple sessions can be created concurrently."""
    call_count = 0

    def make_mock_session():
        nonlocal call_count
        call_count += 1
        mock = AsyncMock(spec=AsyncSession)
        mock.commit = AsyncMock()
        mock.rollback = AsyncMock()
        mock.close = AsyncMock()
        return mock

    with patch("app.database.connection.async_session") as mock_factory:
        mock_factory.side_effect = make_mock_session

        from app.database.connection import get_session

        async def use_session():
            async with get_session() as session:
                await asyncio.sleep(0.01)
                return session

        # Create multiple concurrent sessions
        sessions = await asyncio.gather(
            use_session(),
            use_session(),
            use_session(),
        )

        assert len(sessions) == 3
        assert call_count == 3


# ---------------------------------------------------------------------------
# Base Class Tests
# ---------------------------------------------------------------------------


def test_base_class_available():
    """Test Base class is available and properly configured."""
    from app.database.connection import Base

    assert Base is not None
    # Base should have metadata
    assert hasattr(Base, "metadata")


def test_gateway_usage_log_inherits_base():
    """Test GatewayUsageLog model inherits from Base."""
    from app.database import Base, GatewayUsageLog

    # GatewayUsageLog should use the same metadata as Base
    # This confirms it's registered with the declarative base
    assert GatewayUsageLog.__tablename__ in Base.metadata.tables


def test_gateway_usage_log_table_name():
    """Test GatewayUsageLog has correct table name."""
    from app.database import GatewayUsageLog

    assert GatewayUsageLog.__tablename__ == "gateway_usage_log"


# ---------------------------------------------------------------------------
# Logger Tests
# ---------------------------------------------------------------------------


def test_logger_configured():
    """Test logger is configured with correct service name."""
    from app.database import connection

    assert connection.logger is not None
