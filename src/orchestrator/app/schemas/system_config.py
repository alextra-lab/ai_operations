"""
System Configuration Schemas

Pydantic models for system configuration sections.
ADR-038: JSONB for flexible configuration storage.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class LogLevel(str, Enum):
    """Log level options."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class PasswordPolicy(BaseModel):
    """Password policy configuration."""

    min_length: int = Field(ge=6, le=32, default=8, description="Minimum password length")
    require_uppercase: bool = Field(default=True, description="Require uppercase letters")
    require_lowercase: bool = Field(default=True, description="Require lowercase letters")
    require_numbers: bool = Field(default=True, description="Require numbers")
    require_special: bool = Field(default=False, description="Require special characters")


class CorpusConfig(BaseModel):
    """Corpus management configuration."""

    chunk_size: int = Field(
        ge=128,
        le=8192,
        default=512,
        description="Document chunk size in tokens (must not exceed embedding model context window)",
    )
    chunk_overlap: int = Field(
        ge=0,
        le=512,
        default=50,
        description="Character overlap between chunks",
    )
    default_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Default embedding model for collections",
    )
    max_document_size_mb: int = Field(
        ge=1,
        le=500,
        default=50,
        description="Maximum document size in MB",
    )
    allowed_file_types: list[str] = Field(
        default=["pdf", "txt", "docx", "md"],
        description="Allowed file types for upload",
    )

    @field_validator("allowed_file_types")
    @classmethod
    def validate_file_types(cls, v: list[str]) -> list[str]:
        """Validate file types are non-empty strings."""
        if not v:
            raise ValueError("At least one file type must be allowed")
        valid_types = {"pdf", "txt", "docx", "md", "csv", "json", "xml", "html"}
        for ft in v:
            if not ft or ft not in valid_types:
                raise ValueError(f"Invalid file type: {ft}. Must be one of: {valid_types}")
        return v


class AuthConfig(BaseModel):
    """Authentication configuration."""

    session_timeout_minutes: int = Field(
        ge=5,
        le=1440,
        default=60,
        description="Session timeout in minutes",
    )
    refresh_token_ttl_days: int = Field(
        ge=1,
        le=90,
        default=30,
        description="Refresh token time-to-live in days",
    )
    password_policy: PasswordPolicy = Field(
        default_factory=PasswordPolicy, description="Password policy settings"
    )


class FeatureFlags(BaseModel):
    """Feature flags configuration."""

    multi_collection_search: bool = Field(
        default=False,
        description="Enable multi-collection RAG search",
    )
    export_functionality: bool = Field(default=True, description="Enable export features")
    conversation_cache: bool = Field(default=True, description="Enable conversation caching")
    telemetry_enabled: bool = Field(default=True, description="Enable telemetry collection")


class SystemConfig(BaseModel):
    """System-level configuration."""

    log_level: LogLevel = Field(default=LogLevel.INFO, description="System log level")
    max_workers: int = Field(ge=1, le=32, default=4, description="Maximum worker threads")
    request_timeout_seconds: int = Field(
        ge=5,
        le=300,
        default=30,
        description="Request timeout in seconds",
    )
    enable_debug_endpoints: bool = Field(default=False, description="Enable debug API endpoints")


class SystemConfigFull(BaseModel):
    """Full system configuration (all sections)."""

    corpus: CorpusConfig
    auth: AuthConfig
    features: FeatureFlags
    system: SystemConfig


class ConfigSectionResponse(BaseModel):
    """Response for configuration section GET/PUT."""

    section: str
    config: dict[str, Any]
    updated_at: str
    updated_by: str | None = None
    restart_required: bool = False


class ConfigExportResponse(BaseModel):
    """Response for configuration export."""

    config_yaml: str
    exported_at: str


class ConfigImportRequest(BaseModel):
    """Request for configuration import."""

    config_yaml: str = Field(description="YAML configuration to import")
    validate_only: bool = Field(default=False, description="Validate without applying")


class ConfigImportResponse(BaseModel):
    """Response for configuration import."""

    success: bool
    sections_updated: list[str]
    restart_required: bool = False
    validation_errors: list[str] | None = None
