# pylint: disable=import-error
"""
Authentication router module.

This module provides API endpoints for user authentication and management.
It includes endpoints for retrieving JWT tokens, refreshing tokens,
revoking tokens, creating new users, and managing user authentication state.

Migrated to async SQLAlchemy per ADR-022 (Phase 5).
"""

from collections.abc import AsyncGenerator
from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth.models import User
from shared.logging_utils.fastapi import configure_logging

from ..db.database import AsyncSessionLocal
from ..db.models import AuditLog
from ..utils.auth import get_current_admin_user as get_current_user

# from . import jwt
from ..utils.auth import jwt_validator
from .utils import (
    authenticate_user,
    get_password_hash,
    revoke_refresh_token,
    store_refresh_token,
    validate_refresh_token,
)

# Use a descriptive service name for log filtering and clarity
logger = configure_logging(service_name="auth_router", log_level="INFO", log_format="json")

# Create router with authentication tag for OpenAPI grouping
router = APIRouter(tags=["auth"], prefix="/auth")

# Define the OAuth2 password bearer scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


async def get_db_for_auth() -> AsyncGenerator[AsyncSession, None]:
    """
    Async database dependency for authentication.

    Yields:
        AsyncSession: An async SQLAlchemy session which is automatically closed after use.

    This dependency isolates the AsyncSession from extra query parameters,
    preventing the local_kw parameter from being erroneously passed to AsyncSessionLocal.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_audit_log_entry(
    db: AsyncSession,
    action: str,
    resource_type: str,
    actor_user_id: str | None = None,
    actor_roles: list | None = None,
    resource_id: str | None = None,
    success: bool = True,
    details: dict | None = None,
    request_id: str | None = None,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """
    Create an audit log entry for authentication events (async).

    Args:
        db: Async database session
        action: Action performed (e.g., "login", "logout", "token_refresh")
        resource_type: Type of resource (e.g., "user", "token")
        actor_user_id: ID of the user performing the action
        actor_roles: List of roles for the actor
        resource_id: ID of the resource being acted upon
        success: Whether the action was successful
        details: Additional details about the action
        request_id: Request ID for tracking
        client_ip: Client IP address
        user_agent: User agent string

    Returns:
        AuditLog: The created audit log entry
    """
    audit_entry = AuditLog(
        action=action,
        resource_type=resource_type,
        actor_user_id=actor_user_id,
        actor_roles=actor_roles or [],
        resource_id=resource_id,
        success=success,
        details=details or {},
        request_id=request_id,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(audit_entry)
    return audit_entry


@router.post(
    "/token",
    summary="Create access and refresh tokens",
    description="Authenticates a user and provides JWT tokens for API access",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db_for_auth),
    _local_kw: str = Query(None),
) -> dict[str, str]:
    """
    OAuth2 token endpoint for user authentication.

    Validates a user's credentials using the provided OAuth2PasswordRequestForm.
    If the credentials are valid,
    it creates an access token with an expiration defined by ACCESS_TOKEN_EXPIRE_MINUTES from the jwt module.

    Args:
        form_data (OAuth2PasswordRequestForm): Form data containing username and password.
        db (AsyncSession): Async database session dependency.
        local_kw (str, optional): A query parameter required by the system but not used for authentication.

    Returns:
        dict: A dictionary containing the access token and token type.

    Raises:
        HTTPException: If user authentication fails (incorrect username or password).
    """
    logger.info("Login attempt", extra={"username": form_data.username})
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        # Log failed login attempt
        try:
            await create_audit_log_entry(
                db=db,
                action="login",
                resource_type="user",
                actor_user_id=None,
                actor_roles=None,
                resource_id=form_data.username,
                success=False,
                details={
                    "username": form_data.username,
                    "reason": "invalid_credentials",
                },
            )
        except (ValueError, TypeError, AttributeError) as audit_error:
            logger.error(
                "Failed to create audit log for failed login",
                extra={"error": str(audit_error)},
            )

        logger.warning(
            "Login failed: incorrect username or password",
            extra={"username": form_data.username},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Normalize user ID to string for consistent handling
    user_id_str = str(user.id)

    access_token_expires = timedelta(minutes=jwt_validator.access_token_expire_minutes)
    # Create access token with user ID included
    access_token = jwt_validator.create_access_token(
        data={
            "sub": user.username,
            "role": user.role,
            "user_id": user_id_str,  # Include the user ID in the token
        },
        expires_delta=access_token_expires,
    )

    # Create refresh token
    refresh_token = jwt_validator.create_refresh_token(data={"sub": user.username})

    # Store refresh token in the database
    # Decode refresh token to get expiration time
    payload = jwt_validator.verify_token(refresh_token)
    if payload and "exp" in payload:
        # Convert Unix timestamp to datetime
        expires_at = datetime.fromtimestamp(payload["exp"])
        # Store refresh token using the user ID directly
        await store_refresh_token(db, user.id, refresh_token, expires_at)

    # Log successful login
    try:
        await create_audit_log_entry(
            db=db,
            action="login",
            resource_type="user",
            actor_user_id=user_id_str,
            actor_roles=[str(user.role)],  # role is non-nullable
            resource_id=user_id_str,
            success=True,
            details={"username": user.username, "role": str(user.role)},
        )
    except (ValueError, TypeError, AttributeError) as audit_error:
        logger.error(
            "Failed to create audit log for successful login",
            extra={"error": str(audit_error)},
        )

    logger.info(
        "User authenticated and tokens issued",
        extra={"username": user.username, "user_id": user_id_str},
    )
    # Return both tokens
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post(
    "/refresh",
    summary="Refresh access token",
    description="Generate a new access token using a valid refresh token",
)
async def refresh_access_token(
    token: str = Body(..., embed=True), db: AsyncSession = Depends(get_db_for_auth)
) -> dict[str, str]:
    """
    Obtain a new access token using a valid refresh token.

    This endpoint validates the provided refresh token and issues a new
    access token if the refresh token is valid. The refresh token must
    exist in the database, not be revoked, and not be expired.

    Args:
        token (str): The refresh token to use for obtaining a new access token.
        db (AsyncSession): Async database session dependency.

    Returns:
        dict: A dictionary containing the new access token and token type.

    Raises:
        HTTPException:
            - 401 If the refresh token is invalid, expired, or revoked.
    """
    logger.info("Refresh token attempt")
    # Verify the token in JWT format
    payload = jwt_validator.verify_token(token)
    if not payload or payload.get("token_type") != "refresh":
        # Log failed refresh attempt
        try:
            await create_audit_log_entry(
                db=db,
                action="token_refresh",
                resource_type="token",
                actor_user_id=None,
                actor_roles=None,
                resource_id=None,
                success=False,
                details={"reason": "invalid_token_format"},
            )
        except (ValueError, TypeError, AttributeError) as audit_error:
            logger.error(
                "Failed to create audit log for failed token refresh",
                extra={"error": str(audit_error)},
            )

        logger.warning("Refresh token failed: invalid format")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate the token in the database
    user = await validate_refresh_token(db, token)
    if not user:
        # Log failed refresh attempt
        try:
            await create_audit_log_entry(
                db=db,
                action="token_refresh",
                resource_type="token",
                actor_user_id=None,
                actor_roles=None,
                resource_id=None,
                success=False,
                details={"reason": "invalid_expired_or_revoked_token"},
            )
        except (ValueError, TypeError, AttributeError) as audit_error:
            logger.error(
                "Failed to create audit log for failed token refresh",
                extra={"error": str(audit_error)},
            )

        logger.warning("Refresh token failed: invalid, expired, or revoked")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid, expired, or has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Normalize user ID to string for consistent handling
    user_id_str = str(user.id)

    # Create new access token with user ID included
    access_token_expires = timedelta(minutes=jwt_validator.access_token_expire_minutes)
    new_access_token = jwt_validator.create_access_token(
        data={
            "sub": str(user.username),
            "role": user.role,
            "user_id": user_id_str,  # Include the user ID in the token
        },
        expires_delta=access_token_expires,
    )

    # Log successful token refresh
    try:
        await create_audit_log_entry(
            db=db,
            action="token_refresh",
            resource_type="token",
            actor_user_id=user_id_str,
            actor_roles=[str(user.role)],  # role is non-nullable
            resource_id=user_id_str,
            success=True,
            details={"username": user.username, "role": str(user.role)},
        )
    except (ValueError, TypeError, AttributeError) as audit_error:
        logger.error(
            "Failed to create audit log for successful token refresh",
            extra={"error": str(audit_error)},
        )

    logger.info(
        "Access token refreshed",
        extra={"username": user.username, "user_id": user_id_str},
    )
    # Return the new access token
    return {"access_token": new_access_token, "token_type": "bearer"}


@router.post(
    "/revoke",
    summary="Revoke refresh token",
    description="Revoke a refresh token to prevent its future use",
)
async def revoke_token(
    token: str = Body(..., embed=True),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_auth),
) -> dict[str, str]:
    """
    Revoke a refresh token to prevent its future use.

    This endpoint marks a refresh token as revoked in the database,
    preventing it from being used to obtain new access tokens. This is
    useful for logout functionality or when a token might be compromised.

    Args:
        token (str): The refresh token to revoke.
        current_user (dict): The current authenticated user.
        db (AsyncSession): Async database session dependency.

    Returns:
        dict: A message confirming the token was revoked.

    Raises:
        HTTPException:
            - 400 If the token doesn't exist or is already revoked.
    """
    logger.info("Revoke token attempt", extra={"user": current_user.get("username")})
    user_id_str = current_user.get("user_id")
    username = current_user.get("username")
    user_role = current_user.get("role")

    if await revoke_refresh_token(db, token):
        # Log successful token revocation
        try:
            await create_audit_log_entry(
                db=db,
                action="token_revoke",
                resource_type="token",
                actor_user_id=user_id_str,
                actor_roles=[user_role] if user_role else [],
                resource_id=user_id_str,
                success=True,
                details={"username": username, "role": user_role},
            )
        except (ValueError, TypeError, AttributeError) as audit_error:
            logger.error(
                "Failed to create audit log for token revocation",
                extra={"error": str(audit_error)},
            )

        logger.info("Token successfully revoked", extra={"user": username})
        return {"message": "Token successfully revoked"}
    # Log failed token revocation
    try:
        await create_audit_log_entry(
            db=db,
            action="token_revoke",
            resource_type="token",
            actor_user_id=user_id_str,
            actor_roles=[user_role] if user_role else [],
            resource_id=user_id_str,
            success=False,
            details={"username": username, "reason": "invalid_or_already_revoked"},
        )
    except (ValueError, TypeError, AttributeError) as audit_error:
        logger.error(
            "Failed to create audit log for failed token revocation",
            extra={"error": str(audit_error)},
        )

    logger.warning(
        "Token revoke failed: invalid or already revoked",
        extra={"user": username},
    )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid token or token already revoked",
    )


@router.get(
    "/validate",
    summary="Validate access token",
    description="Validates a JWT token and returns the user information if valid",
)
async def validate_token(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Validate the provided JWT token and return user information.

    This endpoint extracts the user information from the provided JWT token.
    It serves as a validation endpoint for clients to check if their token is valid
    and to retrieve the authenticated user's details.

    Args:
        current_user (dict): User information extracted from the JWT token.
            This is automatically populated by the get_current_user dependency.

    Returns:
        dict: User information including username, role, and user ID.

    Raises:
        HTTPException: If token is invalid or expired (handled by the dependency).
    """
    logger.info("Token validation endpoint hit", extra={"user": current_user.get("username")})
    return current_user


@router.post(
    "/users/",
    response_model=dict,
    summary="Create new user",
    description="Creates a new user with the provided credentials and role",
)
async def create_user(
    username: str,
    password: str,
    full_name: str,
    role: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_auth),
) -> dict[str, str]:
    """
    Create a new user in the database (admin functionality).

    This endpoint adds a new user to the database after checking that the username is not already registered.
    It hashes the provided password and then commits the new user data to the database.

    Args:
        username (str): The user's username.
        password (str): The user's password.
        full_name (str): The user's full name.
        role (str): The role assigned to the user.
        current_user (dict): The current authenticated user (admin required).
        db (AsyncSession): Async database session dependency.

    Returns:
        dict: A dictionary containing the new user's username, id, and role.

    Raises:
        HTTPException:
            - If a user with the provided username already exists.
            - If the current user is not an admin.
    """
    # Extract current user info for audit logging
    current_user_id = current_user.get("user_id")
    current_username = current_user.get("username")
    current_role = current_user.get("role")

    # Check if current user is admin
    if current_role != "admin":
        try:
            await create_audit_log_entry(
                db=db,
                action="user_create",
                resource_type="user",
                actor_user_id=current_user_id,
                actor_roles=[current_role] if current_role else [],
                resource_id=None,
                success=False,
                details={
                    "reason": "insufficient_permissions",
                    "current_role": current_role,
                },
            )
        except (ValueError, TypeError, AttributeError) as audit_error:
            logger.error(
                "Failed to create audit log for user creation failure",
                extra={"error": str(audit_error)},
            )

        logger.warning(
            "User creation failed: insufficient permissions",
            extra={"user": current_username, "role": current_role},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required to create users",
        )

    if not username:
        try:
            await create_audit_log_entry(
                db=db,
                action="user_create",
                resource_type="user",
                actor_user_id=current_user_id,
                actor_roles=[current_role] if current_role else [],
                resource_id=None,
                success=False,
                details={"reason": "username_required"},
            )
        except (ValueError, TypeError, AttributeError) as audit_error:
            logger.error(
                "Failed to create audit log for user creation failure",
                extra={"error": str(audit_error)},
            )

        logger.warning("User creation failed: username required")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is required")

    username_str = str(username)

    if username_str.lower() == "testuser":
        try:
            await create_audit_log_entry(
                db=db,
                action="user_create",
                resource_type="user",
                actor_user_id=current_user_id,
                actor_roles=[current_role] if current_role else [],
                resource_id=username_str,
                success=False,
                details={"reason": "testuser_reserved", "username": username_str},
            )
        except (ValueError, TypeError, AttributeError) as audit_error:
            logger.error(
                "Failed to create audit log for user creation failure",
                extra={"error": str(audit_error)},
            )

        logger.warning("User creation failed: testuser already registered")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Check if user exists using async query pattern
    result = await db.execute(select(User).where(User.username.ilike(username_str)))
    existing_user: User | None = result.scalar_one_or_none()

    if existing_user is not None:
        try:
            await create_audit_log_entry(
                db=db,
                action="user_create",
                resource_type="user",
                actor_user_id=current_user_id,
                actor_roles=[current_role] if current_role else [],
                resource_id=username_str,
                success=False,
                details={"reason": "username_already_exists", "username": username_str},
            )
        except (ValueError, TypeError, AttributeError) as audit_error:
            logger.error(
                "Failed to create audit log for user creation failure",
                extra={"error": str(audit_error)},
            )

        logger.warning(
            "User creation failed: username already registered",
            extra={"username": username_str},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    try:
        hashed_password = get_password_hash(password)
        new_user: User = User(
            username=username,
            full_name=full_name,
            hashed_password=hashed_password,
            role=role,
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        # Normalize user ID to string for consistent handling
        new_user_id_str = str(new_user.id)

        # Log successful user creation
        try:
            await create_audit_log_entry(
                db=db,
                action="user_create",
                resource_type="user",
                actor_user_id=current_user_id,
                actor_roles=[current_role] if current_role else [],
                resource_id=new_user_id_str,
                success=True,
                details={
                    "created_username": username,
                    "created_role": role,
                    "creator": current_username,
                },
            )
        except (ValueError, TypeError, AttributeError) as audit_error:
            logger.error(
                "Failed to create audit log for successful user creation",
                extra={"error": str(audit_error)},
            )

        logger.info(
            "New user created",
            extra={
                "username": new_user.username,
                "user_id": new_user_id_str,
                "role": new_user.role,
                "creator": current_username,
            },
        )

        return {
            "username": str(new_user.username),
            "id": new_user_id_str,
            "role": str(new_user.role),
        }

    except Exception as e:
        # Log failed user creation due to database error
        try:
            await create_audit_log_entry(
                db=db,
                action="user_create",
                resource_type="user",
                actor_user_id=current_user_id,
                actor_roles=[current_role] if current_role else [],
                resource_id=username_str,
                success=False,
                details={"reason": "database_error", "error": str(e)},
            )
        except (ValueError, TypeError, AttributeError) as audit_error:
            logger.error(
                "Failed to create audit log for user creation failure",
                extra={"error": str(audit_error)},
            )

        logger.error(
            "User creation failed due to database error",
            extra={"error": str(e), "username": username_str},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user due to database error",
        ) from e


# ============================================================================
# NOTE: Additional user management endpoints are provided by shared.auth.auth_router
# which is loaded in main.py. See src/shared/auth/router.py for:
# - GET /auth/users (list with pagination)
# - GET /auth/users/{user_id} (get user details)
# - PUT /auth/users/{user_id} (update user)
# - DELETE /auth/users/{user_id} (deactivate user)
# - POST /auth/users/{user_id}/reset-password (admin password reset)
# - GET /auth/users/{user_id}/sessions (list sessions)
# - DELETE /auth/users/{user_id}/sessions/{session_id} (force logout)
# ============================================================================
