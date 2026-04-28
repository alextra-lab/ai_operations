"""
Shared database utilities for user management.

This module provides async database connection and session management
utilities that can be used across all services.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.config.loader import load_database_config
from shared.logging_utils.fastapi import configure_logging

from .models import Base

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio.engine import AsyncEngine

logger = configure_logging(service_name="auth_database")


class DatabaseManager:
    """
    Centralized async database manager for user authentication.

    This class manages async database connections and sessions for user management
    across all services.
    """

    def __init__(self, database_url: str | None = None):
        """
        Initialize the database manager.

        Args:
            database_url: Database connection URL. If None, will use environment variable.
        """
        # Use the new asyncpg driver by default
        db_config = load_database_config()
        self.database_url = database_url or db_config.get_connection_string(async_driver=True)

        # Create async engine with connection pooling, but avoid pool_size/max_overflow for SQLite
        engine_kwargs = {"pool_pre_ping": True, "pool_recycle": 3600, "future": True}
        if not self.database_url.startswith("sqlite"):
            engine_kwargs["pool_pre_ping"] = db_config.pool_pre_ping
            engine_kwargs["pool_recycle"] = db_config.pool_recycle
            engine_kwargs["pool_size"] = db_config.pool_size
            engine_kwargs["max_overflow"] = db_config.max_overflow
        self.engine: AsyncEngine = create_async_engine(self.database_url, **engine_kwargs)

        # Create async session factory
        self.SessionLocal = async_sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine, expire_on_commit=False
        )

    async def create_tables(self) -> None:
        """Create all tables defined in the models."""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}", exc_info=True)
            raise

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async database session.

        Yields:
            SQLAlchemy AsyncSession
        """
        async with self.SessionLocal() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}", exc_info=True)
                raise

    async def test_connection(self) -> bool:
        """
        Test the async database connection.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}", exc_info=True)
            return False


# Global database manager instance (lazy-initialized)
_db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    """
    Get or create the global database manager instance (lazy initialization).

    This avoids instantiating the database connection at module import time,
    which can cause issues with:
    - Environment variables not being set yet
    - Test configuration
    - Container startup timing

    Returns:
        DatabaseManager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


# Convenience function for getting async database sessions
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for getting async database sessions.
    Yields:
        SQLAlchemy AsyncSession
    """
    async with get_db_manager().get_session() as session:
        yield session


async def init_database() -> None:
    """Initialize the database by creating all tables."""
    await get_db_manager().create_tables()


async def test_database_connection() -> bool:
    """Test the async database connection."""
    return await get_db_manager().test_connection()
