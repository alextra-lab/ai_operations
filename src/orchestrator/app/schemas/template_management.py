"""
Template Management Schemas for AI Operations Platform.

These schemas support CRUD operations, version control, and approval workflows
for prompt templates used in use case configurations.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
# Template CRUD Schemas
# ============================================================================


class TemplateBase(BaseModel):
    """Base template fields shared across operations."""

    template_id: str = Field(
        ..., description="Unique template identifier", min_length=1, max_length=255
    )
    prompt_type: str = Field(
        default="system",
        description="Type of prompt (system, user, assistant)",
        max_length=50,
    )
    template_content: str = Field(
        ..., description="Template content with variable placeholders", min_length=1
    )
    variables: list[str] = Field(
        default_factory=list, description="List of variable names used in template"
    )
    metadata_json: dict[str, Any] = Field(
        default_factory=dict, description="Additional template metadata"
    )


class TemplateCreate(TemplateBase):
    """Schema for creating a new template."""

    use_case_id: UUID | None = Field(None, description="Optional use case to bind this template to")
    deployment_status: str = Field(default="draft", description="Initial deployment status")


class TemplateUpdate(BaseModel):
    """Schema for updating an existing template."""

    template_content: str | None = Field(None, description="Updated template content")
    variables: list[str] | None = Field(None, description="Updated variable list")
    metadata_json: dict[str, Any] | None = Field(None, description="Updated metadata")
    deployment_status: str | None = Field(None, description="Updated deployment status")


class TemplateResponse(TemplateBase):
    """Schema for template responses."""

    id: UUID = Field(..., description="Template UUID primary key")
    use_case_id: UUID | None = Field(None, description="Associated use case ID")
    version_number: int = Field(..., description="Template version number")
    is_active_version: bool = Field(..., description="Whether this is the active version")
    deployment_status: str = Field(
        ..., description="Current deployment status (draft/pending/approved/deployed)"
    )
    created_by_user_id: UUID | None = Field(None, description="User who created this version")
    approved_by_user_id: UUID | None = Field(None, description="User who approved this version")
    approved_at: datetime | None = Field(None, description="When this version was approved")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    """Schema for paginated template list."""

    templates: list[TemplateResponse] = Field(..., description="List of templates")
    total_count: int = Field(..., description="Total number of templates matching filter")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")


# ============================================================================
# Version Control Schemas
# ============================================================================


class TemplateVersionResponse(BaseModel):
    """Schema for template version information."""

    id: UUID
    template_id: str
    version_number: int
    is_active_version: bool
    deployment_status: str
    created_by_user_id: UUID | None
    approved_by_user_id: UUID | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemplateVersionListResponse(BaseModel):
    """Schema for template version history."""

    template_id: str
    versions: list[TemplateVersionResponse]
    total_versions: int


class TemplateVersionCreate(BaseModel):
    """Schema for creating a new template version."""

    template_content: str = Field(..., description="New template content")
    variables: list[str] = Field(default_factory=list, description="Variable list for new version")
    metadata_json: dict[str, Any] = Field(
        default_factory=dict, description="Metadata for new version"
    )
    change_notes: str | None = Field(None, description="Notes describing changes in this version")


# ============================================================================
# Approval Workflow Schemas
# ============================================================================


class TemplateApprovalRequest(BaseModel):
    """Schema for template approval request."""

    approval_notes: str | None = Field(None, description="Notes from approver")


class TemplateRejectionRequest(BaseModel):
    """Schema for template rejection."""

    rejection_reason: str = Field(
        ..., description="Reason for rejecting the template", min_length=1
    )


class TemplateActivationRequest(BaseModel):
    """Schema for activating a specific template version."""

    version_number: int = Field(..., description="Version number to activate", ge=1)


# ============================================================================
# Template Comparison/Diff Schemas
# ============================================================================


class TemplateDiffRequest(BaseModel):
    """Schema for comparing two template versions."""

    version_1: int = Field(..., description="First version number to compare")
    version_2: int = Field(..., description="Second version number to compare")


class TemplateDiffResponse(BaseModel):
    """Schema for template diff result."""

    template_id: str
    version_1: int
    version_2: int
    content_diff: str = Field(..., description="Unified diff of template content")
    variables_added: list[str] = Field(default_factory=list)
    variables_removed: list[str] = Field(default_factory=list)
    metadata_changes: dict[str, Any] = Field(default_factory=dict)
