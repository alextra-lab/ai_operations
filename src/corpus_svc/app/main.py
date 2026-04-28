"""
Retriever service FastAPI application entry point.

This module configures the FastAPI application, sets up middleware, routes,
and handles application lifecycle events.
"""

import time
from collections.abc import Awaitable, Callable

import uvicorn
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter

from shared.auth import auth_router, init_database
from shared.config.loader import (
    load_embedding_config,
    load_opentelemetry_config,
    load_retrieval_config,
)
from shared.logging_utils.fastapi import (
    RequestIDLoggerMiddleware,
    RequestLoggingMiddleware,
    configure_logging,
    get_logger,
    is_verbose_logging_enabled,
)
from shared.telemetry_utils.telemetry import (
    get_span_id,
    get_trace_id,
    setup_telemetry,
)

from .clients import EmbeddingServiceClient
from .db.connection import (
    check_database_connection,
)

# Import Qdrant repository and lifecycle functions
from .repositories.vector_repository import (
    close_vector_repository,
    get_vector_repository,
)
from .routers import (
    analytics,  # Import the analytics router
    chunking,  # NEW: Chunking strategies (P4-F9)
    collections,  # Import collection management routers
    documents,  # Use refactored documents router
    test_suites,  # NEW: Corpus test suites (P4-F10)
)
from .routers import query as query_router  # Use refactored query router
from .routers import usage as usage_router
from .utils import embeddings

# Load centralized configurations
retrieval_config = load_retrieval_config()
embedding_config = load_embedding_config()
otel_config = load_opentelemetry_config()

# Setup logging
configure_logging(service_name=retrieval_config.name)
logger = get_logger(name=retrieval_config.name)
verbose_logging = is_verbose_logging_enabled()

# Service configuration from centralized config
SERVICE_NAME = retrieval_config.name
API_VERSION = retrieval_config.version
DEBUG = retrieval_config.debug
LLM_GUARD_ENABLE_CORS = retrieval_config.enable_cors
CORS_ORIGINS = retrieval_config.cors_origins

# Embedding Service Client Configuration from centralized config
EMBEDDING_SERVICE_URL = retrieval_config.embedding_service_url
EMBEDDING_SERVICE_TOKEN = retrieval_config.embedding_service_token
EMBEDDING_CLIENT_TIMEOUT_SECONDS = embedding_config.client_timeout_seconds
EMBEDDING_CLIENT_MAX_RETRIES = embedding_config.client_max_retries
EMBEDDING_CLIENT_BATCH_SIZE = embedding_config.batch_size
EMBEDDING_CLIENT_MODEL_NAME = embedding_config.model_name

# Create FastAPI app
app = FastAPI(
    title="Retriever Service API",
    description="Document retrieval and management service API",
    version=API_VERSION,
    debug=DEBUG,
)

# Configure CORS middleware if enabled
if LLM_GUARD_ENABLE_CORS:
    app.add_middleware(
        CORSMiddleware,  # type: ignore[arg-type,call-arg]
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
            service_name=retrieval_config.name,
            otlp_endpoint=otel_config.endpoint,
        )
        logger.info("OpenTelemetry OTLP exporter configured")
    except Exception as e:
        logger.error(f"Failed to configure telemetry: {e!s}")


# Add request ID middleware
@app.middleware("http")
async def add_request_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    Add request ID middleware for request tracking.

    This middleware adds trace and span IDs to the request state and response headers
    for request tracking and observability.

    Args:
        request: FastAPI request object
        call_next: Next middleware function

    Returns:
        Response from next middleware
    """
    # Get trace & span IDs from telemetry
    trace_id = get_trace_id() or "unknown"
    span_id = get_span_id() or "unknown"

    # Store in request state
    request.state.trace_id = trace_id
    request.state.span_id = span_id

    # Measure request duration
    start_time = time.time()

    try:
        # Process request
        response = await call_next(request)

        # Add tracing headers to response
        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Span-ID"] = span_id

        # Log request
        duration = time.time() - start_time
        logger.info(
            f"{request.method} {request.url.path} completed in {duration:.4f}s",
            extra={
                "method": request.method,
                "path": request.url.path,
                "duration": duration,
                "status_code": response.status_code,
                "trace_id": trace_id,
                "span_id": span_id,
            },
        )

        return response

    except Exception as e:
        # Log exception and return error response
        duration = time.time() - start_time
        logger.error(
            f"Request failed: {e!s}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "duration": duration,
                "error": str(e),
                "trace_id": trace_id,
                "span_id": span_id,
            },
            exc_info=True,
        )

        # Return JSON error response
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "trace_id": trace_id,
            },
        )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> Response:
    """
    Health check endpoint for the Retriever service.

    Checks health of service dependencies:
    - Database connection
    - Embedding service connection

    Returns:
        Health status information
    """
    db_healthy = await check_database_connection()
    embedding_service_healthy = False
    embedding_service_status = "unhealthy"
    qdrant_healthy = False
    qdrant_status = "unhealthy"

    if embeddings.embedding_client:
        try:
            await embeddings.embedding_client.get_service_health()
            embedding_service_healthy = True
            embedding_service_status = "healthy"
        except Exception as e:
            logger.error(f"Embedding service health check failed: {e}", exc_info=True)
            embedding_service_status = "unhealthy"  # Or provide more error detail
    else:
        embedding_service_status = "not_configured"

    # Check Qdrant health
    # Note: get_vector_repository() initializes the client and collection if not already done.
    # This might be the first time it's called if no other endpoint has triggered it yet.
    try:
        qdrant_repo = await get_vector_repository()  # Ensures it's initialized
        if qdrant_repo and await qdrant_repo.health_check():
            qdrant_healthy = True
            qdrant_status = "healthy"
        else:
            qdrant_status = "unhealthy"  # or "not_configured" if qdrant_repo is None (should not happen with current factory)
    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}", exc_info=True)
        qdrant_status = "unhealthy"

    # Check overall health - all dependencies must be healthy
    is_healthy = all([db_healthy, embedding_service_healthy, qdrant_healthy])

    # Prepare health check response
    health_status = {
        "status": "healthy" if is_healthy else "unhealthy",
        "service": SERVICE_NAME,
        "version": API_VERSION,
        "timestamp": time.time(),
        "dependencies": {
            "database": "healthy" if db_healthy else "unhealthy",
            "embedding_service": embedding_service_status,
            "vector_database": qdrant_status,
        },
        "features": {
            "centralized_metadata": True,
            "usage_tracking": True,
            "hot_analytics": True,
            "chunk_content_in_vector_db_only": True,
        },
    }

    # Set status code based on health
    status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        content=health_status,
        status_code=status_code,
    )


# Service info endpoint
@app.get("/info", tags=["Info"])
async def service_info() -> Response:
    """
    Service information endpoint.

    Returns information about the refactored service design and capabilities.
    """
    info = {
        "service": SERVICE_NAME,
        "version": API_VERSION,
        "design": "refactored",
        "description": "Refactored retrieval service with centralized metadata and usage tracking",
        "features": {
            "centralized_metadata": "All document metadata stored in master documents table",
            "usage_tracking": "Retrieval events tracked without storing chunk content",
            "hot_analytics": "Analytics for hot documents and chunks",
            "chunk_content_in_vector_db_only": "Chunk content stored only in vector database",
            "no_chunk_table": "No chunk table in PostgreSQL database",
        },
        "schema_version": "2.0",
        "migration": "002_refactor_retrieval_metadata_tracking",
    }

    return JSONResponse(content=info, status_code=status.HTTP_200_OK)


# Create API router with version prefix
api_router = APIRouter(prefix=f"/api/{API_VERSION}")

# Include routes from other modules
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(
    query_router.router, prefix="/query", tags=["Query"]
)  # Use the imported query_router
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(usage_router.router, prefix="/usage", tags=["Usage"])
api_router.include_router(chunking.router, prefix="/chunking", tags=["Chunking"])  # NEW: P4-F9
api_router.include_router(
    test_suites.router, prefix="/test-suites", tags=["Test-Suites"]
)  # NEW: P4-F10

# Include API router in app
app.include_router(api_router)
app.include_router(auth_router)

# Include collection routers (admin and public)
app.include_router(collections.admin_router, tags=["Collections-Admin"])
app.include_router(collections.public_router, tags=["Collections-Public"])


# Startup event
@app.on_event("startup")
async def startup_event() -> None:
    """Initialize application on startup."""
    global global_embedding_client  # Add this line
    # No longer need 'global embedding_client' here as we directly use the imported global_embedding_client
    logger.info(f"Starting {SERVICE_NAME} service...")
    await init_database()

    # Initialize database connection pool
    try:
        # With SQLAlchemy, the engine is initialized at the module level.
        # We can perform a health check here to ensure the connection is ready.
        if await check_database_connection():
            logger.info("Database connection successful.")
        else:
            logger.error("Database connection failed on startup.")
    except Exception as e:
        logger.error(f"Failed to initialize database connection: {e!s}", exc_info=True)

    # Initialize Embedding Service Client
    if EMBEDDING_SERVICE_URL:
        embeddings.embedding_client = EmbeddingServiceClient(
            base_url=EMBEDDING_SERVICE_URL,
            token=None,  # No static token - will use per-request JWT forwarding
            timeout_seconds=EMBEDDING_CLIENT_TIMEOUT_SECONDS,
            max_retries=EMBEDDING_CLIENT_MAX_RETRIES,  # This is for the client's own retry logic if any, not the backoff decorator
            batch_size=EMBEDDING_CLIENT_BATCH_SIZE,
            model_name=EMBEDDING_CLIENT_MODEL_NAME,
        )
        logger.info("EmbeddingServiceClient initialized successfully.")
    else:
        logger.warning(
            "EMBEDDING_SERVICE_URL not configured. EmbeddingServiceClient will not be available."
        )

    # Initialize Qdrant Vector Repository (this also initializes the collection)
    try:
        (
            await get_vector_repository()
        )  # This will call initialize_collection internally on first call
        # Note: initialize_collection now returns a boolean indicating success/failure rather than raising exceptions
        # But we still need to handle any exceptions that might occur before that point
        logger.info("Qdrant vector repository initialized and collection checked/created.")
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant vector repository: {e}", exc_info=True)
        # We'll continue startup despite this error - the health check will report unhealthy
        # for the vector database, but the service can still start and handle basic operations
        logger.warning(
            "Service will continue to start but Qdrant-related functionality may be degraded or unavailable."
        )


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up resources on shutdown."""
    # global_embedding_client is already in scope from module import
    logger.info(f"Shutting down {SERVICE_NAME} service...")

    # The SQLAlchemy engine manages the connection pool, so no explicit close is needed here.
    # If you needed to dispose of the engine explicitly, it would be done here.
    # await engine.dispose()
    logger.info("Database connections managed by SQLAlchemy engine.")

    # Close Embedding Service Client session
    if embeddings.embedding_client:
        try:
            await embeddings.embedding_client.close()
            logger.info("EmbeddingServiceClient session closed.")
        except Exception as e:
            logger.error(f"Error closing EmbeddingServiceClient session: {e}", exc_info=True)

    # Close Qdrant Vector Repository
    try:
        await close_vector_repository()
        # logger.info("Qdrant vector repository closed.") # Logging is in close_vector_repository
    except Exception as e:
        logger.error(f"Error closing Qdrant vector repository: {e}", exc_info=True)


# Run API server directly when executed as script
if __name__ == "__main__":
    from shared.config.loader import load_logging_config

    logging_config = load_logging_config(service_name=retrieval_config.name)
    log_level: str = str(logging_config.level).lower()

    logger.info(
        "Starting %s API server on port %s",
        SERVICE_NAME,
        retrieval_config.port,
    )

    # Run with uvicorn
    uvicorn.run(
        "src.corpus_svc.app.main:app",
        host=retrieval_config.host,
        port=retrieval_config.port,
        log_level=log_level,
        reload=retrieval_config.debug,
    )
