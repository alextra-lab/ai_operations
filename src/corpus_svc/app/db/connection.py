"""
Database connection utilities for the Corpus Service using SQLAlchemy.

This module provides utilities for connecting to the PostgreSQL database,
managing sessions, and executing queries with proper error handling,
leveraging the shared SQLAlchemy async configuration.

Architecture:
- Uses async SQLAlchemy engine from shared.db.connection
- Provides transaction-managed session context for proper commit/rollback
- FastAPI dependency `get_db_session` for route injection

Note: Connection pool settings are managed in shared.db.connection (P5-A4).
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.connection import Base, async_session, engine
from shared.logging_utils.fastapi import configure_logging
from shared.telemetry_utils.telemetry import create_span

logger = configure_logging(service_name="corpus_db")

# Re-export for convenience
__all__ = [
    "Base",
    "async_session",
    "check_database_connection",
    "engine",
    "get_db_session",
    "get_session",
    "init_db",
]


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a transactional scope around a series of operations.

    This is an async context manager that provides a SQLAlchemy `AsyncSession`.
    It handles session creation, commit, rollback, and closing.

    Usage:
        async with get_session() as session:
            # Operations auto-commit on success, rollback on error
            session.add(model)

    Yields:
        AsyncSession: A SQLAlchemy asynchronous session object.
    """
    session: AsyncSession = async_session()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error("Session rollback due to error: %s", e, exc_info=True)
        raise
    finally:
        await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get a database session.

    This dependency provides a transaction-managed async session for routes.
    The session auto-commits on success and rolls back on error.

    Usage:
        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_db_session)):
            result = await session.execute(select(Item))
            return result.scalars().all()

    Yields:
        AsyncSession: A SQLAlchemy asynchronous session.
    """
    async with get_session() as session:
        yield session


async def check_database_connection() -> bool:
    """
    Check database connection by executing a simple query using SQLAlchemy.

    This function is used for health checks to verify database connectivity.

    Returns:
        True if connection is successful, False otherwise.
    """
    try:
        with create_span("check_db_connection_corpus"):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        logger.info("Database connection check successful.")
        return True
    except Exception as e:
        logger.error("Database connection check failed: %s", e, exc_info=True)
        return False


async def init_db() -> None:
    """
    Initialize the corpus service database tables.

    This function creates all tables defined in the models' Base metadata.
    Called during application startup to ensure schema exists.

    Note: This also imports models to register table definitions.
    """
    from . import models  # Import to register table definitions

    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    logger.info("Corpus service database tables initialized.")
