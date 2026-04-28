"""
Token analytics router for LLMaaS rate limit monitoring and usage metrics.

This module provides endpoints for monitoring token usage rates, calculating
utilization against pricing tier limits, and generating recommendations for
tier management.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import admin_required
from shared.auth.models import User
from shared.logging_utils.fastapi import get_logger

from ..db.database import get_async_db
from ..db.models import ModelConfig, PricingTier, TokenUsage
from ..schemas.pricing import TokenRateMetrics, TokenRateResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/analytics/tokens", tags=["Token Analytics"])


@router.get("/rate-limits/current", response_model=TokenRateResponse)
async def get_current_token_rate(
    window_minutes: int = Query(
        1, ge=1, le=60, description="Time window in minutes for rate calculation"
    ),
    model_id: str | None = Query(None, description="Filter by specific model ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_required),
) -> TokenRateResponse:
    """
    Calculate tokens-per-minute for rate limit monitoring.
    Queries pricing_tiers table for tier limits and provides utilization metrics.
    """
    try:
        # Calculate time window
        since = datetime.now(UTC) - timedelta(minutes=window_minutes)

        # Build query for token usage aggregation
        stmt = (
            select(
                func.sum(TokenUsage.tokens_in).label("total_in"),
                func.sum(TokenUsage.tokens_out).label("total_out"),
                TokenUsage.model_id,
            )
            .where(TokenUsage.created_at >= since)
            .group_by(TokenUsage.model_id)
        )

        if model_id:
            stmt = stmt.where(TokenUsage.model_id == model_id)

        # Execute query
        result = await db.execute(stmt)
        results = result.all()

        # Calculate TPM and get tier limits from database
        rate_metrics = []
        for row in results:
            # Get model configuration
            model_config_stmt = select(ModelConfig).where(
                and_(
                    ModelConfig.model_id == row.model_id,
                    ModelConfig.is_active == True,  # noqa: E712
                )
            )
            model_config_result = await db.execute(model_config_stmt)
            model_config = model_config_result.scalar_one_or_none()

            if not model_config:
                logger.warning(f"No active model config found for {row.model_id}")
                continue

            # Get pricing tier
            if not model_config.default_pricing_tier_id:
                logger.warning(f"No pricing tier assigned to model {row.model_id}")
                continue

            tier_stmt = select(PricingTier).where(
                and_(
                    PricingTier.id == model_config.default_pricing_tier_id,
                    PricingTier.is_active == True,  # noqa: E712
                )
            )
            tier_result = await db.execute(tier_stmt)
            tier = tier_result.scalar_one_or_none()

            if not tier:
                logger.warning(f"No active pricing tier found for model {row.model_id}")
                continue

            # Calculate rates
            tokens_in_pm = (row.total_in or 0) / window_minutes
            tokens_out_pm = (row.total_out or 0) / window_minutes
            total_tpm = tokens_in_pm + tokens_out_pm

            # Calculate utilization percentage
            utilization = (
                (total_tpm / tier.rate_limit_tpm * 100) if tier and tier.rate_limit_tpm > 0 else 0
            )

            # Determine recommended action
            recommended_action = "OK"
            if utilization > 90:
                recommended_action = "UPGRADE_TIER"
            elif utilization > 80:
                recommended_action = "THROTTLE"

            rate_metrics.append(
                TokenRateMetrics(
                    model_id=row.model_id,
                    tokens_in_per_minute=tokens_in_pm,
                    tokens_out_per_minute=tokens_out_pm,
                    total_tokens_per_minute=total_tpm,
                    rate_limit_tpm=tier.rate_limit_tpm if tier else 0,
                    utilization_percentage=utilization,
                    tier_name=tier.tier_key if tier else "unknown",
                    recommended_action=recommended_action,
                )
            )

        logger.info(
            f"Calculated rate metrics for {len(rate_metrics)} models over {window_minutes} minute window"
        )

        return TokenRateResponse(
            metrics=rate_metrics,
            window_minutes=window_minutes,
            calculated_at=datetime.now(UTC),
        )

    except Exception as e:
        logger.error(f"Error calculating token rates: {e!s}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/usage/summary")
async def get_token_usage_summary(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours (max 1 week)"),
    model_id: str | None = Query(None, description="Filter by specific model ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_required),
) -> dict[str, Any]:
    """
    Get token usage summary over specified time window.
    Provides aggregated statistics for monitoring and reporting.
    """
    try:
        # Calculate time window
        since = datetime.now(UTC) - timedelta(hours=hours)

        # Build query
        stmt = (
            select(
                func.sum(TokenUsage.tokens_in).label("total_tokens_in"),
                func.sum(TokenUsage.tokens_out).label("total_tokens_out"),
                func.count(TokenUsage.id).label("total_requests"),
                func.avg(TokenUsage.call_duration_ms).label("avg_duration_ms"),
                TokenUsage.model_id,
            )
            .where(TokenUsage.created_at >= since)
            .group_by(TokenUsage.model_id)
        )

        if model_id:
            stmt = stmt.where(TokenUsage.model_id == model_id)

        # Execute query
        result = await db.execute(stmt)
        results = result.all()

        # Format response
        summary = []
        for row in results:
            total_tokens = (row.total_tokens_in or 0) + (row.total_tokens_out or 0)

            # Calculate average TPM over the period
            avg_tpm = total_tokens / (hours * 60) if hours > 0 else 0

            summary.append(
                {
                    "model_id": row.model_id,
                    "total_tokens_in": row.total_tokens_in or 0,
                    "total_tokens_out": row.total_tokens_out or 0,
                    "total_tokens": total_tokens,
                    "total_requests": row.total_requests or 0,
                    "avg_duration_ms": float(row.avg_duration_ms or 0),
                    "avg_tokens_per_minute": avg_tpm,
                    "time_window_hours": hours,
                }
            )

        return {
            "summary": summary,
            "time_window_hours": hours,
            "calculated_at": datetime.now(UTC),
            "total_models": len(summary),
        }

    except Exception as e:
        logger.error(f"Error generating usage summary: {e!s}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/tiers/status")
async def get_pricing_tier_status(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_required),
) -> dict[str, Any]:
    """
    Get current status of all pricing tiers with usage indicators.
    Provides overview of tier utilization and recommendations.
    """
    try:
        # Get all active pricing tiers
        tiers_stmt = select(PricingTier).where(PricingTier.is_active == True)  # noqa: E712
        tiers_result = await db.execute(tiers_stmt)
        tiers = tiers_result.scalars().all()

        # Get usage data for last hour
        since = datetime.now(UTC) - timedelta(hours=1)

        tier_status = []
        for tier in tiers:
            # Get models using this tier
            models_stmt = select(ModelConfig).where(
                and_(
                    ModelConfig.default_pricing_tier_id == tier.id,
                    ModelConfig.is_active == True,  # noqa: E712
                )
            )
            models_result = await db.execute(models_stmt)
            models = models_result.scalars().all()

            if not models:
                tier_status.append(
                    {
                        "tier_key": tier.tier_key,
                        "tier_name": tier.tier_name,
                        "plan_size": tier.plan_size,
                        "model_class": tier.model_class,
                        "rate_limit_tpm": tier.rate_limit_tpm,
                        "input_rate_per_1m": float(tier.input_rate_per_1m),
                        "output_rate_per_1m": float(tier.output_rate_per_1m),
                        "models_using": 0,
                        "total_usage_tpm": 0,
                        "utilization_percentage": 0,
                        "status": "unused",
                        "recommended_action": "OK",
                    }
                )
                continue

            # Calculate total usage for models using this tier
            model_ids = [model.model_id for model in models]

            usage_stmt = select(
                func.sum(TokenUsage.tokens_in).label("total_in"),
                func.sum(TokenUsage.tokens_out).label("total_out"),
            ).where(
                and_(
                    TokenUsage.model_id.in_(model_ids),
                    TokenUsage.created_at >= since,
                )
            )
            usage_result = await db.execute(usage_stmt)
            usage_row = usage_result.first()

            total_usage_tpm = 0.0
            if usage_row:
                total_usage_tpm = (
                    (usage_row.total_in or 0) + (usage_row.total_out or 0)
                ) / 60  # Convert to per-minute
            utilization = (
                (total_usage_tpm / tier.rate_limit_tpm * 100) if tier.rate_limit_tpm > 0 else 0
            )

            # Determine status and recommendation
            if utilization > 90:
                status = "critical"
                recommended_action = "UPGRADE_TIER"
            elif utilization > 80:
                status = "warning"
                recommended_action = "THROTTLE"
            elif utilization > 50:
                status = "moderate"
                recommended_action = "MONITOR"
            else:
                status = "healthy"
                recommended_action = "OK"

            tier_status.append(
                {
                    "tier_key": tier.tier_key,
                    "tier_name": tier.tier_name,
                    "plan_size": tier.plan_size,
                    "model_class": tier.model_class,
                    "rate_limit_tpm": tier.rate_limit_tpm,
                    "input_rate_per_1m": float(tier.input_rate_per_1m),
                    "output_rate_per_1m": float(tier.output_rate_per_1m),
                    "models_using": len(models),
                    "total_usage_tpm": total_usage_tpm,
                    "utilization_percentage": utilization,
                    "status": status,
                    "recommended_action": recommended_action,
                }
            )

        # Sort by utilization (highest first)
        tier_status.sort(key=lambda x: float(x.get("utilization_percentage", 0)), reverse=True)  # type: ignore[arg-type]

        return {
            "tier_status": tier_status,
            "calculated_at": datetime.now(UTC),
            "time_window_minutes": 60,
            "total_tiers": len(tier_status),
            "critical_tiers": len([t for t in tier_status if t["status"] == "critical"]),
            "warning_tiers": len([t for t in tier_status if t["status"] == "warning"]),
        }

    except Exception as e:
        logger.error(f"Error getting pricing tier status: {e!s}")
        raise HTTPException(status_code=500, detail="Internal server error")
