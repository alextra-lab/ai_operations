"""
Pydantic schemas for collection management.

This module defines request/response schemas for the collection management API,
enabling corpus managers to organize documents with enforced embedding model consistency.

See ADR-021: Collection-Based Document Management
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, validator


class CollectionBase(BaseModel):
    """Base collection schema with common fields."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Collection name (lowercase alphanumeric with underscores/hyphens)",
    )
    description: str | None = Field(
        None, description="Human-readable description of collection purpose"
    )


class CollectionCreate(CollectionBase):
    """
    Schema for creating a new collection.

    Embedding model is set at creation and is immutable. All documents in this
    collection will use the specified embedding model for consistency.
    """

    embedding_model: str = Field(
        ...,
        min_length=1,
        description="Embedding model identifier (e.g., 'text-embedding-3-small')",
    )
    embedding_provider: str = Field(
        ..., min_length=1, description="Embedding provider (e.g., 'openai', 'local')"
    )
    embedding_dimensions: int = Field(
        ..., gt=0, description="Vector dimensions for this embedding model"
    )

    # Auto-chunking configuration (P4-DOC-07)
    preflight_sample_tokens: int | None = Field(
        10000,
        ge=1000,
        le=100000,
        description="Sample size in tokens for preflight analysis (default: 10000)",
    )
    auto_chunk_enabled: bool | None = Field(
        True, description="Enable automatic chunking strategy detection (default: true)"
    )
    preflight_strategies: list[str] | None = Field(
        None,
        description="Chunking strategies to test during auto-detection (default: all available)",
    )

    @validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """
        Validate and normalize collection name.

        Names must be lowercase alphanumeric with optional underscores/hyphens.
        This ensures compatibility with Qdrant collection naming rules.
        """
        # Normalize to lowercase
        v = v.lower().strip()

        # Validate format
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Collection name must be alphanumeric with optional underscores and hyphens"
            )

        # Check for reserved names
        reserved_names = {"system", "admin", "metadata", "index"}
        if v in reserved_names:
            raise ValueError(f"Collection name '{v}' is reserved")

        return v

    @validator("embedding_provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate embedding provider."""
        allowed_providers = {"openai", "local", "azure", "cohere"}
        if v.lower() not in allowed_providers:
            raise ValueError(f"Embedding provider must be one of: {', '.join(allowed_providers)}")
        return v.lower()


class CollectionUpdate(BaseModel):
    """
    Schema for updating a collection.

    Only description, is_active, and preflight settings can be updated.
    Embedding model is immutable to preserve vector space consistency.
    """

    description: str | None = None
    is_active: bool | None = None

    # Auto-chunking configuration (P4-DOC-07)
    preflight_sample_tokens: int | None = Field(
        None,
        ge=1000,
        le=100000,
        description="Sample size in tokens for preflight analysis",
    )
    auto_chunk_enabled: bool | None = None
    preflight_strategies: list[str] | None = None


class CollectionResponse(CollectionBase):
    """Schema for collection API responses."""

    id: UUID
    embedding_model: str
    embedding_provider: str
    embedding_dimensions: int
    qdrant_collection_name: str
    is_default: bool
    is_active: bool
    is_system_managed: bool
    preflight_sample_tokens: int
    preflight_strategies: list[str]
    auto_chunk_enabled: bool
    created_by: str
    created_at: datetime
    updated_at: datetime
    document_count: int

    class Config:
        from_attributes = True


class CollectionListResponse(BaseModel):
    """Schema for paginated collection list responses."""

    collections: list[CollectionResponse] = Field(
        default_factory=list, description="List of collections"
    )
    total: int = Field(
        ..., ge=0, description="Total number of collections matching filter criteria"
    )
    skip: int = Field(default=0, ge=0, description="Number of items skipped for pagination")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of items returned")


class CollectionStatsResponse(BaseModel):
    """Schema for collection statistics."""

    id: UUID
    name: str
    document_count: int
    total_documents_size_bytes: int = Field(..., description="Total size of all documents in bytes")
    embedding_model: str
    avg_chunks_per_document: float = Field(..., description="Average number of chunks per document")
    created_at: datetime
    last_document_added: datetime | None = Field(
        None, description="Timestamp of most recently added document"
    )
