"""
Scope-based access control for AI Operations Platform.

This module provides FastAPI dependencies for enforcing scope-based
authorization on API endpoints. Scopes allow for fine-grained access
control beyond role-based permissions.
"""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from .manager import auth_manager
from .models import TokenPayload


def requires_scope(
    required_scope: str,
) -> Callable[[HTTPAuthorizationCredentials], TokenPayload]:
    """
    Create a FastAPI dependency that requires a specific scope.

    This dependency checks if the authenticated user's token contains
    the specified scope. If the scope is missing, a 403 Forbidden error
    is raised.

    Args:
        required_scope: The scope string to check for (e.g., "inference:chat")

    Returns:
        FastAPI dependency function that returns TokenPayload

    Example:
        ```python
        @router.post("/v1/chat/completions")
        async def chat_completions(
            token: TokenPayload = Depends(requires_scope("inference:chat"))
        ):
            # User has inference:chat scope
            pass
        ```

    Raises:
        HTTPException: 403 Forbidden if the token lacks the required scope
    """

    def scope_checker(
        credentials: HTTPAuthorizationCredentials = Depends(auth_manager.security),
    ) -> TokenPayload:
        """Check if the authenticated user has the required scope."""
        # First authenticate the user (get token payload)
        payload = auth_manager.get_user_from_request(credentials)

        # Admin users bypass scope checks (have full access)
        if payload.is_admin():
            return payload

        # Then check if they have the required scope
        if not payload.has_scope(required_scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope: {required_scope}",
            )

        return payload

    return scope_checker


def requires_any_scope(
    required_scopes: list[str],
) -> Callable[[HTTPAuthorizationCredentials], TokenPayload]:
    """
    Create a FastAPI dependency that requires any of the specified scopes.

    This dependency checks if the authenticated user's token contains
    at least one of the specified scopes. If none of the scopes are present,
    a 403 Forbidden error is raised.

    Args:
        required_scopes: List of acceptable scope strings

    Returns:
        FastAPI dependency function that returns TokenPayload

    Example:
        ```python
        @router.post("/v1/models")
        async def list_models(
            token: TokenPayload = Depends(requires_any_scope([
                "inference:chat",
                "inference:embeddings"
            ]))
        ):
            # User has at least one of the required scopes
            pass
        ```

    Raises:
        HTTPException: 403 Forbidden if the token lacks all required scopes
    """

    def scope_checker(
        credentials: HTTPAuthorizationCredentials = Depends(auth_manager.security),
    ) -> TokenPayload:
        """Check if the authenticated user has any of the required scopes."""
        # First authenticate the user (get token payload)
        payload = auth_manager.get_user_from_request(credentials)

        # Admin users bypass scope checks (have full access)
        if payload.is_admin():
            return payload

        # Then check if they have any of the required scopes
        if not payload.has_any_scope(required_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scopes. Need one of: {required_scopes}",
            )

        return payload

    return scope_checker
