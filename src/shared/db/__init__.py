"""
Shared database utilities for the AI Operations Platform (AIOP) stack.

This package provides async SQLAlchemy infrastructure for all services.

Quick Start:
    from shared.db import Base, get_db_session, check_database_connection

    # Define models
    class MyModel(Base):
        __tablename__ = "my_table"
        id = Column(Integer, primary_key=True)

    # Use in FastAPI routes
    @router.get("/items")
    async def get_items(session: AsyncSession = Depends(get_db_session)):
        result = await session.execute(select(MyModel))
        return result.scalars().all()

    # Health checks
    @router.get("/health")
    async def health():
        return {"database": await check_database_connection()}

Modules:
    connection: Core async engine and session utilities

See Also:
    - ADR-022: Backend Async Database Migration
    - docs/development/plans/active/PHASE_05_INFRASTRUCTURE_OVERHAUL.md
"""

from shared.db.connection import (
    # Configuration constants
    DEFAULT_MAX_OVERFLOW,
    DEFAULT_POOL_PRE_PING,
    DEFAULT_POOL_RECYCLE,
    DEFAULT_POOL_SIZE,
    # Core exports
    Base,
    async_session,
    # Health check
    check_database_connection,
    engine,
    # Factory functions
    get_async_engine,
    # Session utilities
    get_async_session,
    get_async_sessionmaker,
    get_database_url,
    get_db_session,
    get_session,
    # Table initialization
    init_db_tables,
)

__all__ = [
    "DEFAULT_MAX_OVERFLOW",
    "DEFAULT_POOL_PRE_PING",
    "DEFAULT_POOL_RECYCLE",
    # Configuration constants
    "DEFAULT_POOL_SIZE",
    # Core exports
    "Base",
    "async_session",
    # Health check
    "check_database_connection",
    "engine",
    "get_async_engine",
    "get_async_session",
    "get_async_sessionmaker",
    # Factory functions
    "get_database_url",
    "get_db_session",
    # Session utilities
    "get_session",
    # Table initialization
    "init_db_tables",
]
