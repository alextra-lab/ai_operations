"""
Inference Gateway - Main FastAPI application.

OpenAI-compatible API for centralized LLM provider access.
Implements chat completions, embeddings, and model management.
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from shared.config.loader import load_inference_gateway_config
from shared.logging_utils.fastapi import configure_logging  # type: ignore[import-untyped]

from .database import check_database_connection, init_db
from .middleware.rate_limit_middleware import RateLimitMiddleware
from .routers.admin import router as admin_router
from .routers.chat import router as chat_router
from .routers.embeddings import router as embeddings_router
from .routers.responses import router as responses_router
from .services.circuit_breaker import configure_circuit_breaker
from .services.rate_limiter import configure_rate_limiter, init_rate_limiter
from .services.redis_client import configure_redis, init_redis, shutdown_redis
from .services.usage_logger import init_usage_logger

logger = configure_logging(service_name="gateway_main")

# Surface outbound provider HTTP calls (method, URL, status code) in gateway logs so
# first-time LLMaaS connectivity issues are debuggable. httpx emits one line per request;
# LOG_VERBOSE=true bumps to DEBUG and adds connection-level httpcore detail.
configure_logging(service_name="httpx")
if os.environ.get("LOG_VERBOSE", "false").lower() == "true":
    configure_logging(service_name="httpcore")

# Load configuration
gateway_config = load_inference_gateway_config()
SERVICE_NAME = gateway_config.name
SERVICE_VERSION = gateway_config.version
ENV = gateway_config.environment

# Configure shared services with settings
configure_circuit_breaker(gateway_config.circuit_breaker)
configure_rate_limiter(gateway_config.rate_limiter)
configure_redis(gateway_config.redis)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown tasks:
    - Startup: Initialize Redis connection and usage logger
    - Shutdown: Gracefully close Redis and flush pending usage records

    Args:
        app: FastAPI application instance

    Yields:
        None: Application runs until shutdown
    """
    # Startup
    logger.info(
        "Inference Gateway starting",
        extra={"service": SERVICE_NAME, "version": SERVICE_VERSION, "env": ENV},
    )

    # Initialize database (P5-A3)
    await init_db()
    db_healthy = await check_database_connection()
    if db_healthy:
        logger.info("Database connected and ready")
    else:
        logger.warning("Database connection check failed")

    # Initialize Redis connection (P2-T4)
    redis_client = await init_redis(gateway_config.redis)
    if redis_client.is_available:
        logger.info("Redis connected and ready")
    else:
        logger.warning("Redis unavailable - rate limiting will fall back to PostgreSQL")

    # Initialize usage logger
    usage_logger = init_usage_logger(gateway_config.usage_logger)
    await usage_logger.start()
    logger.info("Usage logger started", extra=usage_logger.get_stats())

    # Initialize rate limiter
    rate_limiter = await init_rate_limiter(gateway_config.rate_limiter)
    logger.info(
        "Rate limiter initialized",
        extra={"enabled": rate_limiter.enable_rate_limiting},
    )

    yield  # Application runs

    # Shutdown
    logger.info("Inference Gateway shutting down")
    await usage_logger.shutdown()
    logger.info("Usage logger stopped")
    await shutdown_redis()
    logger.info("Redis disconnected")


# Create FastAPI app
app = FastAPI(
    title="Inference Gateway",
    description="Centralized LLM and Embedding Provider Access",
    version=SERVICE_VERSION,
    docs_url="/docs" if ENV != "production" else None,
    redoc_url="/redoc" if ENV != "production" else None,
    lifespan=lifespan,
)
app.state.gateway_config = gateway_config

# CORS configuration
CORS_ORIGINS = gateway_config.cors_origins
ENABLE_CORS = gateway_config.enable_cors

if ENABLE_CORS:
    app.add_middleware(  # type: ignore[call-arg,arg-type]
        CORSMiddleware,  # type: ignore[arg-type]
        allow_origins=CORS_ORIGINS if "*" not in CORS_ORIGINS else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add rate limiting middleware
# Note: Add BEFORE routers so it runs before request processing
app.add_middleware(RateLimitMiddleware)  # type: ignore[call-arg,arg-type]

# Register routers
app.include_router(admin_router)
app.include_router(chat_router)
app.include_router(embeddings_router)
app.include_router(responses_router)


@app.get("/health")
async def health_check() -> JSONResponse:
    """
    Health check endpoint.

    Includes:
    - Service status
    - Database connection status (P5-A3)
    - Redis connection status (P2-T4)

    Returns:
        JSONResponse with service and dependency health status
    """
    from .services.redis_client import get_redis_client

    # Check Database health (P5-A3)
    db_healthy = await check_database_connection()
    db_health = {
        "status": "healthy" if db_healthy else "unhealthy",
        "type": "postgresql",
    }

    # Check Redis health
    redis_client = get_redis_client()
    redis_health = await redis_client.health_check()

    # Overall status (healthy if core dependencies are up)
    # Database is required, Redis is optional
    overall_status = "healthy" if db_healthy else "degraded"

    return JSONResponse(
        status_code=200 if db_healthy else 503,
        content={
            "status": overall_status,
            "service": SERVICE_NAME,
            "version": SERVICE_VERSION,
            "environment": ENV,
            "dependencies": {
                "database": db_health,
                "redis": redis_health,
            },
        },
    )


@app.get("/")
async def root() -> JSONResponse:
    """
    Root endpoint - service information.

    Returns:
        JSONResponse with service metadata
    """
    return JSONResponse(
        status_code=200,
        content={
            "service": SERVICE_NAME,
            "version": SERVICE_VERSION,
            "environment": ENV,
            "status": "operational",
            "message": "Inference Gateway API - See /docs for API documentation",
        },
    )
