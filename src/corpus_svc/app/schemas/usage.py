"""
Schemas for usage statistics operations in the Retriever service.
"""

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class RAGConfidenceUpdateRequest(BaseModel):
    """Request model for updating RAG confidence."""

    run_id: uuid.UUID = Field(..., description="The run ID of the usage stats record to update.")
    rag_confidence: float = Field(..., description="The RAG confidence score.", ge=0.0, le=1.0)


class UsageStatsCreateRequest(BaseModel):
    """Request model for creating a usage stats record."""

    document_id: uuid.UUID | None = None
    chunk_ids: list[uuid.UUID]
    user_id: str | None = None
    query_text: str | None = None
    relevancy_scores: list[float] | None = None
    metadata: dict | None = None
    run_id: uuid.UUID | None = None
    rag_confidence: float | None = None
    total_results_found: int | None = None
    source_document_count: int | None = None
    average_relevancy: float | None = None


class UsageStatsResponse(BaseModel):
    """Response model for usage statistics."""

    id: uuid.UUID
    document_id: uuid.UUID | None = None
    chunk_ids: list[uuid.UUID]
    accessed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    user_id: str | None = None
    query_text: str | None = None
    relevancy_scores: list[float] | None = None
    metadata: dict | None = Field(None, alias="metadata_")
    average_relevancy: float | None = None
    rag_confidence: float | None = None
    total_results_found: int | None = None
    source_document_count: int | None = None
    run_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}
