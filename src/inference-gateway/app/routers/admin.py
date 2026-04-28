"""
Admin API router for Inference Gateway.

Provides management endpoints for:
- Rate limit configuration
- Provider management
- Usage statistics

Requires 'admin' role for access.

P5-A15 VERIFIED (Nov 28, 2025):
- All 17 endpoints are async with `async def`
- Uses `get_db` from shared.database (async context manager)
- All DB operations use `await db.execute(text(query))`
- AsyncSession pattern verified
"""

import json
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from shared.auth import admin_required, get_current_user  # type: ignore[import-untyped]
from shared.auth.models import TokenPayload  # type: ignore[import-untyped]
from shared.database import get_db  # type: ignore[import-untyped]
from shared.logging_utils.fastapi import configure_logging  # type: ignore[import-untyped]
from shared.providers import (  # type: ignore[import-untyped]
    ProviderConfig,
    ProviderConfigUpdate,
    ProviderListResponse,
)
from sqlalchemy import text

logger = configure_logging(service_name="admin_router")

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(admin_required)],
)


# === Pydantic Models ===


class RateLimitConfig(BaseModel):
    """Rate limit configuration model."""

    id: Optional[UUID] = None
    limit_type: str = Field(..., description="Type: global, provider, integration, use_case")
    identifier: Optional[str] = Field(
        None, description="Identifier (e.g., 'openai', 'service:cortex')"
    )
    requests_per_minute: int = Field(..., gt=0, description="Max requests per minute")
    tokens_per_minute: Optional[int] = Field(
        None, gt=0, description="Max tokens per minute (optional)"
    )
    burst_size: int = Field(10, ge=0, description="Burst allowance")
    enabled: bool = Field(True, description="Enable/disable toggle")
    description: Optional[str] = Field(None, description="Human-readable description")


class RateLimitStats(BaseModel):
    """Current rate limit usage statistics."""

    limit_type: str
    identifier: Optional[str]
    current_count: int
    limit: int
    window_remaining_seconds: int


# === Endpoints ===


@router.get("/rate-limits", response_model=List[RateLimitConfig])
async def list_rate_limits(
    enabled_only: bool = False,
    token: TokenPayload = Depends(get_current_user),
) -> List[RateLimitConfig]:
    """
    List all configured rate limits.

    Args:
        enabled_only: Only return enabled limits
        token: JWT token (admin required)

    Returns:
        List of rate limit configurations
    """
    try:
        async with get_db() as db:
            query = """
                SELECT
                    id,
                    limit_type,
                    identifier,
                    requests_per_minute,
                    tokens_per_minute,
                    burst_size,
                    enabled,
                    description
                FROM gateway_rate_limits
            """

            if enabled_only:
                query += " WHERE enabled = true"

            query += " ORDER BY limit_type, identifier"

            result = await db.execute(text(query))
            rows = result.fetchall()

            return [
                RateLimitConfig(
                    id=row[0],
                    limit_type=row[1],
                    identifier=row[2],
                    requests_per_minute=row[3],
                    tokens_per_minute=row[4],
                    burst_size=row[5],
                    enabled=row[6],
                    description=row[7],
                )
                for row in rows
            ]

    except Exception as e:
        logger.error("Error listing rate limits", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to list rate limits") from e


@router.post("/rate-limits", response_model=RateLimitConfig, status_code=201)
async def create_rate_limit(
    config: RateLimitConfig,
    token: TokenPayload = Depends(get_current_user),
) -> RateLimitConfig:
    """
    Create a new rate limit configuration.

    Args:
        config: Rate limit configuration
        token: JWT token (admin required)

    Returns:
        Created rate limit configuration
    """
    try:
        async with get_db() as db:
            # Check if limit already exists
            check_query = text(
                """
                SELECT id FROM gateway_rate_limits
                WHERE limit_type = :limit_type::rate_limit_type
                  AND COALESCE(identifier, '') = COALESCE(:identifier, '')
                """
            )
            result = await db.execute(
                check_query,
                {"limit_type": config.limit_type, "identifier": config.identifier},
            )
            existing = result.fetchone()

            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"Rate limit already exists for {config.limit_type}:{config.identifier}",
                )

            # Insert new rate limit
            insert_query = text(
                """
                INSERT INTO gateway_rate_limits (
                    limit_type,
                    identifier,
                    requests_per_minute,
                    tokens_per_minute,
                    burst_size,
                    enabled,
                    description
                ) VALUES (
                    :limit_type::rate_limit_type,
                    :identifier,
                    :requests_per_minute,
                    :tokens_per_minute,
                    :burst_size,
                    :enabled,
                    :description
                )
                RETURNING id
                """
            )

            result = await db.execute(
                insert_query,
                {
                    "limit_type": config.limit_type,
                    "identifier": config.identifier,
                    "requests_per_minute": config.requests_per_minute,
                    "tokens_per_minute": config.tokens_per_minute,
                    "burst_size": config.burst_size,
                    "enabled": config.enabled,
                    "description": config.description,
                },
            )
            row = result.fetchone()
            config.id = row[0] if row else None

            await db.commit()

            logger.info(
                "Rate limit created",
                extra={
                    "limit_type": config.limit_type,
                    "identifier": config.identifier,
                    "requests_per_minute": config.requests_per_minute,
                },
            )

            return config

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating rate limit", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to create rate limit") from e


@router.put("/rate-limits/{limit_id}", response_model=RateLimitConfig)
async def update_rate_limit(
    limit_id: UUID,
    config: RateLimitConfig,
    token: TokenPayload = Depends(get_current_user),
) -> RateLimitConfig:
    """
    Update an existing rate limit configuration.

    Args:
        limit_id: Rate limit ID
        config: Updated configuration
        token: JWT token (admin required)

    Returns:
        Updated rate limit configuration
    """
    try:
        async with get_db() as db:
            update_query = text(
                """
                UPDATE gateway_rate_limits
                SET
                    requests_per_minute = :requests_per_minute,
                    tokens_per_minute = :tokens_per_minute,
                    burst_size = :burst_size,
                    enabled = :enabled,
                    description = :description
                WHERE id = :id
                RETURNING id
                """
            )

            result = await db.execute(
                update_query,
                {
                    "id": limit_id,
                    "requests_per_minute": config.requests_per_minute,
                    "tokens_per_minute": config.tokens_per_minute,
                    "burst_size": config.burst_size,
                    "enabled": config.enabled,
                    "description": config.description,
                },
            )
            row = result.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Rate limit not found")

            await db.commit()

            config.id = limit_id

            logger.info(
                "Rate limit updated",
                extra={"limit_id": str(limit_id), "enabled": config.enabled},
            )

            return config

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating rate limit", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to update rate limit") from e


@router.delete("/rate-limits/{limit_id}", status_code=204)
async def delete_rate_limit(
    limit_id: UUID,
    token: TokenPayload = Depends(get_current_user),
) -> None:
    """
    Delete a rate limit configuration.

    Args:
        limit_id: Rate limit ID
        token: JWT token (admin required)
    """
    try:
        async with get_db() as db:
            delete_query = text(
                """
                DELETE FROM gateway_rate_limits
                WHERE id = :id
                RETURNING id
                """
            )

            result = await db.execute(delete_query, {"id": limit_id})
            row = result.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Rate limit not found")

            await db.commit()

            logger.info("Rate limit deleted", extra={"limit_id": str(limit_id)})

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting rate limit", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to delete rate limit") from e


@router.get("/rate-limits/stats", response_model=List[RateLimitStats])
async def get_rate_limit_stats(
    token: TokenPayload = Depends(get_current_user),
) -> List[RateLimitStats]:
    """
    Get current rate limit usage statistics.

    Shows current request counts for all configured limits.

    Args:
        token: JWT token (admin required)

    Returns:
        List of rate limit usage statistics
    """
    try:
        import time

        from ..services.redis_client import get_redis_client

        redis_client = get_redis_client()
        stats = []

        # Get all enabled rate limits
        async with get_db() as db:
            result = await db.execute(
                text(
                    """
                    SELECT limit_type, identifier, requests_per_minute, burst_size
                    FROM gateway_rate_limits
                    WHERE enabled = true
                    ORDER BY limit_type, identifier
                    """
                )
            )
            limits = result.fetchall()

            # Check Redis for current counts
            for row in limits:
                limit_type, identifier, rpm, burst = row

                # Build Redis key
                key_parts = ["ratelimit", limit_type]
                if identifier:
                    key_parts.append(identifier)
                key = ":".join(key_parts)

                # Get current count from Redis
                if redis_client.is_available:
                    try:
                        now = time.time()
                        window_start = now - 60  # 1 minute window

                        # Count entries in sorted set
                        count = await redis_client.client.zcount(key, window_start, now)  # type: ignore

                        # Get oldest entry for window remaining calculation
                        oldest_entries = await redis_client.client.zrange(  # type: ignore
                            key, 0, 0, withscores=True
                        )
                        if oldest_entries:
                            oldest_timestamp = oldest_entries[0][1]
                            window_remaining = int(60 - (now - oldest_timestamp))
                        else:
                            window_remaining = 60

                        stats.append(
                            RateLimitStats(
                                limit_type=limit_type,
                                identifier=identifier,
                                current_count=count,
                                limit=rpm + burst,
                                window_remaining_seconds=window_remaining,
                            )
                        )

                    except Exception as e:
                        logger.warning(
                            "Error getting Redis stats",
                            extra={"key": key, "error": str(e)},
                        )
                        # Add placeholder stats
                        stats.append(
                            RateLimitStats(
                                limit_type=limit_type,
                                identifier=identifier,
                                current_count=0,
                                limit=rpm + burst,
                                window_remaining_seconds=60,
                            )
                        )
                else:
                    # Redis not available - return zero counts
                    stats.append(
                        RateLimitStats(
                            limit_type=limit_type,
                            identifier=identifier,
                            current_count=0,
                            limit=rpm + burst,
                            window_remaining_seconds=60,
                        )
                    )

        return stats

    except Exception as e:
        logger.error("Error getting rate limit stats", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to get rate limit stats") from e


# === Circuit Breaker Endpoints ===


class CircuitBreakerState(BaseModel):
    """Circuit breaker state for a provider."""

    provider: str
    state: str = Field(..., description="State: CLOSED, OPEN, HALF_OPEN")
    failure_count: int = Field(0, description="Current failure count")
    success_count: int = Field(0, description="Current success count")
    last_failure_time: Optional[float] = Field(None, description="Timestamp of last failure")
    opened_at: Optional[float] = Field(None, description="Timestamp when circuit opened")


@router.get("/circuit-breaker/states", response_model=List[CircuitBreakerState])
async def get_circuit_breaker_states(
    token: TokenPayload = Depends(get_current_user),
) -> List[CircuitBreakerState]:
    """
    Get circuit breaker states for all providers.

    Shows current circuit state, failure counts, and timestamps.

    Args:
        token: JWT token (admin required)

    Returns:
        List of circuit breaker states
    """
    try:
        from ..services.circuit_breaker import get_circuit_breaker

        circuit_breaker = get_circuit_breaker()

        # Get all states
        states = await circuit_breaker.get_all_states()

        # Convert to response models
        return [
            CircuitBreakerState(
                provider=provider,
                state=info["state"],
                failure_count=info["failure_count"],
                success_count=info["success_count"],
                last_failure_time=info["last_failure_time"],
                opened_at=info["opened_at"],
            )
            for provider, info in states.items()
        ]

    except Exception as e:
        logger.error("Error getting circuit breaker states", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to get circuit breaker states") from e


@router.post("/circuit-breaker/{provider}/reset", status_code=204)
async def reset_circuit_breaker(
    provider: str,
    token: TokenPayload = Depends(get_current_user),
) -> None:
    """
    Manually reset circuit breaker for a provider.

    Forces circuit to CLOSED state, clearing failure counts.

    Args:
        provider: Provider name
        token: JWT token (admin required)
    """
    try:
        from ..services.circuit_breaker import get_circuit_breaker

        circuit_breaker = get_circuit_breaker()

        # Reset circuit
        await circuit_breaker.reset(provider)

        logger.info(
            "Circuit breaker manually reset",
            extra={"provider": provider, "admin_user": token.sub},
        )

    except Exception as e:
        logger.error(
            "Error resetting circuit breaker",
            extra={"provider": provider, "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to reset circuit breaker") from e


# === Provider Management Endpoints ===


@router.get("/providers", response_model=ProviderListResponse)
async def list_providers(
    limit: int = 50,
    offset: int = 0,
    enabled_only: bool = False,
    token: TokenPayload = Depends(get_current_user),
) -> ProviderListResponse:
    """
    List all configured providers with pagination.

    Args:
        limit: Maximum number of providers to return
        offset: Number of providers to skip
        enabled_only: Only return enabled providers
        token: JWT token (admin required)

    Returns:
        Paginated list of provider configurations
    """
    try:
        async with get_db() as db:
            # Count total
            count_query = "SELECT COUNT(*) FROM gateway_providers"
            if enabled_only:
                count_query += " WHERE is_enabled = true"

            result = await db.execute(text(count_query))
            total = result.scalar() or 0

            # Get providers
            query = """
                SELECT
                    id,
                    name,
                    provider_type::text,
                    base_url,
                    is_enabled,
                    status::text,
                    priority,
                    config_json,
                    health_check_url,
                    last_health_check,
                    last_health_status,
                    error_count,
                    success_count,
                    circuit_state,
                    created_at,
                    updated_at
                FROM gateway_providers
            """

            if enabled_only:
                query += " WHERE is_enabled = true"

            query += " ORDER BY priority ASC, name ASC LIMIT :limit OFFSET :offset"

            result = await db.execute(text(query), {"limit": limit, "offset": offset})
            rows = result.fetchall()

            items = [
                ProviderConfig(
                    id=row[0],
                    name=row[1],
                    provider_type=row[2],
                    base_url=row[3],
                    api_key=None,
                    is_enabled=row[4],
                    status=row[5],
                    priority=row[6],
                    config_json=row[7] or {},  # asyncpg returns dict from JSONB
                    health_check_url=row[8],
                    last_health_check=row[9].isoformat() if row[9] else None,
                    last_health_status=row[10],
                    error_count=row[11],
                    success_count=row[12],
                    circuit_state=row[13],
                    created_at=row[14].isoformat() if row[14] else None,
                    updated_at=row[15].isoformat() if row[15] else None,
                    models=None,  # Gateway providers don't have models list
                    connection=None,  # Gateway providers don't have connection config
                )
                for row in rows
            ]

            return ProviderListResponse(
                items=items,
                total=total,
                limit=limit,
                offset=offset,
            )

    except Exception as e:
        logger.error("Error listing providers", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to list providers") from e


@router.get("/providers/{provider_id}", response_model=ProviderConfig)
async def get_provider(
    provider_id: UUID,
    token: TokenPayload = Depends(get_current_user),
) -> ProviderConfig:
    """
    Get a specific provider by ID.

    Args:
        provider_id: Provider UUID
        token: JWT token (admin required)

    Returns:
        Provider configuration
    """
    try:
        async with get_db() as db:
            query = text(
                """
                SELECT
                    id,
                    name,
                    provider_type::text,
                    base_url,
                    is_enabled,
                    status::text,
                    priority,
                    config_json,
                    health_check_url,
                    last_health_check,
                    last_health_status,
                    error_count,
                    success_count,
                    circuit_state,
                    created_at,
                    updated_at
                FROM gateway_providers
                WHERE id = :id
                """
            )

            result = await db.execute(query, {"id": provider_id})
            row = result.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Provider not found")

            return ProviderConfig(
                id=row[0],
                name=row[1],
                provider_type=row[2],
                base_url=row[3],
                api_key=None,
                is_enabled=row[4],
                status=row[5],
                priority=row[6],
                config_json=row[7] or {},  # asyncpg returns dict from JSONB
                health_check_url=row[8],
                last_health_check=row[9].isoformat() if row[9] else None,
                last_health_status=row[10],
                error_count=row[11],
                success_count=row[12],
                circuit_state=row[13],
                created_at=row[14].isoformat() if row[14] else None,
                updated_at=row[15].isoformat() if row[15] else None,
                models=None,  # Gateway providers don't have models list
                connection=None,  # Gateway providers don't have connection config
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error getting provider",
            extra={"provider_id": str(provider_id), "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to get provider") from e


@router.post("/providers", response_model=ProviderConfig, status_code=201)
async def create_provider(
    config: ProviderConfig,
    token: TokenPayload = Depends(get_current_user),
) -> ProviderConfig:
    """
    Create a new provider.

    Args:
        config: Provider configuration
        token: JWT token (admin required)

    Returns:
        Created provider configuration
    """
    try:
        async with get_db() as db:
            # Check if provider name already exists
            check_query = text("SELECT id FROM gateway_providers WHERE name = :name")
            result = await db.execute(check_query, {"name": config.name})
            existing = result.fetchone()

            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"Provider with name '{config.name}' already exists",
                )

            # Insert provider (without API key encryption for now - manual secret management)
            insert_query = text(
                """
                INSERT INTO gateway_providers (
                    name,
                    provider_type,
                    base_url,
                    api_key_encrypted,
                    is_enabled,
                    status,
                    priority,
                    config_json,
                    health_check_url,
                    created_by
                ) VALUES (
                    :name,
                    CAST(:provider_type AS provider_type),
                    :base_url,
                    :api_key,
                    :is_enabled,
                    CAST(:status AS provider_status),
                    :priority,
                    :config_json,
                    :health_check_url,
                    :created_by
                )
                RETURNING id, created_at, updated_at
                """
            )

            result = await db.execute(
                insert_query,
                {
                    "name": config.name,
                    "provider_type": config.provider_type,
                    "base_url": config.base_url,
                    "api_key": config.api_key,  # Store plaintext for now (ADR-051 manual mgmt)
                    "is_enabled": config.is_enabled,
                    "status": config.status,
                    "priority": config.priority,
                    "config_json": json.dumps(
                        config.config_json or {}
                    ),  # SQLAlchemy text() requires JSON string
                    "health_check_url": config.health_check_url,
                    "created_by": UUID(
                        token.user_id
                    ),  # Fixed: use user_id (UUID) not sub (username)
                },
            )
            row = result.fetchone()
            if row:
                config.id = row[0]
                config.created_at = row[1].isoformat() if row[1] else None
                config.updated_at = row[2].isoformat() if row[2] else None

            await db.commit()

            logger.info(
                "Provider created",
                extra={
                    "provider_id": str(config.id),
                    "provider_name": config.name,
                    "provider_type": config.provider_type,
                    "admin_user": token.sub,
                },
            )

            # Clear API key from response
            config.api_key = None
            return config

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating provider", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to create provider") from e


@router.put("/providers/{provider_id}", response_model=ProviderConfig)
async def update_provider(
    provider_id: UUID,
    config: ProviderConfigUpdate,
    token: TokenPayload = Depends(get_current_user),
) -> ProviderConfig:
    """
    Update an existing provider.

    Args:
        provider_id: Provider UUID
        config: Updated provider configuration
        token: JWT token (admin required)

    Returns:
        Updated provider configuration
    """
    try:
        async with get_db() as db:
            # Build update query dynamically based on what's provided
            update_parts = []
            params: dict[str, Any] = {"id": provider_id}

            if config.name is not None:
                update_parts.append("name = :name")
                params["name"] = config.name

            if config.provider_type is not None:
                update_parts.append("provider_type = CAST(:provider_type AS provider_type)")
                params["provider_type"] = config.provider_type

            if config.base_url is not None:
                update_parts.append("base_url = :base_url")
                params["base_url"] = config.base_url

            # Only update API key if provided
            if config.api_key is not None:
                update_parts.append("api_key_encrypted = :api_key")
                params["api_key"] = config.api_key

            if config.is_enabled is not None:
                update_parts.append("is_enabled = :is_enabled")
                params["is_enabled"] = config.is_enabled

            if config.status is not None:
                update_parts.append("status = CAST(:status AS provider_status)")
                params["status"] = config.status

            if config.priority is not None:
                update_parts.append("priority = :priority")
                params["priority"] = config.priority

            if config.config_json is not None:
                update_parts.append("config_json = :config_json")
                params["config_json"] = json.dumps(
                    config.config_json or {}
                )  # SQLAlchemy text() requires JSON string

            if config.health_check_url is not None:
                update_parts.append("health_check_url = :health_check_url")
                params["health_check_url"] = config.health_check_url

            if config.timeout_seconds is not None:
                update_parts.append("timeout_seconds = :timeout_seconds")
                params["timeout_seconds"] = config.timeout_seconds

            if not update_parts:
                raise HTTPException(status_code=400, detail="No fields to update")

            update_query = text(
                f"""
                UPDATE gateway_providers
                SET {", ".join(update_parts)}
                WHERE id = :id
                RETURNING updated_at
                """
            )

            result = await db.execute(update_query, params)
            row = result.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Provider not found")

            await db.commit()

            logger.info(
                "Provider updated",
                extra={"provider_id": str(provider_id), "admin_user": token.sub},
            )

            # Fetch and return updated provider
            return await get_provider(provider_id, token)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error updating provider",
            extra={"provider_id": str(provider_id), "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to update provider") from e


@router.delete("/providers/{provider_id}", status_code=204)
async def delete_provider(
    provider_id: UUID,
    token: TokenPayload = Depends(get_current_user),
) -> None:
    """
    Delete a provider.

    Args:
        provider_id: Provider UUID
        token: JWT token (admin required)
    """
    try:
        async with get_db() as db:
            delete_query = text(
                """
                DELETE FROM gateway_providers
                WHERE id = :id
                RETURNING id
                """
            )

            result = await db.execute(delete_query, {"id": provider_id})
            row = result.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Provider not found")

            await db.commit()

            logger.info(
                "Provider deleted",
                extra={"provider_id": str(provider_id), "admin_user": token.sub},
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error deleting provider",
            extra={"provider_id": str(provider_id), "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to delete provider") from e


@router.post("/providers/{provider_id}/test", status_code=200)
async def test_provider(
    provider_id: UUID,
    token: TokenPayload = Depends(get_current_user),
) -> dict:
    """
    Test provider connectivity and health.

    Args:
        provider_id: Provider UUID
        token: JWT token (admin required)

    Returns:
        Test result with status and latency
    """
    try:
        import time

        import httpx

        # Get provider config
        provider = await get_provider(provider_id, token)

        # Test health check URL if available, otherwise test base URL
        test_url = provider.health_check_url or f"{provider.base_url}/models"

        start_time = time.time()
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(test_url)
                latency_ms = int((time.time() - start_time) * 1000)

                # Update health check results
                async with get_db() as db:
                    update_query = text(
                        """
                        UPDATE gateway_providers
                        SET last_health_check = NOW(),
                            last_health_status = :status
                        WHERE id = :id
                        """
                    )
                    await db.execute(
                        update_query,
                        {"id": provider_id, "status": response.status_code == 200},
                    )
                    await db.commit()

                return {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                    "message": f"Provider responded in {latency_ms}ms",
                }

            except httpx.TimeoutException:
                return {
                    "success": False,
                    "status_code": None,
                    "latency_ms": None,
                    "message": "Request timed out after 5 seconds",
                }
            except Exception as e:
                return {
                    "success": False,
                    "status_code": None,
                    "latency_ms": None,
                    "message": f"Connection error: {str(e)}",
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error testing provider",
            extra={"provider_id": str(provider_id), "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to test provider") from e


# === Metrics Endpoints ===


class GatewayMetrics(BaseModel):
    """Aggregate metrics for Gateway usage."""

    total_requests: int = Field(..., description="Total number of requests")
    successful_requests: int = Field(..., description="Number of successful requests")
    failed_requests: int = Field(..., description="Number of failed requests")
    success_rate: float = Field(..., description="Success rate percentage")
    total_input_tokens: int = Field(..., description="Total input tokens")
    total_output_tokens: int = Field(..., description="Total output tokens")
    total_cost_eur: float = Field(..., description="Total cost in EUR")
    avg_latency_ms: float = Field(..., description="Average total latency (ms)")
    p50_latency_ms: Optional[float] = Field(None, description="P50 latency (ms)")
    p95_latency_ms: Optional[float] = Field(None, description="P95 latency (ms)")
    p99_latency_ms: Optional[float] = Field(None, description="P99 latency (ms)")
    unique_models: int = Field(..., description="Number of unique models used")
    unique_users: int = Field(..., description="Number of unique users")
    streaming_requests: int = Field(..., description="Number of streaming requests")


class TimeSeriesPoint(BaseModel):
    """Single time-series data point."""

    timestamp: str = Field(..., description="ISO timestamp")
    value: float = Field(..., description="Metric value")
    label: Optional[str] = Field(None, description="Optional label")


class TimeSeriesData(BaseModel):
    """Time-series metrics data."""

    latency: List[TimeSeriesPoint] = Field(default_factory=list, description="Latency over time")
    tokens: List[TimeSeriesPoint] = Field(default_factory=list, description="Token usage over time")
    cost: List[TimeSeriesPoint] = Field(default_factory=list, description="Cost over time")
    requests: List[TimeSeriesPoint] = Field(
        default_factory=list, description="Request count over time"
    )


class ProviderMetrics(BaseModel):
    """Per-provider metrics breakdown."""

    provider_name: str = Field(..., description="Provider name")
    request_count: int = Field(..., description="Number of requests")
    success_rate: float = Field(..., description="Success rate percentage")
    avg_latency_ms: float = Field(..., description="Average latency (ms)")
    total_cost_eur: float = Field(..., description="Total cost (EUR)")
    total_tokens: int = Field(..., description="Total tokens")


class ModelMetrics(BaseModel):
    """Per-model metrics breakdown."""

    model_name: str = Field(..., description="Model name")
    request_count: int = Field(..., description="Number of requests")
    total_tokens: int = Field(..., description="Total tokens")
    total_cost_eur: float = Field(..., description="Total cost (EUR)")
    avg_latency_ms: float = Field(..., description="Average latency (ms)")


@router.get("/metrics/aggregate", response_model=GatewayMetrics)
async def get_aggregate_metrics(
    hours: int = 24,
    provider: Optional[str] = None,
    token: TokenPayload = Depends(get_current_user),
) -> GatewayMetrics:
    """
    Get aggregate Gateway metrics for specified time window.

    Args:
        hours: Time window in hours (default: 24)
        provider: Filter by provider name (optional)
        token: JWT token (admin required)

    Returns:
        Aggregate metrics
    """
    try:
        async with get_db() as db:
            # Build query with optional provider filter
            # Safe to use f-string for hours since FastAPI validates it as integer
            where_clause = f"WHERE ts_utc >= NOW() - INTERVAL '{hours} hours'"
            params = {}

            if provider:
                where_clause += " AND provider_name = :provider"
                params["provider"] = provider

            query = text(
                f"""
                SELECT
                    COUNT(*) as total_requests,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_requests,
                    SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as failed_requests,
                    ROUND(100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) as success_rate,
                    SUM(tokens_in) as total_input_tokens,
                    SUM(tokens_out) as total_output_tokens,
                    ROUND(CAST(SUM(COALESCE(cost_eur, 0)) AS NUMERIC), 6) as total_cost_eur,
                    ROUND(AVG(latency_total_ms), 2) as avg_latency_ms,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY latency_total_ms) as p50_latency_ms,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_total_ms) as p95_latency_ms,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_total_ms) as p99_latency_ms,
                    COUNT(DISTINCT model_requested) as unique_models,
                    COUNT(DISTINCT user_id) as unique_users,
                    SUM(CASE WHEN stream_enabled THEN 1 ELSE 0 END) as streaming_requests
                FROM gateway_usage_log
                {where_clause}
                """
            )

            result = await db.execute(query, params)
            row = result.fetchone()

            if not row or row[0] == 0:
                # No data - return zeros
                return GatewayMetrics(
                    total_requests=0,
                    successful_requests=0,
                    failed_requests=0,
                    success_rate=0.0,
                    total_input_tokens=0,
                    total_output_tokens=0,
                    total_cost_eur=0.0,
                    avg_latency_ms=0.0,
                    p50_latency_ms=0.0,
                    p95_latency_ms=0.0,
                    p99_latency_ms=0.0,
                    unique_models=0,
                    unique_users=0,
                    streaming_requests=0,
                )

            return GatewayMetrics(
                total_requests=row[0] or 0,
                successful_requests=row[1] or 0,
                failed_requests=row[2] or 0,
                success_rate=float(row[3] or 0.0),
                total_input_tokens=row[4] or 0,
                total_output_tokens=row[5] or 0,
                total_cost_eur=float(row[6] or 0.0),
                avg_latency_ms=float(row[7] or 0.0),
                p50_latency_ms=float(row[8]) if row[8] is not None else None,
                p95_latency_ms=float(row[9]) if row[9] is not None else None,
                p99_latency_ms=float(row[10]) if row[10] is not None else None,
                unique_models=row[11] or 0,
                unique_users=row[12] or 0,
                streaming_requests=row[13] or 0,
            )

    except Exception as e:
        logger.error("Error fetching aggregate metrics", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to fetch aggregate metrics") from e


@router.get("/metrics/timeseries", response_model=TimeSeriesData)
async def get_timeseries_metrics(
    hours: int = 24,
    interval_minutes: int = 60,
    provider: Optional[str] = None,
    token: TokenPayload = Depends(get_current_user),
) -> TimeSeriesData:
    """
    Get time-series metrics data.

    Args:
        hours: Time window in hours (default: 24)
        interval_minutes: Data point interval in minutes (default: 60)
        provider: Filter by provider name (optional)
        token: JWT token (admin required)

    Returns:
        Time-series data for charts
    """
    try:
        async with get_db() as db:
            # Safe to use f-string for hours since FastAPI validates it as integer
            where_clause = f"WHERE ts_utc >= NOW() - INTERVAL '{hours} hours'"
            params: dict[str, Any] = {"interval_minutes": interval_minutes}

            if provider:
                where_clause += " AND provider_name = :provider"
                params["provider"] = provider

            query = text(
                f"""
                SELECT
                    DATE_TRUNC('hour', ts_utc) as time_bucket,
                    ROUND(AVG(latency_total_ms), 2) as avg_latency,
                    SUM(tokens_in + tokens_out) as total_tokens,
                    ROUND(CAST(SUM(COALESCE(cost_eur, 0)) AS NUMERIC), 6) as total_cost,
                    COUNT(*) as request_count
                FROM gateway_usage_log
                {where_clause}
                GROUP BY time_bucket
                ORDER BY time_bucket
                """
            )

            result = await db.execute(query, params)
            rows = result.fetchall()

            latency_data = []
            tokens_data = []
            cost_data = []
            requests_data = []

            for row in rows:
                timestamp = row[0].isoformat() if row[0] else ""
                latency_data.append(
                    TimeSeriesPoint(timestamp=timestamp, value=float(row[1] or 0), label=None)
                )
                tokens_data.append(
                    TimeSeriesPoint(timestamp=timestamp, value=float(row[2] or 0), label=None)
                )
                cost_data.append(
                    TimeSeriesPoint(timestamp=timestamp, value=float(row[3] or 0), label=None)
                )
                requests_data.append(
                    TimeSeriesPoint(timestamp=timestamp, value=float(row[4] or 0), label=None)
                )

            return TimeSeriesData(
                latency=latency_data,
                tokens=tokens_data,
                cost=cost_data,
                requests=requests_data,
            )

    except Exception as e:
        logger.error("Error fetching time-series metrics", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to fetch time-series metrics") from e


@router.get("/metrics/by-provider", response_model=List[ProviderMetrics])
async def get_metrics_by_provider(
    hours: int = 24,
    token: TokenPayload = Depends(get_current_user),
) -> List[ProviderMetrics]:
    """
    Get metrics broken down by provider.

    Args:
        hours: Time window in hours (default: 24)
        token: JWT token (admin required)

    Returns:
        List of provider metrics
    """
    try:
        async with get_db() as db:
            # Safe to use f-string for hours since FastAPI validates it as integer
            query = text(
                f"""
                SELECT
                    COALESCE(provider_name, 'Unknown') as provider_name,
                    COUNT(*) as request_count,
                    ROUND(100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) as success_rate,
                    ROUND(AVG(latency_total_ms), 2) as avg_latency_ms,
                    ROUND(CAST(SUM(COALESCE(cost_eur, 0)) AS NUMERIC), 6) as total_cost_eur,
                    SUM(tokens_in + tokens_out) as total_tokens
                FROM gateway_usage_log
                WHERE ts_utc >= NOW() - INTERVAL '{hours} hours'
                GROUP BY provider_name
                ORDER BY request_count DESC
                """
            )

            result = await db.execute(query)
            rows = result.fetchall()

            return [
                ProviderMetrics(
                    provider_name=row[0],
                    request_count=row[1] or 0,
                    success_rate=float(row[2] or 0.0),
                    avg_latency_ms=float(row[3] or 0.0),
                    total_cost_eur=float(row[4] or 0.0),
                    total_tokens=row[5] or 0,
                )
                for row in rows
            ]

    except Exception as e:
        logger.error("Error fetching provider metrics", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to fetch provider metrics") from e


@router.get("/metrics/by-model", response_model=List[ModelMetrics])
async def get_metrics_by_model(
    hours: int = 24,
    token: TokenPayload = Depends(get_current_user),
) -> List[ModelMetrics]:
    """
    Get metrics broken down by model.

    Args:
        hours: Time window in hours (default: 24)
        token: JWT token (admin required)

    Returns:
        List of model metrics
    """
    try:
        async with get_db() as db:
            # Safe to use f-string for hours since FastAPI validates it as integer
            query = text(
                f"""
                SELECT
                    model_requested as model_name,
                    COUNT(*) as request_count,
                    SUM(tokens_in + tokens_out) as total_tokens,
                    ROUND(CAST(SUM(COALESCE(cost_eur, 0)) AS NUMERIC), 6) as total_cost_eur,
                    ROUND(AVG(latency_total_ms), 2) as avg_latency_ms
                FROM gateway_usage_log
                WHERE ts_utc >= NOW() - INTERVAL '{hours} hours'
                GROUP BY model_requested
                ORDER BY request_count DESC
                """
            )

            result = await db.execute(query)
            rows = result.fetchall()

            return [
                ModelMetrics(
                    model_name=row[0],
                    request_count=row[1] or 0,
                    total_tokens=row[2] or 0,
                    total_cost_eur=float(row[3] or 0.0),
                    avg_latency_ms=float(row[4] or 0.0),
                )
                for row in rows
            ]

    except Exception as e:
        logger.error("Error fetching model metrics", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to fetch model metrics") from e


# === Router Management Endpoints ===


@router.post("/router/reload", status_code=200)
async def reload_router(
    token: TokenPayload = Depends(get_current_user),
) -> dict:
    """
    Reload model routing table from database.

    Call this after syncing models or updating provider assignments
    to refresh the inference gateway's routing cache.

    Args:
        token: JWT token (admin required)

    Returns:
        Reload status and route count
    """
    try:
        from ..routers.chat import simple_router as chat_router
        from ..routers.embeddings import simple_router as embeddings_router
        from ..routers.responses import simple_router as responses_router

        # Reload all routers
        await chat_router.reload()
        await embeddings_router.reload()
        await responses_router.reload()

        # Get route count
        routes = await chat_router.get_route_map()

        logger.info(
            "Model routing table reloaded",
            extra={
                "route_count": len(routes),
                "admin_user": token.sub,
            },
        )

        return {
            "success": True,
            "message": f"Successfully reloaded {len(routes)} model routes",
            "route_count": len(routes),
        }

    except Exception as e:
        logger.error("Error reloading router", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to reload router: {str(e)}") from e


@router.get("/router/routes", status_code=200)
async def get_router_routes(
    token: TokenPayload = Depends(get_current_user),
) -> dict:
    """
    Get current model routing table.

    Shows which models are routed to which gateway providers.

    Args:
        token: JWT token (admin required)

    Returns:
        Current routing table
    """
    try:
        from ..routers.chat import simple_router

        routes = await simple_router.get_route_map()

        return {
            "route_count": len(routes),
            "routes": routes,
        }

    except Exception as e:
        logger.error("Error getting routes", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to get routes: {str(e)}") from e
