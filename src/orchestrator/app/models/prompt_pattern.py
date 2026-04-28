"""
SQLAlchemy model for Prompt Patterns.

Represents the prompt pattern library table for reusable prompt engineering patterns.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import TIMESTAMP, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db.database import Base


class PromptPattern(Base):
    """
    Prompt Pattern Library Model.

    Stores reusable prompt engineering patterns from promptingguide.ai
    that can be applied to use cases during creation.
    """

    __tablename__ = "prompt_patterns"

    # Primary Key
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Identification
    pattern_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Templates
    system_prompt_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    developer_prompt_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    fewshots_template: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=list, server_default="'[]'::jsonb"
    )

    # Metadata
    variables: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=list, server_default="'[]'::jsonb"
    )
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tags: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=list, server_default="'[]'::jsonb"
    )
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    # Sampling preset recommendation (ADR-023)
    recommended_preset: Mapped[str] = mapped_column(
        String(50), nullable=False, default="balanced", server_default="'balanced'"
    )
    max_tokens_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    special_params: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="'{}'::jsonb"
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        """String representation."""
        return f"<PromptPattern(pattern_id='{self.pattern_id}', name='{self.name}', category='{self.category}')>"
