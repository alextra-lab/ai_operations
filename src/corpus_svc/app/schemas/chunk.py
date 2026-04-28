"""
Chunk schemas for the Retriever service.

This module defines the Pydantic models for document chunks and related operations,
including chunking configuration and embedding representation.
"""

import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RecursiveChunkingConfig(BaseModel):
    """Configuration for recursive chunking strategy."""

    max_chunk_size: int = Field(2000, description="Maximum size of a chunk in characters")
    min_chunk_size: int = Field(200, description="Minimum size of a chunk in characters")
    overlap_size: int = Field(50, description="Overlap size between chunks in characters")
    separators: list[str] = Field(
        default_factory=lambda: ["\n\n", "\n", ". ", ", ", " "],
        description="List of separators to use for splitting text (in order of preference)",
    )
    adapt_to_content_type: bool = Field(
        True, description="Whether to adapt chunk size based on document type"
    )
    metadata_fields: list[str] = Field(
        default_factory=list,
        description="Document metadata fields to include in chunk metadata",
    )

    @field_validator("max_chunk_size")
    def max_chunk_size_must_be_positive(cls, v: int) -> int:
        """Validate max_chunk_size."""
        if v <= 0:
            raise ValueError("max_chunk_size must be positive")
        return v

    @field_validator("min_chunk_size")
    def min_chunk_size_must_be_positive(cls, v: int) -> int:
        """Validate min_chunk_size."""
        if v <= 0:
            raise ValueError("min_chunk_size must be positive")
        return v

    @model_validator(mode="before")
    def check_sizes(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Validate min_chunk_size and max_chunk_size relationship."""
        min_size = values.get("min_chunk_size")
        max_size = values.get("max_chunk_size")

        if min_size is not None and max_size is not None and min_size > max_size:
            raise ValueError("min_chunk_size must be less than or equal to max_chunk_size")

        return values


class ChunkBase(BaseModel):
    """Base model for chunk data (chunk text is NOT stored in the relational DB, only in the vector DB)."""

    document_id: str = Field(..., description="ID of the parent document")
    chunk_index: int = Field(..., description="Index of the chunk within the document")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional chunk metadata")
    parent_chunk_id: str | None = Field(
        None, description="ID of the parent chunk (for hierarchical chunking)"
    )
    depth: int = Field(0, description="Depth level in the chunk hierarchy")


class ChunkCreate(ChunkBase):
    """Model for creating a new chunk (text is only stored in the vector DB, not in the relational DB)."""

    content: str = Field(
        ...,
        description="Text content of the chunk (only stored in the vector DB, not in the relational DB)",
    )
    embedding: list[float] | None = Field(None, description="Vector embedding of the chunk content")
    embedding_model: str | None = Field(None, description="Name of the embedding model used")
    embedding_provider: str | None = Field(None, description="Name of the embedding provider used")
    embedding_dimensions: int | None = Field(
        None, description="Number of dimensions in the embedding vector"
    )
    embedding_id: str | None = Field(
        None,
        description="ID of the embedding in the vector store (e.g., Qdrant point ID)",
    )


class Chunk(ChunkBase):
    """Model for a stored chunk."""

    id: str = Field(..., description="Chunk unique identifier")
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        description="Chunk creation timestamp",
    )
    embedding_id: str | None = Field(None, description="ID of the embedding in the vector store")
    embedding_model: str | None = Field(None, description="Name of the embedding model used")
    embedding_provider: str | None = Field(None, description="Name of the embedding provider used")
    embedding_dimensions: int | None = Field(
        None, description="Number of dimensions in the embedding vector"
    )

    model_config = ConfigDict(from_attributes=True)


class ChunkUpdate(BaseModel):
    """Model for updating chunk metadata (text is only updated in the vector DB, not in the relational DB)."""

    content: str | None = Field(
        None,
        description="Updated chunk content (only in the vector DB, not in the relational DB)",
    )
    metadata: dict[str, Any] | None = Field(None, description="Updated chunk metadata")
    embedding: list[float] | None = Field(None, description="Updated vector embedding")
    embedding_model: str | None = Field(None, description="Name of the embedding model used")
    embedding_id: str | None = Field(None, description="ID of the embedding in the vector store")


class ChunkSearchQuery(BaseModel):
    """Model for chunk semantic search query."""

    query: str = Field(..., description="Search query string")
    filter: dict[str, Any] | None = Field(None, description="Metadata filter criteria")
    document_ids: list[str] | None = Field(
        None, description="List of document IDs to search within"
    )
    top_k: int = Field(10, description="Number of results to return")
    similarity_threshold: float | None = Field(0.7, description="Minimum similarity score (0-1)")
    embedding_model: str | None = Field(None, description="Embedding model to use for query")
    rerank: bool = Field(False, description="Whether to rerank results with a cross-encoder model")
    rerank_model: str | None = Field(None, description="Reranking model to use if rerank is True")

    @field_validator("top_k")
    def top_k_must_be_positive(cls, v: int) -> int:
        """Validate top_k."""
        if v <= 0:
            raise ValueError("top_k must be positive")
        return v

    @field_validator("similarity_threshold")
    def similarity_threshold_must_be_between_0_and_1(cls, v: float | None) -> float | None:
        """Validate similarity_threshold."""
        if v is not None and (v < 0 or v > 1):
            raise ValueError("similarity_threshold must be between 0 and 1")
        return v


class ChunkSearchResult(BaseModel):
    """Model for chunk search result."""

    chunk: Chunk = Field(..., description="Chunk data")
    score: float = Field(..., description="Similarity score (0-1)")
    document_title: str | None = Field(None, description="Title of the parent document")
    document_source: str | None = Field(None, description="Source of the parent document")

    model_config = {"from_attributes": True}


class ChunkSearchResponse(BaseModel):
    """Model for chunk search API response."""

    results: list[ChunkSearchResult] = Field(default_factory=list, description="Search results")
    query: str = Field(..., description="Search query")
    top_k: int = Field(..., description="Number of results requested")
    count: int = Field(..., description="Number of results returned")
    embedding_model: str = Field(..., description="Embedding model used")
    processing_time_ms: float = Field(..., description="Query processing time in milliseconds")


class ContentExtractorConfig(BaseModel):
    """Configuration for content extraction."""

    extract_text: bool = Field(True, description="Whether to extract text content")
    extract_metadata: bool = Field(True, description="Whether to extract document metadata")
    extract_images: bool = Field(False, description="Whether to extract embedded images")
    ocr_images: bool = Field(False, description="Whether to perform OCR on extracted images")
    extract_tables: bool = Field(False, description="Whether to extract tables from document")
    language_detection: bool = Field(True, description="Whether to detect document language")
    max_content_length: int | None = Field(
        None, description="Maximum content length to extract (in characters)"
    )
    structured_to_text_format: str = Field(
        "tabular",
        description="Format for converting structured data to text (tabular, markdown)",
    )


class ChunkingPipelineConfig(BaseModel):
    """Configuration for document chunking pipeline."""

    chunking_strategy: str = Field(
        "recursive", description="Chunking strategy to use (recursive, sliding, etc.)"
    )
    chunking_config: RecursiveChunkingConfig = Field(
        default_factory=lambda: RecursiveChunkingConfig(),  # type: ignore[call-arg]
        description="Configuration for chunking strategy",
    )
    content_extraction_config: ContentExtractorConfig = Field(
        default_factory=lambda: ContentExtractorConfig(),  # type: ignore[call-arg]
        description="Configuration for content extraction",
    )
    embedding_enabled: bool = Field(True, description="Whether to create embeddings for chunks")
    embedding_model: str | None = Field(None, description="Embedding model to use")
    embedding_batch_size: int = Field(32, description="Batch size for embedding creation")
    store_chunks: bool = Field(True, description="Whether to store chunks in database")
