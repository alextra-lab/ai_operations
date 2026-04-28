"""
Token Usage Schemas

Pydantic models for token tracking and aggregation.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


class TokenUsageBase(BaseModel):
    """Base schema for token usage"""

    run_id: str = Field(..., description="Unique run identifier")
    request_id: str | None = Field(None, description="Request identifier")
    user_id: UUID = Field(..., description="User who made the request")
    center_id: str | None = Field(None, description="Organization/center identifier")
    use_case_id: UUID | None = Field(None, description="Use case ID")
    use_case_name: str | None = Field(None, description="Use case name")
    intent_type: str | None = Field(None, description="Intent type")
    model_id: str = Field(..., description="Model identifier")
    model_provider: str | None = Field(None, description="Model provider")
    model_version: str | None = Field(None, description="Model version")
    tokens_in: int = Field(0, ge=0, description="Input tokens")
    tokens_out: int = Field(0, ge=0, description="Output tokens")
    total_tokens: int = Field(0, ge=0, description="Total tokens")
    cost_per_1k_in: Decimal | None = Field(None, description="Cost per 1k input tokens")
    cost_per_1k_out: Decimal | None = Field(None, description="Cost per 1k output tokens")
    total_cost: Decimal | None = Field(None, description="Total cost")
    request_type: str | None = Field(None, description="Request type")
    streaming_used: bool = Field(False, description="Whether streaming was used")
    call_duration_ms: int | None = Field(None, ge=0, description="Call duration in milliseconds")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata")

    @field_validator("total_tokens", mode="before")
    @classmethod
    def validate_total_tokens(cls, v: int, info: ValidationInfo) -> int:
        """Calculate total_tokens if not provided"""
        if v == 0 and info.data:
            tokens_in = info.data.get("tokens_in", 0)
            tokens_out = info.data.get("tokens_out", 0)
            return int(tokens_in) + int(tokens_out)
        return v


class TokenUsageCreate(TokenUsageBase):
    """Schema for creating token usage records"""


class TokenUsageResponse(TokenUsageBase):
    """Schema for token usage response"""

    id: UUID = Field(..., description="Token usage record ID")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class TokenUsageSummary(BaseModel):
    """Summary of token usage for a time period"""

    center_id: str | None = Field(None, description="Center identifier")
    user_id: UUID | None = Field(None, description="User identifier")
    total_requests: int = Field(0, ge=0, description="Total number of requests")
    unique_users: int | None = Field(None, ge=0, description="Number of unique users")
    total_tokens_in: int = Field(0, ge=0, description="Total input tokens")
    total_tokens_out: int = Field(0, ge=0, description="Total output tokens")
    total_tokens: int = Field(0, ge=0, description="Total tokens")
    total_cost: Decimal | None = Field(None, description="Total cost")
    avg_tokens_per_request: Decimal | None = Field(None, description="Average tokens per request")
    top_models: dict[str, int] | None = Field(None, description="Request counts by model")

    model_config = ConfigDict(from_attributes=True)


class CenterUsageSummaryResponse(BaseModel):
    """Response schema for center usage summary"""

    center_id: str = Field(..., description="Center identifier")
    start_date: datetime = Field(..., description="Start of date range")
    end_date: datetime = Field(..., description="End of date range")
    summary: TokenUsageSummary = Field(..., description="Usage summary")


class AllCentersUsageSummaryResponse(BaseModel):
    """Response schema for all centers usage summary"""

    start_date: datetime = Field(..., description="Start of date range")
    end_date: datetime = Field(..., description="End of date range")
    centers: list[TokenUsageSummary] = Field(..., description="Per-center summaries")
    grand_total: TokenUsageSummary = Field(..., description="Grand total across all")


class DailyUsagePoint(BaseModel):
    """Single data point for daily usage"""

    date: datetime = Field(..., description="Usage date")
    total_tokens: int = Field(0, ge=0, description="Total tokens")
    total_requests: int = Field(0, ge=0, description="Total requests")
    total_cost: Decimal | None = Field(None, description="Total cost")


class UserUsageResponse(BaseModel):
    """Response schema for user usage"""

    user_id: UUID = Field(..., description="User identifier")
    center_id: str | None = Field(None, description="Center identifier")
    summary: TokenUsageSummary = Field(..., description="Usage summary")
    daily_usage: list[DailyUsagePoint] = Field(default_factory=list, description="Daily breakdown")


class ModelUsageResponse(BaseModel):
    """Response schema for model usage"""

    model_id: str = Field(..., description="Model identifier")
    model_provider: str | None = Field(None, description="Model provider")
    summary: TokenUsageSummary = Field(..., description="Usage summary")
