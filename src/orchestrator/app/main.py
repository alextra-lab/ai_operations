# pylint: disable=import-error
"""
Main API entry point for the AI Operations Platform (AIOP) Orchestrator API.

This module initializes the FastAPI application, registers middleware,
and includes router components from various modules.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.auth import auth_router
from shared.config.loader import load_orchestrator_config
from shared.logging_utils.fastapi import (
    RequestIDLoggerMiddleware,
    RequestLoggingMiddleware,
    configure_logging,
    is_verbose_logging_enabled,
)

from .middleware.audit import audit_middleware
from .middleware.rls import rls_middleware
from .middleware.sanitization import sanitize_request
from .middleware.security_headers import security_headers_middleware
from .routers.admin import router as admin_router
from .routers.admin_audit import router as admin_audit_router
from .routers.admin_config import router as admin_config_router
from .routers.admin_developer_teams import router as admin_developer_teams_router
from .routers.admin_gateway_metrics import router as admin_gateway_metrics_router
from .routers.admin_gateway_providers import router as admin_gateway_providers_router
from .routers.admin_grouping_roles import router as admin_grouping_roles_router
from .routers.admin_intent_models import router as admin_intent_models_router
from .routers.admin_pricing import router as admin_pricing_router
from .routers.admin_roles import router as admin_roles_router
from .routers.admin_user_roles import router as admin_user_roles_router
from .routers.capabilities import router as capabilities_router
from .routers.chunking import router as chunking_router
from .routers.collection_management import router as collection_mgmt_router
from .routers.config_public import router as config_public_router
from .routers.core import router as core_router
from .routers.corpus import router as corpus_router
from .routers.health import router as health_router
from .routers.models import router as models_router
from .routers.orchestrator import router as orchestrator_router
from .routers.output_templates import router as output_templates_router
from .routers.prompt_patterns import router as prompt_patterns_router
from .routers.query import router as query_router
from .routers.query_history import router as query_history_router
from .routers.run_manifests import router as run_manifests_router
from .routers.security import router as security_router
from .routers.stateless import router as stateless_router
from .routers.summaries import router as summaries_router
from .routers.templates import router as templates_router
from .routers.token_analytics import router as token_analytics_router
from .routers.tools_admin import router as tools_admin_router
from .routers.tools_analytics import router as tools_analytics_router
from .routers.tools_developer import router as tools_developer_router
from .routers.tools_health import router as tools_health_router
from .routers.tools_registration import router as tools_registration_router
from .routers.tools_testing import router as tools_testing_router
from .routers.use_case_management import router as use_case_mgmt_router
from .routers.use_case_validation import router as use_case_validation_router
from .routers.use_cases import router as use_cases_router
from .routers.websocket import router as websocket_router

# Load centralized configuration
orchestrator_config = load_orchestrator_config()

# Configure the centralized logger for the main application
logger = configure_logging(
    service_name=orchestrator_config.name, log_level="INFO", log_format="json"
)
verbose_logging = is_verbose_logging_enabled()


@asynccontextmanager
async def lifespan(_fastapi_app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager that handles application startup and shutdown events.
    This replaces the deprecated on_event handlers.
    """
    from shared.auth import init_database  # dynamic import for test patching

    # Import backend init to ensure app tables (including pricing history) exist
    from .db.database import init_db

    logger.info("Application startup: Initializing database connection")
    await init_database()
    # Create backend tables asynchronously (ADR-022 async migration)
    try:
        await init_db()
    except Exception:  # pragma: no cover - defensive
        logger.error("Failed to init backend DB tables", exc_info=True)
    yield
    logger.info("Application shutdown: Cleaning up resources")


def create_app() -> FastAPI:
    fastapi_app = FastAPI(
        title="AI Operations Platform (AIOP) Orchestrator API",
        version=orchestrator_config.version,
        lifespan=lifespan,
    )
    fastapi_app.state.orchestrator_config = orchestrator_config
    # Note: init_db() is now async and called in lifespan().
    # For tests, use pytest-asyncio fixtures to initialize the database.

    # CORS origins: use config if specified, otherwise use development defaults
    cors_origins = orchestrator_config.cors_origins
    if cors_origins == ["*"]:
        # Default to known development origins for security
        cors_origins = [
            "http://localhost:4200",  # Angular dev server
            "http://localhost:4201",  # Docker UI port
            "http://127.0.0.1:4200",  # Alternative localhost
            "http://127.0.0.1:4201",  # Alternative localhost Docker
            "http://localhost:3000",  # Alternative dev server port
        ]

    # Add CORS middleware to allow Angular frontend to access the API
    fastapi_app.add_middleware(  # type: ignore[call-arg,arg-type]
        CORSMiddleware,  # type: ignore[arg-type]
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )

    # Register middleware - order matters!
    # 1. Request ID tracking (first to generate ID for all subsequent middleware)
    fastapi_app.add_middleware(RequestIDLoggerMiddleware)
    # 2. Request/response logging
    fastapi_app.add_middleware(
        RequestLoggingMiddleware,
        logger=logger,
        verbose=verbose_logging,
    )
    # 3. RLS session variables (must be set before any DB operations)
    fastapi_app.middleware("http")(rls_middleware)
    # 4. Request sanitization
    fastapi_app.middleware("http")(sanitize_request)
    # 5. Audit logging
    fastapi_app.middleware("http")(audit_middleware)
    # 6. Security headers
    fastapi_app.middleware("http")(security_headers_middleware)
    fastapi_app.include_router(core_router)
    fastapi_app.include_router(health_router)
    fastapi_app.include_router(auth_router)
    fastapi_app.include_router(admin_router)
    fastapi_app.include_router(admin_audit_router)  # NEW: P4-ADMIN-04 Audit logs UI + API
    fastapi_app.include_router(admin_config_router)  # NEW: System configuration management
    fastapi_app.include_router(config_public_router)  # ADR-067: Public config (categories, intents)
    fastapi_app.include_router(
        admin_gateway_providers_router
    )  # NEW: P3-T1 Gateway provider management
    fastapi_app.include_router(admin_gateway_metrics_router)  # NEW: P3-T2 Gateway metrics dashboard
    fastapi_app.include_router(admin_pricing_router)  # NEW: Admin pricing management
    fastapi_app.include_router(admin_grouping_roles_router)  # NEW: RBAC V2 grouping roles
    fastapi_app.include_router(admin_developer_teams_router)  # NEW: RBAC V2 teams
    fastapi_app.include_router(admin_user_roles_router)  # NEW: RBAC V2 user role management
    fastapi_app.include_router(admin_roles_router)  # NEW: ADR-041 Role-based use case permissions
    fastapi_app.include_router(tools_admin_router)  # NEW: T1-F3 Tool CRUD API (Admin)
    fastapi_app.include_router(
        tools_developer_router
    )  # NEW: T1-F5 Tool Discovery & Listing (Developer)
    fastapi_app.include_router(
        admin_intent_models_router
    )  # ADR-069: Intent model configuration (Development)
    fastapi_app.include_router(tools_health_router)  # NEW: T4-F1 Tool Health Monitoring Dashboard
    fastapi_app.include_router(
        tools_analytics_router
    )  # NEW: T4-F2 Tool Invocation Audit & Analytics
    fastapi_app.include_router(tools_testing_router)  # NEW: T4-F4 Tool Testing Interface
    fastapi_app.include_router(
        tools_registration_router
    )  # NEW: T5-F1 MCP Tool Registration Workflow
    fastapi_app.include_router(capabilities_router)  # NEW: Stateless Core v1 capabilities
    fastapi_app.include_router(chunking_router)  # NEW: Chunking and preflight analysis proxy
    fastapi_app.include_router(collection_mgmt_router)  # NEW: Collection management
    fastapi_app.include_router(run_manifests_router)  # NEW: Stateless Core v1 run manifests
    fastapi_app.include_router(
        stateless_router
    )  # NEW: Stateless Core v1 export/summary (ADR-030/031)
    fastapi_app.include_router(summaries_router)  # NEW: P4-F11 Summary generation
    fastapi_app.include_router(token_analytics_router)  # NEW: Token analytics
    fastapi_app.include_router(orchestrator_router)
    fastapi_app.include_router(corpus_router)
    fastapi_app.include_router(query_router)
    fastapi_app.include_router(query_history_router)
    fastapi_app.include_router(security_router)
    fastapi_app.include_router(templates_router)
    fastapi_app.include_router(output_templates_router)  # ADR-066: Custom visualization templates
    fastapi_app.include_router(prompt_patterns_router)  # NEW: Pattern library
    fastapi_app.include_router(use_case_mgmt_router)  # NEW: UC management endpoints
    fastapi_app.include_router(use_case_validation_router)  # NEW: UC validation
    fastapi_app.include_router(use_cases_router)
    fastapi_app.include_router(websocket_router)
    fastapi_app.include_router(models_router)

    # Log all registered routes for debugging
    for route in fastapi_app.routes:
        path = getattr(route, "path", None)
        if path is not None:
            logger.info(f"Registered route: {path}")

    return fastapi_app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

__all__ = ["create_app", "lifespan"]
