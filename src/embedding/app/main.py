"""
Embedding Service for AI Operations Platform.

This service provides text embedding generation using multiple embedding models,
with support for both local models and OpenAI-compatible inference servers.
"""

import os
import signal
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from types import FrameType
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from shared.config.loader import load_embedding_config, load_opentelemetry_config
from shared.logging_utils.fastapi import (
    RequestIDLoggerMiddleware,
    RequestLoggingMiddleware,
    configure_logging,
    get_logger,
    is_verbose_logging_enabled,
)
from shared.telemetry_utils.telemetry import setup_telemetry

from .providers import provider_factory
from .routers.admin import router as admin_router
from .routers.embedding import (
    create_openai_embeddings as embedding_router_create_openai,  # This is actually defined in embedding_router, not directly used here for a route
)
from .routers.embedding import router as embedding_router
from .schemas.embedding import OpenAIEmbeddingRequest, OpenAIEmbeddingResponse
from .utils.auth import get_current_admin_user, get_current_user

# Load centralized configuration
embedding_config = load_embedding_config()
otel_config = load_opentelemetry_config()

# Configure logging using centralized config
configure_logging(embedding_config.name)
logger = get_logger(embedding_config.name)
verbose_logging = is_verbose_logging_enabled()


# Set up signal handlers for hot reload at module level
def handle_sighup(_signum: int, _frame: FrameType | None) -> None:
    """Handle SIGHUP signal for configuration reload."""
    logger.info("Received SIGHUP signal, scheduling configuration reload")
    # We can't do async operations in a signal handler, so we just log the event
    # The actual reload will be done when an admin endpoint is called


try:
    signal.signal(signal.SIGHUP, handle_sighup)
    logger.info("SIGHUP signal handler registered")
except (AttributeError, ValueError) as e:
    logger.warning(f"Failed to register SIGHUP handler: {e!s}")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI application.

    Handles startup and shutdown tasks.
    """
    # Startup tasks
    logger.info("Embedding service starting up")

    # Load provider configuration
    try:
        config_path = os.environ.get("CONFIG_PATH")
        logger.info(f"Loading provider configuration from {config_path or 'default paths'}")
        await provider_factory.load_providers(
            config_path,
            embedding_settings=embedding_config,
        )
        logger.info("Provider configuration loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load provider configuration: {e!s}")

    yield

    # Shutdown tasks
    logger.info("Embedding service shutting down")


# Initialize FastAPI app with centralized config
app = FastAPI(
    title="Embedding Service",
    description="Text embedding generation service for AI Operations Platform",
    version=embedding_config.version,
    lifespan=lifespan,
)

# Set up CORS with restrictive defaults
app.add_middleware(  # type: ignore[call-arg,arg-type]
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=[],  # Default to no origins allowed
    allow_credentials=False,
    allow_methods=["POST"],  # Only allow POST, since embedding endpoints use POST
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# Add request ID middleware
app.add_middleware(RequestIDLoggerMiddleware)
app.add_middleware(
    RequestLoggingMiddleware,
    logger=logger,  # type: ignore[arg-type]
    verbose=verbose_logging,
)

# Set up OpenTelemetry if enabled (using centralized config)
if otel_config.enabled and otel_config.endpoint:
    try:
        setup_telemetry(
            app=app,
            service_name=embedding_config.name,
            otlp_endpoint=otel_config.endpoint,
        )
        logger.info("OpenTelemetry OTLP exporter configured")
    except Exception as e:
        logger.error(f"Failed to configure telemetry: {e!s}")


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint.

    Returns:
        dict: Health status information
    """
    # Check provider health
    provider_health: dict[str, Any] = {}
    try:
        provider_health = await provider_factory.get_provider_health()
    except Exception as e:
        logger.error(f"Error checking provider health: {e!s}")
        provider_health = {"error": {"available": False, "error": "Provider health check failed"}}

    # Overall service health
    providers_available = False
    if provider_health:
        for provider in provider_health.values():
            if isinstance(provider, dict) and provider.get("available", False):
                providers_available = True
                break

    return {
        "status": "healthy" if providers_available else "degraded",
        "service": embedding_config.name,
        "version": embedding_config.version,
        "providers": provider_health,
    }


@app.exception_handler(Exception)
async def generic_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled exceptions.

    Args:
        request: The request that caused the exception
        exc: The unhandled exception

    Returns:
        JSONResponse with error details
    """
    logger.exception(f"Unhandled exception: {exc!s}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred",
        },
    )


# Include OpenAI-compatible API endpoint
@app.post("/v1/embeddings", response_model=OpenAIEmbeddingResponse)
async def openai_compatible_embeddings_route(
    request: OpenAIEmbeddingRequest,
    current_user: Any = Depends(get_current_user),
) -> OpenAIEmbeddingResponse:
    """OpenAI-compatible embeddings endpoint."""
    return await embedding_router_create_openai(request, current_user)


# Example of using JWT/role-based dependencies in a route:
@app.get("/admin/whoami")
async def whoami_admin(user: dict = Depends(get_current_admin_user)) -> dict[str, Any]:
    """
    Example endpoint to show the current admin user's JWT payload.
    """
    return {"user": user}


# Include routers
app.include_router(embedding_router)
app.include_router(admin_router)
