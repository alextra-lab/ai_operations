"""
Pydantic schemas for Prompt Pattern Library.

These schemas define the request/response models for the Pattern Library API,
which provides reusable prompt engineering patterns for use case scaffolding.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PatternVariable(BaseModel):
    """Variable placeholder in a pattern template."""

    name: str = Field(..., description="Variable name (e.g., 'domain', 'task_type')")
    description: str = Field(..., description="Description of what this variable represents")
    default: str | None = Field(None, description="Optional default value")


class FewShotExample(BaseModel):
    """Few-shot example pair for pattern templates."""

    user: str = Field(..., description="Example user input")
    assistant: str = Field(..., description="Example assistant response")


class PromptPatternBase(BaseModel):
    """Base schema for prompt patterns."""

    pattern_id: str = Field(
        ...,
        description="Unique identifier (e.g., 'chain-of-thought', 'rag-citations')",
        min_length=1,
        max_length=100,
    )
    name: str = Field(..., description="Human-readable pattern name", min_length=1, max_length=255)
    category: str = Field(
        ...,
        description="Pattern category (reasoning, rag, json, tools, etc.)",
        min_length=1,
        max_length=100,
    )
    description: str = Field(
        ...,
        description="Detailed description of the pattern and when to use it",
        min_length=1,
    )

    system_prompt_template: str | None = Field(
        None, description="Template for system-level prompt (user-visible)"
    )
    developer_prompt_template: str | None = Field(
        None, description="Template for developer-level instructions (hidden)"
    )
    fewshots_template: list[FewShotExample] = Field(
        default_factory=list, description="Example input/output pairs"
    )

    variables: list[PatternVariable] = Field(
        default_factory=list, description="Placeholder variables in templates"
    )
    source_url: str | None = Field(
        None,
        description="Source reference URL (e.g., promptingguide.ai)",
        max_length=500,
    )
    tags: list[str] = Field(default_factory=list, description="Tags for searchability")

    # Sampling preset recommendation (ADR-023)
    recommended_preset: str = Field(
        default="balanced",
        description="Recommended sampling preset (strict, balanced, creative)",
        max_length=50,
    )
    max_tokens_override: int | None = Field(
        None,
        description="Override max_tokens for patterns with specific needs (e.g., ReAct with tool use)",
        gt=0,
        le=16384,
    )
    special_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Pattern-specific parameters (e.g., max_tool_steps, tool_step_timeout)",
    )


class PromptPatternCreate(PromptPatternBase):
    """Schema for creating a new prompt pattern."""

    created_by: str | None = Field(None, description="User who created this pattern")


class PromptPatternUpdate(BaseModel):
    """Schema for updating an existing prompt pattern."""

    name: str | None = Field(None, min_length=1, max_length=255)
    category: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, min_length=1)
    system_prompt_template: str | None = None
    developer_prompt_template: str | None = None
    fewshots_template: list[FewShotExample] | None = None
    variables: list[PatternVariable] | None = None
    source_url: str | None = Field(None, max_length=500)
    tags: list[str] | None = None
    recommended_preset: str | None = Field(None, max_length=50)
    max_tokens_override: int | None = Field(None, gt=0, le=16384)
    special_params: dict[str, Any] | None = None


class PromptPatternResponse(PromptPatternBase):
    """Schema for prompt pattern responses."""

    id: UUID = Field(..., description="Internal UUID")
    use_count: int = Field(default=0, description="Number of times this pattern has been applied")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: str | None = Field(None, description="User who created this pattern")

    class Config:
        from_attributes = True


class PromptPatternListResponse(BaseModel):
    """Paginated list response for prompt patterns."""

    patterns: list[PromptPatternResponse] = Field(..., description="List of patterns")
    total: int = Field(..., description="Total number of patterns matching filters")
    page: int = Field(..., description="Current page number (1-based)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")


class ApplyPatternRequest(BaseModel):
    """Request to apply a pattern to a use case."""

    pattern_id: str = Field(..., description="Pattern to apply (e.g., 'chain-of-thought')")
    variables: dict[str, str] = Field(
        default_factory=dict,
        description="Variable substitutions (e.g., {'domain': 'threat intelligence'})",
    )


class ApplyPatternResponse(BaseModel):
    """Response after applying a pattern."""

    system_prompt: str | None = Field(
        None, description="Rendered system prompt with variables substituted"
    )
    developer_prompt: str | None = Field(
        None, description="Rendered developer prompt with variables substituted"
    )
    fewshots: list[FewShotExample] = Field(
        default_factory=list,
        description="Few-shot examples (variables substituted if any)",
    )
    pattern_used: str = Field(..., description="Pattern ID that was applied")
    variables_applied: dict[str, str] = Field(..., description="Variables that were substituted")
