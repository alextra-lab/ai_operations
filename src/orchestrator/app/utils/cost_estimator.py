"""
Cost Estimation Utility for LLM Token Usage.

This module provides cost estimation functionality for various LLM models
based on input/output token counts and model-specific pricing.

Pricing Fallback Order (EUR per 1M tokens):
1. Model-specific pricing from database history (preferred)
2. Model registry fields on `models` row (if set)
3. Environment defaults (PRICING_DEFAULT_INPUT_PER_MILLION / OUTPUT)
4. Generic default (EUR 1.00 / 2.00 per million)
"""

from functools import lru_cache
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config.loader import load_orchestrator_config
from shared.logging_utils.fastapi import configure_logging

from ..db.models import Model
from ..services.pricing_history_service import PricingHistoryService

logger = configure_logging(service_name="cost_estimator")

GENERIC_DEFAULT_INPUT_EUR = 1.00
GENERIC_DEFAULT_OUTPUT_EUR = 2.00


async def estimate_cost(
    model_id: str, tokens_in: int, tokens_out: int, session: AsyncSession | None = None
) -> dict[str, Any]:
    """
    Estimate the cost of an LLM API call based on token usage.

    Pricing Fallback Order:
    1. Model-specific pricing from database (if session provided)
    2. Environment variable defaults
    3. Hardcoded pricing for known models
    4. Generic default

    Args:
        model_id: The model identifier
        tokens_in: Number of input tokens
        tokens_out: Number of output tokens
        session: Optional database session for registry lookup

    Returns:
        Dictionary containing cost breakdown with pricing source
    """
    # Try to get pricing from pricing history/model registry first
    input_price, output_price, pricing_source = await _get_model_pricing(model_id, session)

    # Calculate costs (pricing is per million tokens)
    input_cost = (tokens_in / 1_000_000) * input_price
    output_cost = (tokens_out / 1_000_000) * output_price
    total_cost = input_cost + output_cost

    return {
        "input_cost": round(input_cost, 6),
        "output_cost": round(output_cost, 6),
        "total_cost": round(total_cost, 6),
        "currency": "EUR",
        "pricing_source": pricing_source,
        "pricing_per_million": {"input": input_price, "output": output_price},
    }


async def _get_model_pricing(
    model_id: str, session: AsyncSession | None
) -> tuple[float, float, str]:
    """
    Get pricing for a model using fallback logic.

    Returns:
        Tuple of (input_price, output_price, pricing_source)
    """
    # 1. Try per-model pricing history (preferred) or registry fields (if present)
    if session is not None:
        try:
            # Pricing history
            history = PricingHistoryService(session)
            active = await history.get_active_price_by_model_id(model_id)
            if active is not None:
                return (active[0], active[1], "pricing_history")

            # Fallback to registry fields if set on model row
            stmt = select(Model).where(Model.model_id == model_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model and model.input_price_per_million is not None:
                return (
                    float(model.input_price_per_million),
                    float(model.output_price_per_million or 0.0),
                    "model_registry",
                )
        except SQLAlchemyError as e:
            logger.warning(
                "Failed to query model registry for pricing: %s",
                e,
                extra={"model_id": model_id, "error": str(e)},
            )

    else:
        # Attempt to open a short-lived async session for DB-backed pricing
        try:
            from ..db.database import AsyncSessionLocal

            async with AsyncSessionLocal() as temp_session:
                history = PricingHistoryService(temp_session)
                active = await history.get_active_price_by_model_id(model_id)
                if active is not None:
                    return (active[0], active[1], "pricing_history")

                stmt = select(Model).where(Model.model_id == model_id)
                result = await temp_session.execute(stmt)
                model = result.scalar_one_or_none()
                if model and model.input_price_per_million is not None:
                    return (
                        float(model.input_price_per_million),
                        float(model.output_price_per_million or 0.0),
                        "model_registry",
                    )
        except (SQLAlchemyError, ImportError) as e:  # pragma: no cover
            logger.debug(
                "DB-backed pricing unavailable, falling back to env/defaults",
                extra={"model_id": model_id, "error": str(e)},
            )

    # 2. Use orchestrator configuration defaults
    config_input, config_output = _get_pricing_defaults()
    if config_input is not None and config_output is not None:
        return (config_input, config_output, "shared_config_default")

    # 3. Use generic default (EUR)
    return (
        GENERIC_DEFAULT_INPUT_EUR,
        GENERIC_DEFAULT_OUTPUT_EUR,
        "generic_default",
    )


@lru_cache(maxsize=1)
def _get_pricing_defaults() -> tuple[float, float]:
    """Fetch pricing defaults from shared orchestrator configuration."""
    settings = load_orchestrator_config()
    return (
        float(settings.pricing_default_input_per_million),
        float(settings.pricing_default_output_per_million),
    )


def _normalize_model_id(model_id: str) -> str:
    """
    Normalize model ID to match pricing keys.

    Handles various model ID formats:
    - Full identifiers (gpt-4o-2024-08-06)
    - Short identifiers (gpt-4o)
    - Provider-prefixed (openai/gpt-4o)

    Args:
        model_id: Raw model identifier

    Returns:
        Normalized model identifier for pricing lookup
    """
    # Remove provider prefix if present
    if "/" in model_id:
        model_id = model_id.split("/")[-1]

    # Return simplified identifier; do not enforce catalog here
    return model_id


__all__ = [
    "_normalize_model_id",
    "estimate_cost",
]
