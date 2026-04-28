"""
Shared database connection utilities for the AI Operations Platform (AIOP) stack.

This module provides the core async SQLAlchemy infrastructure used by all services.
Services should import from this module for consistent database configuration.

Architecture:
- Async-first design per ADR-022
- Connection pooling configured for production workloads
- Transaction-managed sessions with automatic commit/rollback
- FastAPI dependency for route injection

Usage:
    # In service code
    from shared.db.connection import Base, get_db_session, check_database_connection

    # For models
    class MyModel(Base):
        __tablename__ = "my_table"
        ...

    # For routes
    @router.get("/items")
    async def get_items(session: AsyncSession = Depends(get_db_session)):
        result = await session.execute(select(Item))
        return result.scalars().all()

Connection Pool Settings (P5-A4, P5-A7):
    Default values (configurable via environment):
    - DB_POOL_SIZE: 10 (concurrent connections)
    - DB_MAX_OVERFLOW: 20 (additional connections under load)
    - DB_POOL_RECYCLE: 3600 (recycle connections hourly, in seconds)
    - DB_POOL_PRE_PING: true (verify connections before use)

    Environment variables allow per-deployment tuning without code changes.
    Use higher values for production, lower for development/testing.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from shared.config.loader import load_database_config

# Module-level logger (services can override with their own)
logger = logging.getLogger(__name__)

# Base class for all models - includes AsyncAttrs for async relationship loading
Base = declarative_base(cls=AsyncAttrs)


# =============================================================================
# CONNECTION POOL CONFIGURATION (ADR-022, P5-A7)
# =============================================================================

# Default constants (can be overridden via environment)
DEFAULT_POOL_SIZE = 10
DEFAULT_MAX_OVERFLOW = 20
DEFAULT_POOL_RECYCLE = 3600  # 1 hour
DEFAULT_POOL_PRE_PING = True


def get_pool_config() -> dict[str, Any]:
    """
    Get connection pool configuration from environment or defaults.

    Environment variables:
        - DB_POOL_SIZE: Number of connections in pool (default: 10)
        - DB_MAX_OVERFLOW: Extra connections under load (default: 20)
        - DB_POOL_RECYCLE: Connection recycle time in seconds (default: 3600)
        - DB_POOL_PRE_PING: Verify connections before use (default: true)

    Returns:
        dict: Pool configuration suitable for create_async_engine.
    """
    db_config = load_database_config()
    return {
        "pool_size": db_config.pool_size or DEFAULT_POOL_SIZE,
        "max_overflow": db_config.max_overflow or DEFAULT_MAX_OVERFLOW,
        "pool_recycle": db_config.pool_recycle or DEFAULT_POOL_RECYCLE,
        "pool_pre_ping": (
            db_config.pool_pre_ping
            if db_config.pool_pre_ping is not None
            else DEFAULT_POOL_PRE_PING
        ),
    }


__all__ = [
    "DEFAULT_MAX_OVERFLOW",
    "DEFAULT_POOL_PRE_PING",
    "DEFAULT_POOL_RECYCLE",
    "DEFAULT_POOL_SIZE",
    "Base",
    "async_session",
    "check_database_connection",
    "engine",
    "get_async_engine",
    "get_async_session",
    "get_async_sessionmaker",
    "get_database_url",
    "get_db_session",
    "get_pool_config",
    "get_session",
    "init_db_tables",
]


def get_database_url() -> str:
    """
    Get database URL using centralized configuration.

    Returns:
        str: PostgreSQL async connection string (postgresql+asyncpg://...).
    """
    db_config = load_database_config()
    return cast("str", db_config.get_connection_string(async_driver=True))


def get_async_engine(
    db_url: str | None = None,
    pool_size: int | None = None,
    max_overflow: int | None = None,
    pool_recycle: int | None = None,
    pool_pre_ping: bool | None = None,
    echo: bool = False,
    use_null_pool: bool = False,
    **kwargs: Any,
) -> AsyncEngine:
    """
    Create an async SQLAlchemy engine with connection pooling.

    Pool settings are resolved in this order:
    1. Explicit function arguments (if provided)
    2. Environment variables (DB_POOL_SIZE, DB_MAX_OVERFLOW, etc.)
    3. Default constants

    Args:
        db_url: Database URL. If None, loads from config.
        pool_size: Number of connections to keep in the pool.
        max_overflow: Additional connections allowed under load.
        pool_recycle: Seconds before recycling connections.
        pool_pre_ping: Verify connections before use.
        echo: Enable SQL logging for debugging.
        use_null_pool: Disable pooling (useful for testing).
        **kwargs: Additional engine options.

    Returns:
        AsyncEngine: Configured async SQLAlchemy engine.

    Example:
        # Default production settings (uses env vars or defaults)
        engine = get_async_engine()

        # Testing with null pool
        engine = get_async_engine(use_null_pool=True)

        # Custom settings (override env vars)
        engine = get_async_engine(pool_size=20, max_overflow=40)
    """
    if db_url is None:
        db_url = get_database_url()

    # Build engine options
    engine_options: dict[str, Any] = {
        "echo": echo,
        "future": True,
        **kwargs,
    }

    # Configure pooling
    if use_null_pool:
        engine_options["poolclass"] = NullPool
    else:
        # Get pool config from environment/defaults
        pool_config = get_pool_config()

        # Override with explicit arguments if provided
        engine_options.update(
            {
                "pool_size": (pool_size if pool_size is not None else pool_config["pool_size"]),
                "max_overflow": (
                    max_overflow if max_overflow is not None else pool_config["max_overflow"]
                ),
                "pool_recycle": (
                    pool_recycle if pool_recycle is not None else pool_config["pool_recycle"]
                ),
                "pool_pre_ping": (
                    pool_pre_ping if pool_pre_ping is not None else pool_config["pool_pre_ping"]
                ),
            }
        )

    return create_async_engine(db_url, **engine_options)


def get_async_sessionmaker(
    async_engine: AsyncEngine,
    expire_on_commit: bool = False,
    autocommit: bool = False,
    autoflush: bool = False,
) -> async_sessionmaker[AsyncSession]:
    """
    Create an async session factory bound to an engine.

    Args:
        async_engine: AsyncEngine to bind sessions to.
        expire_on_commit: Expire objects after commit (default False for async).
        autocommit: Enable autocommit mode (default False).
        autoflush: Enable autoflush mode (default False).

    Returns:
        async_sessionmaker: Factory for creating AsyncSession instances.
    """
    return async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=expire_on_commit,
        autocommit=autocommit,
        autoflush=autoflush,
    )


# =============================================================================
# MODULE-LEVEL ENGINE AND SESSION FACTORY
# =============================================================================

# Create engine and sessionmaker at module level for reuse
DATABASE_URL = get_database_url()
engine = get_async_engine(DATABASE_URL)
async_session = get_async_sessionmaker(engine)


# =============================================================================
# SESSION UTILITIES
# =============================================================================


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a transactional scope around a series of operations.

    This context manager handles:
    - Session creation from the module-level factory
    - Automatic commit on successful completion
    - Automatic rollback on exception
    - Session cleanup (close)

    Usage:
        async with get_session() as session:
            session.add(new_item)
            # Auto-commits on exit, rolls back on exception

    Yields:
        AsyncSession: Transaction-managed async session.

    Raises:
        Exception: Re-raises any exception after rollback.
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
    FastAPI dependency for database sessions.

    This dependency provides a transaction-managed async session for routes.
    The session auto-commits on success and rolls back on error.

    Usage:
        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_db_session)):
            result = await session.execute(select(Item))
            return result.scalars().all()

    Yields:
        AsyncSession: Transaction-managed async session.
    """
    async with get_session() as session:
        yield session


# Alias for backwards compatibility
get_async_session = get_db_session


# =============================================================================
# HEALTH CHECK
# =============================================================================


async def check_database_connection(
    custom_engine: AsyncEngine | None = None,
) -> bool:
    """
    Check database connection by executing a simple query.

    This function is used for health checks to verify database connectivity.

    Args:
        custom_engine: Optional engine to use. Defaults to module engine.

    Returns:
        bool: True if connection is successful, False otherwise.

    Example:
        # In health endpoint
        @router.get("/health")
        async def health():
            db_ok = await check_database_connection()
            return {"database": "healthy" if db_ok else "unhealthy"}
    """
    target_engine = custom_engine or engine
    try:
        async with target_engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        logger.debug("Database connection check successful.")
        return True
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Database connection check failed: %s", e, exc_info=True)
        return False


# =============================================================================
# TABLE INITIALIZATION
# =============================================================================


async def init_db_tables(
    metadata_bases: list[Any] | None = None,
    custom_engine: AsyncEngine | None = None,
) -> None:
    """
    Initialize database tables from SQLAlchemy metadata.

    This is a helper function for services to create their tables.
    Services should call this during startup with their model Base classes.

    Args:
        metadata_bases: List of Base classes with metadata to create.
                       Defaults to [Base] if None.
        custom_engine: Optional engine to use. Defaults to module engine.

    Example:
        # In service startup
        from shared.db.connection import init_db_tables, Base
        from myservice.models import ServiceBase

        async def startup():
            await init_db_tables([Base, ServiceBase])

    Note:
        Services may define their own init_db() for custom initialization
        logic (importing models, etc.). This function handles the generic
        table creation pattern.
    """
    target_engine = custom_engine or engine
    bases = metadata_bases or [Base]

    async with target_engine.begin() as conn:
        for base in bases:
            await conn.run_sync(base.metadata.create_all)

    logger.info("Database tables initialized for %d base classes.", len(bases))
