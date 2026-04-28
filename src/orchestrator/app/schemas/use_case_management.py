"""
Use Case Management Schemas for AI Operations Platform.

Pydantic models for Use Case CRUD, versioning, and lifecycle management.
Use Cases are sovereign entities that own all configuration and prompts.

Architecture: ADR-018 Use Case Owned Architecture
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shared.logging_utils.fastapi import get_logger

logger = get_logger(__name__)

# ============================================================================
# Prompt Set Models
# ============================================================================


class FewshotPair(BaseModel):
    """Example user/assistant pair for few-shot learning."""

    user: str = Field(..., description="User message in example")
    assistant: str = Field(..., description="Assistant response in example")


class UseCasePromptSet(BaseModel):
    """Multi-role prompt set for a use case."""

    system_prompt: str | None = Field(
        None, description="User-visible system prompt (persona, task)"
    )
    developer_prompt: str | None = Field(
        None,
        description="Hidden developer instructions (citations, format, guardrails)",
    )
    prompt_template: str | None = Field(
        None, description="User-facing input guidance with {{variable}} placeholders"
    )
    fewshots: list[FewshotPair] = Field(
        default_factory=list, description="Example user/assistant pairs"
    )
    variables: list[str] = Field(
        default_factory=list, description="Required variables for template substitution"
    )


# ============================================================================
# Use Case Request/Response Models
# ============================================================================


class UseCaseCreateRequest(BaseModel):
    """Request to create a new use case."""

    use_case_id: str = Field(
        ..., min_length=1, max_length=255, description="Unique use case identifier"
    )
    name: str = Field(..., min_length=1, max_length=255, description="Display name")
    description: str | None = Field(None, description="Use case description")
    category: str | None = Field(
        None, max_length=100, description="Category (security, general, etc.)"
    )
    intent_type: str = Field(..., description="Intent type (QUERY, RULE_GENERATION, etc.)")
    team_id: str | None = Field(
        None,
        max_length=100,
        description="Developer team ID (format: team:team_name). Auto-assigned if user has teams.",
    )
    config_json: dict[str, Any] = Field(
        default_factory=dict,
        description="Complete use case configuration (UseCaseConfig)",
    )
    metadata_json: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    prompts: UseCasePromptSet | None = Field(None, description="Multi-role prompt set")


class UseCaseUpdateRequest(BaseModel):
    """Request to update use case details."""

    name: str | None = Field(None, min_length=1, max_length=255, description="Updated name")
    description: str | None = Field(None, description="Updated description")
    category: str | None = Field(None, max_length=100, description="Updated category")
    config_json: dict[str, Any] | None = Field(
        None, description="Updated configuration (creates new version)"
    )
    metadata_json: dict[str, Any] | None = Field(
        None, description="Updated metadata (for parameter injection audit trail)"
    )
    prompts: UseCasePromptSet | None = Field(None, description="Updated prompt set")


class UseCaseCloneRequest(BaseModel):
    """Request to clone a use case."""

    new_use_case_id: str = Field(
        ..., min_length=1, max_length=255, description="ID for cloned use case"
    )
    new_name: str | None = Field(
        None, description="Name for clone (defaults to 'Original Name (Copy)')"
    )


class StateTransitionRequest(BaseModel):
    """Request to transition use case lifecycle state."""

    to_state: str = Field(..., description="Target state (draft, review, published, archived)")


class UseCaseResponse(BaseModel):
    """Response with complete use case details."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Internal UUID")
    use_case_id: str = Field(..., description="Unique use case identifier")
    name: str = Field(..., description="Display name")
    description: str | None = Field(None, description="Use case description")
    category: str | None = Field(None, description="Category")
    intent_type: str = Field(..., description="Intent type")
    team_id: str | None = Field(None, description="Developer team ID (format: team:team_name)")
    version: int = Field(..., description="Current version number")
    lifecycle_state: str = Field(
        ..., description="Lifecycle state (draft, review, published, archived)"
    )
    is_active: bool = Field(..., description="Whether use case is active for execution")
    config_json: dict[str, Any] = Field(..., description="Complete configuration")
    metadata_json: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    prompts: UseCasePromptSet | None = Field(None, description="Prompt set (if loaded)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by_user_id: UUID | None = Field(None, description="Creator user ID")
    approved_by_user_id: UUID | None = Field(None, description="Approver user ID")
    published_by_user_id: UUID | None = Field(None, description="Publisher user ID")
    approved_at: datetime | None = Field(None, description="Approval timestamp")
    published_at: datetime | None = Field(None, description="Publication timestamp")

    @classmethod
    def from_orm(cls, db_obj: Any) -> "UseCaseResponse":
        """Create response from database model, extracting prompts from metadata."""
        # Extract prompts from metadata if present
        prompts_data = db_obj.metadata_json.get("prompts") if db_obj.metadata_json else None
        prompts = None
        if prompts_data:
            try:
                prompts = UseCasePromptSet(**prompts_data)
            except Exception as e:
                # If prompts data is invalid, log and continue without prompts
                # This prevents 500 errors from corrupted prompt data
                logger.warning(
                    "Invalid prompts data in use case %s metadata, skipping prompts: %s",
                    db_obj.id,
                    str(e),
                    exc_info=True,
                )

        # Create a clean metadata_json without the prompts key to avoid duplication
        clean_metadata = dict(db_obj.metadata_json) if db_obj.metadata_json else {}
        clean_metadata.pop(
            "prompts", None
        )  # Remove prompts from metadata since it's in top-level field

        # Create response using model_validate
        return cls.model_validate(
            {
                **{k: getattr(db_obj, k) for k in cls.model_fields if hasattr(db_obj, k)},
                "metadata_json": clean_metadata,
                "prompts": prompts,
            }
        )


class UseCaseListResponse(BaseModel):
    """Response with paginated list of use cases."""

    use_cases: list[UseCaseResponse] = Field(..., description="List of use cases")
    total: int = Field(..., description="Total count (before pagination)")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


# ============================================================================
# Version History Models
# ============================================================================


class VersionSnapshot(BaseModel):
    """Snapshot of a specific version."""

    version: int = Field(..., description="Version number")
    config_snapshot: dict[str, Any] = Field(..., description="Configuration at this version")
    updated_at: str = Field(..., description="When this version was created (ISO format)")
    updated_by: str | None = Field(None, description="User who created this version")
    is_active: bool = Field(default=False, description="Whether this is the active version")


class UseCaseVersionListResponse(BaseModel):
    """Response with version history for a use case."""

    use_case_id: str = Field(..., description="Use case identifier")
    current_version: int = Field(..., description="Current version number")
    versions: list[VersionSnapshot] = Field(..., description="All versions (oldest to newest)")
    total_versions: int = Field(..., description="Total number of versions")
