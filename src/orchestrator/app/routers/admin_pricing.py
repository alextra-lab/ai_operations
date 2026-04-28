"""
Admin pricing management router for LLMaaS pricing tier and model configuration.

This module provides CRUD operations for pricing tiers and model configurations,
including audit trail functionality for compliance and change tracking.

P5-A23 Phase 7: Converted to async database patterns (Nov 2025).
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import admin_required
from shared.auth.models import TokenPayload, User
from shared.logging_utils.fastapi import get_logger

from ..db.database import get_async_db
from ..db.models import ModelConfig, PricingTier, PricingTierAudit
from ..schemas.pricing import (
    ModelConfigCreate,
    ModelConfigListResponse,
    ModelConfigResponse,
    ModelConfigUpdate,
    ModelPriceChangeRequest,
    ModelPriceCurrentResponse,
    ModelPriceHistoryEntry,
    PricingAuditResponse,
    PricingTierCreate,
    PricingTierListResponse,
    PricingTierResponse,
    PricingTierUpdate,
)
from ..services.pricing_history_service import PricingHistoryService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin/pricing", tags=["Admin - Pricing"])


@router.get("/tiers", response_model=PricingTierListResponse)
async def list_pricing_tiers(
    active_only: bool = Query(False, description="Filter to active tiers only"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_required),
) -> PricingTierListResponse:
    """List all pricing tiers (admin only)."""
    try:
        stmt = select(PricingTier)

        if active_only:
            stmt = stmt.where(PricingTier.is_active)

        # Get total counts
        count_result = await db.execute(select(PricingTier))
        total_count = len(count_result.scalars().all())

        active_result = await db.execute(select(PricingTier).where(PricingTier.is_active))
        active_count = len(active_result.scalars().all())

        # Apply pagination
        stmt = stmt.order_by(PricingTier.tier_key).offset(skip).limit(limit)
        result = await db.execute(stmt)
        tiers = result.scalars().all()

        return PricingTierListResponse(
            tiers=[PricingTierResponse.model_validate(t) for t in tiers],
            total_count=total_count,
            active_count=active_count,
        )

    except Exception as e:
        logger.error(f"Error listing pricing tiers: {e!s}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/tiers", response_model=PricingTierResponse, status_code=201)
async def create_pricing_tier(
    tier: PricingTierCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_required),
) -> PricingTierResponse:
    """Create new pricing tier (admin only)."""
    try:
        # Validate unique tier_key
        result = await db.execute(select(PricingTier).where(PricingTier.tier_key == tier.tier_key))
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=400, detail=f"Pricing tier {tier.tier_key} already exists"
            )

        # Validate unique plan_size + model_class combination
        result = await db.execute(
            select(PricingTier).where(
                PricingTier.plan_size == tier.plan_size,
                PricingTier.model_class == tier.model_class,
            )
        )
        existing_combination = result.scalar_one_or_none()
        if existing_combination:
            raise HTTPException(
                status_code=400,
                detail=f"Plan {tier.plan_size} with model {tier.model_class} already exists",
            )

        # Create new tier
        new_tier = PricingTier(
            **tier.dict(), created_by=current_user.id, updated_by=current_user.id
        )
        db.add(new_tier)
        await db.flush()  # Flush to get the ID

        # Audit log
        audit = PricingTierAudit(
            pricing_tier_id=new_tier.id,
            action="CREATE",
            changed_by=current_user.id,
            new_values=tier.dict(),
            change_reason="New pricing tier created via admin UI",
        )
        db.add(audit)

        await db.commit()
        await db.refresh(new_tier)

        logger.info(f"Created pricing tier {tier.tier_key} by user {current_user.id}")
        return new_tier

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating pricing tier: {e!s}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/tiers/{tier_id}", response_model=PricingTierResponse)
async def update_pricing_tier(
    tier_id: UUID,
    tier_update: PricingTierUpdate,
    change_reason: str = Query(..., description="Reason for the change (required for audit)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_required),
) -> PricingTierResponse:
    """Update pricing tier (admin only). Requires change reason for audit."""
    try:
        result = await db.execute(select(PricingTier).where(PricingTier.id == tier_id))
        existing = result.scalar_one_or_none()
        if not existing:
            raise HTTPException(status_code=404, detail="Pricing tier not found")

        # Store old values for audit
        old_values = {
            "tier_name": existing.tier_name,
            "input_rate_per_1m": str(existing.input_rate_per_1m),
            "output_rate_per_1m": str(existing.output_rate_per_1m),
            "rate_limit_tpm": existing.rate_limit_tpm,
            "description": existing.description,
            "is_active": existing.is_active,
            "is_default": existing.is_default,
        }

        # Update fields
        update_data = tier_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing, key, value)
        existing.updated_by = current_user.id

        # Audit log
        audit = PricingTierAudit(
            pricing_tier_id=tier_id,
            action="UPDATE",
            changed_by=current_user.id,
            old_values=old_values,
            new_values=update_data,
            change_reason=change_reason,
        )
        db.add(audit)

        await db.commit()
        await db.refresh(existing)

        logger.info(f"Updated pricing tier {existing.tier_key} by user {current_user.id}")
        return existing

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating pricing tier: {e!s}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/tiers/{tier_id}", status_code=204)
async def delete_pricing_tier(
    tier_id: UUID,
    change_reason: str = Query(..., description="Reason for deletion (required for audit)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_required),
) -> None:
    """Delete pricing tier (admin only). Soft delete if in use."""
    try:
        result = await db.execute(select(PricingTier).where(PricingTier.id == tier_id))
        tier = result.scalar_one_or_none()
        if not tier:
            raise HTTPException(status_code=404, detail="Pricing tier not found")

        # Check if tier is in use
        count_result = await db.execute(
            select(ModelConfig).where(ModelConfig.default_pricing_tier_id == tier_id)
        )
        models_using = len(count_result.scalars().all())

        old_values: dict[str, Any]
        new_values: dict[str, Any] | None

        if models_using > 0:
            # Soft delete: deactivate instead
            tier.is_active = False
            tier.updated_by = current_user.id
            action = "DEACTIVATE"
            old_values = {"is_active": True}
            new_values = {"is_active": False}
            change_reason = (
                f"{change_reason} (deactivated due to {models_using} models using this tier)"
            )
        else:
            # Hard delete: safe to remove
            action = "DELETE"
            old_values = {"tier_key": tier.tier_key, "is_active": tier.is_active}
            new_values = None

        # Audit log
        audit = PricingTierAudit(
            pricing_tier_id=tier_id,
            action=action,
            changed_by=current_user.id,
            old_values=old_values,
            new_values=new_values,
            change_reason=change_reason,
        )
        db.add(audit)

        if action == "DELETE":
            stmt = delete(PricingTier).where(PricingTier.id == tier_id)
            await db.execute(stmt)

        await db.commit()

        logger.info(f"{action} pricing tier {tier.tier_key} by user {current_user.id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting pricing tier: {e!s}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/tiers/{tier_id}/audit", response_model=list[PricingAuditResponse])
async def get_pricing_tier_audit(
    tier_id: UUID,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Number of records to return"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_required),
) -> list[PricingAuditResponse]:
    """Get audit history for pricing tier (admin only)."""
    try:
        # Verify tier exists
        result = await db.execute(select(PricingTier).where(PricingTier.id == tier_id))
        tier = result.scalar_one_or_none()
        if not tier:
            raise HTTPException(status_code=404, detail="Pricing tier not found")

        stmt = (
            select(PricingTierAudit)
            .where(PricingTierAudit.pricing_tier_id == tier_id)
            .order_by(PricingTierAudit.changed_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        audits = result.scalars().all()
        return [PricingAuditResponse.model_validate(a) for a in audits]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pricing tier audit: {e!s}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/models", response_model=ModelConfigListResponse)
async def list_model_configs(
    active_only: bool = Query(False, description="Filter to active models only"),
    provider: str | None = Query(None, description="Filter by model provider"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_required),
) -> ModelConfigListResponse:
    """List all model configurations (admin only)."""
    try:
        stmt = select(ModelConfig)

        if active_only:
            stmt = stmt.where(ModelConfig.is_active)

        if provider:
            stmt = stmt.where(ModelConfig.model_provider == provider.lower())

        # Get total counts
        count_result = await db.execute(select(ModelConfig))
        total_count = len(count_result.scalars().all())

        active_result = await db.execute(select(ModelConfig).where(ModelConfig.is_active))
        active_count = len(active_result.scalars().all())

        # Apply pagination
        stmt = stmt.order_by(ModelConfig.model_name).offset(skip).limit(limit)
        result = await db.execute(stmt)
        models = result.scalars().all()

        return ModelConfigListResponse(
            models=[ModelConfigResponse.model_validate(m) for m in models],
            total_count=total_count,
            active_count=active_count,
        )

    except Exception as e:
        logger.error(f"Error listing model configs: {e!s}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/models", response_model=ModelConfigResponse, status_code=201)
async def create_model_config(
    model: ModelConfigCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_required),
) -> ModelConfigResponse:
    """Create new model configuration (admin only)."""
    try:
        # Validate unique model_id
        result = await db.execute(select(ModelConfig).where(ModelConfig.model_id == model.model_id))
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail=f"Model {model.model_id} already exists")

        # Validate pricing tier exists if specified
        if model.default_pricing_tier_id:
            tier_result = await db.execute(
                select(PricingTier).where(PricingTier.id == model.default_pricing_tier_id)
            )
            tier = tier_result.scalar_one_or_none()
            if not tier:
                raise HTTPException(status_code=400, detail="Specified pricing tier does not exist")
            if not tier.is_active:
                raise HTTPException(status_code=400, detail="Specified pricing tier is not active")

        # Create new model config
        new_model = ModelConfig(
            **model.dict(), created_by=current_user.id, updated_by=current_user.id
        )
        db.add(new_model)
        await db.commit()
        await db.refresh(new_model)

        logger.info(f"Created model config {model.model_id} by user {current_user.id}")
        return new_model

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating model config: {e!s}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


# -----------------------------------------------------------------------------
# Per-model pricing (history-based) endpoints
# NOTE: These must come BEFORE /models/{model_id} routes to ensure proper matching
# -----------------------------------------------------------------------------


@router.get(
    "/models/{model_id:path}/pricing/current",
    response_model=ModelPriceCurrentResponse,
)
async def get_current_model_pricing(
    model_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_required),
) -> ModelPriceCurrentResponse:
    """Return the active per-model pricing (EUR per 1M tokens)."""
    svc = PricingHistoryService(db)
    active = await svc.get_active_price_by_model_id(model_id)
    if not active:
        raise HTTPException(status_code=404, detail="No pricing configured for model")

    # Try to resolve the window for the active record
    effective_from = None
    effective_to = None
    history = await svc.get_price_history(model_id)
    for rec in history:
        if rec.effective_to is None:
            effective_from = rec.effective_from
            effective_to = rec.effective_to
            break

    return ModelPriceCurrentResponse(
        model_id=model_id,
        currency="EUR",
        input_price_per_million=active[0],
        output_price_per_million=active[1],
        effective_from=effective_from,
        effective_to=effective_to,
    )


@router.get(
    "/models/{model_id:path}/pricing/history",
    response_model=list[ModelPriceHistoryEntry],
)
async def get_model_pricing_history(
    model_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_required),
) -> list[ModelPriceHistoryEntry]:
    """Return the pricing history for a model (most recent first)."""
    svc = PricingHistoryService(db)
    records = await svc.get_price_history(model_id)
    resp: list[ModelPriceHistoryEntry] = []
    for rec in records:
        resp.append(
            ModelPriceHistoryEntry(
                id=rec.id,
                model_uuid=rec.model_id,
                model_id=model_id,
                input_price_per_million=rec.input_price_per_million,
                output_price_per_million=rec.output_price_per_million,
                effective_from=rec.effective_from,
                effective_to=rec.effective_to,
                changed_by_user_id=rec.changed_by_user_id,
                change_reason=rec.change_reason,
                created_at=rec.created_at,
            )
        )
    return resp


@router.post(
    "/models/{model_id:path}/pricing/change",
    response_model=ModelPriceCurrentResponse,
    status_code=201,
)
async def set_model_pricing_change(
    model_id: str,
    body: ModelPriceChangeRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(admin_required),
) -> ModelPriceCurrentResponse:
    """Create a new per-model price record with optional future effective time."""
    try:
        svc = PricingHistoryService(db)
        rec = await svc.set_price_change(
            model_id_str=model_id,
            input_price_per_million=body.input_price_per_million,
            output_price_per_million=body.output_price_per_million,
            effective_from=body.effective_from,
            changed_by_user_id=str(current_user.user_id) if current_user else None,
            change_reason=body.change_reason,
        )
        await db.commit()
        active = await svc.get_active_price_by_model_id(model_id)
        return ModelPriceCurrentResponse(
            model_id=model_id,
            currency="EUR",
            input_price_per_million=active[0] if active else rec.input_price_per_million,
            output_price_per_million=active[1] if active else rec.output_price_per_million,
            effective_from=rec.effective_from,
            effective_to=rec.effective_to,
        )
    except Exception as e:
        logger.error("Failed to set model pricing change: %s", e)
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/models/{model_id}", response_model=ModelConfigResponse)
async def update_model_config(
    model_id: UUID,
    model_update: ModelConfigUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_required),
) -> ModelConfigResponse:
    """Update model configuration (admin only)."""
    try:
        result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
        existing = result.scalar_one_or_none()
        if not existing:
            raise HTTPException(status_code=404, detail="Model configuration not found")

        # Validate pricing tier exists if being updated
        if model_update.default_pricing_tier_id:
            tier_result = await db.execute(
                select(PricingTier).where(PricingTier.id == model_update.default_pricing_tier_id)
            )
            tier = tier_result.scalar_one_or_none()
            if not tier:
                raise HTTPException(status_code=400, detail="Specified pricing tier does not exist")
            if not tier.is_active:
                raise HTTPException(status_code=400, detail="Specified pricing tier is not active")

        # Update fields
        update_data = model_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing, key, value)
        existing.updated_by = current_user.id

        await db.commit()
        await db.refresh(existing)

        logger.info(f"Updated model config {existing.model_id} by user {current_user.id}")
        return existing

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating model config: {e!s}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/models/{model_id}", status_code=204)
async def delete_model_config(
    model_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_required),
) -> None:
    """Delete model configuration (admin only)."""
    try:
        result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
        model = result.scalar_one_or_none()
        if not model:
            raise HTTPException(status_code=404, detail="Model configuration not found")

        # Soft delete by deactivating
        model.is_active = False
        model.updated_by = current_user.id

        await db.commit()

        logger.info(f"Deactivated model config {model.model_id} by user {current_user.id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting model config: {e!s}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
