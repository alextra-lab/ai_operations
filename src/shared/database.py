"""
Shared database utilities for all services.

This module re-exports the core database utilities from shared.db for convenience.
Services can import directly from here or from shared.db.connection.

Usage:
    # Option 1: Import from this module
    from shared.database import get_db, get_async_session

    # Option 2: Import from shared.db
    from shared.db import get_db_session, get_session

Both approaches provide the same functionality.

Note: The `get_db` context manager and `get_async_session` dependency
are provided for backwards compatibility. New code should prefer
importing from `shared.db.connection` directly.
"""

# Re-export all utilities from shared.db.connection
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

# Backwards compatibility alias
get_db = get_session  # Context manager (alias for get_session)

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
    # Session utilities
    "get_db",
    "get_db_session",
    "get_session",
    # Table initialization
    "init_db_tables",
]
