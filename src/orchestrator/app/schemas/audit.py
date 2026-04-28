"""
Pydantic schemas for audit log API endpoints.

These schemas define the request/response models for audit log queries.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    """Response model for a single audit log entry."""

    id: UUID
    event_time: datetime
    actor_user_id: UUID | None
    actor_username: str | None = None  # Joined from users table
    actor_roles: list[str]
    action: str
    resource_type: str
    resource_id: str | None
    use_case_id: UUID | None
    use_case_name: str | None = None  # Joined from use_cases table
    request_id: str | None
    client_ip: str | None
    user_agent: str | None
    success: bool
    details: dict
    created_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Paginated response for audit log queries."""

    total: int = Field(..., description="Total number of matching records")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of records per page")
    total_pages: int = Field(..., description="Total number of pages")
    logs: list[AuditLogResponse] = Field(..., description="Audit log entries for current page")


class AuditLogStatsResponse(BaseModel):
    """Statistics summary for audit logs."""

    total_events: int = Field(..., description="Total number of audit events")
    success_count: int = Field(..., description="Number of successful events")
    failure_count: int = Field(..., description="Number of failed events")
    unique_users: int = Field(..., description="Number of unique users")
    unique_resource_types: int = Field(..., description="Number of unique resource types")
    date_range_start: datetime | None = Field(None, description="Start of date range")
    date_range_end: datetime | None = Field(None, description="End of date range")
    top_actions: list[dict] = Field(default_factory=list, description="Most common actions")
    top_resource_types: list[dict] = Field(
        default_factory=list, description="Most common resource types"
    )
