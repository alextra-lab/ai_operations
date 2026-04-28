"""
Query History Router for AI Operations Platform.

This module provides API endpoints for query history management, including:
- List query history with filtering and pagination
- Get single query history record
- Delete query history record
- Fork queries for reuse
- Manage conversation threads

All endpoints enforce RLS policies for user isolation.

P5-A13: Migrated to async database patterns (Nov 2025).
"""

import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import get_current_user
from shared.auth.models import TokenPayload
from shared.logging_utils.fastapi import configure_logging

from ..db.database import ENABLE_TRANSCRIPT_STORAGE, AsyncSessionLocal
from ..schemas.query_history import (
    ForkQueryRequest,
    ForkQueryResponse,
    QueryHistoryCreate,
    QueryHistoryListResponse,
    QueryHistoryResponse,
    QueryHistoryUpdate,
    ThreadCreate,
    ThreadListResponse,
    ThreadMessageResponse,
    ThreadResponse,
    ThreadUpdate,
)
from ..services.async_history_service import AsyncHistoryService
from ..utils.auth import jwt_validator

# Configure logger for this module
logger = configure_logging(service_name="query_history_router")

router = APIRouter(prefix="/api/v1/query-history", tags=["query-history"])


# =============================================================================
# PII Storage Guard (ADR-030: Stateless Architecture Enforcement)
# =============================================================================


def require_transcript_storage() -> None:
    """
    Guard for endpoints that require transcript storage enabled.

    Raises HTTPException 501 if ENABLE_TRANSCRIPT_STORAGE is false (Core Edition).
    This enforces the stateless architecture defined in ADR-030.
    """
    if not ENABLE_TRANSCRIPT_STORAGE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "error": "transcript_storage_disabled",
                "message": (
                    "History write operations are disabled in Core Edition (ADR-030). "
                    "History is recorded internally by the orchestrator pipeline. "
                    "Set ENABLE_TRANSCRIPT_STORAGE=true for Plus Edition."
                ),
                "documentation": "https://docs.aio.ai/adrs/ADR-030",
            },
        )


# =============================================================================
# Database Dependencies (P5-A13: Async Migration)
# =============================================================================


async def get_async_db_with_rls(
    request: Request,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Async database dependency for API routes with RLS support.

    Sets PostgreSQL session variables for Row-Level Security policies.

    Yields:
        AsyncSession: An async SQLAlchemy session which is automatically closed.
    """
    async with AsyncSessionLocal() as db:
        try:
            # Extract and set RLS session variables from JWT token
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                try:
                    token_payload = jwt_validator.verify_token(token)
                    if token_payload:
                        user_id = token_payload.get("user_id") or token_payload.get("sub")
                        # Get role from token (singular "role", not "roles")
                        role = token_payload.get("role", "")
                    else:
                        user_id = None
                        role = ""

                    # Lookup all roles from database
                    from sqlalchemy import select

                    from ..db.models import UserRoleMembership

                    role_stmt = select(UserRoleMembership).where(
                        UserRoleMembership.user_id == user_id
                    )
                    role_result = await db.execute(role_stmt)
                    role_records = role_result.scalars().all()
                    roles = (
                        [r.role for r in role_records] if role_records else [role] if role else []
                    )

                    # Format roles as PostgreSQL array
                    roles_str = ",".join(str(r) for r in roles) if roles else ""

                    # Set RLS session variables using text() for raw SQL
                    await db.execute(text(f"SET LOCAL aio.user_id = '{user_id}'"))
                    await db.execute(text(f"SET LOCAL aio.user_roles = '{{{roles_str}}}'"))

                    logger.info(
                        "Set RLS session variables",
                        extra={
                            "user_id": str(user_id),
                            "roles": roles,
                        },
                    )
                except Exception as exc:
                    logger.warning("Failed to set RLS session variables", extra={"error": str(exc)})

            yield db
        finally:
            await db.close()


async def get_async_history_service(
    db: AsyncSession = Depends(get_async_db_with_rls),
) -> AsyncHistoryService:
    """
    Create and return an AsyncHistoryService instance.

    Args:
        db: Async database session from dependency

    Returns:
        AsyncHistoryService: Configured async history service
    """
    return AsyncHistoryService(db_session=db)


# =============================================================================
# Query History List Endpoint
# =============================================================================


@router.get("", response_model=QueryHistoryListResponse)
async def list_query_history(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    use_case_id: uuid.UUID | None = Query(None, description="Filter by use case UUID"),
    intent_type: str | None = Query(None, description="Filter by intent type"),
    response_status: str | None = Query(None, description="Filter by response status"),
    search_query: str | None = Query(None, description="Full-text search on query text"),
    history_service: AsyncHistoryService = Depends(get_async_history_service),
    current_user: TokenPayload = Depends(get_current_user),
) -> QueryHistoryListResponse:
    """
    List query history for the current user with filtering and pagination.

    RLS policies automatically filter to current user's records.

    Args:
        limit: Maximum number of records to return (1-100)
        offset: Number of records to skip for pagination
        use_case_id: Optional filter by use case UUID
        intent_type: Optional filter by intent type
        response_status: Optional filter by response status
        search_query: Optional full-text search on query text
        history_service: Async history service dependency
        current_user: Current authenticated user

    Returns:
        QueryHistoryListResponse: Paginated list of query history records

    Raises:
        HTTPException: If database error occurs
    """
    try:
        logger.info(
            "Listing query history",
            extra={
                "user_id": str(current_user.user_id),
                "limit": limit,
                "offset": offset,
                "filters": {
                    "use_case_id": str(use_case_id) if use_case_id else None,
                    "intent_type": intent_type,
                    "response_status": response_status,
                    "search_query": search_query,
                },
            },
        )

        # Get history list with filters
        history_list, total_count = await history_service.list_history(
            limit=limit,
            offset=offset,
            use_case_id=use_case_id,
            intent_type=intent_type,
            response_status=response_status,
            search_query=search_query,
        )

        # Convert to response format
        items = [QueryHistoryResponse.model_validate(h) for h in history_list]

        has_more = (offset + len(items)) < total_count

        return QueryHistoryListResponse(
            items=items,
            total=total_count,
            limit=limit,
            offset=offset,
            has_more=has_more,
        )

    except Exception as e:
        logger.error(
            "Error listing query history",
            extra={"user_id": str(current_user.user_id), "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve query history",
        ) from e


# ============================================================================
# Thread Management Endpoints
# NOTE: These must come BEFORE /{history_id} to avoid routing conflicts
# ============================================================================


@router.post("/threads", response_model=ThreadResponse)
async def create_thread(
    request: ThreadCreate,
    history_service: AsyncHistoryService = Depends(get_async_history_service),
    current_user: TokenPayload = Depends(get_current_user),
) -> ThreadResponse:
    """
    Create a new conversation thread (Plus Edition only).

    Args:
        request: Thread creation request
        history_service: Async history service dependency
        current_user: Current authenticated user

    Returns:
        ThreadResponse: The created thread

    Raises:
        HTTPException: 501 if transcript storage disabled, 500 if database error
    """
    # ADR-030: Block PII storage in Core Edition
    require_transcript_storage()

    try:
        logger.info(
            "Creating conversation thread",
            extra={
                "user_id": str(current_user.user_id),
                "title": request.title,
            },
        )

        thread = await history_service.create_thread(
            user_id=uuid.UUID(current_user.user_id),
            title=request.title,
            description=request.description,
            center_id=request.center_id,
            discussion_id=request.discussion_id,
            use_case_id=request.use_case_id,
            use_case_name=request.use_case_name,
            source=request.source,
            metadata=request.metadata,
        )

        logger.info(
            "Thread created successfully",
            extra={
                "user_id": str(current_user.user_id),
                "thread_id": str(thread.thread_id),
            },
        )

        return ThreadResponse.model_validate(thread)

    except Exception as e:
        logger.error(
            "Error creating thread",
            extra={
                "user_id": str(current_user.user_id),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation thread",
        ) from e


@router.get("/threads", response_model=ThreadListResponse)
async def list_threads(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    discussion_id: str | None = Query(None),
    use_case_id: uuid.UUID | None = Query(None),
    is_active: bool | None = Query(True),
    history_service: AsyncHistoryService = Depends(get_async_history_service),
    current_user: TokenPayload = Depends(get_current_user),
) -> ThreadListResponse:
    """
    List conversation threads for the current user.

    Args:
        limit: Maximum number of threads to return
        offset: Number of threads to skip
        discussion_id: Optional filter by discussion ID
        use_case_id: Optional filter by use case UUID
        is_active: Optional filter by active status
        history_service: Async history service dependency
        current_user: Current authenticated user

    Returns:
        ThreadListResponse: Paginated list of threads
    """
    try:
        logger.info(
            "Listing threads",
            extra={
                "user_id": str(current_user.user_id),
                "discussion_id": discussion_id,
                "limit": limit,
            },
        )

        threads, total = await history_service.list_threads(
            limit=limit,
            offset=offset,
            discussion_id=discussion_id,
            use_case_id=use_case_id,
            is_active=is_active,
        )

        return ThreadListResponse(
            items=[ThreadResponse.model_validate(t) for t in threads],
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(threads)) < total,
        )

    except Exception as e:
        logger.error(
            "Error listing threads",
            extra={
                "user_id": str(current_user.user_id),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list threads",
        ) from e


@router.get("/threads/{thread_id}/messages", response_model=list[ThreadMessageResponse])
async def get_thread_messages(
    thread_id: uuid.UUID,
    history_service: AsyncHistoryService = Depends(get_async_history_service),
    current_user: TokenPayload = Depends(get_current_user),
) -> list[ThreadMessageResponse]:
    """
    Get all messages in a conversation thread.

    Args:
        thread_id: UUID of the thread
        history_service: Async history service dependency
        current_user: Current authenticated user

    Returns:
        List of thread messages

    Raises:
        HTTPException: If thread not found or access fails
    """
    try:
        logger.info(
            "Fetching thread messages",
            extra={
                "user_id": str(current_user.user_id),
                "thread_id": str(thread_id),
            },
        )

        # First, get the thread to verify access
        thread = await history_service.get_thread(thread_id)
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found or not accessible",
            )

        # Get messages using internal thread.id
        messages = await history_service.get_thread_messages(thread.id)

        return [ThreadMessageResponse.model_validate(m) for m in messages]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error fetching thread messages",
            extra={
                "user_id": str(current_user.user_id),
                "thread_id": str(thread_id),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve thread messages",
        ) from e


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: uuid.UUID,
    history_service: AsyncHistoryService = Depends(get_async_history_service),
    current_user: TokenPayload = Depends(get_current_user),
) -> ThreadResponse:
    """
    Get a conversation thread by ID.

    Args:
        thread_id: UUID of the thread
        history_service: Async history service dependency
        current_user: Current authenticated user

    Returns:
        ThreadResponse: The conversation thread

    Raises:
        HTTPException: If thread not found or not accessible
    """
    try:
        logger.info(
            "Fetching conversation thread",
            extra={
                "user_id": str(current_user.user_id),
                "thread_id": str(thread_id),
            },
        )

        thread = await history_service.get_thread(thread_id)

        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found or not accessible",
            )

        return ThreadResponse.model_validate(thread)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error fetching thread",
            extra={
                "user_id": str(current_user.user_id),
                "thread_id": str(thread_id),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation thread",
        ) from e


@router.patch("/threads/{thread_id}", response_model=ThreadResponse)
async def update_thread(
    thread_id: uuid.UUID,
    request: ThreadUpdate,
    history_service: AsyncHistoryService = Depends(get_async_history_service),
    current_user: TokenPayload = Depends(get_current_user),
) -> ThreadResponse:
    """
    Update thread metadata (Plus Edition only).

    Args:
        thread_id: UUID of the thread to update
        request: Thread update data
        history_service: Async history service dependency
        current_user: Current authenticated user

    Returns:
        ThreadResponse: Updated thread

    Raises:
        HTTPException: 501 if transcript storage disabled, 404/500 otherwise
    """
    # ADR-030: Block PII storage in Core Edition
    require_transcript_storage()

    try:
        logger.info(
            "Updating thread",
            extra={
                "user_id": str(current_user.user_id),
                "thread_id": str(thread_id),
            },
        )

        thread = await history_service.update_thread(
            thread_id=thread_id,
            title=request.title,
            description=request.description,
            is_active=request.is_active,
            discussion_id=request.discussion_id,
            metadata=request.metadata,
        )

        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found or not accessible",
            )

        return ThreadResponse.model_validate(thread)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error updating thread",
            extra={
                "user_id": str(current_user.user_id),
                "thread_id": str(thread_id),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update thread",
        ) from e


@router.delete("/threads/{thread_id}")
async def delete_thread(
    thread_id: uuid.UUID,
    archive: bool = Query(True, description="Archive instead of permanently deleting"),
    history_service: AsyncHistoryService = Depends(get_async_history_service),
    current_user: TokenPayload = Depends(get_current_user),
) -> dict[str, str]:
    """
    Delete or archive a conversation thread (Plus Edition only).

    Args:
        thread_id: UUID of the thread to delete
        archive: If True, archive instead of deleting
        history_service: Async history service dependency
        current_user: Current authenticated user

    Returns:
        Status message

    Raises:
        HTTPException: 501 if transcript storage disabled, 404/500 otherwise
    """
    # ADR-030: Block PII storage in Core Edition
    require_transcript_storage()

    try:
        logger.info(
            "Deleting thread",
            extra={
                "user_id": str(current_user.user_id),
                "thread_id": str(thread_id),
                "archive": archive,
            },
        )

        success = await history_service.delete_thread(thread_id=thread_id, archive=archive)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found or not accessible",
            )

        return {"status": "archived" if archive else "deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error deleting thread",
            extra={
                "user_id": str(current_user.user_id),
                "thread_id": str(thread_id),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete thread",
        ) from e


# ============================================================================
# Query History Endpoints
# NOTE: Keep generic /{history_id} route AFTER specific /threads routes
# ============================================================================


@router.get("/{history_id}", response_model=QueryHistoryResponse)
async def get_query_history(
    history_id: uuid.UUID,
    history_service: AsyncHistoryService = Depends(get_async_history_service),
    current_user: TokenPayload = Depends(get_current_user),
) -> QueryHistoryResponse:
    """
    Get a single query history record by ID.

    RLS policies ensure users can only access their own records.

    Args:
        history_id: UUID of the history record
        history_service: Async history service dependency
        current_user: Current authenticated user

    Returns:
        QueryHistoryResponse: The query history record

    Raises:
        HTTPException: If record not found or not accessible
    """
    try:
        logger.info(
            "Fetching query history",
            extra={
                "user_id": str(current_user.user_id),
                "history_id": str(history_id),
            },
        )

        history = await history_service.get_history(history_id)

        if not history:
            logger.warning(
                "Query history not found or not accessible",
                extra={
                    "user_id": str(current_user.user_id),
                    "history_id": str(history_id),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Query history not found or not accessible",
            )

        return QueryHistoryResponse.model_validate(history)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error fetching query history",
            extra={
                "user_id": str(current_user.user_id),
                "history_id": str(history_id),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve query history",
        ) from e


@router.delete("/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_query_history(
    history_id: uuid.UUID,
    history_service: AsyncHistoryService = Depends(get_async_history_service),
    current_user: TokenPayload = Depends(get_current_user),
) -> None:
    """
    Delete a query history record by ID (Plus Edition only).

    RLS policies ensure users can only delete their own records.

    Args:
        history_id: UUID of the history record to delete
        history_service: Async history service dependency
        current_user: Current authenticated user

    Returns:
        None (204 No Content on success)

    Raises:
        HTTPException: 501 if transcript storage disabled, 404/500 otherwise
    """
    # ADR-030: Block PII storage in Core Edition
    require_transcript_storage()

    try:
        logger.info(
            "Deleting query history",
            extra={
                "user_id": str(current_user.user_id),
                "history_id": str(history_id),
            },
        )

        deleted = await history_service.delete_history(history_id)

        if not deleted:
            logger.warning(
                "Query history not found or not accessible for deletion",
                extra={
                    "user_id": str(current_user.user_id),
                    "history_id": str(history_id),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Query history not found or not accessible",
            )

        logger.info(
            "Query history deleted successfully",
            extra={
                "user_id": str(current_user.user_id),
                "history_id": str(history_id),
            },
        )

        return

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error deleting query history",
            extra={
                "user_id": str(current_user.user_id),
                "history_id": str(history_id),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete query history",
        ) from e


@router.patch("/{history_id}", response_model=QueryHistoryResponse)
async def update_query_history(
    history_id: uuid.UUID,
    update_data: QueryHistoryUpdate,
    history_service: AsyncHistoryService = Depends(get_async_history_service),
    current_user: TokenPayload = Depends(get_current_user),
) -> QueryHistoryResponse:
    """
    Update a query history record by ID (Plus Edition only).

    RLS policies ensure users can only update their own records.

    Args:
        history_id: UUID of the history record to update
        update_data: Query history update data
        history_service: Async history service dependency
        current_user: Current authenticated user

    Returns:
        QueryHistoryResponse: The updated query history record

    Raises:
        HTTPException: 501 if transcript storage disabled, 404/500 otherwise
    """
    # ADR-030: Block PII storage in Core Edition
    require_transcript_storage()

    try:
        logger.info(
            "Updating query history",
            extra={
                "user_id": str(current_user.user_id),
                "history_id": str(history_id),
            },
        )

        # Convert Pydantic model to dict, excluding unset fields
        update_dict = update_data.model_dump(exclude_unset=True)

        history = await history_service.update_history(history_id, update_dict)

        if not history:
            logger.warning(
                "Query history not found or not accessible for update",
                extra={
                    "user_id": str(current_user.user_id),
                    "history_id": str(history_id),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Query history not found or not accessible",
            )

        logger.info(
            "Query history updated successfully",
            extra={
                "user_id": str(current_user.user_id),
                "history_id": str(history_id),
            },
        )

        return QueryHistoryResponse.model_validate(history)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error updating query history",
            extra={
                "user_id": str(current_user.user_id),
                "history_id": str(history_id),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update query history",
        ) from e


@router.post("", response_model=QueryHistoryResponse, status_code=201)
async def create_query_history(
    history_data: QueryHistoryCreate,
    history_service: AsyncHistoryService = Depends(get_async_history_service),
    current_user: TokenPayload = Depends(get_current_user),
) -> QueryHistoryResponse:
    """
    Create new query history record (Plus Edition only).

    Args:
        history_data: Query history creation data
        history_service: Async history service dependency
        current_user: Current authenticated user

    Returns:
        QueryHistoryResponse: The created query history record

    Raises:
        HTTPException: 501 if transcript storage disabled, 500 if database error
    """
    # ADR-030: Block PII storage in Core Edition
    if not ENABLE_TRANSCRIPT_STORAGE:
        logger.warning(
            "Blocked history write attempt (Core Edition)",
            extra={
                "user_id": str(current_user.user_id),
                "has_query_text": bool(history_data.query_text),
                "has_response_text": bool(getattr(history_data, "response_text", None)),
                "endpoint": "POST /api/v1/query-history",
            },
        )
        require_transcript_storage()

    try:
        logger.info(
            "Creating query history",
            extra={
                "user_id": str(current_user.user_id),
                "run_id": history_data.run_id,
                "intent_type": history_data.intent_type,
            },
        )

        history = await history_service.create_history(
            user_id=uuid.UUID(current_user.user_id), history_data=history_data
        )

        logger.info(
            "Query history created successfully",
            extra={
                "user_id": str(current_user.user_id),
                "history_id": str(history.id),
                "run_id": history_data.run_id,
            },
        )

        return QueryHistoryResponse.model_validate(history)

    except Exception as e:
        logger.error(
            "Error creating query history",
            extra={
                "user_id": str(current_user.user_id),
                "run_id": history_data.run_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create query history",
        ) from e


@router.post("/fork", response_model=ForkQueryResponse)
async def fork_query(
    request: ForkQueryRequest,
    history_service: AsyncHistoryService = Depends(get_async_history_service),
    current_user: TokenPayload = Depends(get_current_user),
) -> ForkQueryResponse:
    """
    Fork a query by creating a copy with parent link (Plus Edition only).

    This creates a new history record with:
    - Same query_text and query_params
    - Same use_case_id and intent_type
    - Parent link to source query
    - New run_id and new user
    - Status set to 'pending'

    Args:
        request: Fork query request with source_query_id
        history_service: Async history service dependency
        current_user: Current authenticated user

    Returns:
        ForkQueryResponse: The newly created forked query

    Raises:
        HTTPException: 501 if transcript storage disabled, 404/500 otherwise
    """
    # ADR-030: Block PII storage in Core Edition
    require_transcript_storage()

    try:
        logger.info(
            "Forking query",
            extra={
                "user_id": str(current_user.user_id),
                "source_query_id": str(request.source_query_id),
            },
        )

        forked_query = await history_service.fork_query(
            source_query_id=request.source_query_id,
            new_user_id=uuid.UUID(current_user.user_id),
        )

        logger.info(
            "Query forked successfully",
            extra={
                "user_id": str(current_user.user_id),
                "source_query_id": str(request.source_query_id),
                "new_query_id": str(forked_query.id),
            },
        )

        return ForkQueryResponse(
            forked_query=QueryHistoryResponse.model_validate(forked_query),
            source_query_id=request.source_query_id,
        )

    except ValueError as e:
        logger.warning(
            "Invalid fork request",
            extra={
                "user_id": str(current_user.user_id),
                "source_query_id": str(request.source_query_id),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(
            "Error forking query",
            extra={
                "user_id": str(current_user.user_id),
                "source_query_id": str(request.source_query_id),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fork query",
        ) from e
