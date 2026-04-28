"""
Intent Model Configuration Router

Manages system-wide intent-to-model default configurations (ADR-069).
AIOps developers use this to configure which models are used for each intent type.

**Authorization:** Developer-only endpoints (requires developer role or higher)
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import get_current_user
from shared.auth.models import TokenPayload
from shared.logging_utils.fastapi import configure_logging

from ..db.database import get_async_db
from ..schemas.intent import RequestType
from ..services.model_registry_service import ModelRegistryService

logger = configure_logging(service_name="intent_model_config")

# Router setup
router = APIRouter(
    prefix="/api/v1/development/intent-models",
    tags=["Development", "Intent Models"],
)


# ============================================================================
# Pydantic Models
# ============================================================================


class AvailableModel(BaseModel):
    """Model available for intent configuration."""

    model_id: str = Field(description="Model identifier from registry")
    provider: str = Field(description="Model provider (e.g., openai, anthropic)")
    context_window: int | None = Field(description="Context window size in tokens")
    capabilities: list[str] = Field(
        default_factory=list, description="Model capabilities (e.g., json_mode, vision)"
    )
    is_active: bool = Field(description="Whether model is currently active")


class IntentModelDefault(BaseModel):
    """Intent model default configuration."""

    id: UUID = Field(description="Unique identifier")
    intent_code: str = Field(description="Intent type code (e.g., QUERY)")
    model_id: str = Field(description="Model identifier from registry")
    temperature: float | None = Field(
        default=None,
        description="Optional temperature override (0.0-1.0). NULL = use ModelType default.",
        ge=0.0,
        le=1.0,
    )
    priority: int = Field(description="Selection priority (lower = higher priority)")
    is_active: bool = Field(description="Whether this is the active default")
    effective_date: datetime = Field(description="When this configuration becomes effective")
    notes: str | None = Field(description="Admin notes about this configuration")
    created_at: datetime = Field(description="Creation timestamp")
    created_by: UUID | None = Field(description="User who created this configuration")
    updated_at: datetime = Field(description="Last update timestamp")
    updated_by: UUID | None = Field(description="User who last updated this configuration")


class IntentModelDefaultWithModel(IntentModelDefault):
    """Intent model default with model details."""

    model_provider: str | None = Field(description="Model provider")
    model_context_window: int | None = Field(description="Model context window")
    model_capabilities: list[str] = Field(default_factory=list, description="Model capabilities")


class IntentModelSummary(BaseModel):
    """Summary of intent with current model configuration."""

    intent_code: str = Field(description="Intent type code")
    display_name: str = Field(description="Human-readable intent name")
    description: str = Field(description="Intent description")
    current_model_id: str | None = Field(description="Currently configured model ID")
    current_temperature: float | None = Field(
        default=None,
        description="Configured temperature override (0.0-1.0). NULL = use ModelType default.",
    )
    has_default: bool = Field(description="Whether a default is configured")
    icon: str | None = Field(description="Icon identifier")
    color: str | None = Field(description="Color code")


class UpdateIntentModelRequest(BaseModel):
    """Request to update intent model default."""

    model_id: str = Field(description="Model ID from registry", min_length=1)
    temperature: float | None = Field(
        default=None,
        description="Temperature override (0.0-1.0). Omit or null = use ModelType default.",
        ge=0.0,
        le=1.0,
    )
    notes: str | None = Field(default=None, description="Notes about why this model was chosen")
    effective_date: datetime | None = Field(
        default=None, description="When to make this effective (defaults to now)"
    )


class IntentModelHistoryEntry(BaseModel):
    """Historical intent model configuration."""

    id: UUID
    intent_code: str
    model_id: str
    is_active: bool
    effective_date: datetime
    notes: str | None
    created_at: datetime
    created_by_username: str | None


# ============================================================================
# Helper Functions
# ============================================================================


def require_developer(current_user: TokenPayload) -> None:
    """Ensure current user has developer role or higher."""
    if not (
        current_user.has_role("developer")
        or current_user.has_role("admin")
        or current_user.has_role("use_case_publisher")
    ):
        logger.warning(
            "Unauthorized intent model configuration access attempt",
            extra={"user": current_user.sub, "roles": current_user.roles},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Developer privileges required",
        )


def validate_intent_code(intent_code: str) -> None:
    """Validate that intent code is valid."""
    try:
        RequestType(intent_code)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid intent code: {intent_code}"
        )


async def validate_model_exists(db: AsyncSession, model_id: str) -> None:
    """Validate that model exists in registry and is active."""
    result = await db.execute(
        text("SELECT COUNT(*) FROM models WHERE model_id = :model_id AND is_active = TRUE"),
        {"model_id": model_id},
    )
    count = result.scalar()

    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found in active models registry",
        )


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/summary", response_model=list[IntentModelSummary])
async def get_intent_model_summary(
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> list[IntentModelSummary]:
    """
    Get summary of all intents with their current model configurations.

    Shows which intents have configured defaults and which need configuration.
    """
    require_developer(current_user)

    result = await db.execute(
        text(
            "SELECT it.intent_code, it.display_name, it.description, "
            "imd.model_id, imd.temperature, it.icon, it.color, "
            "CASE WHEN imd.id IS NOT NULL THEN TRUE ELSE FALSE END as has_default "
            "FROM intent_types it "
            "LEFT JOIN intent_model_defaults imd "
            "ON it.intent_code = imd.intent_code AND imd.is_active = TRUE "
            "WHERE it.is_system = TRUE ORDER BY it.sort_order"
        )
    )

    summaries = []
    for row in result:
        summaries.append(
            IntentModelSummary(
                intent_code=row.intent_code,
                display_name=row.display_name,
                description=row.description,
                current_model_id=row.model_id,
                current_temperature=float(row.temperature) if row.temperature is not None else None,
                has_default=row.has_default,
                icon=row.icon,
                color=row.color,
            )
        )

    logger.info(
        "Retrieved intent model summary",
        extra={
            "user": current_user.sub,
            "total_intents": len(summaries),
            "configured": sum(1 for s in summaries if s.has_default),
        },
    )

    return summaries


def _model_to_available(m: Any) -> AvailableModel:
    """Map ModelRegistry list item to AvailableModel."""
    caps: list[str] = []
    if getattr(m, "supports_tools", False):
        caps.append("tools")
    if getattr(m, "supports_vision", False):
        caps.append("vision")
    if getattr(m, "supports_audio", False):
        caps.append("audio")
    if getattr(m, "is_reasoning_model", False):
        caps.append("reasoning")
    provider = getattr(m, "provider", None) or str(getattr(m, "provider_type", "unknown"))
    return AvailableModel(
        model_id=m.model_id,
        provider=provider,
        context_window=getattr(m, "context_window", None),
        capabilities=caps,
        is_active=getattr(m, "is_available", True),
    )


@router.get("/available-models", response_model=list[AvailableModel])
async def get_available_models(
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> list[AvailableModel]:
    """
    Get list of models available for intent configuration.

    Returns available LLM models from the Model Registry (same source as
    Model Management). Filters by model_type=llm and is_available=True.
    Falls back to raw SQL if ModelRegistryService fails.
    """
    require_developer(current_user)

    try:
        service = ModelRegistryService(session=db)
        response = await service.list_models(
            model_type="llm",
            available_only=True,
            include_deprecated=False,
            include_hidden=False,
            page=1,
            size=200,
        )
        models = [_model_to_available(m) for m in response.models]
    except Exception as e:
        logger.warning(
            "ModelRegistryService.list_models failed, falling back to raw SQL: %s",
            e,
            exc_info=True,
        )
        models = await _get_available_models_raw(db)

    logger.info(
        "Retrieved available models", extra={"user": current_user.sub, "model_count": len(models)}
    )

    return models


async def _get_available_models_raw(db: AsyncSession) -> list[AvailableModel]:
    """Fallback: query models table directly when ModelRegistryService fails."""
    result = await db.execute(
        text(
            "SELECT model_id, provider, context_window, "
            "COALESCE(supports_tools, false), COALESCE(supports_vision, false), "
            "COALESCE(supports_audio, false), COALESCE(is_reasoning_model, false) "
            "FROM models "
            "WHERE is_available = TRUE AND model_type = 'llm' AND is_hidden = FALSE "
            "AND deprecated = FALSE "
            "ORDER BY provider NULLS LAST, model_id"
        )
    )
    models = []
    for row in result:
        caps: list[str] = []
        if row[3]:
            caps.append("tools")
        if row[4]:
            caps.append("vision")
        if row[5]:
            caps.append("audio")
        if row[6]:
            caps.append("reasoning")
        models.append(
            AvailableModel(
                model_id=row[0],
                provider=row[1] or "unknown",
                context_window=row[2],
                capabilities=caps,
                is_active=True,
            )
        )
    return models


@router.get("/{intent_code}", response_model=IntentModelDefaultWithModel | None)
async def get_intent_model_default(
    intent_code: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> IntentModelDefaultWithModel | None:
    """
    Get current active default for a specific intent.

    Returns None if no default is configured.
    """
    require_developer(current_user)
    validate_intent_code(intent_code)

    result = await db.execute(
        text(
            "SELECT imd.id, imd.intent_code, imd.model_id, imd.temperature, imd.priority, "
            "imd.is_active, imd.effective_date, imd.notes, imd.created_at, "
            "imd.created_by, imd.updated_at, imd.updated_by, "
            "m.provider as model_provider, m.context_window as model_context_window, "
            "ARRAY_REMOVE(ARRAY["
            "CASE WHEN m.supports_tools THEN 'tools' END, "
            "CASE WHEN m.supports_vision THEN 'vision' END, "
            "CASE WHEN m.supports_audio THEN 'audio' END, "
            "CASE WHEN m.is_reasoning_model THEN 'reasoning' END"
            "], NULL)::text[] as model_capabilities "
            "FROM intent_model_defaults imd "
            "JOIN models m ON imd.model_id = m.model_id "
            "WHERE imd.intent_code = :intent_code AND imd.is_active = TRUE"
        ),
        {"intent_code": intent_code},
    )
    row = result.fetchone()

    if not row:
        return None

    temp_val = float(row.temperature) if row.temperature is not None else None
    return IntentModelDefaultWithModel(
        id=row.id,
        intent_code=row.intent_code,
        model_id=row.model_id,
        temperature=temp_val,
        priority=row.priority,
        is_active=row.is_active,
        effective_date=row.effective_date,
        notes=row.notes,
        created_at=row.created_at,
        created_by=row.created_by,
        updated_at=row.updated_at,
        updated_by=row.updated_by,
        model_provider=row.model_provider,
        model_context_window=row.model_context_window,
        model_capabilities=row.model_capabilities or [],
    )


@router.put("/{intent_code}", response_model=IntentModelDefault)
async def update_intent_model_default(
    intent_code: str,
    request: UpdateIntentModelRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> IntentModelDefault:
    """
    Update the default model for an intent.

    Deactivates the current default and creates a new active default.
    Creates audit trail of the change.
    """
    require_developer(current_user)
    validate_intent_code(intent_code)
    await validate_model_exists(db, request.model_id)

    try:
        # Deactivate current default
        await db.execute(
            text(
                "UPDATE intent_model_defaults "
                "SET is_active = FALSE, updated_at = :now, updated_by = :user_id "
                "WHERE intent_code = :intent_code AND is_active = TRUE"
            ),
            {
                "intent_code": intent_code,
                "now": datetime.now(UTC),
                "user_id": UUID(current_user.sub),
            },
        )

        # Create new active default
        effective_date = request.effective_date or datetime.now(UTC)

        result = await db.execute(
            text(
                "INSERT INTO intent_model_defaults "
                "(intent_code, model_id, temperature, priority, is_active, effective_date, "
                "notes, created_by, updated_by) "
                "VALUES (:intent_code, :model_id, :temperature, 1, TRUE, :effective_date, "
                ":notes, :user_id, :user_id) "
                "RETURNING id, intent_code, model_id, temperature, priority, is_active, "
                "effective_date, notes, created_at, created_by, updated_at, updated_by"
            ),
            {
                "intent_code": intent_code,
                "model_id": request.model_id,
                "temperature": request.temperature,
                "effective_date": effective_date,
                "notes": request.notes,
                "user_id": UUID(current_user.sub),
            },
        )

        await db.commit()

        row = result.fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Update succeeded but no row returned",
            )
        temp_val = float(row.temperature) if row.temperature is not None else None
        logger.info(
            "Updated intent model default",
            extra={
                "user": current_user.sub,
                "intent_code": intent_code,
                "model_id": request.model_id,
                "temperature": temp_val,
                "notes": request.notes,
            },
        )
        return IntentModelDefault(
            id=row.id,
            intent_code=row.intent_code,
            model_id=row.model_id,
            temperature=temp_val,
            priority=row.priority,
            is_active=row.is_active,
            effective_date=row.effective_date,
            notes=row.notes,
            created_at=row.created_at,
            created_by=row.created_by,
            updated_at=row.updated_at,
            updated_by=row.updated_by,
        )

    except Exception as e:
        await db.rollback()
        logger.error(
            "Failed to update intent model default",
            extra={"user": current_user.sub, "intent_code": intent_code, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update intent model default: {e!s}",
        )


@router.get("/{intent_code}/history", response_model=list[IntentModelHistoryEntry])
async def get_intent_model_history(
    intent_code: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> list[IntentModelHistoryEntry]:
    """
    Get configuration history for an intent.

    Shows all past and current model assignments with audit information.
    """
    require_developer(current_user)
    validate_intent_code(intent_code)

    result = await db.execute(
        text(
            "SELECT imd.id, imd.intent_code, imd.model_id, imd.is_active, "
            "imd.effective_date, imd.notes, imd.created_at, u.username as created_by_username "
            "FROM intent_model_defaults imd "
            "LEFT JOIN users u ON imd.created_by = u.id "
            "WHERE imd.intent_code = :intent_code ORDER BY imd.created_at DESC"
        ),
        {"intent_code": intent_code},
    )

    history = []
    for row in result:
        history.append(
            IntentModelHistoryEntry(
                id=row.id,
                intent_code=row.intent_code,
                model_id=row.model_id,
                is_active=row.is_active,
                effective_date=row.effective_date,
                notes=row.notes,
                created_at=row.created_at,
                created_by_username=row.created_by_username,
            )
        )

    logger.info(
        "Retrieved intent model history",
        extra={"user": current_user.sub, "intent_code": intent_code, "entries": len(history)},
    )

    return history


@router.post("/refresh-cache", status_code=status.HTTP_204_NO_CONTENT)
async def refresh_model_selector_cache(
    current_user: TokenPayload = Depends(get_current_user),
) -> None:
    """
    Refresh the ModelSelector's in-memory cache of intent defaults.

    Call this after making configuration changes to immediately apply them
    without restarting the service.

    Note: This notifies the orchestrator to refresh its cache. The actual
    refresh happens asynchronously.
    """
    require_developer(current_user)

    # TODO: Implement cache refresh notification mechanism
    # This could be done via:
    # 1. Event bus (Redis pub/sub)
    # 2. Direct call to orchestrator singleton
    # 3. Service restart notification

    logger.info("Model selector cache refresh requested", extra={"user": current_user.sub})

    # For now, log the request
    # Implementation will depend on orchestrator architecture
