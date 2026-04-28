"""
Database module for creating engine, session, and initializing the database schema.

This module sets up async SQLAlchemy infrastructure (ADR-022).

P5-A23 Phase 7: Removed all sync database patterns (Nov 2025).
All database operations now use async patterns.

The init_db() function creates all tables defined in the models.

Connection pool settings are loaded from shared.db.connection (P5-A7) and can be
configured via environment variables: DB_POOL_SIZE, DB_MAX_OVERFLOW, DB_POOL_RECYCLE,
DB_POOL_PRE_PING.
"""

import os
from collections.abc import AsyncGenerator
from typing import cast

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from shared.config.loader import load_database_config, load_orchestrator_config
from shared.db.connection import get_pool_config
from shared.logging_utils.fastapi import configure_logging

# Initialize a logger for the database module using the centralized logging utility
logger = configure_logging(service_name="database", log_level="INFO", log_format="json")

# Base class for declarative class definitions.
Base = declarative_base()

# Check environment
TESTING = os.environ.get("TESTING", "0") == "1"
DEVELOPMENT = os.environ.get("DEVELOPMENT", "0") == "1"

# =============================================================================
# FEATURE FLAGS (ADR-030: Stateless Architecture)
# =============================================================================

# Load database configuration from centralized config
db_config = load_database_config()

# Get DB connection parameters from centralized config
pg_user = db_config.user
pg_password = db_config.password
pg_host = db_config.host
pg_port = db_config.port
explicit_db_name = db_config.database
orchestrator_config = load_orchestrator_config()
# Transcript storage feature flag - controls whether PII can be stored via
# query history endpoints. Default is false for Core Edition (stateless).
# Set to true for Plus Edition with full history storage capabilities.
ENABLE_TRANSCRIPT_STORAGE = orchestrator_config.transcript_storage_enabled


def get_db_name() -> str:
    """
    Get database name from centralized configuration.

    Returns:
        str: Database name from config.
    """
    return cast("str", explicit_db_name)


# =============================================================================
# ASYNC ENGINE (ADR-022)
# =============================================================================


def make_async_engine() -> AsyncEngine:
    """
    Create an async SQLAlchemy engine.

    Pool settings are loaded from environment variables via get_pool_config().

    Returns:
        AsyncEngine: Configured async engine for PostgreSQL.
    """
    connection_url = db_config.get_connection_string(async_driver=True)
    pool_config = get_pool_config()
    return create_async_engine(
        connection_url,
        pool_pre_ping=pool_config["pool_pre_ping"],
        pool_size=pool_config["pool_size"],
        max_overflow=pool_config["max_overflow"],
        pool_recycle=pool_config["pool_recycle"],
        echo=False,
    )


# Async engine and session factory (for migrated routers)
async_engine = make_async_engine()
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Database URL for reference (async)
DATABASE_URL = db_config.get_connection_string(async_driver=True)

db_name = get_db_name()
logger.info("********* Application is using Database: %s ********* ", db_name)


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================


async def init_db() -> None:
    """
    Initialize the database asynchronously.

    This function imports the models module to ensure that all table definitions
    are registered. It then uses run_sync to create all tables defined in the
    models' Base metadata.
    """
    from shared.auth.models import Base as AuthBase  # Import shared auth models

    from . import models, models_rbac  # Register model metadata

    _ = models_rbac  # Silence linters about unused import

    async with async_engine.begin() as conn:
        # Create tables for both backend-specific models and shared auth models
        await conn.run_sync(models.Base.metadata.create_all)
        await conn.run_sync(AuthBase.metadata.create_all)


# =============================================================================
# SESSION DEPENDENCIES
# =============================================================================


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async dependency function to get a database session.

    Yields an async database session and ensures it is closed after the request.
    All routers use this async dependency (ADR-022).
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# =============================================================================
# TEST UTILITIES
# =============================================================================


def cleanup_test_db() -> None:
    """
    Clean up the test database by removing the file.

    This should be called after tests complete to ensure a fresh database
    for the next test run.
    """
    if TESTING and DATABASE_URL.startswith("sqlite") and os.path.exists("./test.db"):
        os.remove("./test.db")
