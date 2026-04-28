"""
Transaction management module for the retrieval service using SQLAlchemy.

This module provides utilities for managing database transactions with SQLAlchemy's AsyncSession.
"""

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging

from .connection import get_session

logger = configure_logging(service_name="transaction_db")

T = TypeVar("T")


async def in_transaction(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    **kwargs: Any,
) -> T:
    """
    Execute a function within a database transaction.

    This utility wraps a function call within a transactional session,
    handling commit, rollback, and session closing automatically.

    Args:
        func: The async function to execute within the transaction.
              The function must accept an `AsyncSession` as its first argument.
        *args: Positional arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        The return value of the executed function.

    Raises:
        Any exception raised by the executed function.
    """
    db_session_override = kwargs.pop("db_session_override", None)

    if db_session_override and isinstance(db_session_override, AsyncSession):
        logger.debug(f"Using db_session_override for {func.__name__}")
        # If a session is provided, use it directly without managing the transaction.
        # This is useful for tests or nested transactional calls.
        return await func(db_session_override, *args, **kwargs)

    # Default behavior: create a new session and manage the transaction.
    async with get_session() as session:
        return await func(session, *args, **kwargs)


async def with_retry(
    func: Callable[..., Awaitable[T]],
    max_retries: int = 3,
    *args: Any,
    **kwargs: Any,
) -> T:
    """
    Execute a function with retry logic for transient database errors.

    This utility function wraps a function call and retries it on
    `OperationalError`, which can indicate transient connection issues.

    Args:
        func: The async function to execute.
        max_retries: Maximum number of retry attempts.
        *args: Positional arguments for the function.
        **kwargs: Keyword arguments for the function.

    Returns:
        The return value of the executed function.

    Raises:
        The last exception that caused the final retry to fail.
    """
    retries = 0
    last_exception = None

    while retries <= max_retries:
        try:
            # The `in_transaction` function will handle session management.
            return await in_transaction(func, *args, **kwargs)
        except OperationalError as e:
            last_exception = e
            retries += 1
            if retries <= max_retries:
                logger.warning(
                    f"Database operation failed, retrying ({retries}/{max_retries}): {e!s}"
                )
            else:
                logger.error(f"Database operation failed after {max_retries} retries: {e!s}")
                raise last_exception
        except Exception as e:
            # Don't retry on non-operational errors.
            logger.error(f"Database operation failed with non-retryable error: {e!s}")
            raise

    # This should not be reached, but is here for completeness.
    raise RuntimeError("Exited retry loop unexpectedly.")
