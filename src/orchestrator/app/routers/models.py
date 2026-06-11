"""
Model Registry API endpoints.

This module provides API endpoints for model registry management,
including listing models, getting model details, recommendations,
and syncing with inference servers.
"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import admin_required, auth_manager, get_current_user
from shared.auth.models import TokenPayload
from shared.config.loader import load_embedding_config, load_orchestrator_config
from shared.logging_utils.fastapi import configure_logging

from ..db.database import get_async_db
from ..schemas.model import (
    ModelDetailedResponse,
    ModelListResponse,
    ModelRecommendation,
    ModelSelectionRequest,
    ModelUpdate,
)
from ..services.model_registry_service import ModelRegistryService

logger = configure_logging(service_name="models_router")

router = APIRouter(prefix="/api/v1/models", tags=["models"])


@router.get("", response_model=ModelListResponse)
async def list_models(
    provider: str | None = Query(None, description="Filter by provider"),
    model_type: str | None = Query(None, description="Filter by model type"),
    available_only: bool = Query(True, description="Only return available models"),
    include_deprecated: bool = Query(False, description="Include deprecated models"),
    include_hidden: bool = Query(False, description="Include hidden models"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> ModelListResponse:
    """
    List available models with filtering and pagination.

    Returns paginated list of models with their capabilities and metadata.
    Accessible by all authenticated users.
    """
    try:
        logger.info(
            "Listing models",
            extra={
                "user_id": str(current_user.user_id),
                "provider": provider,
                "model_type": model_type,
                "page": page,
            },
        )

        service = ModelRegistryService(session=db)

        return await service.list_models(
            provider=provider,
            model_type=model_type,
            available_only=available_only,
            include_deprecated=include_deprecated,
            include_hidden=include_hidden,
            page=page,
            size=size,
        )
    except Exception as e:
        logger.error(
            f"Error listing models: {e}",
            extra={"user_id": str(current_user.user_id), "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve models",
        ) from e


@router.get("/{id}", response_model=ModelDetailedResponse)
async def get_model(
    id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> ModelDetailedResponse:
    """
    Get detailed information about a specific model by its database ID.

    Includes capabilities, pricing, and performance characteristics.
    Accessible by all authenticated users.
    """
    try:
        from ..db.models import Model

        logger.info(
            f"Getting model details for ID {id}",
            extra={"user_id": str(current_user.user_id), "model_uuid": str(id)},
        )

        # Get model by UUID
        stmt = select(Model).where(Model.id == id)
        result = await db.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model with ID {id} not found",
            )

        # Use service to get enriched model details
        service = ModelRegistryService(session=db)
        model_data = await service.get_model(model.model_id)

        if not model_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model {model.model_id} not found",
            )

        return model_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting model {id}: {e}",
            extra={
                "user_id": str(current_user.user_id),
                "model_uuid": str(id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve model details",
        ) from e


@router.post("/recommend", response_model=list[ModelRecommendation])
async def recommend_models(
    request: ModelSelectionRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> list[ModelRecommendation]:
    """
    Get model recommendations based on use case requirements.

    Returns top 5 recommended models sorted by match confidence.
    Accessible by all authenticated users.
    """
    try:
        logger.info(
            f"Recommending models for use case type: {request.use_case_type}",
            extra={
                "user_id": str(current_user.user_id),
                "use_case_type": request.use_case_type,
            },
        )

        service = ModelRegistryService(session=db)

        return await service.recommend_model(request)
    except Exception as e:
        logger.error(
            f"Error recommending models: {e}",
            extra={"user_id": str(current_user.user_id), "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendations",
        ) from e


@router.patch(
    "/{id}/metadata",
    response_model=ModelDetailedResponse,
    dependencies=[Depends(admin_required)],
)
async def update_model_metadata(
    id: UUID,
    metadata_update: ModelUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> ModelDetailedResponse:
    """
    Update model metadata (Admin only) by database ID.

    Allows administrators to override auto-discovered or inferred metadata
    with accurate values. Updates take effect immediately.

    Common use cases:
    - Set accurate context_window for unknown models
    - Set embedding_dimensions for embedding models
    - Update description or specialization
    - Mark models as deprecated
    - Hide/unhide models
    """
    try:
        from ..db.models import Model

        logger.info(
            f"Updating metadata for model ID {id}",
            extra={"user_id": str(current_user.user_id), "model_uuid": str(id)},
        )

        # Get existing model by UUID
        stmt = select(Model).where(Model.id == id)
        result = await db.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model with ID {id} not found",
            )

        # Update fields that were provided
        update_data = metadata_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(model, field):
                setattr(model, field, value)

        # Track admin override
        if not isinstance(model.metadata_json, dict):
            model.metadata_json = {}
        model.metadata_json["admin_override"] = True
        model.metadata_json["last_updated_by"] = str(current_user.user_id)
        model.metadata_json["last_updated_at"] = datetime.now(tz=UTC).isoformat()

        await db.commit()

        logger.info(
            f"Successfully updated model {model.model_id} (ID: {id})",
            extra={
                "user_id": str(current_user.user_id),
                "model_uuid": str(id),
                "model_id": model.model_id,
                "fields_updated": list(update_data.keys()),
            },
        )

        # Return updated model details
        service = ModelRegistryService(session=db)
        updated_model = await service.get_model(model.model_id)

        if not updated_model:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Model updated but failed to retrieve",
            )

        return updated_model

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error updating model {id}: {e}",
            extra={
                "user_id": str(current_user.user_id),
                "model_uuid": str(id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update model metadata",
        ) from e


@router.post("/sync", status_code=status.HTTP_200_OK, dependencies=[Depends(admin_required)])
async def sync_models(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> dict:
    """
    Synchronize model registry with inference server.

    Admin-only endpoint. Discovers new models, updates existing ones,
    and marks unavailable models. Returns detailed sync report.

    Response includes:
    - total_discovered: Number of models found on inference server
    - newly_created: Models auto-created in registry
    - updated_existing: Existing models updated
    - marked_unavailable: Models no longer available
    - created_models: List of newly created model details
    - unavailable_models: List of models marked unavailable
    - warnings: Any issues encountered during sync
    """
    try:
        logger.info(
            "Syncing models with inference server",
            extra={"user_id": str(current_user.user_id)},
        )

        orchestrator_settings = load_orchestrator_config()
        embedding_settings = load_embedding_config()

        # Get Gateway URL for unified model discovery
        gateway_url = orchestrator_settings.inference_gateway_url
        # Strip /v1 for admin calls (admin routes are at /admin, not /v1/admin)
        gateway_url_admin = (
            gateway_url.rstrip("/").removesuffix("/v1")
            if gateway_url.rstrip("/").endswith("/v1")
            else gateway_url.rstrip("/")
        )
        # Fallback to direct inference server if Gateway not available
        inference_endpoint = embedding_settings.openai_base_url
        api_key = embedding_settings.openai_api_key

        # Forward the caller's JWT to the Gateway (it requires a JWT, not the LLMaaS
        # api_key). sync is admin-only, and admin tokens bypass the Gateway scope check.
        gateway_auth_token = request.headers.get("authorization") or request.headers.get(
            "Authorization"
        )

        service = ModelRegistryService(
            session=db,
            inference_endpoint=inference_endpoint,
            api_key=api_key,
            gateway_url=gateway_url,
            gateway_auth_token=gateway_auth_token,
        )

        sync_report = await service.sync_with_inference_server()

        logger.info(
            "Successfully synced models",
            extra={
                "user_id": str(current_user.user_id),
                "summary": sync_report["summary"],
            },
        )

        # Reload inference gateway routing table after sync
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get admin token for gateway call (same identity as current user)
                access_token_data = {
                    "sub": current_user.sub,
                    "user_id": current_user.user_id,
                    "roles": current_user.roles,
                }
                admin_token = auth_manager.create_access_token(data=access_token_data)

                response = await client.post(
                    f"{gateway_url_admin}/admin/router/reload",
                    headers={"Authorization": f"Bearer {admin_token}"},
                )

                if response.status_code == 200:
                    logger.info("Successfully reloaded inference gateway router")
                    sync_report["router_reloaded"] = True
                else:
                    logger.warning(
                        f"Failed to reload router: HTTP {response.status_code}",
                        extra={"response": response.text},
                    )
                    sync_report["router_reloaded"] = False
                    sync_report.setdefault("warnings", []).append(
                        f"Router reload failed: HTTP {response.status_code}"
                    )
        except Exception as reload_error:
            logger.warning(
                "Failed to reload inference gateway router",
                extra={"error": str(reload_error)},
            )
            sync_report["router_reloaded"] = False
            sync_report.setdefault("warnings", []).append(f"Router reload failed: {reload_error!s}")

        return sync_report

    except Exception as e:
        logger.error(
            f"Error syncing models: {e}",
            extra={"user_id": str(current_user.user_id), "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync models",
        ) from e


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(admin_required),
) -> None:
    """
    Delete a model from registry (admin only).

    Cascades to model_pricing_history.

    Args:
        model_id: Model UUID (not model_id string)
        current_user: Current authenticated user (must be admin)
        db: Database session
    """
    from ..db.models import Model

    try:
        # Get model by UUID
        stmt = select(Model).where(Model.id == model_id)
        result = await db.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise HTTPException(status_code=404, detail=f"Model with ID '{model_id}' not found")

        model_identifier = model.model_id

        # Delete model (cascades to pricing history)
        from sqlalchemy import delete

        delete_stmt = delete(Model).where(Model.id == model_id)
        await db.execute(delete_stmt)
        await db.commit()

        logger.info(
            f"Deleted model: {model_identifier}",
            extra={
                "model_id": model_identifier,
                "uuid": str(model_id),
                "user_id": str(current_user.user_id),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error deleting model: {e}",
            extra={"model_id": str(model_id), "error": str(e)},
            exc_info=True,
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete model: {e!s}",
        ) from e
