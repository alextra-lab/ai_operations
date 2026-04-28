"""
Router for admin API endpoints.
"""

import os
import signal
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from shared.config.loader import load_embedding_config
from shared.logging_utils.fastapi import configure_logging

from ..providers import provider_factory
from ..schemas.embedding import AdminConfigReloadResponse
from ..utils.auth import get_current_admin_user  # Use the dependency from security.py

# Configure centralized logger for this router
logger = configure_logging(service_name="admin_router")

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


@router.post("/reload", response_model=AdminConfigReloadResponse)
async def reload_configuration(
    config_path: str | None = None,
    current_user: dict[str, Any] = Depends(get_current_admin_user),
) -> AdminConfigReloadResponse:
    """
    Reload provider configuration. (Admin Only)

    Args:
        config_path: Optional path to configuration file

    Returns:
        AdminConfigReloadResponse: Result of configuration reload
    """
    logger.info(f"Reloading configuration from {config_path or 'default paths'}")

    try:
        embedding_settings = load_embedding_config()
        results = await provider_factory.load_providers(
            config_path,
            embedding_settings=embedding_settings,
        )
        success = any(results.values())

        # Get provider info
        provider_info = {}
        if success:
            # Get provider health
            health = await provider_factory.get_provider_health()

            # Get available models
            models = await provider_factory.get_available_models()

            # Combine information
            for name in results:
                provider_info[name] = {
                    "initialized": results[name],
                    "health": health.get(name, {"available": False}),
                    "models": models.get(name, {}),
                }

        message = (
            "Configuration reloaded successfully" if success else "Failed to load any providers"
        )

        logger.info(
            "Configuration reload result",
            extra={
                "success": success,
                "message": message,
                "providers": list(provider_info.keys()),
                "user_id": current_user.get("user_id"),
            },
        )

        return AdminConfigReloadResponse(success=success, message=message, providers=provider_info)
    except Exception as e:
        logger.exception(f"Error reloading configuration: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error reloading configuration: {e!s}")


@router.get("/health", response_model=dict[str, dict[str, bool]])
async def check_health(
    current_user: dict[str, Any] = Depends(get_current_admin_user),
) -> dict[str, dict[str, bool]]:
    """
    Check health status of all providers. (Admin Only)

    Returns:
        dict: Health status information for all providers
    """
    try:
        health = await provider_factory.get_provider_health()
        logger.info(
            "Checked provider health",
            extra={
                "providers": list(health.keys()),
                "user_id": current_user.get("user_id"),
            },
        )
        return health
    except Exception as e:
        logger.exception(f"Error checking provider health: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error checking provider health: {e!s}")


@router.post("/reload-signal")
async def send_reload_signal(
    background_tasks: BackgroundTasks,
    current_user: dict[str, Any] = Depends(get_current_admin_user),
) -> dict[str, Any]:
    """
    Send SIGHUP signal to trigger configuration reload. (Admin Only)

    This is an alternative way to reload configuration using the system signal mechanism.

    Returns:
        dict: Result of the operation
    """
    logger.info(
        "Sending SIGHUP signal to self",
        extra={"user_id": current_user.get("user_id")},
    )

    def send_signal() -> None:
        os.kill(os.getpid(), signal.SIGHUP)

    try:
        # Use background tasks to avoid killing the request handling process
        background_tasks.add_task(send_signal)
        logger.info(
            "SIGHUP signal scheduled",
            extra={"user_id": current_user.get("user_id")},
        )
        return {"success": True, "message": "SIGHUP signal scheduled"}
    except Exception as e:
        logger.exception(f"Error sending SIGHUP signal: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error sending SIGHUP signal: {e!s}")


@router.get("/status")
async def get_service_status(
    current_user: dict[str, Any] = Depends(get_current_admin_user),
) -> dict[str, Any]:
    """
    Get comprehensive service status information. (Admin Only)

    Returns:
        dict: Status information including provider health, available models, and configuration
    """
    try:
        # Get provider health
        health = await provider_factory.get_provider_health()

        # Get available models
        models = await provider_factory.get_available_models()

        # Get default provider
        default_provider = provider_factory.default_provider

        logger.info(
            "Service status checked",
            extra={
                "providers": list(health.keys()),
                "default_provider": default_provider,
                "user_id": current_user.get("user_id"),
            },
        )

        return {
            "status": "healthy",
            "providers": {
                "health": health,
                "models": models,
                "default": default_provider,
                "count": len(provider_factory.providers),
            },
        }
    except Exception as e:
        logger.exception(f"Error getting service status: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error getting service status: {e!s}")
