"""
Pricing History Service

Provides per-model pricing with effective date windows and history management.

This service enables immutable cost calculation by selecting the price record
active at execution time. It also supports administrative price changes with
audit metadata.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import and_, select

from shared.logging_utils.fastapi import configure_logging

from ..db.models import Model, ModelPricingHistory

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = configure_logging(service_name="pricing_history_service")


class PricingHistoryService:
    """Encapsulates per-model pricing history operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_price_by_model_id(
        self, model_id_str: str, as_of: datetime | None = None
    ) -> tuple[float, float] | None:
        """Return active per-1M input/output prices for a model at a time.

        Args:
            model_id_str: External model identifier (e.g., 'mistral-large').
            as_of: Timestamp at which price should be effective (UTC). Defaults
                to now.

        Returns:
            Tuple of (input_price_per_million, output_price_per_million) or
            None if no pricing was configured.
        """
        as_of = as_of or datetime.now(tz=UTC)

        stmt = select(Model).where(Model.model_id == model_id_str)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            logger.warning(
                "Model not found for pricing lookup",
                extra={"model_id": model_id_str},
            )
            return None

        return await self.get_active_price_by_model_uuid(model.id, as_of)

    async def get_active_price_by_model_uuid(
        self, model_uuid: UUID, as_of: datetime | None = None
    ) -> tuple[float, float] | None:
        """Return active per-1M prices for a model UUID at a time."""
        as_of = as_of or datetime.now(tz=UTC)

        stmt = (
            select(ModelPricingHistory)
            .where(
                and_(
                    ModelPricingHistory.model_id == model_uuid,
                    ModelPricingHistory.effective_from <= as_of,
                    (
                        (ModelPricingHistory.effective_to.is_(None))
                        | (ModelPricingHistory.effective_to > as_of)
                    ),
                )
            )
            .order_by(ModelPricingHistory.effective_from.desc())
        )
        result = await self.session.execute(stmt)
        rec = result.scalar_one_or_none()

        if rec:
            return float(rec.input_price_per_million), float(rec.output_price_per_million)

        # Fallback to current fields on models table if set
        stmt = select(Model).where(Model.id == model_uuid)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model and model.input_price_per_million is not None:
            return (
                float(model.input_price_per_million),
                float(model.output_price_per_million or 0.0),
            )

        return None

    async def set_price_change(
        self,
        model_id_str: str,
        input_price_per_million: float,
        output_price_per_million: float,
        effective_from: datetime | None,
        changed_by_user_id: str | None,
        change_reason: str | None,
    ) -> ModelPricingHistory:
        """Create a new price record and close the previous interval.

        If a current active record exists, its effective_to is set to the new
        effective_from to maintain non-overlapping windows.
        """
        if input_price_per_million < 0 or output_price_per_million < 0:
            raise ValueError("Prices must be non-negative")

        # Resolve model
        stmt = select(Model).where(Model.model_id == model_id_str)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"Unknown model_id: {model_id_str}")

        effective_from = effective_from or datetime.now(tz=UTC)

        # Close currently active record, if any
        stmt = (
            select(ModelPricingHistory)
            .where(
                and_(
                    ModelPricingHistory.model_id == model.id,
                    ModelPricingHistory.effective_from <= effective_from,
                    ModelPricingHistory.effective_to.is_(None),
                )
            )
            .order_by(ModelPricingHistory.effective_from.desc())
        )
        result = await self.session.execute(stmt)
        active = result.scalar_one_or_none()
        if active and active.effective_from < effective_from:
            active.effective_to = effective_from
            self.session.add(active)

        # Create new record
        new_rec = ModelPricingHistory(
            model_id=model.id,
            input_price_per_million=input_price_per_million,
            output_price_per_million=output_price_per_million,
            effective_from=effective_from,
            changed_by_user_id=(None if changed_by_user_id is None else changed_by_user_id),
            change_reason=change_reason,
        )
        self.session.add(new_rec)
        await self.session.flush()

        logger.info(
            "Model price updated",
            extra={
                "model_id": model_id_str,
                "effective_from": effective_from.isoformat(),
                "input_per_million": input_price_per_million,
                "output_per_million": output_price_per_million,
            },
        )

        return new_rec

    async def get_price_history(self, model_id_str: str) -> Iterable[ModelPricingHistory]:
        """Return complete price history for a model (most recent first)."""
        stmt = select(Model).where(Model.model_id == model_id_str)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return []

        stmt = (
            select(ModelPricingHistory)
            .where(ModelPricingHistory.model_id == model.id)
            .order_by(ModelPricingHistory.effective_from.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
