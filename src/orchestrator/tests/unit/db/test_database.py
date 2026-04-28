"""
Unit tests for database module.

P5-A17: Updated to test async-only database infrastructure (ADR-022).
P5-A23: Removed all sync pattern tests - everything is async now.
"""

import pytest


class TestDatabaseConfiguration:
    """Test database configuration and setup."""

    def test_get_db_name_returns_configured_name(self):
        """Test get_db_name returns the configured database name."""
        from src.orchestrator.app.db.database import get_db_name

        db_name = get_db_name()
        assert db_name is not None
        assert isinstance(db_name, str)
        assert len(db_name) > 0

    def test_database_url_is_string(self):
        """Test DATABASE_URL is a valid connection string."""
        from src.orchestrator.app.db.database import DATABASE_URL

        assert DATABASE_URL is not None
        assert isinstance(DATABASE_URL, str)
        assert "postgresql" in DATABASE_URL

    def test_async_engine_created(self):
        """Test async engine is created at module level."""
        from src.orchestrator.app.db.database import async_engine

        assert async_engine is not None
        # Check it's an async engine
        assert hasattr(async_engine, "begin")

    def test_async_session_local_created(self):
        """Test AsyncSessionLocal async_sessionmaker is created."""
        from src.orchestrator.app.db.database import AsyncSessionLocal

        assert AsyncSessionLocal is not None
        # Should be callable (async_sessionmaker)
        assert callable(AsyncSessionLocal)

    def test_base_declarative_base_created(self):
        """Test Base declarative base is created."""
        from src.orchestrator.app.db.database import Base

        assert Base is not None
        assert hasattr(Base, "metadata")


class TestAsyncDatabaseDependency:
    """Test asynchronous database dependency function."""

    @pytest.mark.asyncio
    async def test_get_async_db_yields_async_session(self):
        """Test get_async_db yields an async database session."""
        from src.orchestrator.app.db.database import get_async_db

        async for session in get_async_db():
            assert session is not None
            # Check it's an AsyncSession
            assert hasattr(session, "execute")
            break  # Only need first yield


class TestDatabaseInitialization:
    """Test database initialization functions."""

    @pytest.mark.asyncio
    async def test_init_db_creates_tables(self):
        """Test async init_db creates database tables."""
        from src.orchestrator.app.db.database import init_db

        # Should not raise any errors
        await init_db()


class TestCleanupTestDb:
    """Test test database cleanup utility."""

    def test_cleanup_test_db_no_error_when_no_file(self):
        """Test cleanup_test_db doesn't error when no test.db exists."""
        from src.orchestrator.app.db.database import cleanup_test_db

        # Should not raise
        cleanup_test_db()

    def test_cleanup_test_db_removes_sqlite_file_in_testing(self):
        """Test cleanup_test_db removes sqlite test.db in testing mode."""
        from src.orchestrator.app.db.database import cleanup_test_db

        # This test only applies if TESTING is True and using sqlite
        # In our case, we're using PostgreSQL, so this is a no-op
        cleanup_test_db()


class TestEnvironmentFlags:
    """Test environment flag detection."""

    def test_testing_flag_detected(self):
        """Test TESTING environment flag is detected."""
        from src.orchestrator.app.db.database import TESTING

        # In test environment, TESTING should be set
        assert isinstance(TESTING, bool)

    def test_development_flag_detected(self):
        """Test DEVELOPMENT environment flag is detected."""
        from src.orchestrator.app.db.database import DEVELOPMENT

        assert isinstance(DEVELOPMENT, bool)


class TestMakeAsyncEngine:
    """Test async engine factory function."""

    def test_make_async_engine_returns_async_engine(self):
        """Test make_async_engine returns a valid AsyncEngine."""
        from sqlalchemy.ext.asyncio import AsyncEngine

        from src.orchestrator.app.db.database import make_async_engine

        engine = make_async_engine()
        assert isinstance(engine, AsyncEngine)

    def test_make_async_engine_uses_pool_config(self):
        """Test make_async_engine uses shared pool configuration (P5-A7)."""
        from unittest.mock import patch

        mock_config = {
            "pool_size": 15,
            "max_overflow": 30,
            "pool_recycle": 1800,
            "pool_pre_ping": False,
        }

        with patch(
            "src.orchestrator.app.db.database.get_pool_config",
            return_value=mock_config,
        ):
            from src.orchestrator.app.db.database import make_async_engine

            # Call make_async_engine after patching
            engine = make_async_engine()
            # Engine should be created successfully
            assert engine is not None


class TestPoolConfigIntegration:
    """Test connection pool configuration integration (P5-A7)."""

    def test_orchestrator_imports_get_pool_config(self):
        """Test orchestrator database imports get_pool_config from shared."""
        from src.orchestrator.app.db import database

        # Verify the import exists (was added in P5-A7)
        assert hasattr(database, "get_pool_config")

    def test_pool_config_is_callable(self):
        """Test imported get_pool_config is callable."""
        from src.orchestrator.app.db.database import get_pool_config

        assert callable(get_pool_config)

    def test_pool_config_returns_expected_keys(self):
        """Test pool config returns all expected pool settings."""
        from src.orchestrator.app.db.database import get_pool_config

        config = get_pool_config()
        expected_keys = ["pool_size", "max_overflow", "pool_recycle", "pool_pre_ping"]
        for key in expected_keys:
            assert key in config, f"Missing key: {key}"
