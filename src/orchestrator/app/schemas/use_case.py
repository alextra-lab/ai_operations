"""
Use Case Schema for AI Operations Platform.

This module defines Pydantic schema models for use case-related operations,
including the menu endpoint that returns available use cases to the UI.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from .intent import RequestType


class UseCaseExecution(BaseModel):
    """
    Schema for use case execution request.

    This schema defines the structure of a use case execution request,
    including input fields and optional configuration overrides.
    """

    inputs: dict[str, Any] = Field(..., description="Input field values for the use case template")
    overrides: dict[str, Any] | None = Field(
        None, description="Optional configuration overrides for this execution"
    )


class UseCaseListItem(BaseModel):
    """
    Schema for use case items returned by the menu endpoint.

    This schema provides a lightweight representation of use cases
    suitable for UI display, excluding sensitive configuration data.
    """

    id: UUID = Field(..., description="Unique identifier for the use case")
    name: str = Field(..., description="Display name for the use case", min_length=1)
    description: str | None = Field(None, description="Brief description of the use case")
    category: str | None = Field(None, description="Category for grouping use cases")
    intent_type: RequestType = Field(..., description="Type of request this use case handles")
    is_active: bool = Field(True, description="Whether the use case is active")
    lifecycle_state: str = Field(
        "published", description="Lifecycle state (draft, published, etc.)"
    )
    version: str = Field("1.0", description="Version string")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    # Optional UI fields
    icon: str | None = Field(None, description="Icon identifier for UI display")
    tags: list[str] = Field(
        default_factory=list, description="Tags for categorization and filtering"
    )


class UseCaseListResponse(BaseModel):
    """
    Response schema for the use case menu endpoint.
    """

    use_cases: list[UseCaseListItem] = Field(
        ..., description="List of available use cases for the current user"
    )
    total: int = Field(..., description="Total number of available use cases", ge=0)
