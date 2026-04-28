"""
RBAC V2 Database Models

Additional models for RBAC V2 two-tier role system with team isolation.
Implements ADR-060 access control architecture.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    UUID,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.auth.models import User as AuthUser

from .database import Base
from .models import TimestampMixin


class RoleCollectionAssignment(TimestampMixin, Base):  # type: ignore[valid-type,misc]
    """
    Assigns document collections to roles.

    Users inherit collection access through role memberships.
    Implements ADR-060 Tier 2 resource access control.

    Note: Collections table is in corpus_svc, but this assignment table
    is in orchestrator for RBAC access control.
    """

    __tablename__ = "role_collection_assignments"
    __table_args__ = (
        UniqueConstraint("role_name", "collection_id", name="uq_role_collection_assignment"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    role_name: Mapped[str] = mapped_column(String(50), nullable=False)

    collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Audit fields
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(AuthUser.__table__.c.id),
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Metadata
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )
