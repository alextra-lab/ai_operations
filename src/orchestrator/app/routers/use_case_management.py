"""
Use Case Management Router for AI Operations Platform.

Provides CRUD operations, versioning, lifecycle management, and cloning for Use Cases.
Use Cases are sovereign entities that own all configuration (prompts, model, RAG, tools, policies).

Architecture: ADR-018 Use Case Owned Architecture
Admin and corpus_admin roles only for management operations.
"""

import copy
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import admin_required, get_current_user
from shared.auth.models import TokenPayload
from shared.logging_utils.fastapi import configure_logging

from ..db.database import get_async_db
from ..db.models import UseCase as DBUseCase
from ..schemas.use_case_management import (
    StateTransitionRequest,
    UseCaseCloneRequest,
    UseCaseCreateRequest,
    UseCaseListResponse,
    UseCaseResponse,
    UseCaseUpdateRequest,
    UseCaseVersionListResponse,
)
from ..services.rbac_v2 import (
    can_edit_use_case,
    get_accessible_use_cases,
    get_user_teams,
    has_role,
)
from ..services.use_case_config_loader import invalidate_config_cache_for_use_case

logger = configure_logging(service_name="use_case_mgmt_router")

router = APIRouter(prefix="/api/v1/admin/use-cases", tags=["use-case-management"])


def _deep_merge_config(
    existing: dict[str, Any], incoming: dict[str, Any], _path: str = ""
) -> dict[str, Any]:
    """
    Merge incoming config over existing. Incoming values override; keys only in
    existing are preserved. Prevents overwriting saved fields (e.g. models.llm)
    when the client sends a partial payload or when validation would fill defaults.

    Special handling for output_schema: replace entirely, don't merge nested properties.
    This ensures when a user refines the schema, old properties are removed.
    """
    result = copy.deepcopy(existing)
    for key, incoming_val in incoming.items():
        current_path = f"{_path}.{key}" if _path else key

        # Special case: output_contract.output_schema should be replaced, not merged
        if current_path == "output_contract.output_schema":
            result[key] = copy.deepcopy(incoming_val)
        elif key in result and isinstance(result[key], dict) and isinstance(incoming_val, dict):
            result[key] = _deep_merge_config(result[key], incoming_val, current_path)
        else:
            result[key] = copy.deepcopy(incoming_val)
    return result


# ============================================================================
# Use Case CRUD Endpoints
# ============================================================================


@router.get("", response_model=UseCaseListResponse)
async def list_use_cases_for_management(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    use_case_id_filter: str | None = Query(None, description="Filter by use_case_id"),
    category: str | None = Query(None, description="Filter by category"),
    lifecycle_state: str | None = Query(None, description="Filter by lifecycle state"),
    active_only: bool = Query(False, description="Return only active use cases"),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> UseCaseListResponse:
    """
    List use cases accessible to current user based on RBAC V2.

    Uses RBAC V2 access control (ADR-060) to filter use cases by user's roles and teams.
    Management endpoint - returns more details than /available endpoint.
    """
    try:
        logger.info(
            "Listing use cases for management",
            extra={
                "user_id": str(current_user.user_id),
                "page": page,
                "page_size": page_size,
                "filters": {
                    "use_case_id": use_case_id_filter,
                    "category": category,
                    "lifecycle_state": lifecycle_state,
                    "active_only": active_only,
                },
            },
        )

        # Get accessible use cases using RBAC V2
        all_use_cases = await get_accessible_use_cases(
            UUID(current_user.user_id), db, lifecycle_state=lifecycle_state
        )

        # Apply additional filters (in memory)
        filtered_use_cases = []
        for uc in all_use_cases:
            if use_case_id_filter and use_case_id_filter.lower() not in uc.use_case_id.lower():
                continue

            if category and uc.category != category:
                continue

            if active_only and not uc.is_active:
                continue

            filtered_use_cases.append(uc)

        # Sort by updated_at descending
        filtered_use_cases.sort(key=lambda x: x.updated_at, reverse=True)

        # Apply pagination
        total = len(filtered_use_cases)
        offset = (page - 1) * page_size
        paginated_use_cases = filtered_use_cases[offset : offset + page_size]

        logger.info(
            "Found %d use cases, returning page %d of %d",
            total,
            page,
            (total + page_size - 1) // page_size,
        )

        return UseCaseListResponse(
            use_cases=[UseCaseResponse.from_orm(uc) for uc in paginated_use_cases],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )

    except Exception as e:
        logger.error("Error listing use cases: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve use cases",
        ) from e


@router.post("", response_model=UseCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_use_case(
    use_case_data: UseCaseCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> UseCaseResponse:
    """
    Create a new use case with automatic team assignment.

    Uses RBAC V2 team logic (ADR-060):
    - If team_id provided: Validates user is member of that team (or admin)
    - If single team membership: Auto-assigns to user's team
    - If multiple teams: Requires explicit team_id
    - If no teams: Assigns to 'team:default'

    Requires use_case_admin role or admin role.
    """
    try:
        user_id = UUID(current_user.user_id)

        # Verify user has required role (use_case_admin or admin)
        is_admin = await has_role(user_id, "admin", db)
        is_use_case_admin = await has_role(user_id, "use_case_admin", db)
        if not (is_admin or is_use_case_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="use_case_admin or admin role required to create use cases",
            )

        user_teams = await get_user_teams(user_id, db)

        logger.info(
            "Creating new use case",
            extra={
                "user_id": str(user_id),
                "use_case_id": use_case_data.use_case_id,
                "uc_name": use_case_data.name,
                "user_teams": user_teams,
                "requested_team_id": use_case_data.team_id,
            },
        )

        # Determine team assignment
        if use_case_data.team_id:
            team_id = use_case_data.team_id
            is_admin = await has_role(user_id, "admin", db)
            if not is_admin and team_id not in user_teams:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You are not a member of team '{team_id}'",
                )
        elif len(user_teams) == 1:
            team_id = user_teams[0]
        elif len(user_teams) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are a member of multiple teams. Please specify team_id.",
            )
        else:
            team_id = "team:default"

        # Check if use_case_id already exists
        stmt = select(DBUseCase).where(DBUseCase.use_case_id == use_case_data.use_case_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Use case with ID '{use_case_data.use_case_id}' already exists",
            )

        # Validate and normalize config_json through UseCaseConfig (applies defaults)
        from ..schemas.use_case_config import UseCaseConfig

        if use_case_data.config_json:
            # Validate and normalize through Pydantic model
            validated_config = UseCaseConfig(**use_case_data.config_json)
            normalized_config = validated_config.model_dump()
        else:
            # Use default config
            normalized_config = UseCaseConfig().model_dump()

        # Prepare metadata with prompts
        metadata: dict[str, Any] = {
            "created_from_pattern": (
                use_case_data.metadata_json.get("created_from_pattern")
                if use_case_data.metadata_json
                else None
            ),
            "version_history": [],
        }

        # Store prompts in metadata if provided
        if use_case_data.prompts:
            metadata["prompts"] = use_case_data.prompts.model_dump(exclude_none=True)

        # Create use case
        use_case_kwargs = {
            "use_case_id": use_case_data.use_case_id,
            "name": use_case_data.name,
            "description": use_case_data.description,
            "category": use_case_data.category,
            "intent_type": use_case_data.intent_type,
            "team_id": team_id,
            "version": 1,
            "lifecycle_state": "draft",
            "is_active": False,
            "config_json": normalized_config,
            "metadata_json": metadata,
            "created_by_user_id": user_id,
        }
        new_use_case = DBUseCase(**use_case_kwargs)  # type: ignore

        db.add(new_use_case)
        await db.flush()  # Get ID without committing

        logger.info(
            "Created use case: %s (ID: %s, team: %s)",
            new_use_case.use_case_id,
            new_use_case.id,
            team_id,
        )

        await db.commit()
        await db.refresh(new_use_case)

        return UseCaseResponse.from_orm(new_use_case)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Error creating use case: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create use case",
        ) from e


@router.get(
    "/{use_case_id}",
    response_model=UseCaseResponse,
    dependencies=[Depends(admin_required)],
)
async def get_use_case_details(
    use_case_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> UseCaseResponse:
    """
    Get use case details including config and metadata.

    Requires corpus_admin or admin role.

    Path parameter is the use case UUID (id), not the use_case_id string.
    """
    try:
        stmt = select(DBUseCase).where(DBUseCase.id == use_case_id)
        result = await db.execute(stmt)
        use_case = result.scalar_one_or_none()

        if not use_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Use case '{use_case_id}' not found",
            )

        logger.info(
            "Retrieved use case details for %s",
            use_case_id,
            extra={"user_id": str(current_user.user_id)},
        )

        return UseCaseResponse.from_orm(use_case)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving use case: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve use case",
        ) from e


@router.put(
    "/{use_case_id}",
    response_model=UseCaseResponse,
    dependencies=[Depends(admin_required)],
)
async def update_use_case(
    use_case_id: UUID,
    use_case_data: UseCaseUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> UseCaseResponse:
    """
    Update use case details and configuration.

    Creates new version if config_json changes.
    Requires corpus_admin or admin role.

    Security rules (P4-TOOLS-05):
    - Can only update DRAFT use cases (immutability pattern)
    - Must be creator or admin
    - Published/archived use cases must be cloned first

    Path parameter is the use case UUID (id), not the use_case_id string.
    """
    try:
        stmt = select(DBUseCase).where(DBUseCase.id == use_case_id)
        result = await db.execute(stmt)
        use_case = result.scalar_one_or_none()

        if not use_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Use case '{use_case_id}' not found",
            )

        # SECURITY: Check edit permission using RBAC V2
        user_id = UUID(current_user.user_id)
        can_edit = await can_edit_use_case(user_id, use_case, db)
        if not can_edit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot modify {use_case.lifecycle_state} use cases. "
                f"Only draft use cases can be edited, and only by their creator or admin.",
            )

        logger.info(
            "Updating use case %s (lifecycle_state=%s, creator=%s, updater=%s)",
            use_case_id,
            use_case.lifecycle_state,
            use_case.created_by_user_id,
            current_user.user_id,
            extra={"user_id": str(current_user.user_id)},
        )

        # Store old config for version history
        old_config = (use_case.config_json or {}).copy()
        config_changed = False

        # Update fields
        if use_case_data.name is not None:
            use_case.name = use_case_data.name

        if use_case_data.description is not None:
            use_case.description = use_case_data.description

        if use_case_data.category is not None:
            use_case.category = use_case_data.category

        # Track if metadata needs updating
        metadata_changed = False
        updated_metadata = use_case.metadata_json.copy() if use_case.metadata_json else {}

        if use_case_data.config_json is not None and use_case_data.config_json != old_config:
            # Merge incoming with existing so we never overwrite saved fields (e.g. models.llm)
            # when the client sends a partial payload or when validation fills defaults.
            merged_config = _deep_merge_config(old_config, use_case_data.config_json)

            # Debug logging for schema updates
            incoming_schema = use_case_data.config_json.get("output_contract", {}).get(
                "output_schema"
            )
            old_schema = old_config.get("output_contract", {}).get("output_schema")
            merged_schema = merged_config.get("output_contract", {}).get("output_schema")
            logger.info(
                "Schema update: incoming=%s, old=%s, merged=%s",
                type(incoming_schema).__name__ if incoming_schema else "None",
                type(old_schema).__name__ if old_schema else "None",
                type(merged_schema).__name__ if merged_schema else "None",
                extra={"use_case_id": str(use_case_id)},
            )

            from ..schemas.use_case_config import UseCaseConfig

            try:
                validated_config = UseCaseConfig(**merged_config)
                normalized_config = validated_config.model_dump()

                # Log normalized schema
                normalized_schema = normalized_config.get("output_contract", {}).get(
                    "output_schema"
                )
                logger.info(
                    "Normalized schema: %s",
                    type(normalized_schema).__name__ if normalized_schema else "None",
                    extra={"use_case_id": str(use_case_id)},
                )
            except Exception as e:
                logger.error("Invalid config_json in update request: %s", str(e))
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid use case configuration: {e!s}",
                ) from e

            use_case.config_json = normalized_config
            config_changed = True
            metadata_changed = True
            invalidate_config_cache_for_use_case(str(use_case_id))

            # Increment version on config change
            use_case.version += 1

            # Store version history
            version_history = updated_metadata.get("version_history", [])
            version_history.append(
                {
                    "version": use_case.version - 1,
                    "config_snapshot": old_config,
                    "updated_at": datetime.now(UTC).isoformat(),
                    "updated_by": str(current_user.user_id),
                }
            )
            updated_metadata["version_history"] = version_history

        # Update prompts if provided
        if use_case_data.prompts is not None:
            updated_metadata["prompts"] = use_case_data.prompts.model_dump(exclude_none=True)
            metadata_changed = True

        # Merge incoming metadata with existing (preserve parameter injection metadata)
        if use_case_data.metadata_json:
            # Merge incoming metadata (e.g., from parameter injection)
            updated_metadata.update(use_case_data.metadata_json)
            metadata_changed = True

        # Add audit metadata
        if metadata_changed:
            updated_metadata["last_modified_by"] = str(current_user.user_id)
            updated_metadata["last_modified_at"] = datetime.now(UTC).isoformat()
            use_case.metadata_json = updated_metadata

        await db.commit()
        await db.refresh(use_case)

        if config_changed:
            logger.info("Use case %s updated to version %d", use_case_id, use_case.version)
        else:
            logger.info("Use case %s metadata updated (no version change)", use_case_id)

        return UseCaseResponse.from_orm(use_case)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Error updating use case: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update use case",
        ) from e


@router.delete("/{use_case_id}", dependencies=[Depends(admin_required)])
async def delete_use_case(
    use_case_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> dict[str, str]:
    """
    Delete a use case.

    Requires admin role.
    Only draft use cases can be deleted.

    Path parameter is the use case UUID (id), not the use_case_id string.
    """
    try:
        stmt = select(DBUseCase).where(DBUseCase.id == use_case_id)
        result = await db.execute(stmt)
        use_case = result.scalar_one_or_none()

        if not use_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Use case '{use_case_id}' not found",
            )

        # Only allow deletion of draft use cases
        if use_case.lifecycle_state != "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete use case in '{use_case.lifecycle_state}' state. Only draft use cases can be deleted.",
            )

        logger.info(
            "Deleting use case %s",
            use_case_id,
            extra={"user_id": str(current_user.user_id)},
        )

        from sqlalchemy import delete

        delete_stmt = delete(DBUseCase).where(DBUseCase.id == use_case.id)
        await db.execute(delete_stmt)
        await db.commit()

        logger.info("Successfully deleted use case %s", use_case_id)

        return {"message": f"Use case '{use_case_id}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Error deleting use case: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete use case",
        ) from e


# ============================================================================
# Use Case Cloning
# ============================================================================


@router.post(
    "/{use_case_id}/clone",
    response_model=UseCaseResponse,
)
async def clone_use_case(
    use_case_id: UUID,
    clone_data: UseCaseCloneRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> UseCaseResponse:
    """
    Clone an existing use case with a new ID and name.

    Copies all configuration and prompts.
    New clone starts as draft with version 1 and team assignment follows same logic as create.
    Uses RBAC V2 team assignment logic.

    Path parameter is the use case UUID (id), not the use_case_id string.
    """
    try:
        user_id = UUID(current_user.user_id)
        user_teams = await get_user_teams(user_id, db)

        # Load source use case by UUID
        stmt = select(DBUseCase).where(DBUseCase.id == use_case_id)
        result = await db.execute(stmt)
        source_uc = result.scalar_one_or_none()

        if not source_uc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source use case '{use_case_id}' not found",
            )

        # Check if new ID already exists
        stmt = select(DBUseCase).where(DBUseCase.use_case_id == clone_data.new_use_case_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Use case with ID '{clone_data.new_use_case_id}' already exists",
            )

        # Determine team assignment (same logic as create)
        if len(user_teams) == 1:
            team_id = user_teams[0]
        elif len(user_teams) > 1:
            # For clones, default to first team if multiple (can be changed later)
            team_id = user_teams[0]
        else:
            team_id = "team:default"

        logger.info(
            "Cloning use case %s → %s (team: %s)",
            use_case_id,
            clone_data.new_use_case_id,
            team_id,
            extra={"user_id": str(user_id)},
        )

        # Prepare metadata for clone (include prompts if present)
        cloned_metadata = {
            "cloned_from": source_uc.use_case_id,
            "cloned_at": datetime.now(UTC).isoformat(),
            "cloned_by": str(user_id),
            "version_history": [],
        }

        # Copy prompts from source if they exist
        if source_uc.metadata_json and "prompts" in source_uc.metadata_json:
            prompts_data = source_uc.metadata_json["prompts"]
            # Deep copy to ensure all nested data is preserved
            cloned_metadata["prompts"] = copy.deepcopy(prompts_data)
            logger.info(
                "Copied prompts from source use case %s to clone",
                source_uc.use_case_id,
            )
        else:
            logger.warning(
                "Source use case %s has no prompts in metadata_json",
                source_uc.use_case_id,
            )

        # Normalize config_json through UseCaseConfig to ensure all fields are present
        # This preserves existing fields (like input_fields) and applies defaults for missing ones
        from ..schemas.use_case_config import UseCaseConfig

        source_config = source_uc.config_json or {}
        try:
            validated_config = UseCaseConfig(**source_config)
            # Use model_dump(exclude_unset=False) to include all fields, even defaults
            # This ensures all source fields are preserved
            normalized_config = validated_config.model_dump(exclude_unset=False)
            # Explicitly ensure input_fields is present (preserves existing or defaults to empty list)
            if "input_fields" not in normalized_config:
                normalized_config["input_fields"] = []
        except Exception as e:
            logger.warning(
                "Source use case config validation failed during clone, using as-is: %s",
                str(e),
            )
            # If validation fails, use source config as-is (backward compatibility)
            normalized_config = source_config.copy()
            # Ensure input_fields is present even in fallback case
            if "input_fields" not in normalized_config:
                normalized_config["input_fields"] = []

        # Create clone
        clone_kwargs = {
            "use_case_id": clone_data.new_use_case_id,
            "name": clone_data.new_name or f"{source_uc.name} (Copy)",
            "description": source_uc.description,
            "category": source_uc.category,
            "intent_type": source_uc.intent_type,
            "team_id": team_id,
            "version": 1,  # New version lineage
            "lifecycle_state": "draft",
            "is_active": False,
            "config_json": normalized_config,
            "metadata_json": cloned_metadata,
            "created_by_user_id": user_id,
        }
        cloned_uc = DBUseCase(**clone_kwargs)  # type: ignore

        db.add(cloned_uc)
        await db.commit()
        await db.refresh(cloned_uc)

        logger.info("Successfully cloned use case: %s", cloned_uc.use_case_id)

        return UseCaseResponse.from_orm(cloned_uc)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Error cloning use case: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clone use case",
        ) from e


# ============================================================================
# Lifecycle State Management
# ============================================================================


@router.post(
    "/{use_case_id}/transition",
    response_model=UseCaseResponse,
    dependencies=[Depends(admin_required)],
)
async def transition_use_case_state(
    use_case_id: UUID,
    transition: StateTransitionRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> UseCaseResponse:
    """
    Transition use case lifecycle state.

    State machine: draft → review → published → archived

    Requires corpus_admin for draft→review.
    Requires admin for review→published.

    Path parameter is the use case UUID (id), not the use_case_id string.
    """
    try:
        stmt = select(DBUseCase).where(DBUseCase.id == use_case_id)
        result = await db.execute(stmt)
        use_case = result.scalar_one_or_none()

        if not use_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Use case '{use_case_id}' not found",
            )

        # Define valid transitions
        valid_transitions: dict[str, list[str]] = {
            "draft": ["review"],
            "review": ["published", "draft"],  # Can reject back to draft
            "published": ["archived"],
            "archived": [],  # Terminal state
        }

        current_state = use_case.lifecycle_state
        target_state = transition.to_state

        allowed_states: list[str] = valid_transitions.get(current_state, []) or []
        if target_state not in allowed_states:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transition: {current_state} → {target_state}. Valid transitions: {valid_transitions.get(current_state, [])}",
            )

        # Check permission using RBAC V2 with full multi-role support (ADR-060)
        from ..services.rbac_v2 import can_transition_state

        user_id = UUID(current_user.user_id)
        if not await can_transition_state(user_id, use_case, target_state, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to transition use case from {current_state} to {target_state}",
            )

        logger.info(
            "Transitioning use case %s: %s → %s",
            use_case_id,
            current_state,
            target_state,
            extra={"user_id": str(current_user.user_id)},
        )

        # Update state
        use_case.lifecycle_state = target_state

        # Set timestamps and approvers
        if target_state == "review":
            # Just transitioning to review, no approval yet
            pass
        elif target_state == "published":
            use_case.published_at = datetime.now(UTC)
            use_case.published_by_user_id = user_id
            use_case.approved_at = datetime.now(UTC)
            use_case.approved_by_user_id = user_id
            use_case.is_active = True  # Auto-activate on publish
            # Clear team_id on publish (published use cases visible to all)
            use_case.team_id = None
        elif target_state == "draft":
            # Rejected back to draft
            use_case.approved_at = None
            use_case.approved_by_user_id = None

        await db.commit()
        await db.refresh(use_case)

        logger.info("Use case %s transitioned to %s", use_case_id, target_state)

        return UseCaseResponse.from_orm(use_case)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Error transitioning use case state: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to transition use case state",
        ) from e


# ============================================================================
# Version History
# ============================================================================


@router.get(
    "/{use_case_id}/versions",
    response_model=UseCaseVersionListResponse,
    dependencies=[Depends(admin_required)],
)
async def get_use_case_versions(
    use_case_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> UseCaseVersionListResponse:
    """
    Get version history for a use case.

    Returns list of config snapshots from version_history in metadata.

    Path parameter is the use case UUID (id), not the use_case_id string.
    """
    try:
        stmt = select(DBUseCase).where(DBUseCase.id == use_case_id)
        result = await db.execute(stmt)
        use_case = result.scalar_one_or_none()

        if not use_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Use case '{use_case_id}' not found",
            )

        # Get version history from metadata
        version_history = use_case.metadata_json.get("version_history", [])

        # Add current version
        current_version = {
            "version": use_case.version,
            "config_snapshot": use_case.config_json,
            "updated_at": use_case.updated_at.isoformat(),
            "updated_by": (
                str(use_case.created_by_user_id) if use_case.created_by_user_id else None
            ),
            "is_active": True,
        }
        versions = [*version_history, current_version]

        logger.info(
            "Retrieved %d versions for use case %s",
            len(versions),
            use_case_id,
            extra={"user_id": str(current_user.user_id)},
        )

        return UseCaseVersionListResponse(
            use_case_id=str(use_case.use_case_id),
            current_version=use_case.version,
            versions=versions,
            total_versions=len(versions),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving use case versions: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve version history",
        ) from e


@router.post(
    "/{use_case_id}/rollback",
    response_model=UseCaseResponse,
    dependencies=[Depends(admin_required)],
)
async def rollback_use_case_version(
    use_case_id: UUID,
    target_version: int = Query(..., description="Version number to rollback to"),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> UseCaseResponse:
    """
    Rollback use case to a previous version.

    Loads config from version history and creates new version.
    Requires admin role.

    Path parameter is the use case UUID (id), not the use_case_id string.
    """
    try:
        stmt = select(DBUseCase).where(DBUseCase.id == use_case_id)
        result = await db.execute(stmt)
        use_case = result.scalar_one_or_none()

        if not use_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Use case '{use_case_id}' not found",
            )

        # Find version in history
        version_history = use_case.metadata_json.get("version_history", [])
        target_snapshot = None

        for v in version_history:
            if v.get("version") == target_version:
                target_snapshot = v.get("config_snapshot")
                break

        if not target_snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {target_version} not found in history",
            )

        logger.info(
            "Rolling back use case %s from v%d to v%d",
            use_case_id,
            use_case.version,
            target_version,
            extra={"user_id": str(current_user.user_id)},
        )

        # Store current config in history before rollback
        version_history.append(
            {
                "version": use_case.version,
                "config_snapshot": (use_case.config_json or {}).copy(),
                "updated_at": datetime.now(UTC).isoformat(),
                "updated_by": str(current_user.user_id),
            }
        )

        # Apply rollback
        use_case.config_json = target_snapshot
        use_case.version += 1  # Rollback creates new version
        use_case.metadata_json["version_history"] = version_history
        use_case.metadata_json["last_rollback"] = {
            "from_version": use_case.version - 1,
            "to_version": target_version,
            "at": datetime.now(UTC).isoformat(),
            "by": str(current_user.user_id),
        }

        await db.commit()
        await db.refresh(use_case)

        logger.info(
            "Rolled back use case %s to version %d (new version: %d)",
            use_case_id,
            target_version,
            use_case.version,
        )

        return UseCaseResponse.from_orm(use_case)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Error rolling back use case: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rollback use case",
        ) from e


# ============================================================================
# Helper Functions
# ============================================================================


def _build_version_summary(version_data: dict[str, Any]) -> dict[str, Any]:
    """Build summary of version for list responses."""
    return {
        "version": version_data.get("version"),
        "updated_at": version_data.get("updated_at"),
        "updated_by": version_data.get("updated_by"),
        "is_active": version_data.get("is_active", False),
    }
