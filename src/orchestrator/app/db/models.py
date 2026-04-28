# pylint: disable=import-error
"""
This module defines backend-specific database models using SQLAlchemy's declarative base.

Note: User and RefreshToken models are now in shared.auth.models for consistency
across all services.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# We reference shared auth models to reuse the canonical users table.
from shared.auth.models import User as AuthUser
from shared.logging_utils.fastapi import configure_logging

from .database import Base  # Fix for mypy/pylance

# Configure logger for the models module with a descriptive service name.
logger = configure_logging(service_name="db_models")


class TimestampMixin:
    """Mixin providing UTC-aware created/updated timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
        nullable=False,
    )


class UserRoleMembership(TimestampMixin, Base):  # type: ignore[valid-type,misc]
    """
    Join table storing Layer 2 custom use case grouping roles for users.

    Examples: threat_hunting, incident_response, compliance_monitoring, threat_intelligence
    Note: System roles (Layer 1) are stored in users.role column, NOT here.
    """

    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role", name="uq_user_roles_user_role"),
        # No CHECK constraint per ADR-041 to allow dynamic custom roles
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(AuthUser.__table__.c.id, ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id)
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )


class UseCase(TimestampMixin, Base):  # type: ignore[valid-type,misc]
    """Registered operational use case."""

    __tablename__ = "use_cases"
    __table_args__ = (
        UniqueConstraint("use_case_id", name="uq_use_cases_use_case_id"),
        CheckConstraint(
            "lifecycle_state IN ('draft','review','published','archived')",
            name="ck_use_cases_lifecycle_state",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    use_case_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100))
    intent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id)
    )
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id)
    )
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id)
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    team_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    prompt_templates: Mapped[list[PromptTemplate]] = relationship(
        "PromptTemplate", back_populates="use_case", cascade="all, delete-orphan"
    )
    assignments: Mapped[list[UserUseCaseAssignment]] = relationship(
        "UserUseCaseAssignment", back_populates="use_case", cascade="all, delete-orphan"
    )
    role_assignments: Mapped[list[RoleUseCaseAssignment]] = relationship(
        "RoleUseCaseAssignment", back_populates="use_case", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list[AuditLog]] = relationship("AuditLog", back_populates="use_case")


class PromptTemplate(TimestampMixin, Base):  # type: ignore[valid-type,misc]
    """Versioned prompt template bound to a use case."""

    __tablename__ = "prompt_templates"
    __table_args__ = (
        UniqueConstraint("template_id", "version_number", name="uq_prompt_templates_version"),
        Index(
            "ix_prompt_templates_active",
            "template_id",
            "is_active_version",
            "deployment_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[str] = mapped_column(String(255), nullable=False)
    use_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("use_cases.id", ondelete="SET NULL")
    )
    prompt_type: Mapped[str] = mapped_column(String(50), default="system", nullable=False)
    version_number: Mapped[int] = mapped_column(default=1, nullable=False)
    template_content: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )
    is_active_version: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deployment_status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id)
    )
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id)
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    use_case: Mapped[UseCase | None] = relationship("UseCase", back_populates="prompt_templates")


class UserUseCaseAssignment(TimestampMixin, Base):  # type: ignore[valid-type,misc]
    """Per-use-case entitlements for a user."""

    __tablename__ = "user_use_case_assignments"
    __table_args__ = (
        UniqueConstraint("user_id", "use_case_id", "assigned_role", name="uq_use_case_assignment"),
        # No CHECK constraint on assigned_role per ADR-041 to allow custom roles
        CheckConstraint("status IN ('active','revoked')", name="ck_use_case_assignment_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(AuthUser.__table__.c.id, ondelete="CASCADE"),
        nullable=False,
    )
    use_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("use_cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_role: Mapped[str] = mapped_column(String(20), nullable=False)
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id)
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=UTC), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    use_case: Mapped[UseCase] = relationship("UseCase", back_populates="assignments")


class RoleUseCaseAssignment(TimestampMixin, Base):  # type: ignore[valid-type,misc]
    """
    Role-based use case access control.

    Links system roles to use cases. Users inherit use case access
    through their role memberships (user_roles table).

    See ADR-041 for architecture rationale.
    """

    __tablename__ = "role_use_case_assignments"
    __table_args__ = (
        UniqueConstraint("role_name", "use_case_id", name="uq_role_use_case_assignment"),
        # No CHECK constraint on role_name - allows dynamic custom roles
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    role_name: Mapped[str] = mapped_column(String(50), nullable=False)

    use_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("use_cases.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Audit fields
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id)
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=UTC), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Metadata
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    # Relationships
    use_case: Mapped[UseCase] = relationship("UseCase", back_populates="role_assignments")


class EncryptionKey(TimestampMixin, Base):  # type: ignore[valid-type,misc]
    """Managed encryption key metadata."""

    __tablename__ = "encryption_keys"
    __table_args__ = (UniqueConstraint("key_id", name="uq_encryption_keys_key_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_id: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id)
    )
    key_type: Mapped[str] = mapped_column(String(50), default="conversation_data", nullable=False)
    algorithm: Mapped[str] = mapped_column(String(50), default="AES-256-GCM", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rotation_count: Mapped[int] = mapped_column(default=0, nullable=False)
    hsm_key_reference: Mapped[str | None] = mapped_column(String(500))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id)
    )


class AuditLog(Base):  # type: ignore[valid-type,misc]
    """Immutable audit trail entry."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_use_case_time", "use_case_id", "event_time"),
        Index("ix_audit_logs_actor_time", "actor_user_id", "event_time"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=UTC), nullable=False
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id)
    )
    actor_roles: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255))
    use_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("use_cases.id")
    )
    request_id: Mapped[str | None] = mapped_column(String(64))
    client_ip: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    use_case: Mapped[UseCase | None] = relationship("UseCase", back_populates="audit_logs")


class QueryHistory(TimestampMixin, Base):  # type: ignore[valid-type,misc]
    """Complete query execution history with metrics, results, and threading support."""

    __tablename__ = "query_history"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_query_history_run_id"),
        Index("idx_query_history_user_id", "user_id"),
        Index("idx_query_history_center_id", "center_id"),
        Index("idx_query_history_use_case_id", "use_case_id"),
        Index(
            "idx_query_history_created_at",
            "created_at",
            postgresql_ops={"created_at": "DESC"},
        ),
        Index("idx_query_history_parent_query_id", "parent_query_id"),
        Index("idx_query_history_thread_id", "thread_id"),
        Index("idx_query_history_response_status", "response_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # User context
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(AuthUser.__table__.c.id, ondelete="CASCADE"),
        nullable=False,
    )
    center_id: Mapped[str | None] = mapped_column(String(255))

    # Use case context
    use_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("use_cases.id", ondelete="SET NULL")
    )
    use_case_name: Mapped[str | None] = mapped_column(String(255))
    intent_type: Mapped[str | None] = mapped_column(String(50))

    # Query details
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    query_params: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Response details
    response_text: Mapped[str | None] = mapped_column(Text)
    response_status: Mapped[str] = mapped_column(String(50), nullable=False)

    # Metrics and metadata
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer)

    # Sources and citations
    sources: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    citations: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Threading and forking
    parent_query_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("query_history.id", ondelete="SET NULL")
    )
    thread_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    fork_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Audit and lifecycle
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Additional context
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    # Relationships
    parent_query: Mapped[QueryHistory | None] = relationship(
        "QueryHistory",
        remote_side=[id],
        back_populates="child_queries",
    )
    child_queries: Mapped[list[QueryHistory]] = relationship(
        "QueryHistory",
        back_populates="parent_query",
        cascade="all, delete-orphan",
    )


class ContextThread(TimestampMixin, Base):  # type: ignore[valid-type,misc]
    """Conversation threads for multi-turn interactions."""

    __tablename__ = "context_threads"
    __table_args__ = (
        UniqueConstraint("thread_id", name="uq_context_threads_thread_id"),
        Index("idx_context_threads_user_id", "user_id"),
        Index("idx_context_threads_is_active", "is_active"),
        Index(
            "idx_context_threads_created_at",
            "created_at",
            postgresql_ops={"created_at": "DESC"},
        ),
        Index("idx_context_threads_discussion_id", "discussion_id"),
        Index("idx_context_threads_discussion_user", "discussion_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, nullable=False
    )

    # Thread metadata
    title: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)

    # User context
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(AuthUser.__table__.c.id, ondelete="CASCADE"),
        nullable=False,
    )
    center_id: Mapped[str | None] = mapped_column(String(255))

    # NEW: DiscussionID for incident/ticket correlation
    discussion_id: Mapped[str | None] = mapped_column(String(255))

    # NEW: Use case tracking
    use_case_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    use_case_name: Mapped[str | None] = mapped_column(String(255))

    # NEW: Source tracking (ui, api, soar)
    source: Mapped[str] = mapped_column(String(50), default="ui", nullable=False)

    # Thread state
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # NEW: Context size tracking for compaction
    context_size_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_context_tokens: Mapped[int] = mapped_column(Integer, default=8000, nullable=False)
    auto_compact: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # First and last messages
    first_query_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("query_history.id", ondelete="SET NULL")
    )
    last_query_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("query_history.id", ondelete="SET NULL")
    )

    # Audit
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # NEW: Last activity timestamp
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=UTC), nullable=False
    )

    # Additional context
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    # Relationships
    messages: Mapped[list[ThreadMessage]] = relationship(
        "ThreadMessage",
        back_populates="thread",
        cascade="all, delete-orphan",
    )


class ThreadMessage(Base):  # type: ignore[valid-type,misc]
    """Ordered messages within conversation threads."""

    __tablename__ = "thread_messages"
    __table_args__ = (
        UniqueConstraint(
            "thread_id",
            "sequence_number",
            name="thread_messages_thread_sequence_unique",
        ),
        CheckConstraint(
            "role IN ('user', 'assistant', 'system')",
            name="ck_thread_messages_role",
        ),
        Index("idx_thread_messages_thread_id", "thread_id"),
        Index("idx_thread_messages_query_id", "query_id"),
        Index("idx_thread_messages_sequence", "thread_id", "sequence_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Thread association
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("context_threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    query_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("query_history.id", ondelete="CASCADE")
    )

    # Message sequence
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Message role and content
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # NEW: Token count for compaction decisions
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # NEW: Model used for this response
    model_used: Mapped[str | None] = mapped_column(String(100))

    # NEW: Compaction flag
    is_summary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    original_message_count: Mapped[int | None] = mapped_column(Integer)

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=UTC), nullable=False
    )

    # Relationships
    thread: Mapped[ContextThread] = relationship("ContextThread", back_populates="messages")


class TokenUsage(Base):  # type: ignore[valid-type,misc]
    """Tracks all LLM token consumption for quota management and cost analysis."""

    __tablename__ = "token_usage"
    __table_args__ = (
        Index("idx_token_usage_user_id", "user_id"),
        Index("idx_token_usage_center_id", "center_id"),
        Index("idx_token_usage_run_id", "run_id"),
        Index("idx_token_usage_use_case_id", "use_case_id"),
        Index("idx_token_usage_model_id", "model_id"),
        Index(
            "idx_token_usage_created_at",
            "created_at",
            postgresql_ops={"created_at": "DESC"},
        ),
        Index("idx_token_usage_center_created", "center_id", "created_at"),
        Index("idx_token_usage_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Request context
    run_id: Mapped[str] = mapped_column(String(255), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(255))

    # User and organization context
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(AuthUser.__table__.c.id, ondelete="CASCADE"),
        nullable=False,
    )
    center_id: Mapped[str | None] = mapped_column(String(255))

    # Use case context
    use_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("use_cases.id", ondelete="SET NULL")
    )
    use_case_name: Mapped[str | None] = mapped_column(String(255))
    intent_type: Mapped[str | None] = mapped_column(String(50))

    # Model information
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    model_provider: Mapped[str | None] = mapped_column(String(100))
    model_version: Mapped[str | None] = mapped_column(String(100))

    # Token counts
    tokens_in: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Cost tracking (optional, can be calculated)
    cost_per_1k_in: Mapped[float | None] = mapped_column()
    cost_per_1k_out: Mapped[float | None] = mapped_column()
    total_cost: Mapped[float | None] = mapped_column()

    # Request classification
    request_type: Mapped[str | None] = mapped_column(String(50))
    streaming_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timing information
    call_duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=UTC), nullable=False
    )

    # Additional metadata
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )


# =============================================================================
# MODEL REGISTRY MODELS
# =============================================================================


import enum


class ModelTypeEnum(str, enum.Enum):
    """Model type enumeration matching database enum."""

    LLM = "llm"
    EMBEDDING = "embedding"
    REASONING = "reasoning"
    MULTIMODAL = "multimodal"
    VISION = "vision"
    AUDIO = "audio"
    OTHER = "other"


class ModelProviderEnum(str, enum.Enum):
    """Model provider enumeration matching database enum."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    OTHER = "other"


class Model(TimestampMixin, Base):  # type: ignore[valid-type,misc]
    """
    AI/ML model registry with comprehensive metadata.

    Stores capabilities, pricing, and performance characteristics
    for available models to enable intelligent model selection.
    """

    __tablename__ = "models"
    __table_args__ = (
        UniqueConstraint("model_id", name="uq_models_model_id"),
        Index("idx_models_model_id", "model_id"),
        Index("idx_models_provider", "provider"),
        Index("idx_models_model_type", "model_type"),
        Index("idx_models_is_available", "is_available"),
        Index("idx_models_specialization", "specialization"),
        Index("idx_models_deprecated", "deprecated", postgresql_where="deprecated = false"),
        CheckConstraint(
            "context_window IS NULL OR context_window > 0",
            name="ck_models_valid_context_window",
        ),
        CheckConstraint(
            "(input_price_per_million IS NULL OR input_price_per_million >= 0) AND "
            "(output_price_per_million IS NULL OR output_price_per_million >= 0)",
            name="ck_models_valid_pricing",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic identification
    model_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_type: Mapped[str] = mapped_column(
        Enum(
            ModelProviderEnum,
            name="model_provider_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    provider: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    model_type: Mapped[str] = mapped_column(
        Enum(
            ModelTypeEnum,
            name="model_type_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    # Capabilities
    context_window: Mapped[int | None] = mapped_column(Integer)
    max_input_tokens: Mapped[int | None] = mapped_column(Integer)
    max_output_tokens: Mapped[int | None] = mapped_column(Integer)
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer)
    supports_tools: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_vision: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_audio: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_reasoning_model: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Reasoning configuration
    reasoning_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Performance characteristics
    typical_latency_ms: Mapped[int | None] = mapped_column(Integer)
    tokens_per_second: Mapped[float | None] = mapped_column()

    # Pricing (per 1M tokens) - using Decimal in schema, but float here for SQLAlchemy
    input_price_per_million: Mapped[float | None] = mapped_column()
    output_price_per_million: Mapped[float | None] = mapped_column()

    # Metadata
    description: Mapped[str | None] = mapped_column(Text)
    specialization: Mapped[str | None] = mapped_column(String(255))
    version: Mapped[str | None] = mapped_column(String(50))
    release_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    deprecated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deprecation_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))

    # Configuration
    default_temperature: Mapped[float] = mapped_column(default=0.7, nullable=False)
    temperature_range: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default={"min": 0.0, "max": 2.0}, nullable=False
    )
    recommended_use_cases: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, nullable=False
    )

    # API configuration
    api_endpoint: Mapped[str | None] = mapped_column(String(512))
    api_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Status tracking
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    health_status: Mapped[str] = mapped_column(String(50), default="unknown", nullable=False)

    # Audit
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id)
    )

    # Additional metadata
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)


class ModelPricingHistory(Base):  # type: ignore[valid-type,misc]
    """Historical per-model pricing with effective windows.

    This table records input/output prices per million tokens for each model
    with an effective interval. At runtime we select the record active at the
    execution timestamp to compute immutable costs.
    """

    __tablename__ = "model_pricing_history"
    __table_args__ = (
        UniqueConstraint(
            "model_id", "effective_from", name="idx_model_pricing_history_unique_anchor"
        ),
        Index(
            "idx_model_pricing_history_model_time",
            "model_id",
            "effective_from",
            postgresql_include=None,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(Model.__table__.c.id, ondelete="CASCADE"),
        nullable=False,
    )

    # Pricing (per 1M tokens, EUR)
    input_price_per_million: Mapped[float] = mapped_column(nullable=False)
    output_price_per_million: Mapped[float] = mapped_column(nullable=False)

    # Effective window
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Audit
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id, ondelete="SET NULL")
    )
    change_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=UTC), nullable=False
    )


class ModelCache(Base):  # type: ignore[valid-type,misc]
    """Caching layer for model metadata from inference server."""

    __tablename__ = "model_cache"
    __table_args__ = (
        UniqueConstraint("model_id", "cache_key", name="unique_model_cache_key"),
        Index("idx_model_cache_expires", "expires_at"),
        Index("idx_model_cache_model_id", "model_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    cache_key: Mapped[str] = mapped_column(String(255), nullable=False)
    cache_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=UTC), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# =============================================================================
# TOOL MANAGEMENT MODELS
# =============================================================================


class Tool(Base):  # type: ignore[valid-type,misc]
    """Platform-level tool configurations for MCP integration."""

    __tablename__ = "tools"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic information
    tool_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(100))

    # DEPRECATED: Hybrid Architecture (ADR-001)
    # Kept for backward compatibility - all MCPs now run in Orchestrator
    tool_purpose: Mapped[str] = mapped_column(String(50), nullable=False, default="orchestrator")
    service_location: Mapped[str] = mapped_column(
        String(50), nullable=False, default="orchestrator"
    )

    # NEW: Security Classification (ADR-057)
    data_source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="internal")
    data_flow_direction: Mapped[str] = mapped_column(String(20), nullable=False, default="ingress")
    network_access_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="internal"
    )
    max_data_sensitivity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="internal"
    )

    # MCP Configuration
    mcp_server_type: Mapped[str] = mapped_column(String(50), nullable=False)
    mcp_command: Mapped[str | None] = mapped_column(Text)
    mcp_endpoint: Mapped[str | None] = mapped_column(String(500))
    mcp_protocol_version: Mapped[str] = mapped_column(
        String(20), default="2024-11-05", nullable=False
    )

    # Capabilities
    capabilities: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    parameters_schema: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Authentication
    requires_authentication: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    authentication_type: Mapped[str | None] = mapped_column(String(50))
    secret_name: Mapped[str | None] = mapped_column(String(255))
    config_options: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Limits
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    rate_limit_per_minute: Mapped[int | None] = mapped_column(Integer)
    max_concurrent_calls: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    # Lifecycle
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_healthy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_health_check: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    health_check_interval_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)

    # Metadata
    version: Mapped[str | None] = mapped_column(String(50))
    documentation_url: Mapped[str | None] = mapped_column(String(500))
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id, ondelete="SET NULL")
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id, ondelete="SET NULL")
    )

    # Table configuration with indexes and constraints
    __table_args__ = (
        Index("idx_tools_category", "category"),
        Index("idx_tools_purpose", "tool_purpose"),
        Index("idx_tools_service_location", "service_location"),
        Index("idx_tools_enabled", "is_enabled", postgresql_where="is_enabled = true"),
        Index("idx_tools_healthy", "is_healthy", postgresql_where="is_healthy = true"),
        Index("idx_tools_tool_id", "tool_id"),
        # Security classification indexes (ADR-057)
        Index("idx_tools_data_source_type", "data_source_type"),
        Index("idx_tools_security", "data_source_type", "max_data_sensitivity"),
        CheckConstraint(
            "category IN ('database', 'vector_db', 'web_scraping', 'reasoning', 'documentation', 'code_analysis', 'threat_intel', 'custom')",
            name="valid_category",
        ),
        CheckConstraint(
            "tool_purpose IN ('retrieval', 'orchestrator')",
            name="valid_tool_purpose",
        ),
        CheckConstraint(
            "service_location IN ('retrieval_service', 'orchestrator')",
            name="valid_service_location",
        ),
        CheckConstraint(
            "mcp_server_type IN ('stdio', 'sse', 'http')",
            name="valid_mcp_server_type",
        ),
        # Security classification constraints (ADR-057)
        CheckConstraint(
            "data_source_type IN ('internal', 'external', 'none', 'mixed')",
            name="valid_data_source_type",
        ),
        CheckConstraint(
            "data_flow_direction IN ('ingress', 'egress', 'bidirectional', 'none')",
            name="valid_data_flow_direction",
        ),
        CheckConstraint(
            "network_access_level IN ('isolated', 'internal', 'external')",
            name="valid_network_access_level",
        ),
        CheckConstraint(
            "max_data_sensitivity IN ('public', 'internal', 'confidential', 'restricted')",
            name="valid_max_data_sensitivity",
        ),
    )

    # Relationships
    secrets: Mapped[list[ToolSecret]] = relationship(
        "ToolSecret", back_populates="tool", cascade="all, delete-orphan"
    )
    health_checks: Mapped[list[ToolHealthCheck]] = relationship(
        "ToolHealthCheck", back_populates="tool", cascade="all, delete-orphan"
    )
    permissions: Mapped[list[ToolPermission]] = relationship(
        "ToolPermission", back_populates="tool", cascade="all, delete-orphan"
    )
    invocations: Mapped[list[ToolInvocation]] = relationship(
        "ToolInvocation", back_populates="tool"
    )


class ToolSecret(Base):  # type: ignore[valid-type,misc]
    """Encrypted storage for tool API keys and credentials."""

    __tablename__ = "tool_secrets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Tool association
    tool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tools.id", ondelete="CASCADE"), nullable=False
    )

    # Secret information
    secret_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    secret_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Encrypted storage
    encrypted_value: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False
    )  # BYTEA in PostgreSQL
    encryption_key_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Lifecycle
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id, ondelete="SET NULL")
    )
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    access_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Table configuration with indexes and constraints
    __table_args__ = (
        Index("idx_tool_secrets_tool_id", "tool_id"),
        Index("idx_tool_secrets_active", "is_active", postgresql_where="is_active = true"),
        Index("idx_tool_secrets_secret_name", "secret_name"),
        CheckConstraint(
            "secret_type IN ('api_key', 'oauth_token', 'oauth_refresh_token', 'password', 'certificate', 'custom')",
            name="valid_secret_type",
        ),
    )

    # Relationships
    tool: Mapped[Tool] = relationship("Tool", back_populates="secrets")


class ToolHealthCheck(Base):  # type: ignore[valid-type,misc]
    """Tool health monitoring history."""

    __tablename__ = "tool_health_checks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Tool association
    tool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tools.id", ondelete="CASCADE"), nullable=False
    )

    # Health check results
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    response_time_ms: Mapped[float | None] = mapped_column()
    error_message: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(100))

    # Details
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=UTC), nullable=False
    )
    mcp_server_info: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Table configuration with indexes and constraints
    __table_args__ = (
        Index("idx_tool_health_tool_id", "tool_id"),
        Index(
            "idx_tool_health_checked_at",
            "checked_at",
            postgresql_ops={"checked_at": "DESC"},
        ),
        Index("idx_tool_health_status", "status"),
        CheckConstraint(
            "status IN ('online', 'offline', 'degraded', 'unknown')",
            name="valid_status",
        ),
    )

    # Relationships
    tool: Mapped[Tool] = relationship("Tool", back_populates="health_checks")


class ToolPermission(Base):  # type: ignore[valid-type,misc]
    """Role-based access control for tools."""

    __tablename__ = "tool_permissions"
    __table_args__ = (
        Index("idx_tool_permissions_tool_id", "tool_id"),
        Index("idx_tool_permissions_role", "role"),
        UniqueConstraint("tool_id", "role", name="uq_tool_permissions_tool_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Tool association
    tool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tools.id", ondelete="CASCADE"), nullable=False
    )

    # Role and permissions
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    can_view: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_use: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_configure: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Constraints
    max_calls_per_hour: Mapped[int | None] = mapped_column(Integer)
    max_calls_per_day: Mapped[int | None] = mapped_column(Integer)

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=UTC), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id, ondelete="SET NULL")
    )

    # Relationships
    tool: Mapped[Tool] = relationship("Tool", back_populates="permissions")


class ToolInvocation(Base):  # type: ignore[valid-type,misc]
    """Complete audit log of tool invocations."""

    __tablename__ = "tool_invocations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Tool and use case association
    tool_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tools.id", ondelete="SET NULL")
    )
    use_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("use_cases.id", ondelete="SET NULL")
    )

    # Request context
    run_id: Mapped[str | None] = mapped_column(String(255))
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id, ondelete="SET NULL")
    )
    center_id: Mapped[str | None] = mapped_column(String(255))

    # Invocation details
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tool_parameters: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Result
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    response_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)

    # Performance
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=UTC), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[float | None] = mapped_column()

    # Metadata
    mcp_protocol_version: Mapped[str | None] = mapped_column(String(20))
    cost_estimate: Mapped[float | None] = mapped_column()

    # Table configuration with indexes and constraints
    __table_args__ = (
        Index("idx_tool_invocations_tool_id", "tool_id"),
        Index("idx_tool_invocations_run_id", "run_id"),
        Index("idx_tool_invocations_user_id", "user_id"),
        Index(
            "idx_tool_invocations_started_at",
            "started_at",
            postgresql_ops={"started_at": "DESC"},
        ),
        Index(
            "idx_tool_invocations_center_id",
            "center_id",
            postgresql_where="center_id IS NOT NULL",
        ),
        Index("idx_tool_invocations_status", "status"),
        CheckConstraint(
            "status IN ('success', 'error', 'timeout', 'blocked', 'rate_limited')",
            name="valid_invocation_status",
        ),
    )

    # Relationships
    tool: Mapped[Tool | None] = relationship("Tool", back_populates="invocations")


class PricingTier(Base, TimestampMixin):  # type: ignore[valid-type,misc]
    """LLMaaS pricing tier definitions with rate limits and token pricing."""

    __tablename__ = "pricing_tiers"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Tier identification
    tier_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    tier_name: Mapped[str] = mapped_column(String(100), nullable=False)
    plan_size: Mapped[str] = mapped_column(String(10), nullable=False)  # "XS", "S", "M", "L", "XL"
    model_class: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "Large", "Small", "Codestral/Llama"

    # Pricing (per million tokens)
    input_rate_per_1m: Mapped[float] = mapped_column(nullable=False)  # e.g., 1.10 for XS|Large
    output_rate_per_1m: Mapped[float] = mapped_column(nullable=False)  # e.g., 0.30 for XS|Large

    # Rate limits
    rate_limit_tpm: Mapped[int] = mapped_column(Integer, nullable=False)  # Tokens per minute limit

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Metadata
    description: Mapped[str | None] = mapped_column(Text)

    # User tracking
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id, ondelete="SET NULL")
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id, ondelete="SET NULL")
    )

    # Table configuration
    __table_args__ = (
        Index("idx_pricing_tiers_active", "is_active"),
        Index("idx_pricing_tiers_plan_model", "plan_size", "model_class"),
        UniqueConstraint("plan_size", "model_class", name="unique_plan_model"),
    )

    # Relationships
    model_configs: Mapped[list[ModelConfig]] = relationship(
        "ModelConfig", back_populates="default_pricing_tier"
    )
    audit_entries: Mapped[list[PricingTierAudit]] = relationship(
        "PricingTierAudit", back_populates="pricing_tier"
    )


class ModelConfig(Base, TimestampMixin):  # type: ignore[valid-type,misc]
    """Model configurations with tokenizer settings and pricing tier associations."""

    __tablename__ = "model_configs"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Model identification
    model_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )  # e.g., "mistral-large-latest"
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)  # Display name
    model_provider: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "mistral", "openai", "meta"

    # Tokenizer configuration
    tokenizer_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "tiktoken", "sentencepiece", "huggingface"
    tokenizer_file_path: Mapped[str | None] = mapped_column(
        String(255)
    )  # Path to bundled tokenizer
    encoding_name: Mapped[str | None] = mapped_column(
        String(100)
    )  # e.g., "cl100k_base" for GPT models

    # Pricing tier association
    default_pricing_tier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pricing_tiers.id", ondelete="SET NULL")
    )

    # Capabilities
    supports_streaming: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_context_tokens: Mapped[int] = mapped_column(Integer, default=8192, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_available: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )  # Health check status

    # Metadata
    description: Mapped[str | None] = mapped_column(Text)

    # User tracking
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id, ondelete="SET NULL")
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(AuthUser.__table__.c.id, ondelete="SET NULL")
    )

    # Table configuration
    __table_args__ = (
        Index("idx_model_configs_active", "is_active"),
        Index("idx_model_configs_provider", "model_provider"),
    )

    # Relationships
    default_pricing_tier: Mapped[PricingTier | None] = relationship(
        "PricingTier", back_populates="model_configs"
    )


class PricingTierAudit(Base):  # type: ignore[valid-type,misc]
    """Audit trail for all pricing tier changes with user attribution."""

    __tablename__ = "pricing_tier_audit"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Audit details
    pricing_tier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pricing_tiers.id", ondelete="CASCADE"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "CREATE", "UPDATE", "DELETE", "ACTIVATE", "DEACTIVATE"
    changed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(AuthUser.__table__.c.id, ondelete="SET NULL"),
        nullable=False,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=UTC), nullable=False
    )

    # Snapshot of changes
    old_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    new_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    change_reason: Mapped[str | None] = mapped_column(Text)

    # Table configuration
    __table_args__ = (
        Index(
            "idx_pricing_audit_tier",
            "pricing_tier_id",
            "changed_at",
            postgresql_ops={"changed_at": "DESC"},
        ),
        Index(
            "idx_pricing_audit_action",
            "action",
            "changed_at",
            postgresql_ops={"changed_at": "DESC"},
        ),
        CheckConstraint(
            "action IN ('CREATE', 'UPDATE', 'DELETE', 'ACTIVATE', 'DEACTIVATE')",
            name="valid_audit_action",
        ),
    )

    # Relationships
    pricing_tier: Mapped[PricingTier] = relationship("PricingTier", back_populates="audit_entries")


class RunManifest(Base, TimestampMixin):  # type: ignore[valid-type,misc]
    """Run manifest model for stateless telemetry storage (ADR-030)."""

    __tablename__ = "run_manifests"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ts_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=UTC)
    )
    use_case_id: Mapped[str] = mapped_column(String, nullable=False)
    template_ver: Mapped[str] = mapped_column(String, nullable=False)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    params_hash: Mapped[str] = mapped_column(String, nullable=False)
    schema_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    conformance: Mapped[float] = mapped_column(
        String, nullable=False
    )  # Using String to match NUMERIC(4,3) in SQL
    tool_chain: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    idempotence_ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    latency_total_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_llm_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_tools_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False)
    result_kind: Mapped[str] = mapped_column(String, nullable=False)

    def __repr__(self) -> str:
        return f"<RunManifest(run_id={self.run_id}, use_case_id={self.use_case_id}, result_kind={self.result_kind})>"


class OutputTemplate(TimestampMixin, Base):  # type: ignore[valid-type,misc]
    """
    Custom output visualization template.

    Built-in templates live in the frontend TemplateRegistryService.
    Custom templates are persisted here and merged at runtime (ADR-066).
    """

    __tablename__ = "output_templates"
    __table_args__ = (UniqueConstraint("template_id", name="uq_output_templates_template_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    data_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    layout: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    export_formats: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(AuthUser.__table__.c.id, ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<OutputTemplate(template_id={self.template_id!r}, "
            f"name={self.name!r}, is_builtin={self.is_builtin})>"
        )


# Note: No logging statements are present in model definitions by default.
# If you need to log model events, use SQLAlchemy event listeners or custom methods.
