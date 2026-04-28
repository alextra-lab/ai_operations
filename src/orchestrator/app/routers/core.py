# pylint: disable=import-error
"""
Core router module.

This module defines the core API endpoints for the AI Operations Platform (AIOP) API.
"""

from typing import Any

from fastapi import APIRouter, Depends, Request

from shared.auth.models import TokenPayload
from shared.logging_utils.fastapi import configure_logging

from ..utils.auth import get_current_user

logger = configure_logging(service_name="core_router", log_level="INFO", log_format="json")

# Create router with 'core' tag for OpenAPI grouping
router = APIRouter(tags=["core"])


@router.get("/")
def read_root(request: Request) -> dict[str, str]:
    """
    Root endpoint that returns a welcome message.

    Returns:
        dict: A simple welcome message
    """
    client_host = request.client.host if request.client else "unknown"
    logger.info("Root endpoint accessed", extra={"client": client_host})
    return {"message": "Hello from Orchestrator API"}


@router.get("/protected")
def protected_route(
    request: Request, current_user: TokenPayload = Depends(get_current_user)
) -> dict[str, Any]:
    """
    Protected route that requires authentication.

    Args:
        request (Request): The incoming request.
        current_user (TokenPayload): The authenticated user information.

    Returns:
        Dict[str, Any]: A message confirming access and the user information.
    """
    client_host = request.client.host if request.client else "unknown"
    logger.info(
        "Protected endpoint accessed",
        extra={
            "client": client_host,
            "username": current_user.sub,
            "user_id": current_user.user_id,
        },
    )
    return {
        "message": "You have access to this protected resource",
        "user": current_user.model_dump(),
    }
