"""
Pydantic schemas for custom output visualization templates.

CRUD payloads and response models for the /api/v1/admin/output-templates
endpoints. Built-in templates are read-only; custom templates support full CRUD.

@see ADR-066: Domain-Neutral Visualization Template Architecture
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class OutputTemplateBase(BaseModel):
    """Shared fields for output templates."""

    template_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique slug identifier (e.g. 'score-table-timeline')",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable template name",
    )
    description: str = Field(
        default="",
        max_length=2000,
        description="Template description",
    )
    data_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema defining the expected data shape",
    )
    layout: dict[str, Any] = Field(
        default_factory=dict,
        description="Layout configuration with sections and component types",
    )
    export_formats: list[str] = Field(
        default_factory=list,
        description="Supported export formats (pdf, csv, json, excel)",
    )


class OutputTemplateCreate(OutputTemplateBase):
    """Payload for creating a custom output template."""


class OutputTemplateUpdate(BaseModel):
    """Payload for updating a custom output template (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    data_schema: dict[str, Any] | None = None
    layout: dict[str, Any] | None = None
    export_formats: list[str] | None = None


class OutputTemplateResponse(OutputTemplateBase):
    """Single output template response."""

    id: UUID
    is_builtin: bool = False
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OutputTemplateListResponse(BaseModel):
    """Paginated list of output templates."""

    templates: list[OutputTemplateResponse]
    total: int
    page: int
    page_size: int
