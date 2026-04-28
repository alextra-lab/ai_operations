"""
Collection management API endpoints.

This module provides REST API endpoints for managing document collections,
enabling corpus managers to organize documents with enforced embedding model consistency.

Admin endpoints require admin or corpus_admin role.
Public endpoints available to all authenticated users.

See ADR-021: Collection-Based Document Management
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import TokenPayload, get_current_user
from shared.config.loader import load_qdrant_config
from shared.logging_utils.fastapi import configure_logging

from ..db.connection import get_db_session
from ..repositories.collection_repository import CollectionRepository
from ..schemas.collections import (
    CollectionCreate,
    CollectionListResponse,
    CollectionResponse,
    CollectionStatsResponse,
    CollectionUpdate,
)

logger = configure_logging(service_name="collections_router")

# Admin router (requires corpus_admin or admin role)
admin_router = APIRouter(prefix="/api/v1/admin/collections", tags=["collections", "admin"])

# Public router (all authenticated users)
public_router = APIRouter(prefix="/api/v1/collections", tags=["collections"])


# ============================================================================
# Dependency Injection
# ============================================================================


def get_collection_repository(
    session: AsyncSession = Depends(get_db_session),
) -> CollectionRepository:
    """Dependency injection for collection repository."""
    return CollectionRepository(session)


async def requires_corpus_admin(
    current_user: TokenPayload = Depends(get_current_user),
) -> TokenPayload:
    """
    Dependency requiring corpus_admin or admin role for collection management.

    Accepts: admin, corpus_admin roles
    """
    allowed_roles = ["admin", "corpus_admin"]

    if not current_user.has_any_role(allowed_roles):
        logger.warning(
            f"User {current_user.sub} with roles {current_user.roles} "
            f"attempted to access collection management (requires: {allowed_roles})"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Required roles: {', '.join(allowed_roles)}",
        )

    return current_user


# ============================================================================
# Admin Collection Management Endpoints
# ============================================================================


@admin_router.get("/", response_model=CollectionListResponse)
async def list_collections(
    active_only: bool = True,
    embedding_model: str | None = None,
    skip: int = 0,
    limit: int = 100,
    repo: CollectionRepository = Depends(get_collection_repository),
    current_user: TokenPayload = Depends(requires_corpus_admin),
) -> CollectionListResponse:
    """
    List all collections with optional filters and pagination.

    **Permissions:** admin, corpus_admin

    **Query Parameters:**
    - active_only: Only return active collections (default: true)
    - embedding_model: Filter by embedding model identifier
    - skip: Number of items to skip for pagination (default: 0)
    - limit: Maximum items to return (default: 100, max: 1000)

    **Returns:**
    - List of collections with total count
    """
    try:
        collections, total = await repo.list_collections(
            active_only=active_only,
            embedding_model=embedding_model,
            skip=skip,
            limit=min(limit, 1000),  # Cap at 1000
        )

        return CollectionListResponse(
            collections=[CollectionResponse.model_validate(c) for c in collections],
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.error(f"Error listing collections: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list collections: {e!s}",
        )


@admin_router.post("/", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    collection: CollectionCreate,
    repo: CollectionRepository = Depends(get_collection_repository),
    current_user: TokenPayload = Depends(requires_corpus_admin),
    session: AsyncSession = Depends(get_db_session),
) -> CollectionResponse:
    """
    Create a new collection.

    **Permissions:** admin, corpus_admin

    **Body:**
    - name: Collection name (lowercase alphanumeric with underscores/hyphens)
    - description: Optional human-readable description
    - embedding_model: Embedding model identifier (immutable after creation)
    - embedding_provider: Provider name (openai, local, etc.)
    - embedding_dimensions: Vector dimensions

    **Returns:**
    - Created collection with generated Qdrant collection name

    **Note:** Embedding model cannot be changed after creation.
    """
    try:
        # Validate embedding model against Model Registry
        # Both services share the same database, so query directly
        from sqlalchemy import text

        stmt = text(
            """
            SELECT provider_type::text, embedding_dimensions
            FROM models
            WHERE model_id = :model_id
            AND model_type = 'embedding'
            AND is_available = true
            """
        )

        try:
            result = await session.execute(stmt, {"model_id": collection.embedding_model})
            row = result.fetchone()
        except Exception as e:
            logger.error(
                f"Error querying models table: {e}",
                exc_info=True,
                extra={"model_id": collection.embedding_model},
            )
            raise ValueError(
                "Failed to validate embedding model: Database error. "
                "Ensure the models table exists and is populated."
            ) from e

        if not row:
            logger.warning(
                f"Embedding model not found: {collection.embedding_model}",
                extra={"model_id": collection.embedding_model},
            )
            raise ValueError(
                f"Embedding model '{collection.embedding_model}' is not available. "
                "Choose an available embedding model from the model registry."
            )

        # Normalize provider_type/dimensions from registry (per ADR-050)
        # provider_type indicates the API protocol: 'openai', 'local', 'azure', 'anthropic'
        provider_type_from_registry = str(row[0]) if row[0] else "local"
        dims_from_registry = int(row[1]) if row[1] else None

        if not dims_from_registry:
            logger.error(
                f"Model missing embedding_dimensions: {collection.embedding_model}",
                extra={
                    "model_id": collection.embedding_model,
                    "provider": provider_type_from_registry,
                },
            )
            raise ValueError(
                f"Embedding model '{collection.embedding_model}' missing embedding_dimensions in registry. "
                "The model may not be properly configured."
            )

        # Create collection in database using authoritative provider_type/dimensions
        # Per ADR-050: Use provider_type as embedding_provider (API protocol)
        normalized = CollectionCreate.model_validate(
            {
                "name": collection.name,
                "description": collection.description,
                "embedding_model": collection.embedding_model,
                "embedding_provider": provider_type_from_registry,
                "embedding_dimensions": dims_from_registry,
                # Pass through preflight settings from request (P4-DOC-07)
                "preflight_sample_tokens": collection.preflight_sample_tokens,
                "auto_chunk_enabled": collection.auto_chunk_enabled,
                "preflight_strategies": collection.preflight_strategies,
            }
        )

        new_collection = await repo.create_collection(
            normalized, created_by=current_user.sub if current_user else "system"
        )

        # Commit transaction
        await session.commit()

        # Create corresponding Qdrant collection
        try:
            from ..repositories.vector_repository import (
                QdrantRepository,
                VectorRepositoryConfig,
            )

            # Extract values from SQLAlchemy Column objects
            coll_name = getattr(new_collection, "qdrant_collection_name", "")
            embed_dims = getattr(new_collection, "embedding_dimensions", 768)
            qdrant_settings = load_qdrant_config()

            qdrant_config = VectorRepositoryConfig(  # type: ignore[call-arg]
                url=qdrant_settings.get_url(),
                port=qdrant_settings.port,
                collection_name=str(coll_name),
                vector_size=int(embed_dims),
            )
            vector_repo = QdrantRepository(qdrant_config)

            logger.info(
                "Creating Qdrant collection for collection %s (%s dimensions)",
                new_collection.id,
                new_collection.embedding_dimensions,
            )

            await vector_repo.initialize_collection(force_recreate=False)

            logger.info(
                "Collection created successfully: %s",
                new_collection.id,
                extra={"embedding_dimensions": new_collection.embedding_dimensions},
            )
        except Exception as e:
            logger.error(f"Failed to create Qdrant collection: {e!s}", exc_info=True)
            # Rollback PostgreSQL collection creation if Qdrant fails
            await session.rollback()
            raise HTTPException(
                status_code=500, detail=f"Failed to create Qdrant collection: {e!s}"
            )

        return CollectionResponse.model_validate(new_collection)

    except ValueError as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating collection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create collection: {e!s}",
        )


@admin_router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(
    collection_id: UUID,
    repo: CollectionRepository = Depends(get_collection_repository),
    current_user: TokenPayload = Depends(requires_corpus_admin),
) -> CollectionResponse:
    """
    Get collection details by ID.

    **Permissions:** admin, corpus_admin

    **Path Parameters:**
    - collection_id: Collection UUID

    **Returns:**
    - Collection details including document count and metadata
    """
    collection = await repo.get_by_id(collection_id)

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection {collection_id} not found",
        )

    return CollectionResponse.model_validate(collection)


@admin_router.put("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: UUID,
    update_data: CollectionUpdate,
    repo: CollectionRepository = Depends(get_collection_repository),
    current_user: TokenPayload = Depends(requires_corpus_admin),
    session: AsyncSession = Depends(get_db_session),
) -> CollectionResponse:
    """
    Update collection (description and is_active only).

    **Permissions:** admin, corpus_admin

    **Path Parameters:**
    - collection_id: Collection UUID

    **Body:**
    - description: Optional new description
    - is_active: Optional active status

    **Returns:**
    - Updated collection details

    **Note:** Embedding model cannot be changed. Create a new collection
    and re-embed documents if you need to change the embedding model.
    """
    try:
        collection = await repo.update_collection(collection_id, update_data)

        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection {collection_id} not found",
            )

        await session.commit()

        logger.info("Updated collection: %s", collection_id)

        return CollectionResponse.model_validate(collection)

    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating collection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update collection: {e!s}",
        )


@admin_router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: UUID,
    repo: CollectionRepository = Depends(get_collection_repository),
    current_user: TokenPayload = Depends(requires_corpus_admin),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Delete collection (must have no documents).

    **Permissions:** admin, corpus_admin

    **Path Parameters:**
    - collection_id: Collection UUID

    **Errors:**
    - 404: Collection not found
    - 400: Collection is system-managed or has documents

    **Note:** System-managed collections (e.g., default) cannot be deleted.
    Collections with documents cannot be deleted - delete or move documents first.
    """
    try:
        success = await repo.delete_collection(collection_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection {collection_id} not found",
            )

        # TODO: Delete corresponding Qdrant collection
        # This will be implemented in Task 1.4

        await session.commit()

        logger.info(f"Deleted collection (id: {collection_id})")

    except ValueError as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting collection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete collection: {e!s}",
        )


@admin_router.get("/{collection_id}/stats", response_model=CollectionStatsResponse)
async def get_collection_stats(
    collection_id: UUID,
    repo: CollectionRepository = Depends(get_collection_repository),
    current_user: TokenPayload = Depends(requires_corpus_admin),
) -> CollectionStatsResponse:
    """
    Get detailed statistics for a collection.

    **Permissions:** admin, corpus_admin

    **Path Parameters:**
    - collection_id: Collection UUID

    **Returns:**
    - Collection statistics including document count, size, and usage metrics
    """
    stats = await repo.get_collection_statistics(collection_id)

    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection {collection_id} not found",
        )

    return CollectionStatsResponse(**stats)


# ============================================================================
# Public Collection Endpoints
# ============================================================================


@public_router.get("/available", response_model=CollectionListResponse)
async def list_available_collections(
    repo: CollectionRepository = Depends(get_collection_repository),
) -> CollectionListResponse:
    """
    List all active collections for Use Case configuration.

    **Permissions:** All authenticated users (TODO: implement auth)

    **Returns:**
    - List of active collections available for use in Use Cases

    **Use:** This endpoint is used in:
    - Document upload (collection selection dropdown)
    - Use Case configuration (RAG vector_collections multi-select)
    - Collection selection UIs across the application
    """
    try:
        collections, total = await repo.list_collections(
            active_only=True,  # Only show active collections
            embedding_model=None,  # All embedding models
            skip=0,
            limit=1000,  # Return all active collections
        )

        return CollectionListResponse(
            collections=[CollectionResponse.model_validate(c) for c in collections],
            total=total,
            skip=0,
            limit=1000,
        )

    except Exception as e:
        logger.error(f"Error listing available collections: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list collections: {e!s}",
        )


@public_router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection_public(
    collection_id: UUID, repo: CollectionRepository = Depends(get_collection_repository)
) -> CollectionResponse:
    """
    Get collection details (public read-only endpoint).

    **Permissions:** All authenticated users (TODO: implement auth)

    **Path Parameters:**
    - collection_id: Collection UUID

    **Returns:**
    - Collection details (read-only)
    """
    collection = await repo.get_by_id(collection_id)

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection {collection_id} not found",
        )

    # Only return active collections to public endpoint
    is_active = collection.is_active
    if is_active is not True:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection {collection_id} not found",
        )

    return CollectionResponse.model_validate(collection)
