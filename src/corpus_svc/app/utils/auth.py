"""
Retrieval service authentication utilities - now using unified auth system.

This module provides backward compatibility while transitioning to the unified auth system.
"""

import uuid

from fastapi import HTTPException, Request, status

# Import from unified auth system
from shared.auth import (
    TokenPayload,
)
from shared.auth import (
    admin_required as admin_auth_required,
)
from shared.auth import (
    auth_manager as jwt_validator,
)
from shared.auth import (
    get_current_user as _get_current_user,
)
from shared.auth import (
    service_required as service_auth_required,
)
from shared.logging_utils.fastapi import configure_logging

logger = configure_logging(service_name="retrieval_auth_utils")


def extract_user_id_from_token(current_user: TokenPayload | dict) -> uuid.UUID:
    """
    Extract user ID from token payload and convert to UUID.

    This function handles the complex user ID extraction logic that was previously
    scattered throughout the retrieval service.

    Args:
        current_user: Token payload from authentication

    Returns:
        User UUID

    Raises:
        HTTPException: If user ID cannot be extracted or is invalid
    """
    try:
        # Handle TokenPayload object (new unified auth)
        if isinstance(current_user, TokenPayload):
            return uuid.UUID(current_user.user_id)

        # Handle dict payload (backward compatibility)
        if isinstance(current_user, dict):
            # Try user_id field first (new format)
            if "user_id" in current_user:
                return uuid.UUID(str(current_user["user_id"]))

            # Try id field (legacy format)
            if "id" in current_user:
                return uuid.UUID(str(current_user["id"]))

            # Handle JWT token payload with 'sub' field (username)
            if "sub" in current_user:
                username = current_user["sub"]
                if username == "testuser":
                    logger.warning(
                        "Using hardcoded test UUID for 'testuser' from JWT token. "
                        "This is a temporary workaround."
                    )
                    return uuid.UUID("00000000-0000-0000-0000-000000000000")
                # Create a deterministic UUID from the username
                user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, username)
                logger.info(f"Created deterministic UUID for username '{username}': {user_uuid}")
                return user_uuid

            logger.error(
                f"JWT token payload does not contain valid user identifier: {current_user}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JWT token payload: missing user identifier.",
            )

        # Handle string input (legacy)
        if isinstance(current_user, str):
            if current_user == "testuser":
                logger.warning(
                    "Using hardcoded test UUID for 'testuser'. This is a temporary workaround."
                )
                return uuid.UUID("00000000-0000-0000-0000-000000000000")
            try:
                return uuid.UUID(current_user)
            except ValueError:
                # For string usernames that aren't UUIDs, create a deterministic UUID
                user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, current_user)
                logger.info(
                    f"Created deterministic UUID for username string '{current_user}': {user_uuid}"
                )
                return user_uuid

        logger.error(
            f"Could not extract valid user ID from current_user object: {type(current_user)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: User ID not available.",
        )

    except ValueError as e:
        logger.error(f"Invalid UUID format in user ID: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format."
        )


def extract_jwt_token(request: Request) -> str | None:
    """Extract JWT token from Authorization header."""
    auth_header = request.headers.get("authorization")

    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]
    return None


# Correct dependency for FastAPI
get_current_user = _get_current_user


# Backward compatibility aliases
get_current_admin_user = admin_auth_required

# Export for backward compatibility
__all__ = [
    "admin_auth_required",
    "extract_user_id_from_token",
    "get_current_admin_user",
    "get_current_user",
    "jwt_validator",
    "service_auth_required",
]
