# pylint: disable=import-error
"""
Health router module.

This module defines health check endpoints for the AI Operations Platform (AIOP) API,
including general service health and component-specific health checks.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth.models import TokenPayload
from shared.logging_utils.fastapi import configure_logging

from ..db.database import get_async_db
from ..services.conversation_cache import get_conversation_cache
from ..utils.auth import get_current_user

# Configure logger for the health router
logger = configure_logging(service_name="health_router", log_level="INFO", log_format="json")

# Create router with 'health' tag for OpenAPI grouping
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(request: Request) -> dict[str, str]:
    """
    Health check endpoint for monitoring and container orchestration.

    Returns:
        dict: A simple status message indicating the service is healthy
    """
    logger.info(
        "Health check endpoint accessed",
        extra={"client": request.client.host if request.client else "unknown"},
    )
    return {"status": "healthy"}


@router.get("/health/cache")
async def cache_health(current_user: TokenPayload = Depends(get_current_user)) -> dict:
    """
    Conversation cache health and statistics endpoint.

    Returns real-time metrics for monitoring dashboards including:
    - Capacity utilization
    - Performance indicators
    - Security status
    - Expiration metrics

    Requires authentication.

    Returns:
        dict: Cache health status and comprehensive statistics
    """
    cache = get_conversation_cache()
    stats = cache.get_stats()

    # Calculate health indicators
    capacity_utilization = (
        (stats["total_sessions"] / stats["max_entries"]) * 100 if stats["max_entries"] > 0 else 0
    )

    # Determine overall health status
    if capacity_utilization >= 95:
        health_status = "critical"
    elif capacity_utilization >= 80:
        health_status = "warning"
    else:
        health_status = "healthy"

    logger.info(
        "Cache health endpoint accessed",
        extra={
            "user_id": current_user.user_id,
            "health_status": health_status,
            "capacity_utilization": capacity_utilization,
        },
    )

    return {
        "status": health_status,
        "stats": stats,
        "health_indicators": {
            "capacity_utilization_pct": round(capacity_utilization, 2),
            "expired_sessions": stats["expired_sessions"],
            "encryption_enabled": stats.get("encryption") == "AES-GCM-256",
            "token_estimation_method": stats.get("token_estimation", "unknown"),
        },
        "thresholds": {
            "warning_threshold_pct": 80,
            "critical_threshold_pct": 95,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/config")
async def config_health(
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> dict:
    """
    Check configuration health, including model availability.

    Validates that critical system configuration is healthy, particularly
    focusing on the default embedding model availability which is required
    for creating new collections.

    Requires authentication.

    Returns:
        dict: Configuration health status with any issues identified
    """
    issues = []

    try:
        # Check embedding model availability
        query = text(
            "SELECT config->>'default_embedding_model' FROM system_config WHERE section = 'corpus'"
        )
        result = await db.execute(query)
        row = result.fetchone()

        if row:
            configured_model = row[0]
            model_query = text(
                "SELECT is_available FROM models "
                "WHERE model_id = :model_id AND model_type = 'embedding'"
            )
            model_result = await db.execute(model_query, {"model_id": configured_model})
            model_row = model_result.fetchone()

            if not model_row:
                issues.append(
                    {
                        "severity": "critical",
                        "component": "corpus_config",
                        "message": f"Default embedding model '{configured_model}' not found in model registry",
                        "recommendation": "Update default_embedding_model in System Configuration or register the model",
                        "impact": "Cannot create new collections",
                    }
                )
            elif not model_row[0]:
                issues.append(
                    {
                        "severity": "critical",
                        "component": "corpus_config",
                        "message": f"Default embedding model '{configured_model}' is not available",
                        "recommendation": "Update default_embedding_model in System Configuration to an available model",
                        "impact": "Cannot create new collections",
                    }
                )
        else:
            issues.append(
                {
                    "severity": "critical",
                    "component": "corpus_config",
                    "message": "Corpus configuration not found",
                    "recommendation": "Initialize system configuration",
                    "impact": "System configuration may be corrupted",
                }
            )

    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error checking configuration health: %s", e, exc_info=True)
        issues.append(
            {
                "severity": "warning",
                "component": "health_check",
                "message": "Error performing configuration health check",
                "recommendation": "Check database connectivity and logs",
                "impact": "Unable to validate configuration",
            }
        )

    is_healthy = len(issues) == 0

    logger.info(
        "Configuration health check completed",
        extra={
            "user_id": current_user.user_id,
            "is_healthy": is_healthy,
            "issue_count": len(issues),
        },
    )

    return {
        "healthy": is_healthy,
        "issues": issues,
        "checked_at": datetime.now(UTC).isoformat(),
        "status": "healthy" if is_healthy else "unhealthy",
    }
