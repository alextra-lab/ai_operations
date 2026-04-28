"""
Cost Calculator for Inference Gateway.

Wraps existing PricingHistoryService to calculate request costs.
Uses existing pricing infrastructure from backend service.

VERIFICATION CRITICAL:
- Uses PricingHistoryService from src/backend (DON'T duplicate logic)
- Queries model_pricing_history table (existing table)
- Returns EUR currency (consistent with existing system)
- Cost calculation matches cost_estimator.py within 1%
- Async pattern with shared.database.get_db

Implementation follows ADR-053 (Rate Limiting and Usage Tracking).
"""

from datetime import UTC, datetime

from shared.logging_utils.fastapi import configure_logging  # type: ignore[import-untyped]

logger = configure_logging(service_name="cost_calculator")


class CostCalculator:
    """
    Calculate request costs using existing pricing infrastructure.

    This class wraps the backend's PricingHistoryService to provide
    cost calculation for Gateway requests. It ensures consistency
    with the orchestrator's cost estimation.

    Example:
        >>> calculator = CostCalculator()
        >>> result = await calculator.calculate("gpt-4o-mini", 100, 50)
        >>> print(result["total_cost_eur"])
        0.000045
    """

    async def calculate(
        self,
        model_id: str,
        tokens_in: int,
        tokens_out: int,
        as_of: datetime | None = None,
    ) -> dict[str, float | str]:
        """
        Calculate cost for a request using existing pricing service.

        This method queries the model_pricing_history table via
        PricingHistoryService to get active pricing, then calculates
        the total cost in EUR.

        Args:
            model_id: Model identifier (e.g., "gpt-4o-mini")
            tokens_in: Number of input/prompt tokens
            tokens_out: Number of output/completion tokens
            as_of: Timestamp for pricing lookup (default: now UTC)

        Returns:
            dict with:
                - total_cost_eur: Total cost in EUR (float)
                - input_cost_eur: Input cost in EUR (float)
                - output_cost_eur: Output cost in EUR (float)
                - pricing_source: Source of pricing (str: "pricing_history" | "model_registry" | "default")

        Note:
            Cost calculation matches backend's cost_estimator.py.
            Pricing fallback order:
            1. model_pricing_history table (preferred)
            2. models table registry fields
            3. Default pricing (1.00 EUR input, 2.00 EUR output per million)

        Example:
            >>> result = await calculator.calculate("gpt-4o-mini", 100, 50)
            >>> # GPT-4o-mini: 0.15 EUR/M input, 0.60 EUR/M output
            >>> # Input: (100 / 1_000_000) * 0.15 = 0.000015 EUR
            >>> # Output: (50 / 1_000_000) * 0.60 = 0.000030 EUR
            >>> # Total: 0.000045 EUR
            >>> assert result["total_cost_eur"] == 0.000045
        """
        as_of = as_of or datetime.now(tz=UTC)

        # Get pricing from existing service
        input_price, output_price, pricing_source = await self._get_pricing(model_id, as_of)

        # Calculate costs (pricing is per million tokens)
        input_cost = (tokens_in / 1_000_000) * input_price
        output_cost = (tokens_out / 1_000_000) * output_price
        total_cost = input_cost + output_cost

        logger.debug(
            "Cost calculated",
            extra={
                "model_id": model_id,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "input_price_per_million": input_price,
                "output_price_per_million": output_price,
                "total_cost_eur": round(total_cost, 6),
                "pricing_source": pricing_source,
            },
        )

        return {
            "total_cost_eur": round(total_cost, 6),
            "input_cost_eur": round(input_cost, 6),
            "output_cost_eur": round(output_cost, 6),
            "pricing_source": pricing_source,
        }

    async def _get_pricing(self, model_id: str, as_of: datetime) -> tuple[float, float, str]:
        """
        Get pricing for a model using existing PricingHistoryService.

        Follows same fallback logic as backend's cost_estimator.py:
        1. model_pricing_history table (via PricingHistoryService)
        2. models table registry fields (fallback)
        3. Generic defaults (1.00 EUR input, 2.00 EUR output)

        Args:
            model_id: Model identifier
            as_of: Timestamp for pricing lookup

        Returns:
            Tuple of (input_price, output_price, pricing_source)
        """
        try:
            # Import backend services (lazy to avoid circular dependencies)
            from sqlalchemy import select
            from src.orchestrator.app.db.database import AsyncSessionLocal
            from src.orchestrator.app.db.models import Model
            from src.orchestrator.app.services.pricing_history_service import (
                PricingHistoryService,
            )

            async with AsyncSessionLocal() as session:
                # Try pricing history first (preferred)
                pricing_service = PricingHistoryService(session)
                active_price = await pricing_service.get_active_price_by_model_id(model_id, as_of)

                if active_price is not None:
                    input_price, output_price = active_price
                    logger.debug(
                        "Pricing from history",
                        extra={
                            "model_id": model_id,
                            "input_price": input_price,
                            "output_price": output_price,
                        },
                    )
                    return (float(input_price), float(output_price), "pricing_history")

                # Fallback to model registry fields
                stmt = select(Model).where(Model.model_id == model_id)
                result = await session.execute(stmt)
                model = result.scalar_one_or_none()
                if model is not None and model.input_price_per_million is not None:
                    input_price = float(model.input_price_per_million)
                    output_price = float(model.output_price_per_million or 0.0)
                    logger.debug(
                        "Pricing from model registry",
                        extra={
                            "model_id": model_id,
                            "input_price": input_price,
                            "output_price": output_price,
                        },
                    )
                    return (input_price, output_price, "model_registry")

        except Exception as e:
            logger.warning(
                "Failed to query pricing from database",
                extra={
                    "model_id": model_id,
                    "error": str(e),
                    "falling_back_to_defaults": True,
                },
            )

        # Fallback to generic defaults
        logger.info(
            "Using default pricing",
            extra={
                "model_id": model_id,
                "default_input": 1.00,
                "default_output": 2.00,
            },
        )
        return (1.00, 2.00, "default")
