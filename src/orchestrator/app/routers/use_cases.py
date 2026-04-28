"""
Use Cases Router for AI Operations Platform.

This module provides API endpoints for use case management and discovery,
including the menu endpoint that returns available use cases based on RBAC.

Migrated to async SQLAlchemy per ADR-022 (Phase 5 - P5-A10).
"""

import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import get_current_user
from shared.auth.models import TokenPayload
from shared.config.schemas import OrchestratorConfig
from shared.logging_utils.fastapi import configure_logging

from ..config.runtime import build_runtime_config
from ..db.database import AsyncSessionLocal, get_async_db
from ..db.models import UseCase, UserRoleMembership
from ..dependencies.config import get_orchestrator_settings
from ..orchestrator.clients.llm_guard_client import LLMGuardClient
from ..orchestrator.clients.retrieval_client import RetrievalClient
from ..orchestrator.context import RequestContext
from ..orchestrator.controller import Orchestrator
from ..orchestrator.runner import Step, UseCaseRunner
from ..orchestrator.steps.assemble_prompt import AssemblePrompt
from ..orchestrator.steps.execute_llm import ExecuteLLM
from ..orchestrator.steps.format_response import FormatResponse
from ..orchestrator.steps.guard_validate import GuardValidate
from ..orchestrator.steps.retrieve_context import RetrieveContext
from ..schemas.intent import RequestType
from ..schemas.response import FormattedResponse
from ..schemas.use_case import (
    UseCaseExecution,
    UseCaseListItem,
    UseCaseListResponse,
)
from ..schemas.use_case_management import UseCaseResponse
from ..services.rbac import (
    user_can_access_use_case,
)
from ..services.rbac_v2 import (
    get_accessible_use_cases,
)
from ..services.tool_executor import ToolExecutor
from ..services.use_case_config_loader import invalidate_config_cache_for_use_case
from ..utils.auth import jwt_validator

# Configure logger for this module
logger = configure_logging(service_name="use_cases_router")

router = APIRouter(prefix="/api/v1/use-cases", tags=["use-cases"])


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async database dependency for API routes.

    Yields:
        AsyncSession: An async SQLAlchemy session which is automatically closed.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def _can_access_draft(
    use_case: UseCase,
    user_id: UUID,
    db: AsyncSession,
) -> bool:
    """
    Check if user can access a draft use case (Tier 3 - team isolation).

    Draft access is granted if:
    - User is the creator (created_by_user_id match), OR
    - User is in the same team (team_id match)

    Args:
        use_case: UseCase object
        user_id: User UUID
        db: Async database session

    Returns:
        True if user can access this draft, False otherwise
    """
    # Check 1: Creator access
    if use_case.created_by_user_id == user_id:
        return True

    # Check 2: Team access
    if use_case.team_id:
        # Get user's team memberships (roles starting with "team:")
        result = await db.execute(
            select(UserRoleMembership.role).where(
                and_(
                    UserRoleMembership.user_id == user_id,
                    UserRoleMembership.role.like("team:%"),
                )
            )
        )
        user_teams = [row.role for row in result.all()]

        if use_case.team_id in user_teams:
            return True

    return False


@router.get("/available", response_model=UseCaseListResponse)
async def get_available_use_cases(
    category: str = Query(None, description="Filter by category"),
    intent_type: str = Query(None, description="Filter by intent type"),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> UseCaseListResponse:
    """
    Get available use cases for the current user based on RBAC.

    This endpoint returns a filtered list of use cases that the current user
    has access to, based on their role assignments and use case assignments.

    Args:
        category: Optional category filter
        intent_type: Optional intent type filter
        db: Async database session
        current_user: Current authenticated user

    Returns:
        UseCaseListResponse: List of available use cases with total count

    Raises:
        HTTPException: If user is not authenticated or database error occurs
    """
    try:
        logger.info(
            "Fetching available use cases for user %s",
            current_user.user_id,
            extra={
                "user_id": str(current_user.user_id),
                "category_filter": category,
                "intent_type_filter": intent_type,
            },
        )

        # Get accessible use cases from RBAC service (async)
        # This returns a list, not a query
        all_use_cases = await get_accessible_use_cases(UUID(current_user.user_id), db)

        # Apply filters if provided (in memory)
        filtered_use_cases = []
        for uc in all_use_cases:
            # Only show active and published use cases in the menu
            if not uc.is_active or uc.lifecycle_state != "published":
                continue

            if category and uc.category != category:
                continue

            if intent_type and uc.intent_type != intent_type:
                continue

            filtered_use_cases.append(uc)

        # Order by category and name
        filtered_use_cases.sort(key=lambda x: (x.category or "", x.name))

        # Convert to response model
        items = []
        for uc in filtered_use_cases:
            # Convert intent_type string to RequestType enum
            try:
                intent_type_enum = RequestType(uc.intent_type)
            except ValueError:
                # Log warning but continue - use the string value
                logger.warning(
                    "Unknown intent_type %s for use case %s, using as-is",
                    uc.intent_type,
                    uc.id,
                )
                # For now, default to QUERY if invalid
                intent_type_enum = RequestType.QUERY

            items.append(
                UseCaseListItem(
                    id=uc.id,
                    name=uc.name,
                    description=uc.description,
                    category=uc.category,
                    intent_type=intent_type_enum,
                    is_active=uc.is_active,
                    lifecycle_state=uc.lifecycle_state,
                    version=str(uc.version) if uc.version else "1.0",
                    updated_at=uc.updated_at,
                    icon=None,  # Optional field - not stored in database
                    tags=[],  # Optional field - not stored in database
                )
            )

        logger.info("Found %d available use cases", len(items))

        return UseCaseListResponse(use_cases=items, total=len(items))

    except Exception as e:
        logger.error("Error fetching available use cases: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch use cases: {e!s}") from e


@router.get("/{use_case_id}", response_model=UseCaseResponse)
async def get_use_case_details(
    use_case_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> UseCaseResponse:
    """
    Get use case details by UUID.

    Returns complete use case information including configuration and metadata.
    Access is controlled by RBAC - user must have access to the use case.

    Args:
        use_case_id: The use case UUID (primary key, per ADR-037)
        db: Async database session
        current_user: Current authenticated user

    Returns:
        UseCaseResponse: Complete use case details

    Raises:
        HTTPException: If use case not found, not accessible, or user lacks access
    """
    try:
        logger.info(
            "Fetching use case details for %s",
            use_case_id,
            extra={
                "user_id": str(current_user.user_id),
                "use_case_id": str(use_case_id),
            },
        )

        # Load use case from database by UUID (ADR-037: UUID Primary Keys)
        # Allow both published and draft (draft access checked below)
        result = await db.execute(select(UseCase).where(UseCase.id == use_case_id))
        use_case = result.scalar_one_or_none()

        if not use_case:
            logger.warning("Use case %s not found", use_case_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Use case not found",
            )

        # Check is_active for non-draft use cases
        # Drafts are created with is_active=False (normal state)
        # Published/review/archived require is_active=True
        if use_case.lifecycle_state != "draft" and not use_case.is_active:
            logger.warning(
                "Use case %s is inactive (state=%s)",
                use_case_id,
                use_case.lifecycle_state,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Use case not found",
            )

        # Check access based on lifecycle state (Tier 3 team isolation for drafts)
        user_id = UUID(current_user.user_id)

        if use_case.lifecycle_state == "draft":
            # Draft: Check creator or team access
            if not await _can_access_draft(use_case, user_id, db):
                logger.warning(
                    "User %s denied access to draft use case %s (not creator/team)",
                    current_user.user_id,
                    use_case_id,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this draft use case",
                )
        else:
            # Published/review/archived: Use RBAC (ADR-041)
            if not await user_can_access_use_case(user_id, use_case.id, db):
                logger.warning(
                    "User %s lacks access to use case %s (RBAC denied)",
                    current_user.user_id,
                    use_case_id,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this use case",
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


@router.get("/{use_case_id}/config")
async def get_use_case_config(
    use_case_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get use case configuration by UUID.

    Returns the complete configuration for a use case, including UI input field
    definitions for dynamic form generation. Access is controlled by RBAC.

    Args:
        use_case_id: The use case UUID (primary key, per ADR-037)
        db: Async database session
        current_user: Current authenticated user

    Returns:
        dict: Use case configuration with metadata:
            - use_case_id: String identifier
            - name: Display name
            - intent_type: Intent classification
            - config: Complete configuration (config_json from database)

    Raises:
        HTTPException: If use case not found, not accessible, or user lacks access
    """
    try:
        logger.info(
            "Fetching use case config for %s",
            use_case_id,
            extra={
                "user_id": str(current_user.user_id),
                "use_case_id": str(use_case_id),
            },
        )

        # Load use case from database by UUID (ADR-037: UUID Primary Keys)
        # Allow both published and draft (draft access checked below)
        result = await db.execute(select(UseCase).where(UseCase.id == use_case_id))
        use_case = result.scalar_one_or_none()

        if not use_case:
            logger.warning("Use case %s not found", use_case_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Use case not found",
            )

        # Check is_active for non-draft use cases
        # Drafts are created with is_active=False (normal state)
        # Published/review/archived require is_active=True
        if use_case.lifecycle_state != "draft" and not use_case.is_active:
            logger.warning(
                "Use case %s is inactive (state=%s)",
                use_case_id,
                use_case.lifecycle_state,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Use case not found",
            )

        # Check access based on lifecycle state (Tier 3 team isolation for drafts)
        user_id = UUID(current_user.user_id)

        if use_case.lifecycle_state == "draft":
            # Draft: Check creator or team access
            if not await _can_access_draft(use_case, user_id, db):
                logger.warning(
                    "User %s denied access to draft use case %s (not creator/team)",
                    current_user.user_id,
                    use_case_id,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this draft use case",
                )
        else:
            # Published/review/archived: Use RBAC (ADR-041)
            if not await user_can_access_use_case(user_id, use_case.id, db):
                logger.warning(
                    "User %s lacks access to use case %s (RBAC denied)",
                    current_user.user_id,
                    use_case_id,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this use case",
                )

        # Return config in the format expected by frontend
        # Based on docs/api/use-case-execution.md format
        config_response = {
            "use_case_id": use_case.use_case_id,
            "name": use_case.name,
            "description": use_case.description or "",
            "category": use_case.category or "",
            "intent_type": use_case.intent_type,
            "config": use_case.config_json,
        }

        logger.info(
            "Retrieved use case config for %s",
            use_case_id,
            extra={"user_id": str(current_user.user_id)},
        )

        return config_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving use case config: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve use case configuration",
        ) from e


@router.post("/{use_case_id}/execute", response_model=FormattedResponse)
async def execute_use_case(
    use_case_id: UUID,
    execution: UseCaseExecution,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
    raw_token_creds: HTTPAuthorizationCredentials | None = Depends(jwt_validator.security),
    settings: OrchestratorConfig = Depends(get_orchestrator_settings),
) -> FormattedResponse:
    """
    Execute a use case with provided inputs.

    This endpoint executes a use case by:
    1. Loading the use case configuration from database
    2. Validating user has access to the use case
    3. Constructing a query from the input fields
    4. Calling the orchestrator to process the query with RAG
    5. Saving the execution to query_history
    6. Returning the formatted response with metrics and sources

    Args:
        use_case_id: The use case UUID (primary key)
        execution: The execution request with inputs and optional overrides
        db: Async database session
        current_user: Current authenticated user

    Returns:
        FormattedResponse: Execution results with response, sources, and metrics

    Raises:
        HTTPException: If use case not found, user lacks access, or execution fails
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())

    try:
        logger.info(
            "Executing use case %s",
            use_case_id,
            extra={
                "user_id": str(current_user.user_id),
                "use_case_id": str(use_case_id),
                "run_id": request_id,
            },
        )

        # Step 1: Load use case from database by UUID (ADR-037: UUID Primary Keys)
        # Allow both published and draft (draft access checked below)
        result = await db.execute(select(UseCase).where(UseCase.id == use_case_id))
        use_case = result.scalar_one_or_none()

        if not use_case:
            logger.warning("Use case %s not found", use_case_id)
            raise HTTPException(status_code=404, detail="Use case not found")

        # Step 2: Check access based on lifecycle state (Tier 3 team isolation for drafts)
        user_id = UUID(current_user.user_id)

        if use_case.lifecycle_state == "draft":
            # Draft: Check creator or team access
            if not await _can_access_draft(use_case, user_id, db):
                logger.warning(
                    "User %s denied access to draft use case %s (not creator/team)",
                    current_user.user_id,
                    use_case_id,
                )
                raise HTTPException(
                    status_code=403,
                    detail="Access denied to this draft use case",
                )
        else:
            # Published/review/archived: Use RBAC (ADR-041)
            if not await user_can_access_use_case(user_id, use_case.id, db):
                logger.warning(
                    "User %s lacks access to use case %s (RBAC denied)",
                    current_user.user_id,
                    use_case_id,
                )
                raise HTTPException(status_code=403, detail="Access denied to this use case")

        # Step 3: Validate required inputs (query text built after config load)
        config = use_case.config_json or {}
        input_fields = config.get("input_fields", [])
        for field in input_fields:
            field_name = field.get("name")
            if field.get("required", False) and field_name not in execution.inputs:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required input field: {field_name}",
                )

        # Step 4: Initialize orchestrator and process query
        runtime_config = build_runtime_config(settings)

        # Extract user's JWT token for Gateway authentication
        raw_token = raw_token_creds.credentials if raw_token_creds else None

        # Create LLMRouter with JWT token and intent model defaults
        from ..orchestrator.llm_router import LLMRouter
        from ..orchestrator.model_selection import (
            ModelSelector,
            load_intent_defaults_from_async_db,
        )

        if raw_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing JWT token"
            )

        # Load intent model defaults from db for deterministic model selection (ADR-069)
        try:
            intent_defaults, intent_temperatures = await load_intent_defaults_from_async_db(db)
        except Exception as e:
            logger.error(
                "Failed to load intent model defaults: %s",
                e,
                extra={"use_case_id": str(use_case_id)},
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Intent model configuration unavailable. Ensure migration 037 has been run "
                    "and intent_model_defaults table exists. Error: "
                )
                + str(e),
            ) from e
        model_selector = ModelSelector(
            preloaded_defaults=intent_defaults,
            preloaded_temperatures=intent_temperatures,
        )

        llm_router = LLMRouter(
            user_jwt_token=raw_token,
            gateway_url=settings.inference_gateway_url,
            request_timeout_seconds=settings.request_timeout_seconds,
            model_selector=model_selector,
        )

        # All services now use async_db
        orchestrator = Orchestrator(async_db=db, config=runtime_config, llm_router=llm_router)

        # Instantiate ToolExecutor with async session (converted in Phase 3)
        tool_executor = ToolExecutor(db=db)

        logger.info(
            "Orchestrator created with Inference Gateway",
            extra={"use_case_id": str(use_case_id), "user_id": str(current_user.user_id)},
        )

        # Get request_type from use case intent_type
        try:
            request_type_param = RequestType(use_case.intent_type)
        except ValueError:
            # Default to QUERY if intent_type is not recognized
            request_type_param = RequestType.QUERY
            logger.warning(
                "Unknown intent_type %s for use case %s, defaulting to QUERY",
                use_case.intent_type,
                use_case_id,
            )

        # Load use case config and prompts from orchestrator (always from DB so
        # model and other edits are picked up even after save from another tab/process)
        invalidate_config_cache_for_use_case(str(use_case_id))
        use_case_cfg = await orchestrator.config_loader.load_config(str(use_case_id))
        use_case_prompts = await orchestrator.load_use_case_prompts(str(use_case_id))

        # ADR-069: Fail early if no model will be available (no pin, no intent default)
        has_model_pin = bool(use_case_cfg and use_case_cfg.models and use_case_cfg.models.llm)
        intent_code = use_case.intent_type or "QUERY"
        has_intent_default = intent_code in intent_defaults
        if not has_model_pin and not has_intent_default:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "No model configured for this use case. Either pin a model in the use case "
                    "Model Selection section, or configure intent defaults at "
                    "Development > Intent Models (/dev/intent-models)."
                ),
            )

        if use_case_cfg and use_case_cfg.models:
            logger.info(
                "Use case config loaded for execution, model=%s",
                use_case_cfg.models.llm or "(none; router selects by intent)",
                extra={"use_case_id": str(use_case_id), "run_id": request_id},
            )

        # Build query text: template if configured, else legacy concatenation
        from ..orchestrator.template_renderer import render_user_prompt_template

        if (
            use_case_cfg
            and use_case_cfg.user_prompt_template
            and (use_case_cfg.user_prompt_template.template or "").strip()
        ):
            try:
                query_text = render_user_prompt_template(
                    template=use_case_cfg.user_prompt_template.template,
                    inputs=execution.inputs,
                    fallback_mode=use_case_cfg.user_prompt_template.fallback_mode,
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e
        else:
            query_parts = []
            for field_name, field_value in execution.inputs.items():
                query_parts.append(f"{field_name}: {field_value}")
            query_text = "\n".join(query_parts)

        logger.info(
            "Constructed query from inputs",
            extra={
                "run_id": request_id,
                "query_length": len(query_text),
                "input_count": len(execution.inputs),
            },
        )

        # Build RequestContext for pipeline execution
        ctx = RequestContext(
            req_id=request_id,
            user_id=str(current_user.user_id),
            user_uuid=UUID(current_user.user_id),
            user_role=(
                current_user.roles[0] if current_user.roles else "user"
            ),  # Deprecated, kept for backward compatibility
            user_roles=(
                current_user.roles if current_user.roles else ["user"]
            ),  # Multi-role support per ADR-060
            request_type=request_type_param,
            query_original=query_text,
            query_sanitized=query_text,
            intent=None,
            use_case_id=use_case_id,
            use_case=use_case_cfg,
            prompts=use_case_prompts,
            thread_id=None,
            discussion_id=None,
            history_messages=[],
            sources=[],
            rag_enabled=False,
            llm_request=None,
            llm_response=None,
            formatted=None,
        )

        # Store execution metadata in context for later use
        ctx.extras["use_case_name"] = use_case.name
        ctx.extras["inputs"] = execution.inputs
        if execution.overrides:
            ctx.extras["overrides"] = execution.overrides

        # Compose HTTP client adapters
        guard_client = LLMGuardClient(base_url=orchestrator.llm_guard_url)
        retrieval_client = RetrievalClient(
            base_url=orchestrator.config.get(
                "retrieval_svc_url", "http://corpus-service:8001/api/v1"
            )
        )

        # Compose pipeline steps for use case execution
        steps: list[Step] = [
            GuardValidate(
                guard=guard_client,
                policy_engine=None,
                token=raw_token,
            ),
            RetrieveContext(
                retrieval=retrieval_client,
                headers=({"Authorization": f"Bearer {raw_token}"} if raw_token else None),
                use_case_id=str(use_case_id),
            ),
            AssemblePrompt(assembler=orchestrator.prompt_assembler),
            ExecuteLLM(
                router=orchestrator.llm_router,
                streaming=False,
                tool_executor=tool_executor,
            ),
            FormatResponse(
                formatter=orchestrator.response_formatter,
                token_tracker=orchestrator.token_tracker,
            ),
        ]

        # Create runner with telemetry integration
        runner = UseCaseRunner(steps=steps, telemetry=orchestrator.telemetry_integration)

        # Execute pipeline (returns FormattedResponse from ctx.formatted)
        formatted = await runner.run(ctx)

        # Validate result
        if not formatted:
            raise HTTPException(
                status_code=500,
                detail="Pipeline completed but no formatted response generated",
            )

        # Step 5: Return the formatted response
        # Note: History saving will be handled separately if needed
        execution_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "Use case execution completed successfully",
            extra={
                "use_case_id": str(use_case_id),
                "execution_time_ms": execution_time_ms,
                "run_id": request_id,
            },
        )

        return cast("FormattedResponse", formatted)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error executing use case: %s",
            str(e),
            extra={
                "user_id": str(current_user.user_id),
                "use_case_id": str(use_case_id),
                "run_id": request_id,
                "error_message": str(e),
            },
        )

        # Note: Error history may be saved by orchestrator if execution started
        raise HTTPException(status_code=500, detail=f"Failed to execute use case: {e!s}") from e
