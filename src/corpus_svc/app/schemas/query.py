"""
Schemas for query operations in the Retriever service.
"""

import uuid
from typing import Any

from pydantic import BaseModel, Field


# Re-using DocumentClassification from document schema if applicable, or define locally
# from .document import DocumentClassification # If it's generic enough
# For now, let's assume filters might be simple key-value pairs
class SearchFilter(BaseModel):
    """Represents a single filter condition for a search query."""

    field: str = Field(
        ...,
        description="The field to filter on (e.g., 'metadata.source', 'classification').",
    )
    value: Any = Field(..., description="The value to filter by.")
    # operator: Optional[str] = Field("eq", description="The operator (e.g., eq, gt, lt, in). Default 'eq'.") # For more complex filtering


class QueryRequest(BaseModel):
    """Request model for a search query."""

    query_text: str = Field(..., description="The natural language query string.")
    collection_names: list[str] = Field(
        default_factory=lambda: ["default"],
        description="List of collection names to search across",
    )
    top_k: int = Field(10, description="Number of top results to return.", gt=0, le=100)
    filters: list[SearchFilter] | None = Field(
        None, description="List of filters to apply to the search."
    )
    min_relevancy_score: float = Field(0.0, description="Minimum relevancy score threshold.")
    run_id: str | None = Field(None, description="Optional run ID for tracking this query.")
    metadata: dict[str, Any] | None = Field(None, description="Optional metadata for this query.")
    # embedding_model kept for backward compatibility; retrieval selects model
    # based on collection metadata during multi-collection search
    embedding_model: str | None = Field(
        None,
        description="Deprecated: Embedding model override (use collection metadata)",
    )


class HybridSearchRequest(BaseModel):
    """Request model for hybrid search combining semantic and keyword search."""

    query_text: str = Field(..., description="The natural language query string.")
    top_k: int = Field(10, description="Number of top results to return.", gt=0, le=100)
    semantic_weight: float = Field(
        0.7, description="Weight for semantic search results.", ge=0.0, le=1.0
    )
    keyword_weight: float = Field(
        0.3, description="Weight for keyword search results.", ge=0.0, le=1.0
    )
    filters: list[SearchFilter] | None = Field(
        None, description="List of filters to apply to the search."
    )
    min_relevancy_score: float = Field(0.0, description="Minimum relevancy score threshold.")


class QueryResultItem(BaseModel):
    """Represents a single search result item."""

    document_id: str = Field(..., description="ID of the source document.")
    chunk_id: str = Field(..., description="ID of the relevant chunk within the document.")
    score: float = Field(
        ..., description="Relevance score of the result (e.g., cosine similarity)."
    )
    text_snippet: str | None = Field(
        None, description="A snippet of the relevant text from the chunk."
    )
    full_text: str | None = Field(
        None, description="Full text of the chunk, if requested/available."
    )
    document_title: str | None = Field(None, description="Title of the source document.")
    document_source: str | None = Field(
        None, description="Source identifier of the document (e.g., URL, path)."
    )
    document_author: str | None = Field(None, description="Author of the source document.")
    document_metadata: dict[str, Any] | None = Field(
        None, description="Metadata of the source document."
    )
    chunk_metadata: dict[str, Any] | None = Field(None, description="Metadata of the chunk.")

    model_config = {"from_attributes": True}


class QueryResponse(BaseModel):
    """Response model for a search query."""

    query_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique ID for this query response.",
    )
    query_text: str | None = Field(None, description="The original query text submitted.")
    search_type: str = Field(
        "semantic",
        description="Type of search performed (semantic, hybrid, document_browse).",
    )
    results: list[QueryResultItem] = Field(
        default_factory=list, description="List of search results."
    )
    total_results: int = Field(0, description="Total number of results returned.")
    processing_time_ms: float = Field(0.0, description="Processing time in milliseconds.")

    model_config = {"from_attributes": True}


class QuerySuggestionsResponse(BaseModel):
    """Response model for query suggestions."""

    partial_query: str = Field(..., description="The partial query that was used for suggestions.")
    suggestions: list[str] = Field(default_factory=list, description="List of suggested queries.")

    model_config = {"from_attributes": True}
