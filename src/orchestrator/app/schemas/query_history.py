"""
Pydantic schemas for query history API.

This module defines the request and response models for query history endpoints.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class QueryHistoryBase(BaseModel):
    """Base schema for query history with common fields."""

    query_text: str = Field(..., description="The original query text")
    use_case_id: uuid.UUID | None = Field(None, description="UUID of the use case")
    use_case_name: str | None = Field(None, description="Name of the use case")
    intent_type: str | None = Field(None, description="Intent type (QUERY, SUMMARIZATION, etc.)")


class QueryHistoryCreate(QueryHistoryBase):
    """Schema for creating a new query history record."""

    run_id: str = Field(..., description="Unique run identifier")
    user_id: uuid.UUID = Field(..., description="UUID of the user")
    center_id: str | None = Field(None, description="Center identifier")
    query_params: dict[str, Any] | None = Field(None, description="Query parameters")
    response_text: str | None = Field(None, description="Response text from LLM")
    response_status: str = Field(..., description="Status of the response")
    metrics: dict[str, Any] | None = Field(None, description="Execution metrics")
    processing_time_ms: int | None = Field(
        None, description="Total processing time in milliseconds"
    )
    sources: dict[str, Any] | None = Field(None, description="Retrieved sources")
    citations: dict[str, Any] | None = Field(None, description="Citations")
    parent_query_id: uuid.UUID | None = Field(None, description="Parent query UUID for forks")
    thread_id: uuid.UUID | None = Field(None, description="Thread UUID")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class QueryHistoryUpdate(BaseModel):
    """Schema for updating an existing query history record."""

    response_text: str | None = None
    response_status: str | None = None
    metrics: dict[str, Any] | None = None
    processing_time_ms: int | None = None
    sources: dict[str, Any] | None = None
    citations: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class QueryHistoryResponse(QueryHistoryBase):
    """Schema for query history response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="UUID of the history record")
    run_id: str = Field(..., description="Unique run identifier")
    user_id: uuid.UUID = Field(..., description="UUID of the user")
    center_id: str | None = Field(None, description="Center identifier")
    query_params: dict[str, Any] | None = Field(None, description="Query parameters")
    response_text: str | None = Field(None, description="Response text from LLM")
    response_status: str = Field(..., description="Status of the response")
    metrics: dict[str, Any] | None = Field(None, description="Execution metrics")
    processing_time_ms: int | None = Field(
        None, description="Total processing time in milliseconds"
    )
    sources: dict[str, Any] | None = Field(None, description="Retrieved sources")
    citations: dict[str, Any] | None = Field(None, description="Citations")
    parent_query_id: uuid.UUID | None = Field(None, description="Parent query UUID")
    thread_id: uuid.UUID | None = Field(None, description="Thread UUID")
    fork_count: int = Field(0, description="Number of times this query has been forked")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    archived_at: datetime | None = Field(None, description="Archive timestamp")
    metadata_json: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class QueryHistoryListResponse(BaseModel):
    """Schema for paginated query history list response."""

    items: list[QueryHistoryResponse] = Field(..., description="List of query history records")
    total: int = Field(..., description="Total number of records matching filters")
    limit: int = Field(..., description="Number of records per page")
    offset: int = Field(..., description="Number of records skipped")
    has_more: bool = Field(..., description="Whether there are more records available")


class HistoryQueryParams(BaseModel):
    """Schema for query history list parameters."""

    limit: int = Field(50, ge=1, le=100, description="Maximum number of records to return")
    offset: int = Field(0, ge=0, description="Number of records to skip")
    use_case_id: uuid.UUID | None = Field(None, description="Filter by use case UUID")
    intent_type: str | None = Field(None, description="Filter by intent type")
    response_status: str | None = Field(None, description="Filter by response status")
    search_query: str | None = Field(None, description="Full-text search on query text")


class ForkQueryRequest(BaseModel):
    """Schema for fork query request."""

    source_query_id: uuid.UUID = Field(..., description="UUID of the query to fork")


class ForkQueryResponse(BaseModel):
    """Schema for fork query response."""

    forked_query: QueryHistoryResponse = Field(..., description="The newly created forked query")
    source_query_id: uuid.UUID = Field(..., description="UUID of the source query")


class ThreadCreate(BaseModel):
    """Schema for creating a conversation thread."""

    title: str | None = Field(None, max_length=500, description="Thread title")
    description: str | None = Field(None, description="Thread description")
    center_id: str | None = Field(None, description="Center identifier")
    discussion_id: str | None = Field(
        None, max_length=255, description="External incident/ticket ID"
    )
    use_case_id: uuid.UUID | None = Field(None, description="Associated use case UUID")
    use_case_name: str | None = Field(None, description="Use case name")
    source: str = Field("ui", description="Source: ui, api, soar")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class ThreadUpdate(BaseModel):
    """Schema for updating a conversation thread."""

    title: str | None = Field(None, max_length=500, description="Thread title")
    description: str | None = Field(None, description="Thread description")
    is_active: bool | None = Field(None, description="Whether thread is active")
    discussion_id: str | None = Field(
        None, max_length=255, description="External incident/ticket ID"
    )
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class ThreadResponse(BaseModel):
    """Schema for conversation thread response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="UUID of the thread record")
    thread_id: uuid.UUID = Field(..., description="Thread identifier")
    title: str | None = Field(None, description="Thread title")
    description: str | None = Field(None, description="Thread description")
    user_id: uuid.UUID = Field(..., description="UUID of the thread owner")
    center_id: str | None = Field(None, description="Center identifier")
    discussion_id: str | None = Field(None, description="External incident/ticket ID")
    use_case_id: uuid.UUID | None = Field(None, description="Associated use case UUID")
    use_case_name: str | None = Field(None, description="Use case name")
    source: str = Field("ui", description="Source: ui, api, soar")
    is_active: bool = Field(True, description="Whether the thread is active")
    message_count: int = Field(0, description="Number of messages in the thread")
    context_size_tokens: int = Field(0, description="Total context size in tokens")
    max_context_tokens: int = Field(8000, description="Maximum context size")
    first_query_id: uuid.UUID | None = Field(None, description="UUID of first query")
    last_query_id: uuid.UUID | None = Field(None, description="UUID of last query")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_activity_at: datetime = Field(..., description="Last activity timestamp")
    archived_at: datetime | None = Field(None, description="Archive timestamp")
    metadata_json: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ThreadMessageResponse(BaseModel):
    """Schema for thread message response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="UUID of the message record")
    thread_id: uuid.UUID = Field(..., description="Thread UUID (internal ID)")
    query_id: uuid.UUID | None = Field(None, description="Associated query UUID")
    sequence_number: int = Field(..., description="Message sequence number")
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    token_count: int = Field(0, description="Token count")
    model_used: str | None = Field(None, description="Model used for response")
    is_summary: bool = Field(False, description="Whether this is a summary message")
    original_message_count: int | None = Field(None, description="Number of messages summarized")
    created_at: datetime = Field(..., description="Creation timestamp")


class ThreadListResponse(BaseModel):
    """Schema for paginated thread list response."""

    items: list[ThreadResponse] = Field(..., description="List of conversation threads")
    total: int = Field(..., description="Total number of threads")
    limit: int = Field(..., description="Number of records per page")
    offset: int = Field(..., description="Number of records skipped")
    has_more: bool = Field(..., description="Whether there are more records available")
