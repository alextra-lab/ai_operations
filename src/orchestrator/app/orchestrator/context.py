"""
Request Context for Orchestrator Pipeline.

Typed execution context that replaces dict-blob pattern.
Enables explicit contracts and better testability.

Part of P4-F11 Layer 4 orchestrator refactoring (Pipeline+Steps pattern).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from ..schemas.intent import IntentResponse, RequestType
from ..schemas.llm import LLMRequest, LLMResponse
from ..schemas.response import FormattedResponse
from ..schemas.use_case_config import UseCaseConfig


class RetrievalSource(BaseModel):
    """Single retrieved document source."""

    document_id: str | None = None
    title: str
    chunk_id: str | None = None
    score: float | None = None
    url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RequestContext(BaseModel):
    """
    Typed execution context for orchestrator pipeline.

    Replaces dict-blob pattern with explicit fields.
    Each step in the pipeline reads from and writes to this context.
    """

    # Request identification
    req_id: str = Field(..., description="Request ID for tracing")
    user_id: str | None = Field(None, description="Username from JWT")
    user_uuid: UUID | None = Field(None, description="User UUID from JWT")
    user_role: str | None = Field(
        None, description="User role from JWT (deprecated, use user_roles)"
    )
    user_roles: list[str] | None = Field(
        None, description="User roles from JWT (multi-role support per ADR-060)"
    )

    # Request classification
    request_type: RequestType | None = Field(None, description="Explicit request type if provided")
    query_original: str = Field(..., description="Original user query")
    query_sanitized: str = Field(..., description="Sanitized query (may be modified by Guard)")
    intent: IntentResponse | None = Field(None, description="Parsed intent")

    # Template & configuration
    use_case_id: UUID | None = Field(
        None, description="Use case UUID (if execution is use-case-driven)"
    )
    use_case: UseCaseConfig | None = Field(None, description="Loaded use case configuration")
    prompts: dict[str, Any] | None = Field(
        None, description="Multi-role prompts (system, developer, fewshots)"
    )

    # Conversation context
    thread_id: UUID | None = Field(None, description="Thread ID for multi-turn conversations")
    discussion_id: str | None = Field(None, description="External incident/ticket ID")
    history_messages: list[dict[str, Any]] = Field(
        default_factory=list, description="Conversation history"
    )

    # Retrieval
    sources: list[RetrievalSource] = Field(
        default_factory=list, description="Retrieved document sources"
    )
    rag_enabled: bool = Field(False, description="Whether RAG is enabled for this request")

    # LLM execution
    llm_request: LLMRequest | None = Field(None, description="Assembled LLM request")
    llm_response: LLMResponse | None = Field(None, description="LLM response")

    # Output
    formatted: FormattedResponse | None = Field(None, description="Final formatted response")

    # Metrics & telemetry
    guard_metrics: dict[str, Any] = Field(default_factory=dict, description="LLM-Guard metrics")
    retrieval_metrics: dict[str, Any] = Field(default_factory=dict, description="Retrieval metrics")
    llm_metrics: dict[str, Any] = Field(default_factory=dict, description="LLM execution metrics")

    # Extensions
    extras: dict[str, Any] = Field(default_factory=dict, description="Additional context data")

    class Config:
        arbitrary_types_allowed = True
