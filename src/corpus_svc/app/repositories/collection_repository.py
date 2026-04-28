"""
Collection repository for database operations.

This module provides CRUD operations for document collections with
embedding model consistency enforcement.

See ADR-021: Collection-Based Document Management
"""

import hashlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging

from ..db.models import Collection
from ..schemas.collections import CollectionCreate, CollectionUpdate

if TYPE_CHECKING:
    from sqlalchemy.sql import Select

logger = configure_logging(service_name="collection_repository")


class CollectionRepository:
    """Repository for collection CRUD operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize collection repository.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def get_by_id(self, collection_id: UUID) -> Collection | None:
        """
        Get collection by ID.

        Args:
            collection_id: Collection UUID

        Returns:
            Collection model or None if not found
        """
        result = await self.session.execute(
            select(Collection).where(Collection.id == collection_id)
        )
        collection = result.scalar_one_or_none()

        if collection:
            logger.debug("Retrieved collection: %s", collection_id)
        else:
            logger.warning("Collection not found: %s", collection_id)

        return collection

    async def get_by_name(self, name: str) -> Collection | None:
        """
        Get collection by name.

        Args:
            name: Collection name

        Returns:
            Collection model or None if not found
        """
        result = await self.session.execute(
            select(Collection).where(Collection.name == name.lower())
        )
        return result.scalar_one_or_none()

    async def get_default_collection(self) -> Collection | None:
        """
        Get the system default collection.

        Returns:
            Default collection or None if not configured
        """
        result = await self.session.execute(
            select(Collection).where(Collection.is_default == True)  # noqa: E712
        )
        return result.scalar_one_or_none()

    async def list_collections(
        self,
        active_only: bool = True,
        embedding_model: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Collection], int]:
        """
        List collections with optional filters and pagination.

        Args:
            active_only: Only return active collections
            embedding_model: Filter by embedding model
            skip: Number of items to skip (pagination)
            limit: Maximum number of items to return

        Returns:
            Tuple of (list of collections, total count)
        """
        from sqlalchemy import ColumnElement

        conditions: list[ColumnElement[bool]] = []

        if active_only:
            conditions.append(Collection.is_active == True)  # noqa: E712

        if embedding_model:
            conditions.append(Collection.embedding_model == embedding_model)

        # Build count query - use text literal to avoid func.count type issues
        from sqlalchemy import text

        if conditions:
            count_query = select(text("COUNT(*)")).select_from(Collection).where(*conditions)
        else:
            count_query = select(text("COUNT(*)")).select_from(Collection)

        # Get total count
        total_result = await self.session.execute(count_query)
        total = int(total_result.scalar() or 0)

        # Build list query with pagination
        list_query = select(Collection)
        if conditions:
            list_query = list_query.where(and_(*conditions))

        list_query = (
            list_query.order_by(Collection.is_default.desc(), Collection.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        # Execute list query
        result = await self.session.execute(list_query)
        collections = list(result.scalars().all())

        logger.info(
            "Listed %s collections (total: %s, filters: active_only=%s, embedding_model=%s)",
            len(collections),
            total,
            active_only,
            embedding_model,
        )

        return collections, total

    async def create_collection(
        self, collection_data: CollectionCreate, created_by: str
    ) -> Collection:
        """
        Create a new collection.

        Args:
            collection_data: Collection creation data
            created_by: Username of creator

        Returns:
            Created collection model

        Raises:
            ValueError: If collection name already exists
        """
        # Check for duplicate name
        existing = await self.get_by_name(collection_data.name)
        if existing:
            raise ValueError(f"Collection '{collection_data.name}' already exists")

        # Generate Qdrant collection name
        qdrant_name = self._generate_qdrant_name(
            collection_data.name,
            collection_data.embedding_model,
            collection_data.embedding_dimensions,
        )

        # Create collection instance
        collection = Collection(
            name=collection_data.name.lower(),
            description=collection_data.description,
            embedding_model=collection_data.embedding_model,
            embedding_provider=collection_data.embedding_provider,
            embedding_dimensions=collection_data.embedding_dimensions,
            qdrant_collection_name=qdrant_name,
            created_by=created_by,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            # Auto-chunking configuration (P4-DOC-07)
            preflight_sample_tokens=collection_data.preflight_sample_tokens or 10000,
            auto_chunk_enabled=(
                collection_data.auto_chunk_enabled
                if collection_data.auto_chunk_enabled is not None
                else True
            ),
        )

        self.session.add(collection)
        await self.session.flush()
        await self.session.refresh(collection)

        logger.info(
            "Created collection: %s (embedding_model=%s)",
            collection.id,
            collection.embedding_model,
            extra={"created_by": str(created_by)},
        )

        return collection

    async def update_collection(
        self, collection_id: UUID, update_data: CollectionUpdate
    ) -> Collection | None:
        """
        Update collection (limited fields only).

        Only description, is_active, and preflight settings can be updated.
        Embedding model is immutable to preserve vector space consistency.

        Args:
            collection_id: Collection UUID
            update_data: Update data with preflight settings (P4-DOC-07)

        Returns:
            Updated collection or None if not found
        """
        collection = await self.get_by_id(collection_id)
        if not collection:
            return None

        # Update allowed fields
        if update_data.description is not None:
            collection.description = update_data.description  # type: ignore[assignment]

        if update_data.is_active is not None:
            collection.is_active = update_data.is_active  # type: ignore[assignment]

        # Update preflight settings (P4-DOC-07)
        if update_data.preflight_sample_tokens is not None:
            collection.preflight_sample_tokens = update_data.preflight_sample_tokens  # type: ignore[assignment]
        if update_data.auto_chunk_enabled is not None:
            collection.auto_chunk_enabled = update_data.auto_chunk_enabled  # type: ignore[assignment]
        if update_data.preflight_strategies is not None:
            collection.preflight_strategies = update_data.preflight_strategies  # type: ignore[assignment]

        collection.updated_at = datetime.now(UTC)  # type: ignore[assignment]

        await self.session.flush()
        await self.session.refresh(collection)

        logger.info("Updated collection: %s", collection_id)

        return collection

    async def delete_collection(self, collection_id: UUID) -> bool:
        """
        Delete collection (must have no documents).

        Args:
            collection_id: Collection UUID

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If collection is system-managed or has documents
        """
        collection = await self.get_by_id(collection_id)
        if not collection:
            logger.warning(f"Cannot delete - collection not found: {collection_id}")
            return False

        # Check if system managed
        is_system_managed = collection.is_system_managed
        if is_system_managed is True:
            raise ValueError(f"Cannot delete system-managed collection '{collection.name}'")

        # Check if has documents (foreign key constraint will also prevent this)
        doc_count_val = getattr(collection, "document_count", 0)
        doc_count = int(doc_count_val) if doc_count_val else 0
        if doc_count > 0:
            raise ValueError(
                f"Cannot delete collection '{collection.name}' with "
                f"{collection.document_count} documents. Delete or move documents first."
            )

        await self.session.delete(collection)
        await self.session.flush()

        logger.info("Deleted collection: %s", collection_id)

        return True

    async def increment_document_count(self, collection_id: UUID) -> bool:
        """
        Increment document count for a collection.

        Note: This is handled automatically by database trigger, but provided
        for manual operations if needed.

        Args:
            collection_id: Collection UUID

        Returns:
            True if updated, False if collection not found
        """
        collection = await self.get_by_id(collection_id)
        if not collection:
            return False

        # Avoid passing SQLAlchemy Column to int(); use getattr for instance value
        doc_count_val = getattr(collection, "document_count", None)
        current = int(doc_count_val) if doc_count_val is not None else 0
        collection.document_count = current + 1  # type: ignore[assignment]
        await self.session.flush()

        return True

    async def decrement_document_count(self, collection_id: UUID) -> bool:
        """
        Decrement document count for a collection.

        Note: This is handled automatically by database trigger, but provided
        for manual operations if needed.

        Args:
            collection_id: Collection UUID

        Returns:
            True if updated, False if collection not found
        """
        collection = await self.get_by_id(collection_id)
        if not collection:
            return False

        # Check document count - handle SQLAlchemy Column type
        doc_count_val = getattr(collection, "document_count", 0)
        doc_count = int(doc_count_val) if doc_count_val else 0
        if doc_count > 0:
            collection.document_count = doc_count - 1  # type: ignore[assignment]
            await self.session.flush()

        return True

    async def get_collections_by_embedding_model(
        self, embedding_model: str, active_only: bool = True
    ) -> list[Collection]:
        """
        Get all collections using a specific embedding model.

        Useful for validating Use Case configurations that reference
        multiple collections.

        Args:
            embedding_model: Embedding model identifier
            active_only: Only return active collections

        Returns:
            List of collections using the specified embedding model
        """
        conditions = [Collection.embedding_model == embedding_model]

        if active_only:
            conditions.append(Collection.is_active == True)  # noqa: E712

        result = await self.session.execute(
            select(Collection).where(and_(*conditions)).order_by(Collection.created_at.desc())
        )

        return list(result.scalars().all())

    async def validate_collections_compatible(
        self, collection_ids: list[UUID]
    ) -> tuple[bool, str | None]:
        """
        Validate that multiple collections use the same embedding model.

        Used when Use Cases reference multiple collections in RAG config.

        Args:
            collection_ids: List of collection UUIDs to validate

        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if all collections use same embedding model
            - (False, error_message) if embedding models differ or collections not found
        """
        if not collection_ids:
            return False, "No collections specified"

        if len(collection_ids) == 1:
            # Single collection always valid
            collection = await self.get_by_id(collection_ids[0])
            if not collection:
                return False, f"Collection {collection_ids[0]} not found"
            is_active = collection.is_active
            if is_active is not True:
                return False, f"Collection '{collection.name}' is not active"
            return True, None

        # Get all collections
        result = await self.session.execute(
            select(Collection).where(Collection.id.in_(collection_ids))
        )
        collections = list(result.scalars().all())

        # Check all collections found
        if len(collections) != len(collection_ids):
            found_ids = {str(c.id) for c in collections}
            missing_ids = {str(cid) for cid in collection_ids} - found_ids
            return False, f"Collections not found: {missing_ids}"

        # Check all active
        inactive = [str(c.name) for c in collections if c.is_active is not True]
        if inactive:
            return False, f"Inactive collections: {', '.join(inactive)}"

        # Check all use same embedding model
        embedding_models = {c.embedding_model for c in collections}
        if len(embedding_models) > 1:
            collection_info_list = [f"{c.name!s} ({c.embedding_model!s})" for c in collections]
            return False, (
                f"Collections use different embedding models: {', '.join(collection_info_list)}. "
                "All collections in a Use Case must use the same embedding model."
            )

        logger.debug(
            "Validated %s collections - all compatible (embedding_model: %s)",
            len(collections),
            collections[0].embedding_model if collections else None,
        )

        return True, None

    @staticmethod
    def _generate_qdrant_name(name: str, embedding_model: str, dimensions: int) -> str:
        """
        Generate Qdrant collection name with model hash.

        Format: fc_<collection_name>_<model_hash>

        The model hash ensures collections with different embedding models
        have distinct names in Qdrant, preventing accidental overwrites.

        Args:
            name: Collection name
            embedding_model: Embedding model identifier
            dimensions: Embedding dimensions

        Returns:
            Qdrant collection name
        """
        # Create hash from model + dimensions
        combined = f"{embedding_model}:{dimensions}"
        model_hash = hashlib.sha256(combined.encode()).hexdigest()[:8]

        # Generate namespaced name
        return f"fc_{name}_{model_hash}"

    async def get_collection_statistics(self, collection_id: UUID) -> dict | None:
        """
        Get detailed statistics for a collection.

        Args:
            collection_id: Collection UUID

        Returns:
            Dictionary with collection statistics or None if not found
        """
        from ..db.models import Document

        collection = await self.get_by_id(collection_id)
        if not collection:
            return None

        # Get document statistics - use text literals to avoid func type issues
        from sqlalchemy import text as sql_text

        stats_query: Select = (
            select(
                sql_text("COUNT(id)").label("document_count"),
                sql_text("SUM(file_size)").label("total_size_bytes"),
                sql_text("AVG(num_chunks)").label("avg_chunks_per_doc"),
                sql_text("MAX(created_at)").label("last_document_added"),
            )
            .select_from(Document)
            .where(Document.collection_id == collection_id)
        )

        result = await self.session.execute(stats_query)
        stats = result.one()

        return {
            "id": collection.id,
            "name": collection.name,
            "document_count": stats.document_count or 0,
            "total_size_bytes": stats.total_size_bytes or 0,
            "embedding_model": collection.embedding_model,
            "avg_chunks_per_document": float(stats.avg_chunks_per_doc or 0),
            "created_at": collection.created_at,
            "last_document_added": stats.last_document_added,
        }
