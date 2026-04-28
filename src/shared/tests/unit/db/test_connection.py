"""
Unit tests for shared.db.connection module.

Tests cover:
- Engine and sessionmaker creation
- Connection pooling configuration
- Environment variable overrides (P5-A7)
- Session utilities (get_session, get_db_session)
- Health check (check_database_connection)
- Table initialization (init_db_tables)
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from shared.db import connection

# =============================================================================
# CONFIGURATION TESTS
# =============================================================================


class TestConfiguration:
    """Test configuration constants and defaults."""

    def test_default_pool_size(self):
        """Test default pool size is set."""
        assert connection.DEFAULT_POOL_SIZE == 10

    def test_default_max_overflow(self):
        """Test default max overflow is set."""
        assert connection.DEFAULT_MAX_OVERFLOW == 20

    def test_default_pool_recycle(self):
        """Test default pool recycle is 1 hour."""
        assert connection.DEFAULT_POOL_RECYCLE == 3600

    def test_default_pool_pre_ping(self):
        """Test default pool pre-ping is enabled."""
        assert connection.DEFAULT_POOL_PRE_PING is True


# =============================================================================
# POOL CONFIG TESTS (P5-A7)
# =============================================================================


class TestGetPoolConfig:
    """Test get_pool_config function with environment overrides."""

    def test_get_pool_config_returns_defaults(self):
        """Test get_pool_config returns default values."""
        # Clear any env vars that might be set
        env_vars = [
            "DB_POOL_SIZE",
            "DB_MAX_OVERFLOW",
            "DB_POOL_RECYCLE",
            "DB_POOL_PRE_PING",
        ]
        with patch.dict(os.environ, {}, clear=True):
            # Remove any env vars if they exist
            for var in env_vars:
                os.environ.pop(var, None)

            config = connection.get_pool_config()

        assert config["pool_size"] == connection.DEFAULT_POOL_SIZE
        assert config["max_overflow"] == connection.DEFAULT_MAX_OVERFLOW
        assert config["pool_recycle"] == connection.DEFAULT_POOL_RECYCLE
        assert config["pool_pre_ping"] == connection.DEFAULT_POOL_PRE_PING

    def test_get_pool_config_env_override_pool_size(self):
        """Test DB_POOL_SIZE environment variable override."""
        with patch.dict(os.environ, {"DB_POOL_SIZE": "25"}):
            config = connection.get_pool_config()
        assert config["pool_size"] == 25

    def test_get_pool_config_env_override_max_overflow(self):
        """Test DB_MAX_OVERFLOW environment variable override."""
        with patch.dict(os.environ, {"DB_MAX_OVERFLOW": "50"}):
            config = connection.get_pool_config()
        assert config["max_overflow"] == 50

    def test_get_pool_config_env_override_pool_recycle(self):
        """Test DB_POOL_RECYCLE environment variable override."""
        with patch.dict(os.environ, {"DB_POOL_RECYCLE": "1800"}):
            config = connection.get_pool_config()
        assert config["pool_recycle"] == 1800

    def test_get_pool_config_env_override_pool_pre_ping_true(self):
        """Test DB_POOL_PRE_PING=true environment variable."""
        with patch.dict(os.environ, {"DB_POOL_PRE_PING": "true"}):
            config = connection.get_pool_config()
        assert config["pool_pre_ping"] is True

    def test_get_pool_config_env_override_pool_pre_ping_false(self):
        """Test DB_POOL_PRE_PING=false environment variable."""
        with patch.dict(os.environ, {"DB_POOL_PRE_PING": "false"}):
            config = connection.get_pool_config()
        assert config["pool_pre_ping"] is False

    def test_get_pool_config_env_override_pool_pre_ping_1(self):
        """Test DB_POOL_PRE_PING=1 environment variable."""
        with patch.dict(os.environ, {"DB_POOL_PRE_PING": "1"}):
            config = connection.get_pool_config()
        assert config["pool_pre_ping"] is True

    def test_get_pool_config_env_override_pool_pre_ping_0(self):
        """Test DB_POOL_PRE_PING=0 environment variable."""
        with patch.dict(os.environ, {"DB_POOL_PRE_PING": "0"}):
            config = connection.get_pool_config()
        assert config["pool_pre_ping"] is False

    def test_get_pool_config_invalid_int_uses_default(self):
        """Test invalid integer values fall back to defaults."""
        with patch.dict(os.environ, {"DB_POOL_SIZE": "not_a_number"}):
            config = connection.get_pool_config()
        assert config["pool_size"] == connection.DEFAULT_POOL_SIZE

    def test_get_pool_config_all_overrides(self):
        """Test all environment variables can be overridden together."""
        env_overrides = {
            "DB_POOL_SIZE": "15",
            "DB_MAX_OVERFLOW": "30",
            "DB_POOL_RECYCLE": "7200",
            "DB_POOL_PRE_PING": "false",
        }
        with patch.dict(os.environ, env_overrides):
            config = connection.get_pool_config()

        assert config["pool_size"] == 15
        assert config["max_overflow"] == 30
        assert config["pool_recycle"] == 7200
        assert config["pool_pre_ping"] is False


class TestEnvHelpers:
    """Test internal environment variable helper functions."""

    def test_get_env_int_returns_default_when_not_set(self):
        """Test _get_env_int returns default when env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TEST_INT_VAR", None)
            result = connection._get_env_int("TEST_INT_VAR", 42)
        assert result == 42

    def test_get_env_int_parses_valid_int(self):
        """Test _get_env_int parses valid integer."""
        with patch.dict(os.environ, {"TEST_INT_VAR": "100"}):
            result = connection._get_env_int("TEST_INT_VAR", 42)
        assert result == 100

    def test_get_env_int_returns_default_on_invalid(self):
        """Test _get_env_int returns default on invalid value."""
        with patch.dict(os.environ, {"TEST_INT_VAR": "invalid"}):
            result = connection._get_env_int("TEST_INT_VAR", 42)
        assert result == 42

    def test_get_env_bool_returns_default_when_not_set(self):
        """Test _get_env_bool returns default when env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TEST_BOOL_VAR", None)
            result = connection._get_env_bool("TEST_BOOL_VAR", True)
        assert result is True

    def test_get_env_bool_parses_true_values(self):
        """Test _get_env_bool recognizes various true values."""
        true_values = ["true", "TRUE", "True", "1", "yes", "YES", "on", "ON"]
        for value in true_values:
            with patch.dict(os.environ, {"TEST_BOOL_VAR": value}):
                result = connection._get_env_bool("TEST_BOOL_VAR", False)
            assert result is True, f"Failed for value: {value}"

    def test_get_env_bool_parses_false_values(self):
        """Test _get_env_bool treats other values as false."""
        false_values = ["false", "FALSE", "0", "no", "off", "anything"]
        for value in false_values:
            with patch.dict(os.environ, {"TEST_BOOL_VAR": value}):
                result = connection._get_env_bool("TEST_BOOL_VAR", True)
            assert result is False, f"Failed for value: {value}"


# =============================================================================
# DATABASE URL TESTS
# =============================================================================


class TestGetDatabaseUrl:
    """Test get_database_url function."""

    def test_get_database_url_returns_string(self):
        """Test get_database_url returns a string."""
        url = connection.get_database_url()
        assert isinstance(url, str)

    def test_get_database_url_is_async(self):
        """Test get_database_url returns async driver URL."""
        url = connection.get_database_url()
        assert "asyncpg" in url or "aiosqlite" in url


# =============================================================================
# ENGINE CREATION TESTS
# =============================================================================


class TestGetAsyncEngine:
    """Test get_async_engine function."""

    def test_get_async_engine_returns_engine(self):
        """Test get_async_engine returns an AsyncEngine."""
        test_url = "sqlite+aiosqlite:///:memory:"
        engine = connection.get_async_engine(test_url, use_null_pool=True)
        assert isinstance(engine, AsyncEngine)

    def test_get_async_engine_with_custom_pool_size(self):
        """Test get_async_engine accepts custom pool settings."""
        test_url = "sqlite+aiosqlite:///:memory:"
        engine = connection.get_async_engine(
            test_url,
            pool_size=20,
            max_overflow=40,
            use_null_pool=True,  # NullPool ignores pool settings but function should accept them
        )
        assert isinstance(engine, AsyncEngine)

    def test_get_async_engine_with_null_pool(self):
        """Test get_async_engine with NullPool for testing."""
        test_url = "sqlite+aiosqlite:///:memory:"
        engine = connection.get_async_engine(test_url, use_null_pool=True)
        assert isinstance(engine, AsyncEngine)

    def test_get_async_engine_uses_config_url_when_none(self):
        """Test get_async_engine loads URL from config when None."""
        with patch.object(connection, "get_database_url") as mock_get_url:
            mock_get_url.return_value = "sqlite+aiosqlite:///:memory:"
            engine = connection.get_async_engine(use_null_pool=True)
            mock_get_url.assert_called_once()
            assert isinstance(engine, AsyncEngine)

    def test_get_async_engine_uses_pool_config(self):
        """Test get_async_engine calls get_pool_config for pool settings."""
        mock_config = {
            "pool_size": 15,
            "max_overflow": 30,
            "pool_recycle": 1800,
            "pool_pre_ping": False,
        }

        # Mock both get_pool_config and create_async_engine to verify behavior
        with (
            patch.object(connection, "get_pool_config", return_value=mock_config) as mock_get_pool,
            patch.object(connection, "create_async_engine") as mock_create,
        ):
            mock_create.return_value = MagicMock(spec=AsyncEngine)
            connection.get_async_engine(
                "postgresql+asyncpg://test:test@localhost/test",
                use_null_pool=False,
            )

            # Verify get_pool_config was called
            mock_get_pool.assert_called_once()

            # Verify create_async_engine received the pool config
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["pool_size"] == 15
            assert call_kwargs["max_overflow"] == 30
            assert call_kwargs["pool_recycle"] == 1800
            assert call_kwargs["pool_pre_ping"] is False

    def test_get_async_engine_explicit_args_override_env(self):
        """Test explicit function arguments override environment config."""
        # Set env vars that would give different values
        with (
            patch.dict(
                os.environ,
                {
                    "DB_POOL_SIZE": "5",
                    "DB_MAX_OVERFLOW": "10",
                },
            ),
            patch.object(connection, "create_async_engine") as mock_create,
        ):
            mock_create.return_value = MagicMock(spec=AsyncEngine)

            # Explicit args should override env vars
            connection.get_async_engine(
                "postgresql+asyncpg://test:test@localhost/test",
                pool_size=25,
                max_overflow=50,
                use_null_pool=False,
            )

            # Verify explicit args were used, not env vars
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["pool_size"] == 25
            assert call_kwargs["max_overflow"] == 50


# =============================================================================
# SESSIONMAKER TESTS
# =============================================================================


class TestGetAsyncSessionmaker:
    """Test get_async_sessionmaker function."""

    def test_get_async_sessionmaker_returns_sessionmaker(self):
        """Test get_async_sessionmaker returns async_sessionmaker."""
        test_url = "sqlite+aiosqlite:///:memory:"
        engine = connection.get_async_engine(test_url, use_null_pool=True)
        session_factory = connection.get_async_sessionmaker(engine)
        assert isinstance(session_factory, async_sessionmaker)

    def test_get_async_sessionmaker_creates_sessions(self):
        """Test sessionmaker can create sessions."""
        test_url = "sqlite+aiosqlite:///:memory:"
        engine = connection.get_async_engine(test_url, use_null_pool=True)
        session_factory = connection.get_async_sessionmaker(engine)
        session = session_factory()
        assert isinstance(session, AsyncSession)

    def test_get_async_sessionmaker_expire_on_commit_default(self):
        """Test expire_on_commit defaults to False for async."""
        test_url = "sqlite+aiosqlite:///:memory:"
        engine = connection.get_async_engine(test_url, use_null_pool=True)
        session_factory = connection.get_async_sessionmaker(engine)
        # expire_on_commit=False is set by default
        assert session_factory.kw.get("expire_on_commit") is False


# =============================================================================
# MODULE-LEVEL OBJECTS TESTS
# =============================================================================


class TestModuleLevelObjects:
    """Test module-level engine and session factory."""

    def test_module_engine_exists(self):
        """Test module-level engine is created."""
        assert connection.engine is not None
        assert isinstance(connection.engine, AsyncEngine)

    def test_module_async_session_exists(self):
        """Test module-level async_session factory is created."""
        assert connection.async_session is not None
        assert isinstance(connection.async_session, async_sessionmaker)

    def test_module_base_exists(self):
        """Test module-level Base class exists."""
        assert connection.Base is not None


# =============================================================================
# SESSION UTILITIES TESTS
# =============================================================================


class TestGetSession:
    """Test get_session context manager."""

    @pytest.mark.asyncio
    async def test_get_session_yields_session(self):
        """Test get_session yields an AsyncSession."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session_factory = MagicMock(return_value=mock_session)

        with patch.object(connection, "async_session", mock_session_factory):
            async with connection.get_session() as session:
                assert session is mock_session

    @pytest.mark.asyncio
    async def test_get_session_commits_on_success(self):
        """Test get_session commits on successful exit."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session_factory = MagicMock(return_value=mock_session)

        with patch.object(connection, "async_session", mock_session_factory):
            async with connection.get_session():
                pass  # Normal exit

        mock_session.commit.assert_awaited_once()
        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_session_rolls_back_on_error(self):
        """Test get_session rolls back on exception."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session_factory = MagicMock(return_value=mock_session)

        with (
            patch.object(connection, "async_session", mock_session_factory),
            pytest.raises(ValueError, match="Test error"),
        ):
            async with connection.get_session():
                raise ValueError("Test error")

        mock_session.rollback.assert_awaited_once()
        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_session_always_closes(self):
        """Test get_session always closes the session."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session_factory = MagicMock(return_value=mock_session)

        with patch.object(connection, "async_session", mock_session_factory):
            try:
                async with connection.get_session():
                    raise RuntimeError("Unexpected error")
            except RuntimeError:
                pass

        mock_session.close.assert_awaited_once()


class TestGetDbSession:
    """Test get_db_session FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_get_db_session_yields_session(self):
        """Test get_db_session yields an AsyncSession."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session_factory = MagicMock(return_value=mock_session)

        with patch.object(connection, "async_session", mock_session_factory):
            gen = connection.get_db_session()
            session = await gen.__anext__()
            assert session is mock_session

    @pytest.mark.asyncio
    async def test_get_async_session_is_alias(self):
        """Test get_async_session is alias for get_db_session."""
        assert connection.get_async_session is connection.get_db_session


# =============================================================================
# HEALTH CHECK TESTS
# =============================================================================


class TestCheckDatabaseConnection:
    """Test check_database_connection function."""

    @pytest.mark.asyncio
    async def test_check_database_connection_success(self):
        """Test check_database_connection returns True on success."""
        mock_connection = AsyncMock()
        mock_connection.execute = AsyncMock()

        # Create a proper async context manager mock
        mock_connect_cm = AsyncMock()
        mock_connect_cm.__aenter__.return_value = mock_connection
        mock_connect_cm.__aexit__.return_value = None

        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_connect_cm

        result = await connection.check_database_connection(custom_engine=mock_engine)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_database_connection_failure(self):
        """Test check_database_connection returns False on failure."""
        # Create a proper async context manager mock that raises
        mock_connect_cm = AsyncMock()
        mock_connect_cm.__aenter__.side_effect = Exception("Connection failed")

        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_connect_cm

        with patch.object(connection, "logger"):
            result = await connection.check_database_connection(custom_engine=mock_engine)
        assert result is False

    @pytest.mark.asyncio
    async def test_check_database_connection_uses_module_engine(self):
        """Test check_database_connection uses module engine by default."""
        mock_connection = AsyncMock()
        mock_connection.execute = AsyncMock()

        # Create a proper async context manager mock
        mock_connect_cm = AsyncMock()
        mock_connect_cm.__aenter__.return_value = mock_connection
        mock_connect_cm.__aexit__.return_value = None

        with patch.object(connection, "engine") as mock_engine:
            mock_engine.connect.return_value = mock_connect_cm

            result = await connection.check_database_connection()
            mock_engine.connect.assert_called()
            assert result is True


# =============================================================================
# TABLE INITIALIZATION TESTS
# =============================================================================


class TestInitDbTables:
    """Test init_db_tables function."""

    @pytest.mark.asyncio
    async def test_init_db_tables_creates_tables(self):
        """Test init_db_tables creates tables from metadata."""
        mock_conn = AsyncMock()
        mock_conn.run_sync = AsyncMock()

        # Create a proper async context manager mock
        mock_begin_cm = AsyncMock()
        mock_begin_cm.__aenter__.return_value = mock_conn
        mock_begin_cm.__aexit__.return_value = None

        mock_engine = MagicMock()
        mock_engine.begin.return_value = mock_begin_cm

        mock_base = MagicMock()
        mock_base.metadata.create_all = MagicMock()

        with patch.object(connection, "logger"):
            await connection.init_db_tables(
                metadata_bases=[mock_base],
                custom_engine=mock_engine,
            )

        mock_conn.run_sync.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_init_db_tables_uses_default_base(self):
        """Test init_db_tables uses module Base when None."""
        mock_conn = AsyncMock()
        mock_conn.run_sync = AsyncMock()

        # Create a proper async context manager mock
        mock_begin_cm = AsyncMock()
        mock_begin_cm.__aenter__.return_value = mock_conn
        mock_begin_cm.__aexit__.return_value = None

        mock_engine = MagicMock()
        mock_engine.begin.return_value = mock_begin_cm

        with patch.object(connection, "logger"):
            await connection.init_db_tables(custom_engine=mock_engine)

        mock_conn.run_sync.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_init_db_tables_multiple_bases(self):
        """Test init_db_tables handles multiple Base classes."""
        mock_conn = AsyncMock()
        mock_conn.run_sync = AsyncMock()

        # Create a proper async context manager mock
        mock_begin_cm = AsyncMock()
        mock_begin_cm.__aenter__.return_value = mock_conn
        mock_begin_cm.__aexit__.return_value = None

        mock_engine = MagicMock()
        mock_engine.begin.return_value = mock_begin_cm

        mock_base1 = MagicMock()
        mock_base2 = MagicMock()

        with patch.object(connection, "logger"):
            await connection.init_db_tables(
                metadata_bases=[mock_base1, mock_base2],
                custom_engine=mock_engine,
            )

        # Should be called once per base
        assert mock_conn.run_sync.await_count == 2


# =============================================================================
# EXPORTS TESTS
# =============================================================================


class TestExports:
    """Test module exports."""

    def test_all_exports_exist(self):
        """Test all items in __all__ exist in module."""
        for name in connection.__all__:
            assert hasattr(connection, name), f"Missing export: {name}"

    def test_base_is_declarative_base(self):
        """Test Base is a SQLAlchemy declarative base."""
        # Base should be a class that can be used for model definitions
        # It has metadata registry but __tablename__ is defined on subclasses
        assert hasattr(connection.Base, "metadata")
        assert hasattr(connection.Base, "registry")

    def test_constants_are_integers(self):
        """Test pool configuration constants are integers."""
        assert isinstance(connection.DEFAULT_POOL_SIZE, int)
        assert isinstance(connection.DEFAULT_MAX_OVERFLOW, int)
        assert isinstance(connection.DEFAULT_POOL_RECYCLE, int)

    def test_pre_ping_is_boolean(self):
        """Test pool pre-ping constant is boolean."""
        assert isinstance(connection.DEFAULT_POOL_PRE_PING, bool)

    def test_get_pool_config_exported(self):
        """Test get_pool_config is in __all__."""
        assert "get_pool_config" in connection.__all__
        assert callable(connection.get_pool_config)
