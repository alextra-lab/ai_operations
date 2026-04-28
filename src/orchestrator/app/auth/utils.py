# pylint: disable=import-error
"""
Utility module for authentication and database operations.

This module contains helper functions for password hashing, user authentication,
JWT token creation and verification, database access for user data, and
refresh token management operations.

All functions use async patterns (ADR-022).
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth.models import RefreshToken, User
from shared.logging_utils.fastapi import configure_logging

from ..db.database import AsyncSessionLocal

# Properly configure logger for this module
logger = configure_logging(service_name="auth_utils", log_level="INFO", log_format="json")

# Password hashing context using bcrypt.
# Configure to work with bcrypt 5.0+ by setting truncate_error=False
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__truncate_error=False,  # Allow automatic truncation for bcrypt 5.0+
    bcrypt__ident="2b",  # Use 2b variant explicitly
)


# =============================================================================
# ASYNC DATABASE SESSION (ADR-022)
# =============================================================================


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async dependency function that provides an AsyncSession.

    Yields:
        AsyncSession: An async SQLAlchemy session, closed after use.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# =============================================================================
# PASSWORD UTILITIES (sync - no DB operations)
# =============================================================================


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password.

    Note: bcrypt has a 72-byte limit. Passwords are truncated to 72 bytes
    before verification to ensure compatibility with bcrypt 5.0+.

    Args:
        plain_password (str): The plain text password.
        hashed_password (str): The hashed password.

    Returns:
        bool: True if the password matches the hash, otherwise False.
    """
    # Truncate password to 72 bytes for bcrypt compatibility
    password_bytes = plain_password.encode("utf-8")[:72]
    password_truncated = password_bytes.decode("utf-8", errors="ignore")
    return bool(pwd_context.verify(password_truncated, hashed_password))


def get_password_hash(password: str) -> str:
    """
    Hash a password for secure storage.

    Note: bcrypt has a 72-byte limit. Passwords are truncated to 72 bytes
    before hashing to ensure compatibility with bcrypt 5.0+.

    Args:
        password (str): The plain text password to hash.

    Returns:
        str: The hashed password.
    """
    # Truncate password to 72 bytes for bcrypt compatibility
    password_bytes = password.encode("utf-8")[:72]
    password_truncated = password_bytes.decode("utf-8", errors="ignore")
    return str(pwd_context.hash(password_truncated))


# =============================================================================
# ASYNC USER FUNCTIONS (ADR-022)
# =============================================================================


async def get_user(db: AsyncSession, username: str) -> User | None:
    """
    Retrieve a user by username from the database (async).

    Args:
        db (AsyncSession): The async database session.
        username (str): The username of the user to retrieve.

    Returns:
        Optional[User]: The User object if found, otherwise None.
    """
    result = await db.execute(select(User).where(User.username.ilike(username)))
    user = result.scalar_one_or_none()
    if user:
        logger.debug("User found in database", extra={"username": username})
    else:
        logger.debug("User not found in database", extra={"username": username})
    return user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    """
    Authenticate a user using a username and password (async).

    Args:
        db (AsyncSession): The async database session.
        username (str): The username of the user.
        password (str): The plain text password provided by the user.

    Returns:
        Optional[User]: The authenticated User object if credentials are valid, otherwise None.
    """
    user = await get_user(db, username)
    if not user:
        logger.info(
            "Authentication failed: user not found",
            extra={
                "username": username,
                "event": "auth_failure",
                "reason": "user_not_found",
            },
        )
        return None

    # Normalize user ID for consistent logging (id is non-nullable PK)
    user_id_str = str(user.id)

    hashed_password = str(user.hashed_password)
    if not verify_password(password, hashed_password):
        logger.info(
            "Authentication failed: invalid password",
            extra={
                "username": username,
                "user_id": user_id_str,
                "event": "auth_failure",
                "reason": "invalid_password",
            },
        )
        return None

    logger.info(
        "User authenticated successfully",
        extra={
            "username": username,
            "user_id": user_id_str,
            "role": user.role,
            "event": "auth_success",
        },
    )
    return user


# =============================================================================
# ASYNC REFRESH TOKEN FUNCTIONS (ADR-022)
# =============================================================================


async def store_refresh_token(
    db: AsyncSession, user_id: UUID | str | Any, token: str, expires_at: datetime
) -> RefreshToken:
    """
    Store a refresh token in the database (async).

    Args:
        db (AsyncSession): The async database session.
        user_id: The ID of the user associated with the token.
        token (str): The refresh token string.
        expires_at (datetime): When the token expires.

    Returns:
        RefreshToken: The created RefreshToken object.
    """
    # Normalize user_id to UUID (callers pass user.id, uuid.uuid4(), or str)
    if isinstance(user_id, str):
        try:
            import uuid

            normalized_user_id = uuid.UUID(user_id)
        except ValueError:
            logger.error("Invalid UUID string format", extra={"user_id": user_id})
            raise
    else:
        normalized_user_id = user_id

    refresh_token = RefreshToken(
        token=token,
        user_id=normalized_user_id,
        expires_at=expires_at,
        revoked=False,
        created_at=datetime.now(UTC),
    )
    db.add(refresh_token)
    await db.commit()
    await db.refresh(refresh_token)

    # Normalize user_id for logging
    user_id_for_log = str(normalized_user_id) if normalized_user_id else None

    logger.info(
        "Refresh token stored",
        extra={
            "user_id": user_id_for_log,
            "expires_at": expires_at.isoformat(),
            "token_id": refresh_token.id,
        },
    )
    return refresh_token


async def get_refresh_token(db: AsyncSession, token: str) -> RefreshToken | None:
    """
    Retrieve a refresh token from the database (async).

    Args:
        db (AsyncSession): The async database session.
        token (str): The refresh token string to look up.

    Returns:
        Optional[RefreshToken]: The RefreshToken object if found, otherwise None.
    """
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == token))
    rt = result.scalar_one_or_none()
    if rt:
        logger.debug("Refresh token found", extra={"token": token})
    else:
        logger.debug("Refresh token not found", extra={"token": token})
    return rt


async def validate_refresh_token(db: AsyncSession, token: str) -> User | None:
    """
    Validate a refresh token and return the associated user if valid (async).

    A token is considered valid if:
    - It exists in the database
    - It has not been revoked
    - It has not expired

    Args:
        db (AsyncSession): The async database session.
        token (str): The refresh token string to validate.

    Returns:
        Optional[User]: The User object associated with the token if valid, otherwise None.
    """
    db_token = await get_refresh_token(db, token)

    if db_token is None:
        logger.info(
            "Refresh token validation failed: not found",
            extra={
                "token": token,
                "event": "token_validation_failure",
                "reason": "token_not_found",
            },
        )
        return None

    # Normalize user ID for consistent logging (user_id is non-nullable FK)
    user_id_str = str(db_token.user_id)

    revoked_status = getattr(db_token, "revoked", False)
    if isinstance(revoked_status, bool) and revoked_status:
        logger.info(
            "Refresh token validation failed: already revoked",
            extra={
                "token": token,
                "user_id": user_id_str,
                "event": "token_validation_failure",
                "reason": "token_revoked",
            },
        )
        return None

    current_time = datetime.now(UTC)
    token_expires = getattr(db_token, "expires_at", None)
    if token_expires is None or token_expires < current_time:
        logger.info(
            "Refresh token validation failed: expired",
            extra={
                "token": token,
                "user_id": user_id_str,
                "event": "token_validation_failure",
                "reason": "token_expired",
                "expires_at": token_expires.isoformat() if token_expires else None,
            },
        )
        return None

    logger.info(
        "Refresh token validated successfully",
        extra={
            "token": token,
            "user_id": user_id_str,
            "event": "token_validation_success",
        },
    )
    # For async, we need to eagerly load the user relationship
    # Since we used scalar_one_or_none(), we need to access the user
    return db_token.user


async def revoke_refresh_token(db: AsyncSession, token: str) -> bool:
    """
    Revoke a refresh token, preventing its further use (async).

    Args:
        db (AsyncSession): The async database session.
        token (str): The refresh token string to revoke.

    Returns:
        bool: True if the token was successfully revoked, False if the token doesn't
              exist or was already revoked.
    """
    db_token = await get_refresh_token(db, token)
    if db_token is None:
        logger.info(
            "Revoke refresh token failed: not found",
            extra={
                "token": token,
                "event": "token_revoke_failure",
                "reason": "token_not_found",
            },
        )
        return False

    # Normalize user ID for consistent logging (user_id is non-nullable FK)
    user_id_str = str(db_token.user_id)

    revoked_status = getattr(db_token, "revoked", False)
    if isinstance(revoked_status, bool) and revoked_status:
        logger.info(
            "Revoke refresh token failed: already revoked",
            extra={
                "token": token,
                "user_id": user_id_str,
                "event": "token_revoke_failure",
                "reason": "already_revoked",
            },
        )
        return False

    revoked_at = datetime.now(UTC)
    db_token.revoked = True  # type: ignore[assignment]
    db_token.revoked_at = revoked_at  # type: ignore[assignment]
    await db.commit()

    logger.info(
        "Refresh token revoked successfully",
        extra={
            "token": token,
            "user_id": user_id_str,
            "revoked_at": revoked_at.isoformat(),
            "event": "token_revoke_success",
        },
    )
    return True
